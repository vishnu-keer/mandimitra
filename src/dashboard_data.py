"""Loading layer for the dashboard. No Streamlit imports here on purpose.

Keeping data access out of app.py means every number on screen can be checked
from a plain Python shell, and the app stays a thin presentation layer over
files the pipeline already wrote. Nothing here trains or re-scores a model.

The only figures computed here are DESCRIPTIVE statistics of the published
price series (a rebased index, rolling volatility, yearly reporting counts),
each labelled as such on screen. Model results are only ever read from
outputs/.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config
from .data_prep import load_clean
from .features import load_features
from .splits import usable_mask

OUTPUT_FILES = {
    "comparison": "model_comparison.csv",
    "predictions": "predictions.csv",
    "importance": "feature_importance.csv",
    "best": "best_model.csv",
    "forecast": "forecast.csv",
    "cv_folds": "cv_folds.csv",
    "boundaries": "split_boundaries.csv",
    "excluded": "excluded.csv",
}
OPTIONAL_FILES = {
    "delta_cv": "experiments/delta_target_cv.csv",
    "legacy_best": "legacy/best_model.csv",
    "dm": "experiments/dm_test.csv",
    "seasonal": "experiments/seasonal_naive.csv",
    "hyper": "experiments/hyperparameter_sensitivity.csv",
}
DATE_COLS = {"predictions": ["date"]}
# Files the dashboard cannot work without. The rest degrade gracefully.
REQUIRED = ("comparison", "predictions", "best", "forecast")


def _read(path, key):
    df = pd.read_csv(path)
    for col in DATE_COLS.get(key, []):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def load_outputs() -> dict:
    """Read whatever the pipeline produced. Missing files come back empty."""
    out, missing = {}, []
    for key, fname in {**OUTPUT_FILES, **OPTIONAL_FILES}.items():
        path = config.OUTPUTS / fname
        if path.exists():
            out[key] = _read(path, key)
        else:
            out[key] = pd.DataFrame()
            if key in REQUIRED:
                missing.append(fname)
    out["missing_required"] = missing
    return out


def load_everything() -> dict:
    data = {"features": load_features(), "clean": load_clean()}
    data.update(load_outputs())
    return data


def available_pairs(features: pd.DataFrame) -> pd.DataFrame:
    """Every (commodity, market) in the feature table, with its gate status.

    The selectors are built only from pairs that qualify AND were evaluated,
    so a combination that cannot support a forecast is never offered.
    """
    rows = []
    for (commodity, market), g in features.groupby(config.GROUP_KEYS):
        usable = {h: int(usable_mask(g, h).sum()) for h in config.HORIZONS}
        rows.append({
            "commodity": commodity, "market": market, "rows": len(g),
            "first": g["date"].min(), "last": g["date"].max(),
            "imputed_pct": round(100 * (~g["observed"]).mean(), 1),
            **{f"usable_h{h}": n for h, n in usable.items()},
            "qualifies": max(usable.values()) >= config.MIN_ROWS_PER_PAIR,
        })
    return pd.DataFrame(rows)


def evaluated_pairs(best: pd.DataFrame) -> set:
    if best.empty:
        return set()
    return set(zip(best["commodity"], best["market"]))


def selectable_pairs(features: pd.DataFrame, best: pd.DataFrame) -> pd.DataFrame:
    p = available_pairs(features)
    ev = evaluated_pairs(best)
    p = p[p["qualifies"]]
    return p[[(c, m) in ev for c, m in zip(p["commodity"], p["market"])]] \
        .reset_index(drop=True)


def dataset_facts(features: pd.DataFrame, clean: pd.DataFrame,
                  commodity: str, market: str) -> dict:
    f = features[(features["commodity"] == commodity)
                 & (features["market"] == market)]
    c = clean[(clean["commodity"] == commodity) & (clean["market"] == market)]
    if f.empty or c.empty:
        return {}
    span = (c["date"].max() - c["date"].min()).days + 1
    reported = int(c["observed"].sum())
    last_obs = c[c["observed"]].sort_values("date").iloc[-1]
    return {
        "first_date": c["date"].min(),
        "last_date": c["date"].max(),
        "last_observed_date": last_obs["date"],
        "last_observed_price": float(last_obs[config.PRICE_COL]),
        "calendar_days": span,
        "days_reported": reported,
        "reported_pct": round(100 * reported / span, 1) if span else 0.0,
        "feature_rows": len(f),
        "imputed_pct": round(100 * (~f["observed"]).mean(), 1),
        "usable": {h: int(usable_mask(f, h).sum()) for h in config.HORIZONS},
        "median_price": round(float(f["price_t"].median()), 0),
        "min_price": round(float(f["price_t"].min()), 0),
        "max_price": round(float(f["price_t"].max()), 0),
    }


def quality_facts(clean: pd.DataFrame, commodity: str, market: str,
                  today=None) -> dict:
    """Data-quality numbers for one series, all descriptive.

    unchanged_pct: share of reported days whose price equals the previous
    REPORTED price (a stale-quote indicator). age_days: days between the latest
    genuine observation and today -- the freshness of the data itself.
    """
    c = clean[(clean["commodity"] == commodity) & (clean["market"] == market)]
    rep = c[c["observed"]].sort_values("date")
    if rep.empty:
        return {}
    d = rep[config.PRICE_COL].diff().dropna()
    gaps = rep["date"].diff().dt.days.dropna()
    today = pd.Timestamp(today or pd.Timestamp.now(tz="UTC").date())
    last = rep["date"].max()
    return {
        "latest_observation": last,
        "age_days": int((today - last).days),
        "unchanged_pct": round(100 * float((d == 0).mean()), 1),
        "longest_gap_days": int(gaps.max()) if not gaps.empty else 0,
        "median_gap_days": float(gaps.median()) if not gaps.empty else 0.0,
    }


def price_history(features: pd.DataFrame, commodity: str, market: str) -> pd.DataFrame:
    f = features[(features["commodity"] == commodity)
                 & (features["market"] == market)]
    return f[["date", "price_t", "ma_7", "observed"]].sort_values("date").copy()


def yearly_reporting(clean: pd.DataFrame, commodity: str, market: str) -> pd.DataFrame:
    """Per calendar year: days with a reported price, carried forward, missing."""
    c = clean[(clean["commodity"] == commodity) & (clean["market"] == market)].copy()
    if c.empty:
        return pd.DataFrame()
    c["year"] = c["date"].dt.year
    has_price = c[config.PRICE_COL].notna()
    c["status"] = np.where(c["observed"], "Reported",
                           np.where(has_price, "Carried forward", "No price"))
    return (c.groupby(["year", "status"]).size().unstack(fill_value=0)
            .reindex(columns=["Reported", "Carried forward", "No price"],
                     fill_value=0).reset_index())


def comparison_series(clean: pd.DataFrame, pairs) -> dict:
    """Descriptive comparison of validated pairs over their COMMON window.

    Returns the common window, a price index rebased to 100 at the first
    common reported date, and 30-day rolling volatility of daily % changes
    computed on reported days only. Descriptive statistics of the published
    data -- not model output.
    """
    frames = []
    for c, m in pairs:
        f = clean[(clean["commodity"] == c) & (clean["market"] == m)]
        s = (f[f["observed"]].set_index("date")[config.PRICE_COL]
             .astype(float).rename(f"{c} / {m}"))
        frames.append(s)
    if len(frames) < 2:
        return {}
    wide = pd.concat(frames, axis=1).sort_index()
    start = max(s.first_valid_index() for s in frames)
    end = min(s.last_valid_index() for s in frames)
    wide = wide.loc[start:end]
    base = wide.dropna().iloc[0]
    index = wide.ffill(limit=config.MAX_FFILL_DAYS) / base * 100.0
    pct = wide.pct_change(fill_method=None) * 100.0
    vol = pct.rolling("30D", min_periods=10).std()
    summary = pd.DataFrame({
        "Reported days": wide.notna().sum(),
        "Median price (Rs./q)": wide.median().round(0),
        "Min (Rs./q)": wide.min().round(0),
        "Max (Rs./q)": wide.max().round(0),
        "Median daily |change| %": pct.abs().median().round(2),
        "Median 30-day volatility %": vol.median().round(2),
    })
    return {"start": start, "end": end, "index": index, "volatility": vol,
            "summary": summary, "base_date": wide.dropna().index[0]}


def provenance_text() -> str:
    path = config.DOCS / "01_DATA_SOURCE.md"
    return path.read_text() if path.exists() else "_Provenance file not found._"
