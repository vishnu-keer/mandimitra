"""Figures and a key-numbers file for the paper, report, deck and poster.

    python presentation/tools/make_figures.py

Everything is computed from the committed files in data/ and outputs/. Nothing
is typed in by hand. Writes:
    research/figures/fig1_price_history.png
    research/figures/fig2_test_rmse.png
    research/figures/fig3_dm_tests.png
    research/figures/fig4_interval_coverage.png
    research/figures/fig5_unchanged_share.png
    research/key_numbers.json

Run it in the documentation environment (presentation/requirements-docs.txt),
not the pipeline environment.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs"
FIG = ROOT / "research" / "figures"
FIG.mkdir(parents=True, exist_ok=True)

INK, MUTED, GREEN = "#1d2430", "#5b6472", "#1f6f4a"
COL = {"Naive": "#6b7280", "ARIMA": "#c27c2c", "RandomForest": "#3b7dc4",
       "GradientBoosting": "#2a9d8f", "RandomForest-delta": "#8e5ea2"}
LABEL = {"Naive": "Naive", "ARIMA": "ARIMA", "RandomForest": "Random Forest",
         "GradientBoosting": "Gradient Boosting",
         "RandomForest-delta": "RF (predicts change)"}
MODELS = list(COL)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                     "axes.edgecolor": "#c9ced6", "axes.labelcolor": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "savefig.dpi": 200, "savefig.bbox": "tight"})

best = pd.read_csv(OUT / "best_model.csv")
comp = pd.read_csv(OUT / "model_comparison.csv")
bounds = pd.read_csv(OUT / "split_boundaries.csv")
dm = pd.read_csv(OUT / "experiments" / "dm_test.csv")
sea = pd.read_csv(OUT / "experiments" / "seasonal_naive.csv")
hyper = pd.read_csv(OUT / "experiments" / "hyperparameter_sensitivity.csv")
legacy = pd.read_csv(OUT / "legacy" / "best_model.csv")
clean = pd.read_parquet(ROOT / "data" / "interim" / "clean.parquet")
feats = pd.read_parquet(ROOT / "data" / "processed" / "features.parquet")
test = comp[comp["split"] == "test"]

# ---------------------------------------------------------------- fig 1
fig, axes = plt.subplots(2, 1, figsize=(9, 5.2), sharex=True)
for ax, c in zip(axes, ["Onion", "Tomato"]):
    s = clean[(clean.commodity == c) & (clean.market == "Jaipur") & clean.observed]
    ax.plot(s["date"], s["modal_price"], color=INK, lw=0.8)
    b = bounds[(bounds.commodity == c) & (bounds.horizon == 1)].iloc[0]
    ax.axvspan(pd.Timestamp(b.cv_start), pd.Timestamp(b.cv_end), color="#8cc0a4", alpha=.25,
               lw=0, label="CV folds (choose the model)")
    ax.axvspan(pd.Timestamp(b.test_start), pd.Timestamp(b.test_end), color=GREEN, alpha=.18,
               lw=0, label="Untouched test")
    ax.set_ylabel("Rs. / quintal")
    ax.set_title(f"{c}, Jaipur — reported daily wholesale price", loc="left",
                 fontsize=10, color=INK)
axes[0].legend(loc="upper left", frameon=False, fontsize=8)
fig.savefig(FIG / "fig1_price_history.png")
plt.close(fig)

# ---------------------------------------------------------------- fig 2
fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), sharey=False)
for ax, c in zip(axes, ["Onion", "Tomato"]):
    t = test[test.commodity == c]
    x = np.arange(3)
    w = 0.16
    for i, m in enumerate(MODELS):
        v = [t[(t.horizon == h) & (t.model == m)]["rmse"].iloc[0] for h in (1, 2, 3)]
        ax.bar(x + (i - 2) * w, v, w, color=COL[m], label=LABEL[m])
    for h in (1, 2, 3):
        sel = best[(best.commodity == c) & (best.horizon == h)]["best_model"].iloc[0]
        i = MODELS.index(sel)
        v = t[(t.horizon == h) & (t.model == sel)]["rmse"].iloc[0]
        ax.text(h - 1 + (i - 2) * w, v + 4, "▼", ha="center", color=INK, fontsize=9)
    ax.set_xticks(x, ["1 day", "2 days", "3 days"])
    ax.set_title(f"{c}/Jaipur — test RMSE (Rs./q); ▼ = chosen by CV", loc="left",
                 fontsize=10, color=INK)
    ax.grid(axis="y", color="#eef0f3")
axes[0].legend(frameon=False, fontsize=7.5, ncol=2, loc="upper left")
fig.savefig(FIG / "fig2_test_rmse.png")
plt.close(fig)

# ---------------------------------------------------------------- fig 3
sq = dm[dm["loss"] == "squared"].copy()
sq["col"] = sq["commodity"] + " h=" + sq["horizon"].astype(str)
piv = sq.pivot_table(index="model", columns="col", values="dm_stat")
pv = sq.pivot_table(index="model", columns="col", values="p_holm")
order = [m for m in MODELS if m in piv.index]
piv, pv = piv.loc[order], pv.loc[order]
fig, ax = plt.subplots(figsize=(9, 2.9))
lim = np.nanmax(np.abs(piv.values))
im = ax.imshow(piv.values, cmap="RdBu", vmin=-lim, vmax=lim, aspect="auto")
ax.set_xticks(range(piv.shape[1]), piv.columns, fontsize=8)
ax.set_yticks(range(piv.shape[0]), [LABEL[m] for m in piv.index], fontsize=8)
for i in range(piv.shape[0]):
    for j in range(piv.shape[1]):
        star = "*" if pv.values[i, j] < 0.05 else ""
        v = piv.values[i, j]
        ax.text(j, i, f"{v:+.1f}{star}", ha="center", va="center", fontsize=8,
                color="white" if abs(v) > 0.55 * lim else INK)
ax.set_title("Diebold–Mariano vs Naive, squared error, test period "
             "(negative = model better; * Holm p<0.05)", loc="left", fontsize=9.5)
fig.colorbar(im, ax=ax, fraction=0.025, pad=0.01)
fig.savefig(FIG / "fig3_dm_tests.png")
plt.close(fig)

# ---------------------------------------------------------------- fig 4
fig, ax = plt.subplots(figsize=(6.5, 3))
lab = [f"{r.commodity[:3]} h={r.horizon}" for r in best.itertuples()]
ax.bar(lab, best["interval_test_coverage"], color="#9aa3ad")
ax.axhline(80, color=GREEN, lw=1.5, ls="--")
ax.text(len(lab) - 0.5, 81.5, "nominal 80%", ha="right", color=GREEN, fontsize=8)
ax.set_ylim(0, 100)
ax.set_ylabel("% of test outcomes inside")
ax.set_title("80% ranges from CV errors, checked once on test", loc="left", fontsize=10)
fig.savefig(FIG / "fig4_interval_coverage.png")
plt.close(fig)

# ---------------------------------------------------------------- fig 5
unch = {}
for (c, m), g in clean[clean.observed].groupby(["commodity", "market"]):
    d = g.sort_values("date")["modal_price"].diff().dropna()
    unch[f"{c}/{m}"] = round(100 * float((d == 0).mean()), 1)
fig, ax = plt.subplots(figsize=(6.5, 2.8))
ks = sorted(unch, key=unch.get)
ax.barh(ks, [unch[k] for k in ks], color=[GREEN if "Jaipur" in k else "#c9ced6" for k in ks])
for i, k in enumerate(ks):
    ax.text(unch[k] + 1, i, f"{unch[k]:.1f}%", va="center", fontsize=8)
ax.set_xlim(0, 100)
ax.set_xlabel("% of reported days with the same price as the previous report")
fig.savefig(FIG / "fig5_unchanged_share.png")
plt.close(fig)

# ----------------------------------------------------------- key numbers
def r2(x):
    return None if pd.isna(x) else round(float(x), 2)


kn = {"source": "Generated by presentation/tools/make_figures.py from outputs/",
      "data_end": str(pd.to_datetime(clean["date"]).max().date()),
      "data_start": str(pd.to_datetime(clean["date"]).min().date()),
      "unchanged_pct": unch,
      "selected": [], "dm_summary": {}, "legacy": [], "seasonal_cv_rmse": {},
      "hyper_selection_changes": []}
for r in best.itertuples():
    t = test[(test.commodity == r.commodity) & (test.horizon == r.horizon)]
    kn["selected"].append({
        "pair": f"{r.commodity}/{r.market}", "h": int(r.horizon), "model": r.best_model,
        "cv_rmse": r2(r.selected_valid_rmse), "test_rmse": r2(r.best_test_rmse),
        "test_mae": r2(r.best_test_mae), "naive_rmse": r2(r.naive_test_rmse),
        "naive_mae": r2(r.naive_test_mae), "vs_naive_pct": r2(r.improvement_over_naive_pct),
        "posthoc_best": r.posthoc_lowest_test_rmse_model,
        "posthoc_rmse": r2(r.posthoc_lowest_test_rmse), "lowest_mae_model": r.lowest_mae_model,
        "n_test": int(r.n_test), "interval_coverage": r2(r.interval_test_coverage),
        "all_test_rmse": {m: r2(t[t.model == m]["rmse"].iloc[0]) for m in MODELS}})
for loss in ("squared", "absolute"):
    s = dm[dm["loss"] == loss]
    kn["dm_summary"][loss] = {"n": int(len(s)),
                              "model_better": int(((s.p_holm < .05) & (s.dm_stat < 0)).sum()),
                              "naive_better": int(((s.p_holm < .05) & (s.dm_stat > 0)).sum())}
g = dm[(dm.loss == "squared") & (dm.commodity == "Onion") & (dm.horizon == 1)
       & (dm.model == "GradientBoosting")].iloc[0]
kn["dm_onion_h1_gbm"] = {"dm": r2(g.dm_stat), "p": round(float(g.p_value), 3)}
for r in legacy.itertuples():
    kn["legacy"].append({"h": int(r.horizon), "model": r.best_model,
                         "test_rmse": r2(r.best_test_rmse),
                         "vs_naive_pct": r2(r.improvement_over_naive_pct)})
cvs = sea[sea.block.str.startswith("cv")].groupby(["commodity", "horizon", "model"])["rmse"].mean()
for (c, h, m), v in cvs.items():
    kn["seasonal_cv_rmse"].setdefault(f"{c} h={h}", {})[m] = round(float(v), 1)
hs = hyper.drop_duplicates(["commodity", "market", "horizon"])
for r in hs[hs.selected_project_settings != hs.selected_sklearn_defaults].itertuples():
    kn["hyper_selection_changes"].append({"pair": f"{r.commodity}/{r.market}",
                                          "h": int(r.horizon),
                                          "project": r.selected_project_settings,
                                          "defaults": r.selected_sklearn_defaults})
usable = {}
for (c, m), g in feats.groupby(["commodity", "market"]):
    usable[f"{c}/{m}"] = int((g["y_h1"].notna() & g["y_h1_observed"].astype(bool)).sum())
kn["usable_h1"] = usable
(ROOT / "research" / "key_numbers.json").write_text(json.dumps(kn, indent=2) + "\n")
print("wrote", len(list(FIG.glob("*.png"))), "figures and research/key_numbers.json")
