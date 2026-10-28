"""Diebold-Mariano test for equal predictive accuracy, with the
Harvey-Leybourne-Newbold (1997) small-sample correction.

    d_t = L(e1_t) - L(e2_t)          loss differential, here squared error
    DM  = mean(d) / sqrt(V / T)      V = long-run variance of d, using
                                     autocovariances up to lag h-1
    HLN = DM * sqrt((T + 1 - 2h + h(h-1)/T) / T), compared with Student t(T-1)

A negative statistic means model 1 has the lower loss. This is a test of the
two forecast series on the SAME target dates; it says nothing about whether a
difference would hold in another period.

References: Diebold & Mariano (1995), J. Business & Economic Statistics
13(3):253-263; Harvey, Leybourne & Newbold (1997), Int. J. Forecasting
13(2):281-291.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import stats


def dm_test(actual, pred1, pred2, h: int = 1, loss: str = "squared") -> dict:
    a, p1, p2 = (np.asarray(x, dtype=float) for x in (actual, pred1, pred2))
    ok = np.isfinite(a) & np.isfinite(p1) & np.isfinite(p2)
    a, p1, p2 = a[ok], p1[ok], p2[ok]
    T = int(a.size)
    if loss == "squared":
        d = (a - p1) ** 2 - (a - p2) ** 2
    elif loss == "absolute":
        d = np.abs(a - p1) - np.abs(a - p2)
    else:
        raise ValueError("loss must be 'squared' or 'absolute'")
    out = {"n": T, "mean_loss_diff": float(d.mean()) if T else float("nan"),
           "dm_stat": float("nan"), "p_value": float("nan")}
    if T < 10 or h < 1:
        return out
    dc = d - d.mean()
    gamma0 = float(np.dot(dc, dc) / T)
    v = gamma0 + 2.0 * sum(float(np.dot(dc[k:], dc[:-k]) / T) for k in range(1, h))
    if not v > 0:                     # identical forecasts, or degenerate variance
        return out
    dm = float(d.mean() / math.sqrt(v / T))
    hln = dm * math.sqrt((T + 1 - 2 * h + h * (h - 1) / T) / T)
    p = float(2 * stats.t.sf(abs(hln), df=T - 1))
    out.update({"dm_stat": hln, "p_value": p})
    return out
