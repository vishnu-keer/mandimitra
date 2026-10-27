"""Evaluation metrics. No model touches this file; it only sees arrays.

All four metrics are reported for every model on the same rows, so the
comparison table is apples-to-apples. Notes on each, because a judge may ask:

  MAE   - mean absolute error, in Rs./quintal. The most directly interpretable
          number on the dashboard: "on average we are off by Rs.X".
  RMSE  - penalises large misses more than MAE. Model selection uses RMSE
          because a big miss on a price signal is worse than several small ones.
  MAPE  - error as a % of the actual price. Comparable across commodities, but
          asymmetric: an under-forecast can cost at most 100%, an over-forecast
          has no ceiling, so it quietly favours models that forecast low. It
          also explodes near zero; rows with a near-zero actual are excluded.
  R2    - share of variance explained. Reported, but read it with care on a
          near-random-walk price series: a model that simply repeats today's
          price scores a high R2 purely from level persistence, without
          predicting any of the change that actually matters.
"""
from __future__ import annotations

import numpy as np

MAPE_FLOOR = 1.0  # Rs./quintal; actuals below this are excluded from MAPE


def _clean_pair(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    ok = np.isfinite(y_true) & np.isfinite(y_pred)
    return y_true[ok], y_pred[ok]


def mae(y_true, y_pred) -> float:
    t, p = _clean_pair(y_true, y_pred)
    return float(np.mean(np.abs(t - p))) if t.size else float("nan")


def rmse(y_true, y_pred) -> float:
    t, p = _clean_pair(y_true, y_pred)
    return float(np.sqrt(np.mean((t - p) ** 2))) if t.size else float("nan")


def mape(y_true, y_pred) -> float:
    t, p = _clean_pair(y_true, y_pred)
    keep = np.abs(t) >= MAPE_FLOOR
    if not keep.any():
        return float("nan")
    return float(np.mean(np.abs((t[keep] - p[keep]) / t[keep])) * 100.0)


def r2(y_true, y_pred) -> float:
    t, p = _clean_pair(y_true, y_pred)
    if t.size < 2:
        return float("nan")
    ss_res = float(np.sum((t - p) ** 2))
    ss_tot = float(np.sum((t - np.mean(t)) ** 2))
    return float("nan") if ss_tot == 0 else 1.0 - ss_res / ss_tot


def all_metrics(y_true, y_pred) -> dict:
    t, _ = _clean_pair(y_true, y_pred)
    return {
        "n": int(t.size),
        "mae": mae(y_true, y_pred),
        "rmse": rmse(y_true, y_pred),
        "mape": mape(y_true, y_pred),
        "r2": r2(y_true, y_pred),
    }
