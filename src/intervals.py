"""Empirical forecast ranges, calibrated before the test window and checked on it.

Method (split-conformal style, no distributional assumption):
  1. Take the selected model's out-of-fold residuals (actual - predicted) from
     the rolling-origin CV folds. Every one of those forecasts was made by a
     model that had not seen its target, and all of them pre-date the test
     window.
  2. The central `level` share of those residuals gives an offset range
     [lo, hi]. The range for a new forecast p is [p + lo, p + hi].
  3. Apply the same offsets to every test-window forecast and COUNT how often
     the actual price fell inside. That count is reported next to the range,
     so a viewer sees both the claim and how well it held up.

If the test coverage is far from `level` -- or the range has zero width, which
happens when most CV errors are exactly 0 because a mandi quotes the same
round-number price day after day -- the range is marked as not held up, and
the dashboard reports the evaluation result instead of drawing the band. The
range is never tuned on test.

MEASURED RESULT (2026-10-27): on Onion/Jaipur and Tomato/Jaipur, 0 of 6
ranges held up -- test coverage was 55-74% against a nominal 80%, and the one
nearest to nominal (Onion h=1, 74%) was zero-width. Price volatility in the
test window differed from the development period. The project therefore does
not present uncertainty bands; it presents this finding.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

LEVEL = 0.80
MIN_RESIDUALS = 50
# Coverage within this many percentage points of LEVEL is called "held up".
COVERAGE_TOLERANCE_PTS = 10.0


def empirical_intervals(predictions: pd.DataFrame, best: pd.DataFrame,
                        level: float = LEVEL) -> pd.DataFrame:
    rows = []
    a = (1.0 - level) / 2.0
    for r in best.itertuples():
        sel = predictions[(predictions["commodity"] == r.commodity)
                          & (predictions["market"] == r.market)
                          & (predictions["horizon"] == r.horizon)
                          & (predictions["model"] == r.best_model)]
        cv = sel[sel["split"] == "valid"]
        te = sel[sel["split"] == "test"]
        resid = (cv["y_true"] - cv["y_pred"]).to_numpy(dtype=float)
        resid = resid[np.isfinite(resid)]
        base = {"commodity": r.commodity, "market": r.market,
                "horizon": r.horizon, "interval_level": level}
        if resid.size < MIN_RESIDUALS or te.empty:
            rows.append({**base, "interval_lo_offset": np.nan,
                         "interval_hi_offset": np.nan, "n_calibration": int(resid.size),
                         "interval_test_coverage": np.nan, "n_test_checked": len(te),
                         "interval_held_up": False,
                         "interval_status": "unavailable: too few CV residuals"})
            continue
        lo, hi = np.quantile(resid, [a, 1.0 - a])
        y, p = te["y_true"].to_numpy(float), te["y_pred"].to_numpy(float)
        inside = (y >= p + lo) & (y <= p + hi)
        cov = float(inside.mean() * 100.0)
        degenerate = bool(np.isclose(hi - lo, 0.0))
        held = (not degenerate) and abs(cov - level * 100.0) <= COVERAGE_TOLERANCE_PTS
        rows.append({**base, "interval_lo_offset": float(lo),
                     "interval_hi_offset": float(hi),
                     "n_calibration": int(resid.size),
                     "interval_test_coverage": round(cov, 1),
                     "n_test_checked": int(len(te)),
                     "interval_held_up": bool(held),
                     "interval_status": (
                         "degenerate: zero width (price usually unchanged)"
                         if degenerate else
                         "held up on test" if held else
                         f"did NOT hold up on test ({cov:.0f}% vs {level*100:.0f}% nominal)")})
    return pd.DataFrame(rows)
