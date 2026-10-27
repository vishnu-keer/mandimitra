"""Experiment: does predicting the price CHANGE fix the tree models?

    python scripts/experiment_delta_target.py

Motivation (measured, see outputs/cv_folds.csv): level-target trees lose to
the naive baseline in every CV fold, and in the October 2013 fold they cannot
predict above Rs.2,197/q because no training target exceeded Rs.3,300.

Decision rule, written down BEFORE this script was first run:
  * Uses the SAME rolling-origin folds as the main pipeline.
  * Never computes anything on the test window.
  * A delta variant joins the main candidate set only if it beats Naive on
    mean per-fold RMSE at one or more horizons. Otherwise it is reported as a
    negative result and the main pipeline is left unchanged.

Writes outputs/experiments/delta_target_cv.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from src import config
from src.features import feature_columns, load_features
from src.metrics import all_metrics
from src.models import NaiveModel, TreeModel
from src.splits import rolling_origin_folds, split_by_date, usable_mask


def main():
    feats = load_features()
    cols = [c for c in feature_columns() if c in feats.columns]
    # identical to src/evaluate.py: drop feature columns that are all-NaN
    cols = [c for c in cols if not feats[c].isna().all()]
    rows = []
    for (commodity, market), pair in feats.groupby(config.GROUP_KEYS):
        pair = pair.sort_values("date")
        for h in config.HORIZONS:
            u = pair[usable_mask(pair, h)]
            if len(u) < config.MIN_ROWS_PER_PAIR:
                continue
            dev, _test_never_used, _ = split_by_date(u, horizon=h)
            for fd in rolling_origin_folds(dev, h):
                fit, val = fd["fit"], fd["val"]
                y = val[f"y_h{h}"].to_numpy(float)
                cands = [NaiveModel(), TreeModel("rf"), TreeModel("gbm"),
                         TreeModel("rf", "delta"), TreeModel("gbm", "delta")]
                for m in cands:
                    m.fit(fit, cols, f"y_h{h}")
                    met = all_metrics(y, m.predict(val, cols))
                    rows.append({"commodity": commodity, "market": market,
                                 "horizon": h, "fold": fd["fold"],
                                 "model": m.name, **met})
    df = pd.DataFrame(rows)
    out = config.OUTPUTS / "experiments"
    out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / "delta_target_cv.csv", index=False)

    piv = df.pivot_table(index=["commodity", "market", "horizon", "fold"],
                         columns="model", values="rmse").round(1)
    print("RMSE per CV fold (test window never touched):\n")
    print(piv.to_string())
    mean = df.groupby(["commodity", "market", "horizon", "model"])["rmse"].mean().unstack().round(2)
    print("\nMEAN per-fold RMSE (the pre-registered decision metric):\n")
    print(mean.to_string())
    print()
    joins = False
    for idx, r in mean.iterrows():
        for v in ("RandomForest-delta", "GradientBoosting-delta"):
            if r[v] < r["Naive"]:
                joins = True
                print(f"  {idx}: {v} beats Naive ({r[v]:.2f} < {r['Naive']:.2f})")
    print("\nDECISION:", "delta variant(s) JOIN the candidate set" if joins
          else "negative result -- no delta variant beats Naive on CV; "
               "main pipeline unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
