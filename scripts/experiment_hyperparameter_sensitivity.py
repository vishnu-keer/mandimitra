"""Audit: did the test window leak into the tree models through their settings?

    python scripts/experiment_hyperparameter_sensitivity.py

Why this exists. The tree settings in src/models.py (max_depth=6,
min_samples_leaf=8, ...) were fixed in Phase 2, under the old protocol, and
their effect was at the time MEASURED ON THE TEST WINDOW (docs/02_METHODOLOGY.md
recorded "Random Forest 98.5 -> 93.4"). Keeping a setting after looking at test
error is a mild form of test-set tuning, even if the setting was motivated by
something else. This script measures whether it matters.

Decision rule, written down BEFORE this script was first run:
  * Same rolling-origin folds as the main pipeline; the test window is never
    touched.
  * Re-run every tree candidate with scikit-learn's DEFAULT settings, which no
    one chose, and recompute the CV selection with those scores.
  * If the selected model is the same at every pair and horizon, the setting
    cannot have changed any reported result, and that is recorded.
  * If any selection changes, that is reported as a limitation. The main
    pipeline is NOT switched either way: choosing between the two settings now,
    with both sets of test results already seen, would be another round of
    test-informed selection.

Writes outputs/experiments/hyperparameter_sensitivity.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor

from src import config
from src.features import feature_columns, load_features
from src.metrics import all_metrics
from src.models import RANDOM_STATE, TreeModel
from src.splits import rolling_origin_folds, split_by_date, usable_mask


class DefaultTree(TreeModel):
    """Same model, scikit-learn default hyperparameters (only the seed fixed)."""

    def fit(self, train, feature_cols, target_col):
        X = train[feature_cols].to_numpy(dtype=float)
        y = train[target_col].to_numpy(dtype=float)
        if self.target_mode == "delta":
            y = y - train["price_t"].to_numpy(dtype=float)
        self.model = (RandomForestRegressor(random_state=RANDOM_STATE, n_jobs=1)
                      if self.kind == "rf" else
                      GradientBoostingRegressor(random_state=RANDOM_STATE))
        self.model.fit(X, y)
        return self


def main():
    feats = load_features()
    cols = [c for c in feature_columns() if c in feats.columns]
    cols = [c for c in cols if not feats[c].isna().all()]     # as evaluate.py
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
                for m in [DefaultTree("rf"), DefaultTree("gbm"),
                          DefaultTree("rf", "delta")]:
                    m.fit(fit, cols, f"y_h{h}")
                    rows.append({"commodity": commodity, "market": market,
                                 "horizon": h, "fold": fd["fold"], "model": m.name,
                                 **all_metrics(y, m.predict(val, cols))})
    dflt = (pd.DataFrame(rows).groupby(["commodity", "market", "horizon", "model"])
            ["rmse"].mean().rename("cv_mean_fold_rmse_default").reset_index())

    comp = pd.read_csv(config.OUTPUTS / "model_comparison.csv")
    cur = comp[comp["split"] == "valid"][["commodity", "market", "horizon", "model",
                                          "cv_mean_fold_rmse"]]
    t = cur.merge(dflt, on=["commodity", "market", "horizon", "model"], how="left")
    # Non-tree candidates have no hyperparameters: same score under both.
    t["cv_mean_fold_rmse_default"] = t["cv_mean_fold_rmse_default"].fillna(
        t["cv_mean_fold_rmse"])
    out = []
    for key, g in t.groupby(["commodity", "market", "horizon"]):
        sel_cur = g.loc[g["cv_mean_fold_rmse"].idxmin(), "model"]
        sel_def = g.loc[g["cv_mean_fold_rmse_default"].idxmin(), "model"]
        for r in g.itertuples():
            out.append({"commodity": key[0], "market": key[1], "horizon": key[2],
                        "model": r.model,
                        "cv_rmse_project_settings": round(r.cv_mean_fold_rmse, 3),
                        "cv_rmse_sklearn_defaults": round(r.cv_mean_fold_rmse_default, 3),
                        "selected_project_settings": sel_cur,
                        "selected_sklearn_defaults": sel_def})
    res = pd.DataFrame(out)
    dest = config.OUTPUTS / "experiments" / "hyperparameter_sensitivity.csv"
    dest.parent.mkdir(parents=True, exist_ok=True)
    res.to_csv(dest, index=False)

    pd.set_option("display.width", 200)
    print(res.pivot_table(index=["commodity", "market", "horizon"], columns="model",
                          values=["cv_rmse_project_settings", "cv_rmse_sklearn_defaults"])
          .round(1).to_string())
    sel = res.drop_duplicates(["commodity", "market", "horizon"])
    changed = sel[sel["selected_project_settings"] != sel["selected_sklearn_defaults"]]
    print()
    for r in sel.itertuples():
        print(f"  {r.commodity}/{r.market} h={r.horizon}: selected with project "
              f"settings={r.selected_project_settings:<18} with sklearn defaults="
              f"{r.selected_sklearn_defaults}")
    print("\nRESULT: " + ("selection UNCHANGED at every pair and horizon -- the "
                          "tree settings did not affect any reported result"
                          if changed.empty else
                          f"selection CHANGES at {len(changed)} pair-horizon(s) -- "
                          f"reported as a limitation; main pipeline not switched"))
    print(f"wrote {dest.relative_to(config.PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
