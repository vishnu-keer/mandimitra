"""Phase 2: features -> five candidate models -> honest comparison -> forward forecast.

    python scripts/run_pipeline.py
    python scripts/run_pipeline.py --commodity Onion --market Jaipur
    python scripts/run_pipeline.py --all-pairs

Protocol: select by rolling-origin CV inside the development block, refit on
the whole development block, report on test once.
See src/evaluate.py for why, and outputs/legacy/README.md for what changed.

Writes to outputs/:
    model_comparison.csv    every model x horizon x split, same rows per split
    predictions.csv         per-row actual vs predicted, valid and test
    feature_importance.csv  tree-model importances
    best_model.csv          CV-selected model per horizon + its test score
    cv_folds.csv            every CV fold x model, with fold dates
    split_boundaries.csv    the exact train/valid/test dates behind every row
    forecast.csv            forward forecast + plain-language trend note

Exits non-zero if the Phase 2 gate fails.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from src import config
from src.data_prep import load_clean
from src.evaluate import evaluate_pair
from src.features import load_features
from src.forecast import forecast_forward
from src.intervals import empirical_intervals
from src.models import CANDIDATE_NAMES
from src.splits import rolling_origin_folds, split_by_date, usable_mask

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 40)


def rule(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def _run_pair(job):
    """Evaluate + forecast one pair. Top-level so it can run in a worker
    process. Each pair is independent and every model is seeded, so running
    pairs in parallel produces exactly the same numbers as running them in
    sequence (verified: see docs/TEST_REPORT.md)."""
    commodity, market, test_fraction, folds = job
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    feats, clean = load_features(), load_clean()
    try:
        res = evaluate_pair(feats, clean, commodity, market,
                            test_fraction=test_fraction, n_folds=folds)
    except ValueError as exc:
        # An evaluation-stage failure (e.g. too few rows every model could
        # score). Reported, not hidden, and never replaced by a made-up result.
        return {"failed": True, "commodity": commodity, "market": market,
                "reason": f"evaluation gate: {exc}"}
    fc = forecast_forward(feats, clean, commodity, market,
                          res["best"], res["feature_cols"])
    res.pop("fitted", None); res.pop("pair_rows", None)
    res["forecast"] = fc
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commodity", default=None)
    ap.add_argument("--market", default=None)
    ap.add_argument("--all-pairs", action="store_true")
    ap.add_argument("--folds", type=int, default=config.CV_FOLDS)
    ap.add_argument("--jobs", type=int, default=None,
                    help="worker processes (default: one per pair, capped at CPU count)")
    ap.add_argument("--test-fraction", type=float, default=config.TEST_FRACTION)
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    feats = load_features()
    clean = load_clean()

    pairs = list(feats[config.GROUP_KEYS].drop_duplicates()
                 .itertuples(index=False, name=None))
    if not args.all_pairs:
        if args.commodity or args.market:
            pairs = [p for p in pairs
                     if (args.commodity is None or p[0] == args.commodity.title())
                     and (args.market is None or p[1] == args.market.title())]
        else:
            pairs = pairs[:1]
    if not pairs:
        print("No matching (commodity, market) pair in features.")
        return 1

    # Data gate, applied BEFORE any model sees the pair. A pair below the gate
    # is reported with its numbers and excluded -- never forced through, and
    # the gate is never lowered to admit it.
    excluded = []
    eligible = []
    for c, m in pairs:
        g = feats[(feats["commodity"] == c) & (feats["market"] == m)]
        usable = {h: int(usable_mask(g, h).sum()) for h in config.HORIZONS}
        if max(usable.values()) < config.MIN_ROWS_PER_PAIR:
            excluded.append({
                "commodity": c, "market": m, "horizon": "all",
                "reason": (f"data gate: {max(usable.values())} usable rows at best "
                           f"(h1={usable[1]}, h2={usable[2]}, h3={usable[3]}); "
                           f"gate is {config.MIN_ROWS_PER_PAIR}")})
        else:
            eligible.append((c, m))
    if excluded:
        rule("0. PAIRS EXCLUDED BY THE DATA GATE  (not evaluated)")
        for e in excluded:
            print(f"  {e['commodity']}/{e['market']}: {e['reason']}")
    pairs = eligible
    if not pairs:
        print("\n  No pair passes the data gate. Nothing to evaluate.")
        return 1

    all_comp, all_pred, all_imp, all_best = [], [], [], []
    all_fc, all_bounds, all_skip, all_folds = [], [], [], []

    jobs = [(c, m, args.test_fraction, args.folds) for c, m in pairs]
    n_workers = args.jobs or min(len(jobs), os.cpu_count() or 1)
    if n_workers > 1:
        with ProcessPoolExecutor(max_workers=n_workers) as ex:
            results = list(ex.map(_run_pair, jobs))       # order preserved
    else:
        results = [_run_pair(j) for j in jobs]

    for (commodity, market), res in zip(pairs, results):
        if res.get("failed"):
            excluded.append({"commodity": commodity, "market": market,
                             "horizon": "all", "reason": res["reason"]})
            print(f"\n  {commodity}/{market} EXCLUDED: {res['reason']}")
            continue
        rule(f"1. SPLIT  -  {commodity} / {market}  "
             f"(development | test, embargoed; CV folds inside development)")
        pair = feats[(feats["commodity"] == commodity)
                     & (feats["market"] == market)]
        for h in config.HORIZONS:
            u = pair[usable_mask(pair, h)]
            if len(u) < config.MIN_ROWS_PER_PAIR:
                print(f"  h={h}: {len(u)} usable rows -- below "
                      f"{config.MIN_ROWS_PER_PAIR}, will be skipped")
                continue
            dev, te, ct = split_by_date(u, args.test_fraction, horizon=h)
            print(f"  h={h}: usable={len(u):4d}  "
                  f"dev={len(dev):4d} ({dev['date'].min().date()} -> {dev['date'].max().date()})  "
                  f"test={len(te):4d} ({te['date'].min().date()} -> {te['date'].max().date()})")
            for fd in rolling_origin_folds(dev, h, args.folds):
                print(f"         fold {fd['fold']}: fit {len(fd['fit']):4d} rows -> "
                      f"{fd['fit']['date'].max().date()} | score {len(fd['val']):3d} rows "
                      f"{fd['val']['date'].min().date()} -> {fd['val']['date'].max().date()}")

        rule(f"2. MODEL COMPARISON  -  {commodity} / {market}")
        show = res["comparison"].copy()
        for c in ("mae", "rmse", "mape", "r2"):
            show[c] = show[c].round(2)
        print(show[["horizon", "model", "split", "diagnostic", "n",
                    "mae", "rmse", "mape", "r2", "converged"]]
              .to_string(index=False))
        print("\n  diagnostic column:")
        print("    in_sample_fit             tree model scored on its own training rows")
        print("    in_sample_h_step          ARIMA, training-window parameters,")
        print("                              each forecast conditioned on data up to t")
        print("    in_sample_period_property Naive. It fits nothing, so this measures")
        print("                              how calm the training period was, NOT")
        print("                              memorisation. Excluded from the gap table.")
        print("    out_of_sample_cv_selection pooled CV folds -- this chose the model")
        print("    out_of_sample_final       test window -- scored once, after selection")

        rule("3. CV FOLDS  (RMSE per fold; selection = lowest MEAN of these)")
        fr = res["cv_folds"]
        piv = fr.pivot_table(index=["horizon", "fold"], columns="model",
                             values="rmse").round(1)
        meta = fr.groupby(["horizon", "fold"])[["val_start", "val_end",
                                                "fit_target_max",
                                                "val_target_max"]].first()
        print(piv.join(meta).to_string())

        rule("3b. SELECTED MODEL PER HORIZON  (lowest mean per-fold CV RMSE)")
        cols = ["horizon", "best_model", "selected_valid_rmse", "n_valid",
                "best_test_rmse", "best_test_mae", "n_test",
                "naive_test_rmse", "improvement_over_naive_pct", "beats_naive",
                "posthoc_lowest_test_rmse_model", "selection_confirmed_by_test"]
        print(res["best"][cols].to_string(index=False))

        if not res["importance"].empty:
            rule("4. FEATURE IMPORTANCE (top 8, tree models)")
            imp = (res["importance"].groupby(["horizon", "model", "feature"])
                   ["importance"].mean().reset_index())
            for (h, m), g in imp.groupby(["horizon", "model"]):
                print(f"\n  h={h}  {m}")
                for r in g.nlargest(8, "importance").itertuples():
                    print(f"    {r.feature:<16} {r.importance:6.3f}  "
                          f"{'#' * max(1, int(r.importance * 40))}")

        rule(f"5. FORWARD FORECAST  -  {commodity} / {market}")
        fc = res["forecast"]
        ivl = empirical_intervals(res["predictions"], res["best"])
        res["best"] = res["best"].merge(
            ivl, on=["commodity", "market", "horizon"], how="left")
        if not fc.empty:
            fc = fc.merge(ivl[["commodity", "market", "horizon",
                               "interval_level", "interval_lo_offset",
                               "interval_hi_offset", "interval_test_coverage",
                               "interval_held_up"]],
                          on=["commodity", "market", "horizon"], how="left")
            fc["range_low"] = (fc["predicted_price"] + fc["interval_lo_offset"]).round(2)
            fc["range_high"] = (fc["predicted_price"] + fc["interval_hi_offset"]).round(2)
        if fc.empty:
            print("  no forecast produced")
        else:
            print(fc[["horizon", "model", "from_date", "forecast_date",
                      "last_reported_price", "predicted_price"]]
                  .to_string(index=False))
            print("\n  " + fc["trend_note"].iloc[0])
            print("\n  80% empirical range (calibrated on CV residuals, checked on test):")
            for r in fc.itertuples():
                print(f"    h={r.horizon}: Rs.{r.range_low:,.0f} - Rs.{r.range_high:,.0f}  "
                      f"test coverage {r.interval_test_coverage}%  "
                      f"{'held up' if r.interval_held_up else 'DID NOT HOLD UP'}")

        all_comp.append(res["comparison"]); all_pred.append(res["predictions"])
        all_imp.append(res["importance"]); all_best.append(res["best"])
        all_bounds.append(res["boundaries"]); all_skip.append(res["skipped"])
        all_folds.append(res["cv_folds"])
        all_fc.append(fc)

    config.OUTPUTS.mkdir(parents=True, exist_ok=True)
    written = {}
    for name, frames in (("model_comparison", all_comp),
                         ("predictions", all_pred),
                         ("feature_importance", all_imp),
                         ("best_model", all_best),
                         ("split_boundaries", all_bounds),
                         ("cv_folds", all_folds),
                         ("forecast", all_fc)):
        good = [f for f in frames if f is not None and not f.empty]
        df = pd.concat(good, ignore_index=True) if good else pd.DataFrame()
        path = config.OUTPUTS / f"{name}.csv"
        df.to_csv(path, index=False)
        written[name] = (path, len(df))

    skip = [f for f in all_skip if f is not None and not f.empty]
    if excluded:
        skip.append(pd.DataFrame(excluded))
    sk = (pd.concat(skip, ignore_index=True) if skip
          else pd.DataFrame(columns=["commodity", "market", "horizon", "reason"]))
    # Always written, even when empty, so the dashboard can say "none".
    sk.to_csv(config.OUTPUTS / "excluded.csv", index=False)
    if not sk.empty:
        rule("5b. PAIRS / HORIZONS EXCLUDED, AND WHY  (outputs/excluded.csv)")
        print(sk.to_string(index=False))

    rule("6. OUTPUTS WRITTEN")
    for name, (path, n) in written.items():
        print(f"  {path.relative_to(config.PROJECT_ROOT)!s:<34} {n:5d} rows")

    # ------------------------------------------------------------------ gate
    rule("7. PHASE 2 GATE")
    comp = pd.concat(all_comp, ignore_index=True)
    best = pd.concat([b for b in all_best if not b.empty], ignore_index=True)
    bounds = pd.concat([b for b in all_bounds if not b.empty], ignore_index=True)
    valid = comp[comp["split"] == "valid"]
    test = comp[comp["split"] == "test"]
    train = comp[comp["split"] == "train"]
    gkeys = ["commodity", "market", "horizon"]

    def same_rows(df):
        return all(g["n"].nunique() == 1 for _, g in df.groupby(gkeys))

    # Re-derive the embargo independently of src/splits.py's own assertions, so
    # the gate is a check and not an echo.
    embargo_ok = True
    for r in bounds.itertuples():
        if (pd.Timestamp(r.train_end) + pd.Timedelta(days=r.horizon)
                >= pd.Timestamp(r.cut_test)):
            embargo_ok = False
    folds_df = pd.concat([f for f in all_folds if not f.empty], ignore_index=True)
    for r in folds_df.drop_duplicates(["commodity", "market", "horizon",
                                       "fold"]).itertuples():
        if (pd.Timestamp(r.fit_end) + pd.Timedelta(days=r.horizon)
                >= pd.Timestamp(r.origin)):
            embargo_ok = False
        if pd.Timestamp(r.val_start) < pd.Timestamp(r.origin):
            embargo_ok = False
    cv_same = all(g["n"].nunique() == 1 for _, g in
                  folds_df.groupby(gkeys + ["fold"]))

    arima_train = train[train["model"] == "ARIMA"]
    arima_diag_ok = bool(
        not arima_train.empty
        and ((arima_train["n"] >= 100) | (arima_train["mae"].isna())).all())

    fc_all = pd.concat([f for f in all_fc if not f.empty], ignore_index=True) \
        if any(not f.empty for f in all_fc) else pd.DataFrame()
    last_obs = feats["date"].max()
    fc_future = (not fc_all.empty
                 and all(pd.Timestamp(d) > last_obs for d in fc_all["forecast_date"]))

    checks = {
        "all seven outputs/*.csv written":
            all(n > 0 for _, n in written.values()),
        "every model scored on the IDENTICAL rows in every CV fold": cv_same,
        "every model scored on the IDENTICAL pooled-CV rows per horizon":
            same_rows(valid),
        "every model scored on the IDENTICAL test rows per horizon":
            same_rows(test),
        f"all {len(CANDIDATE_NAMES)} candidate models present at every scored horizon":
            all(set(g["model"]) == set(CANDIDATE_NAMES)
                for _, g in test.groupby(gkeys)),
        "no fitting target crosses a fold origin or the test cutoff":
            embargo_ok,
        "model selected by rolling-origin CV, not on test":
            not best.empty
            and (best["selection_split"] == "rolling_origin_cv").all()
            and (best["selection_metric"] == "mean_fold_rmse").all(),
        "ARIMA training diagnostic has a real sample (n>=100) or is null":
            arima_diag_ok,
        "every train metric is labelled with what it measures":
            train["diagnostic"].notna().all() and (train["diagnostic"] != "").all(),
        "forecast dates are strictly after the last observed date": fc_future,
    }
    for label, ok in checks.items():
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")

    # ------------------------------------------------------------- headline
    rule("8. THE HONEST HEADLINE")
    print("  Selected by rolling-origin CV; the test column was computed once, after.")
    for r in best.itertuples():
        verdict = "BEATS naive" if r.beats_naive else "does NOT beat naive"
        print(f"  {r.commodity}/{r.market} h={r.horizon}: selected={r.best_model:<17} "
              f"(mean CV RMSE={r.selected_valid_rmse:7.2f})  "
              f"test RMSE={r.best_test_rmse:8.2f}  "
              f"naive={r.naive_test_rmse:8.2f}  "
              f"{verdict} ({r.improvement_over_naive_pct:+.2f}%)")

    unconfirmed = best[~best["selection_confirmed_by_test"]]
    if not unconfirmed.empty:
        print("\n  CV and test would have picked DIFFERENT models here.")
        print("  The CV pick is what we report. The test-best is shown")
        print("  only to be transparent that it was not used to choose:")
        for r in unconfirmed.itertuples():
            print(f"    {r.commodity}/{r.market} h={r.horizon}: reported={r.best_model} "
                  f"(test RMSE {r.best_test_rmse:.2f})  "
                  f"vs post-hoc test-best={r.posthoc_lowest_test_rmse_model} "
                  f"({r.posthoc_lowest_test_rmse:.2f})")

    gap = train[train["comparable_train_gap"]].merge(
        test, on=["commodity", "market", "horizon", "model"],
        suffixes=("_train", "_test"))
    if not gap.empty:
        gap["overfit_gap"] = (gap["rmse_test"] - gap["rmse_train"]).round(1)
        print("\n  Train-vs-test RMSE gap (like-for-like in-sample measurements")
        print("  only; Naive excluded because it fits nothing). A large gap")
        print("  means the model memorised the training window:")
        for r in gap.sort_values("overfit_gap", ascending=False).head(4).itertuples():
            print(f"    {r.commodity}/{r.market} h={r.horizon} {r.model:<17} train={r.rmse_train:7.2f} "
                  f"test={r.rmse_test:7.2f}  gap={r.overfit_gap:7.1f}")

    disagree = best[~best["metrics_agree"]]
    if not disagree.empty:
        print("\n  The reported model is NOT the lowest-test-MAE model at these")
        print("  horizons. Say so; RMSE and MAE answer different questions:")
        for r in disagree.itertuples():
            print(f"    {r.commodity}/{r.market} h={r.horizon}: reported={r.best_model} "
                  f"(test MAE {r.best_test_mae:.2f})  "
                  f"lowest test MAE={r.lowest_mae_model} ({r.lowest_mae:.2f})")

    if not best["beats_naive"].any():
        print("\n  No selected model beats the naive baseline at any horizon on")
        print("  this data. That is a RESULT, not a bug. Daily mandi prices are")
        print("  close to a random walk, so 'tomorrow = today' is a strong")
        print("  forecast. Report it as measured; do not tune against the test")
        print("  set to change it.")

    if all(checks.values()):
        print("\n  PHASE 2 GATE: PASS")
        return 0
    print("\n  PHASE 2 GATE: FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
