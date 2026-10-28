"""Experiment: is a weekly SEASONAL naive baseline stronger than plain Naive?

    python scripts/experiment_seasonal_naive.py

Seasonal naive at horizon h forecasts price[t+h] = price[t+h-7], the price on
the same weekday one week earlier. It is known at the end of day t for any
h <= 7, so it is a legitimate forecast. Mandis have weekly rhythms (weekly
closures, weekday arrivals), so it is the obvious second baseline to check.

Protocol, written down BEFORE this script was first run:
  * Same usable rows, same rolling-origin folds and same test window as the
    main pipeline. Neither baseline fits anything, so "CV score" is simply the
    error on each fold's validation block.
  * Both baselines are scored on the intersection of rows where both exist.
  * Report CV and test side by side. Seasonal naive replaces Naive as the
    reference baseline only if its mean CV RMSE is lower at every horizon of a
    pair. The test numbers are shown for information and decide nothing.

Writes outputs/experiments/seasonal_naive.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from src import config
from src.features import load_features
from src.metrics import all_metrics
from src.splits import rolling_origin_folds, split_by_date, usable_mask

SEASON = 7


def seasonal_forecast(pair: pd.DataFrame, rows: pd.DataFrame, h: int) -> np.ndarray:
    """price_t on date (t + h - 7) for each row; NaN where that day has no input."""
    by_date = pair.set_index("date")["price_t"]
    look = rows["date"] + pd.Timedelta(days=h - SEASON)
    return by_date.reindex(look).to_numpy(dtype=float)


def score(rows, pair, h):
    y = rows[f"y_h{h}"].to_numpy(float)
    naive = rows["price_t"].to_numpy(float)
    seas = seasonal_forecast(pair, rows, h)
    both = np.isfinite(seas) & np.isfinite(naive) & np.isfinite(y)
    return (all_metrics(y[both], naive[both]), all_metrics(y[both], seas[both]),
            int(both.sum()), int(len(y)))


def main():
    feats = load_features()
    out = []
    for (commodity, market), pair in feats.groupby(config.GROUP_KEYS):
        pair = pair.sort_values("date")
        for h in config.HORIZONS:
            u = pair[usable_mask(pair, h)]
            if len(u) < config.MIN_ROWS_PER_PAIR:
                continue
            dev, test, _ = split_by_date(u, horizon=h)
            blocks = [(f"cv_fold_{fd['fold']}", fd["val"])
                      for fd in rolling_origin_folds(dev, h)] + [("test", test)]
            for name, rows in blocks:
                m_n, m_s, n_both, n_all = score(rows, pair, h)
                for model, m in (("Naive", m_n), ("SeasonalNaive7", m_s)):
                    out.append({"commodity": commodity, "market": market,
                                "horizon": h, "block": name, "model": model,
                                "n_scored": n_both, "n_block": n_all,
                                "mae": m["mae"], "rmse": m["rmse"]})
    df = pd.DataFrame(out)
    dest = config.OUTPUTS / "experiments" / "seasonal_naive.csv"
    dest.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(dest, index=False)

    cv = df[df["block"].str.startswith("cv")]
    cvm = cv.groupby(["commodity", "market", "horizon", "model"])["rmse"].mean() \
            .unstack().round(2)
    te = df[df["block"] == "test"].set_index(["commodity", "market", "horizon", "model"])
    tem = te["rmse"].unstack().round(2)
    pd.set_option("display.width", 160)
    print("Mean CV fold RMSE (decides):\n", cvm.to_string(), "\n")
    print("Test RMSE (information only):\n", tem.to_string(), "\n")
    for (c, m), g in cvm.groupby(level=[0, 1]):
        wins = (g["SeasonalNaive7"] < g["Naive"]).all()
        print(f"  {c}/{m}: seasonal naive {'REPLACES' if wins else 'does not replace'} "
              f"Naive as the reference baseline")
    print(f"wrote {dest.relative_to(config.PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
