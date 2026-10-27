"""Feature engineering. Pure functions, no side effects, no I/O.

THE LEAKAGE RULE FOR THIS PROJECT
---------------------------------
The decision point is the END OF DAY t. Standing there, a farmer or trader
knows today's price. So a feature on row t may use any value up to and
including t, and the targets are strictly after t:

    features(row t)  <=  price at t          (today is known)
    y_h1(row t)       =  price at t + 1      (unknown -- this is the job)
    y_h2(row t)       =  price at t + 2
    y_h3(row t)       =  price at t + 3

That is why `price_t` and a rolling mean ending at t are legitimate inputs,
and why the naive baseline is well defined as "price at t". It is also why
there is no `.shift(1)` wrapped around the rolling windows here.

The rule that must never be broken is the other direction: NO feature may
touch t+1 or later. Two things enforce it:

  1. Every window below is backward-looking. No `center=True`, no `bfill`,
     no `interpolate`, and no statistic computed over the whole series.
  2. `verify_no_leakage()` proves it empirically -- it rebuilds features on
     a truncated copy of the data and checks that nothing before the
     truncation point changed. If any feature peeked into the future, the
     truncated run would produce different numbers and the check fails.

Because we use DIRECT multi-horizon targets (a separate model per horizon),
no prediction is ever fed back in as an input. The classic recursive-
forecasting bug -- where day 2's lag accidentally uses day 1's *actual*
price instead of its prediction -- cannot exist in this design.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import config


def _min_periods(window: int, frac=None) -> int:
    """Reported prices required inside a calendar window (see config)."""
    frac = config.ROLLING_MIN_PERIODS_FRAC if frac is None else frac
    return max(2, math.ceil(window * frac))
from .store import load_table, save_table


def feature_columns(lags=None, ma_windows=None, vol_window=None) -> list[str]:
    lags = config.LAGS if lags is None else lags
    ma_windows = config.MA_WINDOWS if ma_windows is None else ma_windows
    vol_window = config.VOL_WINDOW if vol_window is None else vol_window

    cols = ["price_t"]
    cols += [f"lag_{k}" for k in lags]
    cols += [f"ma_{w}" for w in ma_windows]
    cols += [f"vol_{vol_window}", "ret_1", "dev_from_ma", "spread_pct"]
    cols += ["days_since_obs", "dow", "month"]
    return cols


def target_columns(horizons=None) -> list[str]:
    horizons = config.HORIZONS if horizons is None else horizons
    return [f"y_h{h}" for h in horizons]


def target_mask_columns(horizons=None) -> list[str]:
    """Columns saying whether each horizon's target date was really reported."""
    horizons = config.HORIZONS if horizons is None else horizons
    return [f"y_h{h}_observed" for h in horizons]


def add_features(
    df: pd.DataFrame,
    price_col=None,
    lags=None,
    ma_windows=None,
    vol_window=None,
    horizons=None,
    group_keys=None,
) -> pd.DataFrame:
    """Add lag / moving-average / volatility / calendar features and targets."""
    price_col = config.PRICE_COL if price_col is None else price_col
    lags = config.LAGS if lags is None else lags
    ma_windows = config.MA_WINDOWS if ma_windows is None else ma_windows
    vol_window = config.VOL_WINDOW if vol_window is None else vol_window
    horizons = config.HORIZONS if horizons is None else horizons
    group_keys = config.GROUP_KEYS if group_keys is None else group_keys

    pieces = []
    for _, group in df.groupby(group_keys, sort=True):
        g = group.sort_values("date").copy()
        price = g[price_col].astype(float)

        # --- level: today's price, known at the decision point
        g["price_t"] = price

        # --- lags: strictly past
        for k in lags:
            g[f"lag_{k}"] = price.shift(k)

        # --- moving averages over windows ENDING at t (t is known)
        for w in ma_windows:
            g[f"ma_{w}"] = price.rolling(
                window=w, min_periods=_min_periods(w)).mean()

        # --- rolling volatility (std dev) over a window ending at t
        g[f"vol_{vol_window}"] = price.rolling(
            window=vol_window, min_periods=_min_periods(vol_window)).std()

        # --- 1-day return. fill_method=None on purpose: across a calendar gap
        # there is no return to compute, and padding would invent one.
        g["ret_1"] = price.pct_change(1, fill_method=None)

        # --- how far today sits from its own recent average (momentum proxy)
        longest_ma = f"ma_{max(ma_windows)}"
        g["dev_from_ma"] = (price / g[longest_ma]) - 1.0

        # --- intra-day min/max spread as a share of the modal price
        if {"min_price", "max_price"}.issubset(g.columns):
            g["spread_pct"] = (g["max_price"] - g["min_price"]) / price
        else:
            g["spread_pct"] = np.nan

        # --- calendar
        g["dow"] = g["date"].dt.dayofweek.astype("int16")
        g["month"] = g["date"].dt.month.astype("int16")

        if "days_since_obs" not in g.columns:
            g["days_since_obs"] = 0.0

        # --- DIRECT multi-horizon targets: strictly future
        # y_h{h}_observed says whether the market actually REPORTED on t+h.
        # A target that is a carried-forward value is a number the mandi never
        # printed, so Phase 2 trains and scores only where this is True.
        # Without this mask the naive baseline scores free perfect hits
        # wherever price_t and y_h1 are the same imputed value.
        n = len(g)
        obs_arr = (g["observed"].to_numpy(dtype=bool) if "observed" in g.columns
                   else np.ones(n, dtype=bool))
        for h in horizons:
            g[f"y_h{h}"] = price.shift(-h)
            # Shift the observed flag back by h. Rows past the end of the
            # series have no t+h, so they are False: not usable as targets.
            mask = np.zeros(n, dtype=bool)
            if h < n:
                mask[: n - h] = obs_arr[h:]
            g[f"y_h{h}_observed"] = mask

        pieces.append(g)

    out = pd.concat(pieces, ignore_index=True)
    return out.sort_values(group_keys + ["date"]).reset_index(drop=True)


def drop_incomplete_feature_rows(df: pd.DataFrame, feat_cols=None) -> pd.DataFrame:
    """Drop the warm-up rows where a lag/window is not yet defined.

    Target NaNs are KEPT on purpose. The last few rows of each series have a
    complete feature vector but no known future price -- those are exactly
    the rows the forward forecast is made from. Training filters on the
    target instead.
    """
    feat_cols = feature_columns() if feat_cols is None else feat_cols
    present = [c for c in feat_cols if c in df.columns]
    # spread_pct is all-NaN when the source has no min/max columns; do not
    # let an optional feature delete the whole dataset.
    usable = [c for c in present if not df[c].isna().all()]
    return df.dropna(subset=usable).reset_index(drop=True)


def verify_no_leakage(clean_df: pd.DataFrame, cutoff_quantile: float = 0.7,
                      group_keys=None) -> dict:
    """Empirical proof that no feature uses information from after its own row.

    Build features on the full series, then rebuild on a copy truncated at a
    cutoff date. For every row on or before the cutoff, every feature value
    must be identical. A feature that peeked forward would change when the
    future was removed.
    """
    group_keys = config.GROUP_KEYS if group_keys is None else group_keys
    feat_cols = feature_columns()

    full = add_features(clean_df)
    cutoff = clean_df["date"].quantile(cutoff_quantile)
    truncated = add_features(clean_df[clean_df["date"] <= cutoff])

    keys = group_keys + ["date"]
    cols = [c for c in feat_cols if c in full.columns and c in truncated.columns]

    merged = full[full["date"] <= cutoff][keys + cols].merge(
        truncated[keys + cols], on=keys, suffixes=("_full", "_trunc"), how="inner"
    )

    mismatches = {}
    for col in cols:
        a = merged[f"{col}_full"]
        b = merged[f"{col}_trunc"]
        if pd.api.types.is_numeric_dtype(a):
            differs = ~np.isclose(a.astype(float), b.astype(float),
                                  rtol=1e-9, atol=1e-9, equal_nan=True)
        else:
            differs = (a != b) & ~(a.isna() & b.isna())
        if differs.any():
            mismatches[col] = int(differs.sum())

    return {
        "cutoff_date": pd.Timestamp(cutoff).date().isoformat(),
        "rows_compared": int(len(merged)),
        "columns_compared": len(cols),
        "mismatched_columns": mismatches,
        "passed": len(mismatches) == 0 and len(merged) > 0,
    }


def build_feature_table(clean_df: pd.DataFrame) -> pd.DataFrame:
    return drop_incomplete_feature_rows(add_features(clean_df))


def save_features(df: pd.DataFrame, path=None):
    return save_table(df, path or config.FEATURES_PATH)


def load_features(path=None) -> pd.DataFrame:
    return load_table(path or config.FEATURES_PATH)
