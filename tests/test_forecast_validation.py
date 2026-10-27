"""Forecast direction, model-selection integrity, and output traceability.

The dashboard must never show a number that cannot be traced to a file, the
forecast must never land on a date the dataset already covers, and -- since
2026-10-27 -- the model must be chosen by cross-validation, never by the test
window. The selection tests below replaced eight tests that asserted the OLD
rule ("best = lowest test RMSE"); they are stricter, not looser: the central
one proves that changing the test numbers alone cannot change the selection.
"""
import numpy as np
import pandas as pd
import pytest

from src import config
from src.evaluate import _select
from src.forecast import _rule_based_trend

MODELS = ("Naive", "ARIMA", "RandomForest", "GradientBoosting")


# --------------------------------------------------- CV-based selection
def _comparison(cv_rmse, test_rmse, test_mae=None):
    """Synthetic comparison table: one CV ('valid') row and one test row
    per model, at h=1, for one pair."""
    test_mae = test_mae or {m: v / 2 for m, v in test_rmse.items()}
    rows = []
    for model in cv_rmse:
        common = {"commodity": "Onion", "market": "Jaipur", "horizon": 1,
                  "model": model, "mape": 5.0, "r2": 0.8, "converged": True}
        rows.append({**common, "split": "valid", "n": 400,
                     "rmse": cv_rmse[model] * 1.1, "mae": cv_rmse[model] / 2,
                     "cv_mean_fold_rmse": cv_rmse[model]})
        rows.append({**common, "split": "test", "n": 200,
                     "rmse": test_rmse[model], "mae": test_mae[model],
                     "cv_mean_fold_rmse": np.nan})
    return pd.DataFrame(rows)


def test_selection_follows_cv_not_test():
    """THE guarantee. CV prefers ARIMA, test would prefer GradientBoosting:
    the reported model must be ARIMA, and the disagreement must be flagged."""
    comp = _comparison(
        cv_rmse={"Naive": 100.0, "ARIMA": 80.0, "RandomForest": 95.0,
                 "GradientBoosting": 90.0},
        test_rmse={"Naive": 100.0, "ARIMA": 99.0, "RandomForest": 98.0,
                   "GradientBoosting": 70.0})
    best = _select(comp)
    assert best["best_model"].iloc[0] == "ARIMA"
    assert best["posthoc_lowest_test_rmse_model"].iloc[0] == "GradientBoosting"
    assert not bool(best["selection_confirmed_by_test"].iloc[0])
    assert best["selection_split"].iloc[0] == "rolling_origin_cv"
    assert best["selection_metric"].iloc[0] == "mean_fold_rmse"


def test_changing_only_test_numbers_never_changes_the_selection():
    """Invariance: shuffle every test score; the selection cannot move."""
    cv = {"Naive": 100.0, "ARIMA": 90.0, "RandomForest": 95.0,
          "GradientBoosting": 99.0}
    rng = np.random.default_rng(7)
    picks = set()
    for _ in range(25):
        test = {m: float(rng.uniform(50, 150)) for m in MODELS}
        picks.add(_select(_comparison(cv, test))["best_model"].iloc[0])
    assert picks == {"ARIMA"}


def test_reported_test_rmse_is_the_selected_models_not_the_minimum():
    comp = _comparison(
        cv_rmse={"Naive": 100.0, "ARIMA": 80.0, "RandomForest": 95.0,
                 "GradientBoosting": 90.0},
        test_rmse={"Naive": 100.0, "ARIMA": 99.0, "RandomForest": 98.0,
                   "GradientBoosting": 70.0})
    best = _select(comp)
    assert best["best_test_rmse"].iloc[0] == pytest.approx(99.0)     # ARIMA's
    assert best["posthoc_lowest_test_rmse"].iloc[0] == pytest.approx(70.0)
    assert best["selected_valid_rmse"].iloc[0] == pytest.approx(80.0)


def test_selection_changes_when_the_cv_measurements_change():
    """Proves selection is computed, not hardcoded."""
    test = {m: 100.0 for m in MODELS}
    a = _select(_comparison({"Naive": 100.0, "ARIMA": 90.0, "RandomForest": 95.0,
                             "GradientBoosting": 99.0}, test))
    b = _select(_comparison({"Naive": 100.0, "ARIMA": 99.0, "RandomForest": 95.0,
                             "GradientBoosting": 90.0}, test))
    assert a["best_model"].iloc[0] == "ARIMA"
    assert b["best_model"].iloc[0] == "GradientBoosting"


def test_naive_is_selected_when_it_has_the_lowest_cv_rmse():
    """No thumb on the scale for the ML models."""
    best = _select(_comparison(
        {"Naive": 80.0, "ARIMA": 95.0, "RandomForest": 90.0, "GradientBoosting": 85.0},
        {"Naive": 100.0, "ARIMA": 95.0, "RandomForest": 90.0, "GradientBoosting": 85.0}))
    assert best["best_model"].iloc[0] == "Naive"
    assert not bool(best["beats_naive"].iloc[0])
    assert best["improvement_over_naive_pct"].iloc[0] == pytest.approx(0.0)


def test_beats_naive_is_judged_on_test_for_the_selected_model():
    """CV liked ARIMA, but on test ARIMA is worse than Naive: report that."""
    best = _select(_comparison(
        {"Naive": 100.0, "ARIMA": 80.0, "RandomForest": 95.0, "GradientBoosting": 99.0},
        {"Naive": 90.0, "ARIMA": 95.0, "RandomForest": 99.0, "GradientBoosting": 99.0}))
    assert best["best_model"].iloc[0] == "ARIMA"
    assert not bool(best["beats_naive"].iloc[0])
    assert best["improvement_over_naive_pct"].iloc[0] < 0


def test_improvement_percentage_is_arithmetically_correct():
    best = _select(_comparison(
        {"Naive": 100.0, "ARIMA": 110.0, "RandomForest": 110.0, "GradientBoosting": 90.0},
        {"Naive": 100.0, "ARIMA": 110.0, "RandomForest": 110.0, "GradientBoosting": 90.0}))
    # (100 - 90) / 100 = 10%
    assert best["improvement_over_naive_pct"].iloc[0] == pytest.approx(10.0)


def test_metric_disagreement_is_detected_and_reported():
    comp = _comparison(
        cv_rmse={"Naive": 94.0, "ARIMA": 96.0, "RandomForest": 93.0,
                 "GradientBoosting": 87.0},
        test_rmse={"Naive": 94.0, "ARIMA": 96.0, "RandomForest": 93.0,
                   "GradientBoosting": 87.0},
        test_mae={"Naive": 39.0, "ARIMA": 47.0, "RandomForest": 58.0,
                  "GradientBoosting": 50.0})
    best = _select(comp)
    assert best["best_model"].iloc[0] == "GradientBoosting"
    assert best["lowest_mae_model"].iloc[0] == "Naive"
    assert not bool(best["metrics_agree"].iloc[0])


def test_metrics_agree_flag_is_true_when_one_model_wins_both():
    comp = _comparison(
        cv_rmse={"Naive": 100.0, "ARIMA": 99.0, "RandomForest": 98.0,
                 "GradientBoosting": 90.0},
        test_rmse={"Naive": 100.0, "ARIMA": 99.0, "RandomForest": 98.0,
                   "GradientBoosting": 90.0},
        test_mae={"Naive": 60.0, "ARIMA": 58.0, "RandomForest": 55.0,
                  "GradientBoosting": 40.0})
    assert bool(_select(comp)["metrics_agree"].iloc[0])


def test_models_without_a_finite_cv_score_are_excluded_from_selection():
    comp = _comparison({"Naive": 100.0, "GradientBoosting": 90.0},
                       {"Naive": 100.0, "GradientBoosting": 90.0})
    comp.loc[(comp["model"] == "GradientBoosting")
             & (comp["split"] == "valid"), "cv_mean_fold_rmse"] = np.nan
    assert _select(comp)["best_model"].iloc[0] == "Naive"


# ------------------------------------------------------- trend note rules
def test_trend_note_is_deterministic_and_directional():
    up = _rule_based_trend(100.0, 130.0, 100.0)
    down = _rule_based_trend(100.0, 70.0, 100.0)
    flat = _rule_based_trend(100.0, 100.2, 100.0)
    assert "higher" in up and "sharply" in up
    assert "lower" in down and "sharply" in down
    assert "flat" in flat
    assert _rule_based_trend(100.0, 130.0, 100.0) == up      # no randomness
    for note in (up, down, flat):
        assert "not advice" in note


def test_trend_note_handles_a_missing_forecast():
    assert "No forecast" in _rule_based_trend(100.0, float("nan"), 100.0)


# ------------------------------------------- forecast dates / traceability
def test_forecast_dates_are_strictly_after_the_last_observed_date():
    """Run against real generated output if it exists; skip if not built."""
    fc_path = config.OUTPUTS / "forecast.csv"
    feat_path = config.FEATURES_PATH
    if not fc_path.exists():
        pytest.skip("outputs/forecast.csv not built yet")
    from src.features import load_features
    fc = pd.read_csv(fc_path)
    last = load_features()["date"].max()
    assert not fc.empty
    for d in pd.to_datetime(fc["forecast_date"]):
        assert d > last, f"forecast for {d.date()} is not after {last.date()}"


def test_forecast_horizon_offsets_match_the_configured_horizons():
    fc_path = config.OUTPUTS / "forecast.csv"
    if not fc_path.exists():
        pytest.skip("outputs/forecast.csv not built yet")
    fc = pd.read_csv(fc_path)
    for r in fc.itertuples():
        gap = (pd.Timestamp(r.forecast_date) - pd.Timestamp(r.from_date)).days
        assert gap == r.horizon, f"h={r.horizon} forecast is {gap} days out"


def test_every_dashboard_headline_number_exists_in_an_output_file():
    """Traceability: the app reads files, it does not compute its own figures."""
    needed = ["best_model.csv", "model_comparison.csv", "predictions.csv",
              "forecast.csv", "feature_importance.csv"]
    missing = [f for f in needed if not (config.OUTPUTS / f).exists()]
    if missing:
        pytest.skip(f"outputs not built yet: {missing}")

    best = pd.read_csv(config.OUTPUTS / "best_model.csv")
    comp = pd.read_csv(config.OUTPUTS / "model_comparison.csv")
    test = comp[comp["split"] == "test"]
    for r in best.itertuples():
        # Match on the FULL key. Matching on (horizon, model) alone passed
        # while there was one pair and silently cross-matched pairs once a
        # second was added -- caught when Tomato/Jaipur joined.
        match = test[(test["commodity"] == r.commodity)
                     & (test["market"] == r.market)
                     & (test["horizon"] == r.horizon)
                     & (test["model"] == r.best_model)]
        assert len(match) == 1, f"{r.commodity}/{r.market} h={r.horizon}: {len(match)} rows"
        assert not match.empty, f"best model for h={r.horizon} is not in the table"
        assert float(match["rmse"].iloc[0]) == pytest.approx(r.best_test_rmse)
        assert float(match["n"].iloc[0]) == r.n_test


def test_all_models_scored_on_identical_cv_and_test_rows():
    path = config.OUTPUTS / "model_comparison.csv"
    if not path.exists():
        pytest.skip("outputs/model_comparison.csv not built yet")
    comp = pd.read_csv(path)
    for split in ("valid", "test"):
        part = comp[comp["split"] == split]
        assert not part.empty, f"no {split} rows in model_comparison.csv"
        for (_, _, h), g in part.groupby(["commodity", "market", "horizon"]):
            assert g["n"].nunique() == 1, (
                f"{split} h={h}: models scored on different row counts "
                f"{sorted(g['n'])}")
            from src.models import CANDIDATE_NAMES
            assert set(g["model"]) == set(CANDIDATE_NAMES), (
                f"{split} h={h}: candidate set incomplete: {sorted(g['model'])}")


def test_generated_selection_is_reproducible_from_the_cv_folds_file():
    """best_model.csv must be re-derivable from cv_folds.csv alone."""
    need = ["best_model.csv", "cv_folds.csv"]
    if any(not (config.OUTPUTS / f).exists() for f in need):
        pytest.skip("outputs not built yet")
    best = pd.read_csv(config.OUTPUTS / "best_model.csv")
    folds = pd.read_csv(config.OUTPUTS / "cv_folds.csv")
    for r in best.itertuples():
        g = folds[(folds["commodity"] == r.commodity)
                  & (folds["market"] == r.market) & (folds["horizon"] == r.horizon)]
        mean = g.groupby("model")["rmse"].mean()
        assert mean.idxmin() == r.best_model
        assert mean.min() == pytest.approx(r.selected_valid_rmse)
