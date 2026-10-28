"""Are the test-period differences from Naive statistically distinguishable?

    python scripts/experiment_significance.py

For every pair, horizon and model, a Diebold-Mariano test (with the
Harvey-Leybourne-Newbold correction, src/significance.py) of the model's
test-window forecasts against Naive's, on the identical target dates, under
squared-error (the RMSE question) and absolute-error (the MAE question) loss.

Read with care, decided BEFORE running:
  * This is evidence about THIS test window only.
  * Several models are compared with Naive at each pair-horizon, so the
    p-values are also reported Holm-adjusted within each pair-horizon.
  * A non-significant result means "no detectable difference", not "equal".
  * Nothing here changes which model was selected; selection was by CV.

Writes outputs/experiments/dm_test.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from src import config
from src.significance import dm_test


def holm(p):
    p = np.asarray(p, dtype=float)
    order = np.argsort(p)
    adj = np.empty_like(p)
    running = 0.0
    m = len(p)
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p[i]))
        adj[i] = running
    return adj


def main():
    pred = pd.read_csv(config.OUTPUTS / "predictions.csv", parse_dates=["date"])
    best = pd.read_csv(config.OUTPUTS / "best_model.csv")
    test = pred[pred["split"] == "test"]
    rows = []
    for (c, m, h), g in test.groupby(["commodity", "market", "horizon"]):
        wide = g.pivot_table(index="date", columns="model", values="y_pred")
        y = g.drop_duplicates("date").set_index("date")["y_true"].reindex(wide.index)
        sel = best[(best.commodity == c) & (best.market == m)
                   & (best.horizon == h)]["best_model"].iloc[0]
        block = []
        for model in [x for x in wide.columns if x != "Naive"]:
            for loss in ("squared", "absolute"):
                r = dm_test(y, wide[model], wide["Naive"], h=int(h), loss=loss)
                block.append({"commodity": c, "market": m, "horizon": int(h),
                              "model": model, "selected_by_cv": model == sel,
                              "loss": loss, **r})
        b = pd.DataFrame(block)
        for loss in ("squared", "absolute"):
            k = b["loss"] == loss
            b.loc[k, "p_holm"] = holm(b.loc[k, "p_value"].fillna(1.0))
        rows.append(b)
    df = pd.concat(rows, ignore_index=True)
    dest = config.OUTPUTS / "experiments" / "dm_test.csv"
    df.to_csv(dest, index=False)
    pd.set_option("display.width", 200)
    show = df[df["loss"] == "squared"][["commodity", "horizon", "model", "selected_by_cv",
                                        "n", "dm_stat", "p_value", "p_holm"]]
    print("Squared-error loss, model vs Naive on the test window "
          "(negative DM = model better):\n")
    print(show.round(3).to_string(index=False))
    sig = df[(df["p_holm"] < 0.05)]
    print(f"\nHolm-adjusted p < 0.05: {len(sig)} of {len(df)} comparisons")
    for r in sig.itertuples():
        print(f"  {r.commodity} h={r.horizon} {r.model} ({r.loss}): DM={r.dm_stat:.2f}, "
              f"p_holm={r.p_holm:.4f} -> {'model better' if r.dm_stat < 0 else 'Naive better'}")
    print(f"wrote {dest.relative_to(config.PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
