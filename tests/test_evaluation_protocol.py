"""Guarantees of the evaluation protocol (added 2026-10-27).

Every test here asserts a property that, if broken, would make a reported
number wrong -- not merely that a function runs. Synthetic inputs are used
where the correct answer must be known in advance; the last group runs on the
real generated outputs and skips if they have not been built.
"""
import numpy as np
import pandas as pd
import pytest

from src import config
from src.metrics import all_metrics, mae, mape, r2, rmse
from src.models import ArimaModel, TreeModel
from src.splits import (purge_target_overlap, rolling_origin_folds,
                        split_by_date, split_train_valid_test)


def _frame(n=400, start="2020-01-01", gap_every=None):
    dates = pd.date_range(start, periods=n, freq="D")
    if gap_every:
        dates = dates[np.arange(n) % gap_every != 0]
    price = 1000.0 + np.arange(len(dates), dtype=float)
    df = pd.DataFrame({"date": dates, "price_t": price})
    for h in (1, 2, 3):
        df[f"y_h{h}"] = price + h
        df[f"y_h{h}_observed"] = True
    return df


# ---------------------------------------------------------------- embargo
@pytest.mark.parametrize("h", [1, 2, 3])
def test_split_by_date_with_horizon_keeps_every_training_target_before_cutoff(h):
    tr, te, cut = split_by_date(_frame(), 0.2, horizon=h)
    assert ((tr["date"] + pd.Timedelta(days=h)) < cut).all()
    assert tr["date"].max() < te["date"].min()


@pytest.mark.parametrize("h", [1, 2, 3])
def test_without_the_embargo_the_defect_is_real(h):
    """Documents the bug that was fixed: the old split let h rows through."""
    tr, _, cut = split_by_date(_frame(), 0.2)                 # no horizon
    crossing = int(((tr["date"] + pd.Timedelta(days=h)) >= cut).sum())
    assert crossing == h


def test_purge_drops_exactly_the_rows_whose_target_reaches_the_cutoff():
    df = _frame(20)
    cut = df["date"].iloc[10]
    kept = purge_target_overlap(df[df["date"] < cut], 3, cut)
    assert len(kept) == 7                                   # rows 0..6
    assert ((kept["date"] + pd.Timedelta(days=3)) < cut).all()


@pytest.mark.parametrize("h", [1, 3])
def test_three_way_split_embargoes_both_boundaries(h):
    tr, va, te, cv, ct = split_train_valid_test(_frame(500), h)
    assert ((tr["date"] + pd.Timedelta(days=h)) < cv).all()
    assert ((va["date"] + pd.Timedelta(days=h)) < ct).all()
    assert tr["date"].max() < va["date"].min() <= va["date"].max() < te["date"].min()


# --------------------------------------------------------- rolling origin
@pytest.mark.parametrize("h", [1, 2, 3])
def test_rolling_origin_folds_never_fit_on_or_past_their_own_origin(h):
    dev = _frame(500, gap_every=7)                           # weekly closure
    folds = rolling_origin_folds(dev, h, n_folds=4, initial_fraction=0.5)
    assert len(folds) == 4
    for fd in folds:
        assert fd["fit"]["date"].max() < fd["origin"]
        assert ((fd["fit"]["date"] + pd.Timedelta(days=h)) < fd["origin"]).all()
        assert fd["val"]["date"].min() >= fd["origin"]


def test_rolling_origin_folds_expand_and_tile_the_validation_period():
    dev = _frame(400)
    folds = rolling_origin_folds(dev, 1, n_folds=4, initial_fraction=0.5)
    sizes = [len(f["fit"]) for f in folds]
    assert sizes == sorted(sizes) and len(set(sizes)) == 4  # strictly expanding
    val = pd.concat([f["val"] for f in folds])
    assert val["date"].is_unique                            # no overlap
    assert len(val) == 200                                  # covers the back half
    for a, b in zip(folds, folds[1:]):
        assert a["val"]["date"].max() < b["val"]["date"].min()


def test_rolling_origin_rejects_too_few_dates():
    with pytest.raises(ValueError):
        rolling_origin_folds(_frame(40), 1, n_folds=4, initial_fraction=0.5)


# ------------------------------------------------------- ARIMA diagnostic
def _random_walk(n=500, seed=3):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2018-01-01", periods=n, freq="D")
    return pd.Series(1000 + np.cumsum(rng.normal(0, 10, n)), index=idx)


@pytest.mark.parametrize("h", [1, 3])
def test_arima_training_diagnostic_covers_the_training_window(h):
    """Regression test for the n=1 defect."""
    s = _random_walk()
    train_end = s.index[399]
    rows = pd.DataFrame({"date": s.index[:400]})
    m = ArimaModel(h).prepare(s, train_end, fixed_order=(1, 1, 0))
    m.fit(rows, [], "y")
    pred = m.predict(rows, [])
    n_finite = int(np.isfinite(pred).sum())
    burn = config.ARIMA_INSAMPLE_BURN_IN
    assert n_finite >= 400 - burn - h - 1, f"only {n_finite} train predictions"
    assert "in-sample" in m._insample_status


def test_arima_training_predictions_use_only_past_data():
    """Perturbing prices AFTER an origin must not move that origin's forecast."""
    s = _random_walk()
    train_end = s.index[399]
    rows = pd.DataFrame({"date": s.index[100:110]})
    a = ArimaModel(1).prepare(s, train_end, fixed_order=(1, 1, 0))
    a.fit(rows, [], "y")
    s2 = s.copy()
    s2.iloc[111:400] += 500.0          # rows' targets end at index 110
    b = ArimaModel(1).prepare(s2, train_end, fixed_order=(1, 1, 0))
    # The order is fixed and its parameters come from fitting the TRAINING
    # window, which the perturbation changes -- so fix those too, to isolate
    # the conditioning property under test.
    b.fit(rows, [], "y")
    from statsmodels.tsa.arima.model import ARIMA
    params = ARIMA(s.loc[:train_end], order=(1, 1, 0), enforce_stationarity=False,
                   enforce_invertibility=False).fit().params
    a._build_insample_cache(type("R", (), {"params": params})())
    b._build_insample_cache(type("R", (), {"params": params})())
    np.testing.assert_allclose(a.predict(rows, []), b.predict(rows, []))


def test_arima_test_window_forecasts_are_unchanged_by_the_diagnostic():
    s = _random_walk()
    train_end = s.index[399]
    rows = pd.DataFrame({"date": s.index[400:480]})
    with_diag = ArimaModel(2).prepare(s, train_end, fixed_order=(1, 1, 1))
    with_diag.fit(rows, [], "y")
    no_diag = ArimaModel(2).prepare(s, train_end, insample=False,
                                    fixed_order=(1, 1, 1))
    no_diag.fit(rows, [], "y")
    np.testing.assert_array_equal(with_diag.predict(rows, []),
                                  no_diag.predict(rows, []))


def test_arima_walk_end_truncates_without_changing_earlier_forecasts():
    s = _random_walk()
    train_end = s.index[299]
    rows = pd.DataFrame({"date": s.index[300:350]})
    full = ArimaModel(1).prepare(s, train_end, insample=False, fixed_order=(1, 1, 0))
    full.fit(rows, [], "y")
    short = ArimaModel(1).prepare(s, train_end, walk_end=s.index[349],
                                  insample=False, fixed_order=(1, 1, 0))
    short.fit(rows, [], "y")
    np.testing.assert_array_equal(full.predict(rows, []), short.predict(rows, []))
    later = pd.DataFrame({"date": s.index[380:390]})
    assert np.isnan(short.predict(later, [])).all()


# ------------------------------------------------------ delta-target trees
def test_delta_trees_can_predict_above_their_training_maximum():
    """Why the experiment exists: level trees are capped, delta trees are not."""
    tr = _frame(300)
    cols = ["price_t"]
    hi = pd.DataFrame({"price_t": [5000.0]})
    level = TreeModel("rf").fit(tr, cols, "y_h1").predict(hi, cols)[0]
    delta = TreeModel("rf", "delta").fit(tr, cols, "y_h1").predict(hi, cols)[0]
    assert level <= tr["y_h1"].max() + 1e-9
    assert delta > 4990


def test_default_tree_target_mode_is_unchanged():
    assert TreeModel("rf").name == "RandomForest"
    assert TreeModel("gbm").name == "GradientBoosting"
    with pytest.raises(ValueError):
        TreeModel("rf", "log")


# --------------------------------------------------------- metric safety
def test_metrics_are_nan_not_zero_when_there_is_nothing_to_score():
    for f in (mae, rmse, mape, r2):
        assert np.isnan(f([], []))
        assert np.isnan(f([np.nan], [1.0]))


def test_r2_is_undefined_for_one_point_or_constant_truth():
    assert np.isnan(r2([5.0], [4.0]))
    assert np.isnan(r2([5.0, 5.0, 5.0], [4.0, 5.0, 6.0]))


def test_mape_skips_near_zero_actuals_rather_than_exploding():
    assert mape([0.0, 100.0], [50.0, 110.0]) == pytest.approx(10.0)
    assert np.isnan(mape([0.0, 0.5], [1.0, 1.0]))


def test_all_metrics_reports_the_finite_pair_count():
    out = all_metrics([1.0, 2.0, np.nan, 4.0], [1.0, np.nan, 3.0, 5.0])
    assert out["n"] == 2


# ------------------------------------------------ real generated outputs
def _need(*files):
    missing = [f for f in files if not (config.OUTPUTS / f).exists()]
    if missing:
        pytest.skip(f"outputs not built yet: {missing}")


def test_real_outputs_arima_train_rows_have_a_real_sample():
    _need("model_comparison.csv")
    comp = pd.read_csv(config.OUTPUTS / "model_comparison.csv")
    a = comp[(comp["model"] == "ARIMA") & (comp["split"] == "train")]
    assert not a.empty
    assert (a["n"] >= 100).all(), a[["horizon", "n"]].to_string()


def test_real_outputs_every_row_says_what_it_measures():
    _need("model_comparison.csv")
    comp = pd.read_csv(config.OUTPUTS / "model_comparison.csv")
    allowed = {"in_sample_fit", "in_sample_h_step", "in_sample_period_property",
               "out_of_sample_cv_selection", "out_of_sample_final"}
    assert set(comp["diagnostic"]) <= allowed
    naive_train = comp[(comp["model"] == "Naive") & (comp["split"] == "train")]
    assert not naive_train["comparable_train_gap"].astype(bool).any()


def test_real_outputs_fold_and_test_boundaries_respect_the_embargo():
    _need("cv_folds.csv", "split_boundaries.csv")
    folds = pd.read_csv(config.OUTPUTS / "cv_folds.csv")
    for r in folds.itertuples():
        assert pd.Timestamp(r.fit_end) + pd.Timedelta(days=r.horizon) < pd.Timestamp(r.origin)
        assert pd.Timestamp(r.val_start) >= pd.Timestamp(r.origin)
    b = pd.read_csv(config.OUTPUTS / "split_boundaries.csv")
    for r in b.itertuples():
        assert pd.Timestamp(r.train_end) + pd.Timedelta(days=r.horizon) < pd.Timestamp(r.cut_test)
        assert pd.Timestamp(r.cv_end) < pd.Timestamp(r.test_start)


def test_real_outputs_prediction_dates_fall_inside_their_declared_split():
    _need("predictions.csv", "split_boundaries.csv")
    p = pd.read_csv(config.OUTPUTS / "predictions.csv", parse_dates=["date"])
    b = pd.read_csv(config.OUTPUTS / "split_boundaries.csv")
    for r in b.itertuples():
        g = p[(p["horizon"] == r.horizon) & (p["commodity"] == r.commodity)
              & (p["market"] == r.market)]
        t = g[g["split"] == "test"]["date"]
        v = g[g["split"] == "valid"]["date"]
        assert t.min() >= pd.Timestamp(r.test_start)
        assert v.max() <= pd.Timestamp(r.cv_end) < pd.Timestamp(r.test_start)


# ------------------------------------------------------ empirical ranges
def _ivl_inputs(cv_resid, test_resid):
    from src.intervals import empirical_intervals
    rows = []
    for split, res in (("valid", cv_resid), ("test", test_resid)):
        for i, e in enumerate(res):
            rows.append({"commodity": "Onion", "market": "Jaipur", "horizon": 1,
                         "model": "Naive", "split": split, "date": i,
                         "y_true": 1000.0 + e, "y_pred": 1000.0})
    best = pd.DataFrame([{"commodity": "Onion", "market": "Jaipur",
                          "horizon": 1, "best_model": "Naive"}])
    return empirical_intervals(pd.DataFrame(rows), best).iloc[0]


def test_range_is_calibrated_on_cv_only_and_checked_on_test():
    rng = np.random.default_rng(0)
    r = _ivl_inputs(rng.normal(0, 10, 400), rng.normal(0, 10, 400))
    assert r["interval_held_up"]
    assert 70 <= r["interval_test_coverage"] <= 90


def test_range_that_fails_on_test_is_reported_as_failed():
    rng = np.random.default_rng(0)
    r = _ivl_inputs(rng.normal(0, 10, 400), rng.normal(0, 40, 400))  # volatility jump
    assert not r["interval_held_up"]
    assert r["interval_test_coverage"] < 70
    assert "did NOT hold up" in r["interval_status"]


def test_zero_width_range_is_flagged_degenerate_never_held_up():
    r = _ivl_inputs(np.zeros(400), np.zeros(400))      # 100% "coverage"
    assert r["interval_test_coverage"] == 100.0
    assert not r["interval_held_up"]
    assert "degenerate" in r["interval_status"]


def test_range_needs_enough_calibration_residuals():
    r = _ivl_inputs(np.zeros(10), np.zeros(100))
    assert not r["interval_held_up"] and "unavailable" in r["interval_status"]
