"""Shared fixtures.

IMPORTANT DISTINCTION: the series built here are SYNTHETIC, on purpose. A test
needs a controlled, deterministic input whose correct answer is known in
advance -- that is what makes it a test. This is entirely separate from the
project's own dataset, which is real government data and is never synthesised.
No number produced here ever reaches the dashboard or the report.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def straight_line():
    """Contiguous daily series, price = 100 + day index. Every lag is known."""
    dates = pd.date_range("2020-01-01", periods=120, freq="D")
    return pd.DataFrame({
        "commodity": "Onion",
        "market": "Testmarket",
        "date": dates,
        "modal_price": 100.0 + np.arange(len(dates)),
        "min_price": 90.0 + np.arange(len(dates)),
        "max_price": 110.0 + np.arange(len(dates)),
        "observed": True,
        "days_since_obs": 0.0,
    })


@pytest.fixture
def gappy_series():
    """Daily calendar with real gaps and some carried-forward days."""
    dates = pd.date_range("2020-01-01", periods=200, freq="D")
    rng = np.random.default_rng(0)
    price = 1000.0 + np.cumsum(rng.normal(0, 20, len(dates)))
    observed = rng.random(len(dates)) > 0.25
    observed[:10] = True
    df = pd.DataFrame({
        "commodity": "Onion", "market": "Testmarket", "date": dates,
        "modal_price": price, "min_price": price - 40, "max_price": price + 40,
        "observed": observed,
    })
    # Carried-forward days repeat the previous observed price, as the real
    # pipeline does.
    df.loc[~df["observed"], "modal_price"] = np.nan
    df["modal_price"] = df["modal_price"].ffill()
    pos = np.arange(len(df), dtype=float)
    last_obs = pd.Series(np.where(df["observed"], pos, np.nan)).ffill()
    df["days_since_obs"] = pos - last_obs
    return df


@pytest.fixture
def raw_csv_with_dirt(tmp_path):
    """A raw file shaped like the real download, including its known dirt."""
    rows = ["Date,Centre_Name,Commodity_Name,Price"]
    for i, d in enumerate(pd.date_range("2020-01-01", periods=80, freq="D")):
        price = 0 if i % 11 == 0 else 800 + i          # 0 = source's NA code
        rows.append(f"{d:%d-%m-%y},JAIPUR,Onion,{price}")
    rows.append("01-01-20,JAIPUR,Onion,801")            # duplicate date
    rows.append("not-a-date,JAIPUR,Onion,900")          # unparseable date
    rows.append("05-01-20,JAIPUR,Onion,99999999")       # absurd price
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "synthetic_raw.csv").write_text("\n".join(rows) + "\n")
    return raw
