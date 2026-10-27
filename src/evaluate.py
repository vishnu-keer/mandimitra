"""Fit on development, select by rolling-origin CV, report on test. Once.

THE PROTOCOL (revised 2026-10-27)
---------------------------------
    |------------------ development ------------------|--- test ---|
    |--- initial ---|-f1-|-f2-|-f3-|-f4-|          ^embargo
                     each fold: fit on everything before its origin

  select  -> lowest MEAN per-fold RMSE across the CV folds (rule fixed before
             any CV result was seen; see src/config.py)
  final   -> refit every candidate on the whole development block
  report  -> the selected model's metrics on TEST, computed after selection

What this replaced, and why: the earlier version split the data in two and
reported the lowest-TEST-RMSE model as "best". That is model selection on the
test set -- with four candidates and three horizons there are twelve chances
to pick a winner by luck, and the number reported beside the winner is the
number that chose it. A first fix used one validation block; on Onion/Jaipur
that block was the October 2013 price spike, so one extreme year chose
everything. Rolling-origin folds spread selection across the whole
development period. Old results are preserved in outputs/legacy/.

THE RULES THIS FILE ENFORCES
----------------------------
  1. No date appears on both sides of any boundary, and no fitting TARGET
     reaches across one (src/splits.py asserts both; the gate re-checks).
  2. Each CV fold, the pooled CV window and the test window are each scored on
     the IDENTICAL rows for every candidate (the intersection of rows every
     model could predict).
  3. TRAIN metrics are diagnostic only, on each model's own predictable rows,
     and every row says what it measures in the `diagnostic` column. A train
     number for a model with no parameters (Naive) is a property of the
     period, not of a fit, and is excluded from the overfitting comparison.
  4. Only rows whose target date was actually reported by the mandi are used.
  5. The selected model is computed, not chosen.
  6. Post-hoc test winners are reported alongside, labelled post-hoc, and are
     never used to choose anything.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from . import config
from .features import feature_columns
from .metrics import all_metrics
from .models import ArimaModel, NaiveModel, build_models
from .splits import rolling_origin_folds, split_by_date, usable_mask

log = logging.getLogger(__name__)

SPLITS = ("train", "valid", "test")


def _daily_price_series(clean: pd.DataFrame, commodity: str, market: str) -> pd.Series:
    """Continuous daily, gap-free price series for ARIMA's input only.

    ARIMA needs a regularly spaced series with no holes, which the tree models
    do not require. Remaining gaps are forward-filled -- backward-looking only.

    Leading NaNs are DROPPED rather than back-filled. Back-filling them would
    populate the start of the series from a LATER observed price, which is
    future information entering ARIMA's training input. The series therefore
    begins at the first genuinely reported price.
    """
    g = clean[(clean["commodity"] == commodity) & (clean["market"] == market)]
    s = g.set_index("date")[config.PRICE_COL].astype(float).sort_index()
    s = s.asfreq("D").ffill()
    first = s.first_valid_index()
    return s if first is None else s.loc[first:]


def _diagnostic_label(model, split: str) -> str:
    """What the number on this row actually is. Printed, not implied."""
    if split == "valid":
        return "out_of_sample_cv_selection"
    if split == "test":
        return "out_of_sample_final"
    if isinstance(model, NaiveModel):
        return "in_sample_period_property"
    if isinstance(model, ArimaModel):
        return "in_sample_h_step"
    return "in_sample_fit"


def _comparable_train_gap(model, split: str, n: int) -> bool:
    """May this row's train metric be differenced against its test metric?

    True only for a like-for-like in-sample measurement on a real sample. The
    Naive model is excluded: it fits nothing, so its train/test difference
    measures how calm the training period was, not memorisation. Reporting it
    in an overfitting table would invite exactly the wrong conclusion.
    """
    if split != "train":
        return False
    if isinstance(model, NaiveModel):
        return False
    return n >= 50


def _shared_mask(raw: dict, key: str, n: int) -> np.ndarray:
    mask = np.ones(n, dtype=bool)
    for preds in raw.values():
        mask &= np.isfinite(preds[key])
    return mask


def evaluate_pair(features: pd.DataFrame, clean: pd.DataFrame,
                  commodity: str, market: str, horizons=None,
                  test_fraction=None, n_folds=None, initial_fraction=None):
    """Full evaluation for one (commodity, market). Returns a dict of frames."""
    horizons = config.HORIZONS if horizons is None else horizons
    feat_cols = [c for c in feature_columns() if c in features.columns]
    feat_cols = [c for c in feat_cols if not features[c].isna().all()]

    pair = features[(features["commodity"] == commodity)
                    & (features["market"] == market)].sort_values("date").copy()
    if pair.empty:
        raise ValueError(f"No feature rows for {commodity}/{market}")

    comparison, predictions, importances, boundaries = [], [], [], []
    fold_rows, skipped, fitted = [], [], {}
    daily = _daily_price_series(clean, commodity, market)
    base = {"commodity": commodity, "market": market}

    for h in horizons:
        target = f"y_h{h}"
        usable = pair[usable_mask(pair, h)].copy()
        if len(usable) < config.MIN_ROWS_PER_PAIR:
            reason = (f"only {len(usable)} usable rows "
                      f"(need {config.MIN_ROWS_PER_PAIR})")
            log.warning("%s/%s h=%d: %s; skipping", commodity, market, h, reason)
            skipped.append({**base, "horizon": h, "reason": reason})
            continue

        dev, test, cut_test = split_by_date(usable, test_fraction, horizon=h)
        folds = rolling_origin_folds(dev, h, n_folds, initial_fraction)

        # ------------------------------------------------ 1. CV: selection
        oof = {}                       # model name -> out-of-fold predictions
        for fd in folds:
            fit, val = fd["fit"], fd["val"]
            models = build_models(h)
            for m in models:
                if isinstance(m, ArimaModel):
                    m.prepare(daily, fit["date"].max(),
                              walk_end=val["date"].max(), insample=False)
            raw = {}
            for m in models:
                m.fit(fit, feat_cols, target)
                raw[m.name] = {"val": m.predict(val, feat_cols)}
                oof.setdefault(m.name, pd.Series(np.nan, index=dev.index))
                oof[m.name].loc[val.index] = raw[m.name]["val"]
            shared = _shared_mask(raw, "val", len(val))
            y = val[target].to_numpy(dtype=float)
            for m in models:
                met = all_metrics(y[shared], raw[m.name]["val"][shared])
                fold_rows.append({
                    **base, "horizon": h, "fold": fd["fold"], "model": m.name,
                    "fit_start": fit["date"].min().date().isoformat(),
                    "fit_end": fit["date"].max().date().isoformat(),
                    "origin": fd["origin"].date().isoformat(),
                    "val_start": val["date"].min().date().isoformat(),
                    "val_end": val["date"].max().date().isoformat(),
                    "n_fit": len(fit),
                    "val_target_max": float(np.nanmax(y)),
                    "fit_target_max": float(fit[target].max()),
                    **met})

        cv_rows = dev.index[np.isfinite(
            np.column_stack([oof[k].to_numpy() for k in oof])).all(axis=1)]
        cv = dev.loc[cv_rows]

        # ------------------------------------------ 2. final fit on development
        models = build_models(h)
        for m in models:
            if isinstance(m, ArimaModel):
                m.prepare(daily, dev["date"].max(), insample=True)
        frames = {"train": dev, "test": test}
        raw = {}
        for m in models:
            m.fit(dev, feat_cols, target)
            raw[m.name] = {s_: m.predict(frames[s_], feat_cols) for s_ in frames}
            raw[m.name]["valid"] = oof[m.name].loc[cv_rows].to_numpy(dtype=float)
            if isinstance(m, ArimaModel) and m.failed_reason:
                log.warning("%s/%s h=%d: ARIMA did not converge (%s)",
                            commodity, market, h, m.failed_reason)
        frames["valid"] = cv
        shared_test = _shared_mask(raw, "test", len(test))

        if shared_test.sum() < 20 or len(cv) < 20:
            reason = (f"only {len(cv)} CV / {int(shared_test.sum())} test rows "
                      f"every candidate could score (need 20 each)")
            log.warning("%s/%s h=%d: %s; skipping", commodity, market, h, reason)
            skipped.append({**base, "horizon": h, "reason": reason})
            continue

        fr = pd.DataFrame([r for r in fold_rows if r["horizon"] == h
                           and r["commodity"] == commodity
                           and r["market"] == market])
        mean_fold = fr.groupby("model")["rmse"].mean().to_dict()

        boundaries.append({
            **base, "horizon": h,
            "train_start": dev["date"].min().date().isoformat(),
            "train_end": dev["date"].max().date().isoformat(),
            "cv_start": cv["date"].min().date().isoformat(),
            "cv_end": cv["date"].max().date().isoformat(),
            "cv_folds": len(folds),
            "test_start": test["date"].min().date().isoformat(),
            "test_end": test["date"].max().date().isoformat(),
            "cut_test": pd.Timestamp(cut_test).date().isoformat(),
            "n_train": len(dev), "n_cv_scored": len(cv),
            "n_test_scored": int(shared_test.sum()),
        })

        masks = {"valid": np.ones(len(cv), dtype=bool), "test": shared_test}
        for m in models:
            masks["train"] = np.isfinite(raw[m.name]["train"])
            for s_ in SPLITS:
                frame, mask = frames[s_], masks[s_]
                y_true = frame.loc[mask, target].to_numpy(dtype=float)
                metrics = all_metrics(y_true, raw[m.name][s_][mask])
                row = {**base, "horizon": h, "model": m.name, "split": s_,
                       "diagnostic": _diagnostic_label(m, s_),
                       "converged": not (isinstance(m, ArimaModel)
                                         and m.failed_reason is not None)}
                row.update(metrics)
                row["cv_mean_fold_rmse"] = (float(mean_fold.get(m.name, np.nan))
                                            if s_ == "valid" else np.nan)
                row["comparable_train_gap"] = _comparable_train_gap(
                    m, s_, metrics["n"])
                row["note"] = (m._insample_status
                               if isinstance(m, ArimaModel) and s_ == "train"
                               else "")
                comparison.append(row)

            for s_ in ("valid", "test"):
                frame, mask = frames[s_], masks[s_]
                for d, yt, yp in zip(frame.loc[mask, "date"],
                                     frame.loc[mask, target],
                                     raw[m.name][s_][mask]):
                    predictions.append({**base, "horizon": h, "model": m.name,
                                        "split": s_, "date": d,
                                        "y_true": float(yt), "y_pred": float(yp)})

            imp = m.importances(feat_cols)
            if imp:
                for feat, val in imp.items():
                    importances.append({**base, "horizon": h, "model": m.name,
                                        "feature": feat, "importance": val})
            fitted[(h, m.name)] = m

        log.info("%s/%s h=%d: dev=%d cv_scored=%d (%d folds) test_scored=%d "
                 "cut_test=%s", commodity, market, h, len(dev), len(cv),
                 len(folds), int(shared_test.sum()), pd.Timestamp(cut_test).date())

    comp = pd.DataFrame(comparison)
    if comp.empty:
        raise ValueError(f"No horizon produced a scoreable result for "
                         f"{commodity}/{market}")

    return {
        "comparison": comp,
        "predictions": pd.DataFrame(predictions),
        "importance": pd.DataFrame(importances),
        "best": _select(comp),
        "boundaries": pd.DataFrame(boundaries),
        "cv_folds": pd.DataFrame(fold_rows),
        "skipped": pd.DataFrame(skipped),
        "fitted": fitted,
        "feature_cols": feat_cols,
        "pair_rows": pair,
    }


def _select(comp: pd.DataFrame) -> pd.DataFrame:
    """Select on mean per-fold CV RMSE. Report the selected model's TEST metrics.

    Column names are kept from the earlier two-way-split version so the
    dashboard and the forward forecast keep working, but note the redefinition:
    `best_model` is now the CV-selected model, and `best_test_rmse` is
    that model's test RMSE -- which is not necessarily the lowest test RMSE on
    offer. When it is not, `selection_confirmed_by_test` is False and the
    dashboard says so.
    """
    valid = comp[(comp["split"] == "valid")
                 & np.isfinite(comp["cv_mean_fold_rmse"])]
    test = comp[(comp["split"] == "test") & np.isfinite(comp["rmse"])]
    keys = ["commodity", "market", "horizon"]
    rows = []

    for key, vg in valid.groupby(keys):
        commodity, market, h = key
        tg = test[(test["commodity"] == commodity) & (test["market"] == market)
                  & (test["horizon"] == h)]
        if tg.empty:
            continue

        pick = vg.sort_values("cv_mean_fold_rmse").iloc[0]   # <- the selection
        chosen = str(pick["model"])
        sel_test = tg[tg["model"] == chosen]
        if sel_test.empty:
            continue
        sel_test = sel_test.iloc[0]

        naive_test = tg[tg["model"] == "Naive"]
        naive_rmse = (float(naive_test["rmse"].iloc[0])
                      if not naive_test.empty else float("nan"))
        naive_mae = (float(naive_test["mae"].iloc[0])
                     if not naive_test.empty else float("nan"))

        posthoc_rmse = tg.sort_values("rmse").iloc[0]
        posthoc_mae = tg.sort_values("mae").iloc[0]

        rows.append({
            "commodity": commodity, "market": market, "horizon": h,

            # --- how the model was chosen
            "best_model": chosen,
            "selection_split": "rolling_origin_cv",
            "selection_metric": "mean_fold_rmse",
            "selected_valid_rmse": float(pick["cv_mean_fold_rmse"]),
            "selected_cv_pooled_rmse": float(pick["rmse"]),
            "selected_valid_mae": float(pick["mae"]),
            "n_valid": int(pick["n"]),

            # --- what it then scored on the untouched test window
            "best_test_rmse": float(sel_test["rmse"]),
            "best_test_mae": float(sel_test["mae"]),
            "best_test_mape": float(sel_test["mape"]),
            "n_test": int(sel_test["n"]),

            # --- against the baseline, on test
            "naive_test_rmse": naive_rmse,
            "naive_test_mae": naive_mae,
            "improvement_over_naive_pct": (
                float("nan") if not np.isfinite(naive_rmse) or naive_rmse == 0
                else round(100.0 * (naive_rmse - float(sel_test["rmse"]))
                           / naive_rmse, 2)),
            "beats_naive": bool(np.isfinite(naive_rmse)
                                and float(sel_test["rmse"]) < naive_rmse),

            # --- post-hoc only. Never used to choose anything.
            "posthoc_lowest_test_rmse_model": str(posthoc_rmse["model"]),
            "posthoc_lowest_test_rmse": float(posthoc_rmse["rmse"]),
            "selection_confirmed_by_test": bool(
                chosen == str(posthoc_rmse["model"])),
            "lowest_mae_model": str(posthoc_mae["model"]),
            "lowest_mae": float(posthoc_mae["mae"]),
            "metrics_agree": bool(chosen == str(posthoc_mae["model"])),
        })

    out = pd.DataFrame(rows)
    return out.sort_values("horizon").reset_index(drop=True) if not out.empty else out
