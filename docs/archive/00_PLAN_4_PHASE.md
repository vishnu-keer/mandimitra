> **SUPERSEDED — kept for the project history only.** This document was
> written under the first evaluation protocol (Sept 2026), which selected the
> "best" model on the test set. Its results and claims (for example "Gradient
> Boosting beats Naive by 7.33%") are withdrawn. Current results:
> `docs/02_METHODOLOGY.md`; current demo material: `docs/DEMO_SCRIPT.md`,
> `docs/JUDGE_QA.md`.

# Mandi Price Forecast — Zero-Cost 4-Phase Implementation Plan

**Supersedes:** Section K (Phase 0–16 plan) of `FULL_PRD_DRD.md`
**Retains:** Sections B, D, E1–E3, E9–E12, E14, H, I of the PRD/DRD as the specification
**Constraint added:** ₹0 budget. No paid service, no credit card, no cloud, anywhere in the stack.
**Written:** 14 Sept 2026

---

## 0. Before anything else — two things must be settled

### 0.1 The date problem

The PRD header says the exhibition is **15 Sept 2026**. Today is **14 Sept 2026**. If that date is still correct, you have roughly one working day, not a project timeline, and the 4 phases below have to be compressed into a single night.

That is survivable, but it changes one decision: **Phase 1's data acquisition must be a manual download, not a scraper.** A scraper for Agmarknet is a 3–6 hour debugging risk against an ASP.NET page with viewstate tokens. A manual filtered export is 15 minutes. If the exhibition has moved to a later date, tell me and I will put the scraper back into Phase 1 as a reproducibility feature.

**I need you to confirm the real deadline before Phase 1.**

### 0.2 The honest-result problem — read this before we write a line of code

Daily mandi prices for a single commodity in a single market behave close to a **random walk**. The consequence, which is well established in the price-forecasting literature and which you should expect to see in your own results:

> The naive baseline (today's price = tomorrow's prediction) is **very hard to beat** at a 1-day horizon. It is entirely possible that Random Forest and Gradient Boosting will **not** beat it at h=1, and will only start to win at h=3 or h=5.

Your PRD's success criterion D24 says "at least one model beats the naive baseline." I am flagging this now because that criterion may not be met, and if you discover that at 2 AM you will be tempted to fix it dishonestly — by tuning on the test set, by shrinking the test window until a model wins, or by quietly reporting the best of several runs.

The correct move, and the one that will actually impress technically literate judges, is to **treat "the naive baseline is competitive at short horizons" as a finding, not a failure.** It is the reason the baseline is in the design at all (PRD D17 already says this). A student who reports the measured margin and explains why it is small is demonstrably more credible than one claiming 96% accuracy.

> **OUTCOME, measured after the build (added 15 Sept 2026).** This prediction
> was directionally WRONG and the data settled it. Gradient Boosting *did* beat
> the naive baseline at 1 day ahead (+7.33% RMSE), the edge shrank to +1.23% at
> 2 days, and by 3 days nothing beat the baseline. So predictability decays with
> horizon rather than the reverse. The naive baseline also has the lowest MAE at
> every horizon. Full figures: `docs/02_METHODOLOGY.md` section 10.

**Revised success criterion for D24:**
> Every model is evaluated on an identical held-out chronological window; the naive baseline is reported honestly whether or not ML beats it; and the forecast horizon presented in the dashboard is the horizon where the measured results actually support a claim.

---

## 1. Final 4-phase architecture

```
                    ZERO-COST, FULLY LOCAL, SINGLE PROCESS

  PHASE 1 ─ DATA + ML FOUNDATION
  ┌──────────────────────────────────────────────────────────────┐
  │  Free public source (manual export)                          │
  │        │                                                     │
  │        ▼                                                     │
  │  data/raw/*.csv         ← never edited, provenance recorded  │
  │        │                                                     │
  │   src/data_prep.py      ← clean, standardise, calendar-align │
  │        │                                                     │
  │        ▼                                                     │
  │  data/interim/clean.parquet                                  │
  │        │                                                     │
  │   src/features.py       ← lags, MAs, volatility, calendar    │
  │        │                   (past-only, per group)            │
  │        ▼                                                     │
  │  data/processed/features.parquet   ◄── PHASE 1 GATE          │
  └──────────────────────────────────────────────────────────────┘
                              │
  PHASE 2 ─ FORECASTING ENGINE + EVALUATION
  ┌──────────────────────────────────────────────────────────────┐
  │   src/splits.py     ← chronological split, never shuffled    │
  │        │                                                     │
  │   src/models.py     ← Naive │ ARIMA │ RF │ GBM               │
  │        │               (one common fit/predict interface)    │
  │        ▼                                                     │
  │   src/metrics.py + src/evaluate.py                           │
  │        │            ← MAE, RMSE, MAPE, R², residuals,        │
  │        │              feature importance, best-model pick    │
  │        ▼                                                     │
  │   src/forecast.py   ← h-step-ahead forward forecast          │
  │        │                                                     │
  │        ▼                                                     │
  │   scripts/run_pipeline.py  →  outputs/*.csv  ◄── PHASE 2 GATE│
  └──────────────────────────────────────────────────────────────┘
                              │
  PHASE 3 ─ STREAMLIT APPLICATION
  ┌──────────────────────────────────────────────────────────────┐
  │   app.py  ← reads outputs/ + calls src/ directly, in-process │
  │             Streamlit + Plotly, 4 tabs, no network needed    │
  │                                          ◄── PHASE 3 GATE    │
  └──────────────────────────────────────────────────────────────┘
                              │
  PHASE 4 ─ TESTING + EXHIBITION READY
  ┌──────────────────────────────────────────────────────────────┐
  │   tests/ (leakage, chronology, metrics) · edge-case handling │
  │   README · requirements.txt · troubleshooting                │
  │   docs/03_EXHIBITION_SCRIPT.md (30s / 1min / 3min + Q&A)     │
  │                                          ◄── PHASE 4 GATE    │
  └──────────────────────────────────────────────────────────────┘
```

**The one architectural property that matters:** `app.py` imports from `src/`. It never re-implements anything. That is what kept the original DRD's FastAPI/Next.js upgrade path safe (DRD E2), and it stays true here even though we are not building those layers — so the option survives at zero cost.

---

## 2. What is included in each phase

Each phase ends at a **gate**. If the gate does not pass, we do not proceed — we fix. This is the single most important structural change from the 16-phase plan, where a silent failure in Phase 5 could surface as nonsense in Phase 10.

### PHASE 1 — DATA + ML FOUNDATION

**Objective:** a real, inspected, leakage-free feature table on disk.

| # | Task | Notes |
|---|---|---|
| 1.1 | Pick the data source | Ranked ladder in §2.1 below. Record the exact URL, filters and download date in `docs/01_DATA_SOURCE.md`. |
| 1.2 | Download raw CSV manually | Onion + Tomato, 2–3 Rajasthan markets, **2–3 years** of history (not 60–90 days — see §7 R2) |
| 1.3 | `scripts/inspect_data.py` | Row count, date min/max, gap histogram, duplicates, nulls, price units, distinct market/commodity spellings |
| 1.4 | `src/data_prep.py` | Parse dates, strip/title-case names, map spelling variants, drop exact duplicates, resolve same-day duplicates by rule, coerce prices to numeric, drop non-positive prices |
| 1.5 | **Calendar alignment** | Reindex each (commodity, market) group to a continuous daily index. Mandis do not trade every day. This is the step most student projects skip, and skipping it silently corrupts every lag feature. |
| 1.6 | Gap policy | Explicit and documented: forward-fill gaps ≤ N days, leave longer gaps as NaN, drop rows whose features are incomplete. Ffill is past-only, so it is leakage-safe. |
| 1.7 | `src/features.py` | lag 1/3/7 · MA 3/7 · rolling std 7 · day-of-week · month · days-since-last-observation |
| 1.8 | Leakage discipline | Decision point is **end of day t**: a feature may use data up to and including t (today's price is known); every target is strictly after t. All windows are backward-looking — no `center=True`, no `bfill`, no `interpolate`, no full-series statistic. Proven empirically by `verify_no_leakage()`, which rebuilds features on truncated data and asserts nothing before the cutoff changed. |
| 1.9 | Write `features.parquet` | Plus a printed coverage table per commodity/market |

**PHASE 1 GATE — all four must hold:**
1. `features.parquet` exists and every feature column is non-null for the rows we keep.
2. For at least one (commodity, market) pair: **≥ 400 usable daily rows.**
3. A hand-checked spot test: pick a random row, verify `lag_1` equals the modal price of the previous calendar day in `clean.parquet`.
4. `docs/01_DATA_SOURCE.md` names the source, the filters, and the download date.

If gate 2 fails for every pair, we change market selection — not the science.

#### 2.1 The data source ladder (verified free, no card, no paid tier)

Use in order. Stop at the first that clears the Phase 1 gate.

| Rank | Source | Why | Cost / friction |
|---|---|---|---|
| **1** | **[CEDA Agri Market Data](https://agmarknet.ceda.ashoka.edu.in/)** (Ashoka University) | Cleaned, compiled Agmarknet/DMI data with state/district/commodity filters, date-range selection and a Download Data button. Long daily history. Authoritative underlying source (Directorate of Marketing & Inspection, Min. of Agriculture). | Free, no login observed |
| **2** | **[Agmarknet 2.0 Price & Arrivals reports](https://www.agmarknet.gov.in/PriceAndArrivals/DatewiseCommodityReport.aspx)** | The primary government source itself. Date-range commodity reports, exportable. | Free, no key. ASP.NET UI — download manually, do not scrape under time pressure |
| **3** | **[data.gov.in — Variety-wise Daily Market Prices](https://data.gov.in/catalog/variety-wise-daily-market-prices-data-onion)** (per-commodity catalogs) | Official OGD platform, per-commodity historical files | Free; API key is free and card-free if you use the API instead of file download |
| **4** | **[Kaggle Agmarknet mirror](https://www.kaggle.com/datasets/anishaman07/agmarknet-india-commodity-prices-oct24-aug25)** | Pre-assembled, instantly usable | Free Kaggle account. **Disclose in the README that it is a third-party mirror of Agmarknet** — weaker provenance, still real data |
| **5** | **[India Data Portal — APMC arrivals and prices](https://ckandev.indiadataportal.com/dataset/apmc-arrivals-and-prices/resource/a83bd1ad-ba46-41c7-9a80-c75537ce1172)** | CKAN-hosted Agmarknet compilation | Free |

**Correction to PRD D15 / Risk 2.** The PRD plans to use the data.gov.in *"Current daily price of various commodities from various markets (Mandi)"* resource. That resource is a **current/rolling snapshot**, not an archive. You cannot build a multi-year time series from it by calling it once. Phase 1 must verify date coverage empirically before committing to any source — that is what task 1.3 is for. Do not assume.

**Also: never fabricate or pad rows.** A 400-row real dataset is defensible. A 2,000-row dataset with 1,600 synthetic rows ends the conversation with any judge who asks one follow-up question.

---

### PHASE 2 — FORECASTING ENGINE + MODEL EVALUATION

**Objective:** one command turns `features.parquet` into a model comparison table and a forward forecast.

| # | Task | Notes |
|---|---|---|
| 2.1 | `src/splits.py` | Sort by date, split by **date cutoff** (last ~20% of the date range = test). Assert `max(train.date) < min(test.date)`. No `train_test_split`, no `shuffle`, no `KFold`. |
| 2.2 | `src/metrics.py` | MAE, RMSE, MAPE, R². Guard MAPE against zero/near-zero prices. |
| 2.3 | Naive baseline | Prediction for t+h = last observed price at t. Trivially cheap, and it is the yardstick. |
| 2.4 | ARIMA | `statsmodels`. Needs a regular frequency series — this is why Phase 1 task 1.5 exists. Small grid over (p,d,q) selected **on the training window only**, by AIC. |
| 2.5 | RandomForestRegressor | scikit-learn, near-default params. Do not over-tune on a small dataset. |
| 2.6 | GradientBoostingRegressor | scikit-learn, near-default params. |
| 2.7 | **Direct multi-horizon targets** | See §2.2 — this is an architectural recommendation that differs from DRD E12 |
| 2.8 | `src/evaluate.py` | All models, same test window, same metrics → `outputs/model_comparison.csv`; per-row predictions → `outputs/predictions.csv`; residuals; RF/GBM importances → `outputs/feature_importance.csv` |
| 2.9 | Best-model selection | Chosen **programmatically by test RMSE**. Never hardcoded, never hand-picked. Written to the output file so the dashboard reads a computed value. |
| 2.10 | `src/forecast.py` | Forward forecast for the configured horizon, using the selected model |
| 2.11 | `scripts/run_pipeline.py` | `python scripts/run_pipeline.py --commodity Onion --market Jaipur` does all of the above |

**PHASE 2 GATE — all five must hold:**
1. One command produces all four `outputs/*.csv` files without error.
2. `max(train.date) < min(test.date)` asserted in code, not just intended.
3. All four models are scored on the **identical** test rows.
4. Best model is read from measured RMSE — verifiable by editing the data and watching the winner change.
5. The forward forecast dates are strictly after the last date in the dataset.

#### 2.2 Recommendation: direct multi-horizon, not recursive

DRD E12 implies a recursive forward forecast (feed prediction back in as the next lag). I recommend **direct multi-horizon** instead:

- **Recursive:** train one h=1 model, then feed its own prediction in as `lag_1` to predict day 2, and so on. Two problems — errors compound fast, and it is extremely easy to write the bug where day 2's `lag_1` accidentally uses the *actual* day-1 price. That bug inflates your metrics and is exactly what a sharp judge probes for.
- **Direct:** for each horizon h ∈ {1, 2, 3}, train a separate model whose target is `price[t+h]`, using only features available at time t. No feedback loop, so no compounding and **no path for that leakage bug to exist at all**.

Direct costs three model fits instead of one — irrelevant at this dataset size — and buys a cleaner leakage story. ARIMA already does h-step natively, and naive is "last observed price" for every h, so all four models stay directly comparable.

**Horizon:** start at **h = 1, 2, 3**. Extend to 5 or 7 only if the measured error at h=3 is still respectable. Let the data set the horizon, not the slide.

---

### PHASE 3 — COMPLETE STREAMLIT APPLICATION

**Objective:** a reliable, professional, fully offline dashboard.

Your 15 required sections, mapped to 4 tabs so nothing is buried and nothing needs scrolling past during a 3-minute demo:

| Tab | Contains (your numbering) |
|---|---|
| **Header** (always visible) | 1 title & purpose · 2 commodity selector · 3 market selector · 9 best-model badge · headline `st.metric` row |
| **1 · Price History** | 4 historical price chart (Plotly, range slider) · 5 dataset info (rows, date span, gaps, source, units) |
| **2 · Model Comparison** | 6 comparison table · 7 MAE/RMSE/MAPE/R² per model · 8 actual-vs-predicted on the test window · residual plot · naive-baseline delta stated explicitly |
| **3 · Forecast** | 10 forward forecast table + chart · 11 plain-language trend note (**rule-based, no LLM**) · 12 feature importance with a correlation≠causation caveat |
| **4 · Methodology** | 13 methodology · 14 limitations · 15 future work · data provenance · leakage-prevention explanation |

**Build rules:**
- Read precomputed `outputs/*.csv` where possible; use `@st.cache_data` for anything recomputed. The app must never feel slow in front of a judge.
- Every commodity/market combination in the selectors is filtered to those that actually passed the Phase 1 gate — an unselectable bad combination cannot crash.
- Plain-language trend note is a **rule** ("forecast is X% above the 7-day average → prices trending up"), not a model and not an API call. Zero cost, zero network, zero hallucination.
- No custom CSS beyond spacing. You asked not to over-design it; I agree. Reliability reads as professional at an exhibition. A broken animation does not.

**PHASE 3 GATE:**
1. `streamlit run app.py` works with **wifi switched off**.
2. Every commodity × market combination clicks through without a traceback.
3. Every number on screen is traceable to a file in `outputs/`.
4. All 15 required sections present.

---

### PHASE 4 — TESTING + EXHIBITION READY

**Objective:** the project cannot crash, and you cannot be caught out.

**Engineering:**

| # | Task |
|---|---|
| 4.1 | End-to-end run from raw CSV to dashboard, twice, from a clean shell |
| 4.2 | Every commodity × market combination clicked through |
| 4.3 | Insufficient-data case → clear message stating rows found vs rows required, never a crash, never a fake forecast |
| 4.4 | Missing-data / all-NaN column case handled |
| 4.5 | Invalid selection impossible by construction (selectors built from validated data) |
| 4.6 | `tests/test_features_no_leakage.py` — synthetic series with a known spike; assert no feature at time t reflects any value at t or later |
| 4.7 | `tests/test_split_chronology.py` — assert train/test date disjointness and ordering |
| 4.8 | `tests/test_metrics.py` — metrics against hand-computed values |
| 4.9 | `requirements.txt` with pinned versions |
| 4.10 | `README.md` — overview, architecture, setup, run, testing, troubleshooting, data provenance, honest limitations |
| 4.11 | Folder cleanup; `.gitignore`; **no `.env.example`** — see §3 |
| 4.12 | Git commit per phase |

**Exhibition material** → `docs/03_EXHIBITION_SCRIPT.md`, all 16 of your items: 30-second pitch · 1-minute · 3-minute demo script · problem statement · why it matters · dataset explanation · why these four models · why ARIMA · why RF/GBM · why LSTM is future work · how leakage was prevented · how accuracy was evaluated · limitations · future improvements · likely judge questions · honest answers.

**PHASE 4 GATE:** `pytest` passes · demo rehearsed twice end-to-end with a timer · you can answer "how do you know there is no leakage?" and "why should I believe these numbers?" without notes.

---

## 3. What is removed because of the zero-cost constraint

| Removed | From | Why it goes | What replaces it |
|---|---|---|---|
| FastAPI backend | PRD D11.7, DRD E6–E8, E16, Phase 11 | Unnecessary for a local single-user demo; a second process is a second failure mode | `app.py` imports `src/` directly, in-process. The upgrade path stays open because the ML core never knew about the UI. |
| Next.js + Tailwind + Recharts frontend | PRD D11.8, DRD E15, Phases 12–13 | Needs the API above; multi-hour integration risk for zero methodological gain | Streamlit + Plotly |
| PostgreSQL / Supabase | DRD E4, E26 | Paid tiers, accounts, network dependency | Parquet + CSV on disk. Faster than a DB at this size, and `git`-inspectable. |
| SQLite | DRD E4 | Not paid — just unnecessary. A relational DB for one flat table with no concurrent writers is ceremony. | Parquet |
| Streamlit Community Cloud deployment | DRD E22, Phase 15 | Genuinely free, but adds a GitHub-sync + venue-wifi failure mode on demo day | **Local run is the demo.** Optional free deploy *after* the exhibition — noted in future work, not built. |
| LLM API for the plain-language trend note | DRD E18 | Any hosted LLM API costs money or needs a card | Deterministic rule-based sentence from the forecast vs. the 7-day average. Cheaper, faster, cannot hallucinate a price. |
| `.env` / `.env.example` | PRD D18, DRD E17–E18, E24 | There are no secrets left in the project. No DB URL, no API key, no auth. | Removed entirely. `src/config.py` holds paths and hyperparameters in plain Python. You asked for `.env.example` "only if actually required" — it is not. |
| Auth / user accounts | PRD D18 | No users to authenticate in a local demo | — |
| Monitoring / observability | DRD E20, E23 | Nothing deployed to monitor | Python `logging` to stdout at INFO |
| MLflow-style versioning | DRD E13 | Overhead for a 4-model project | `joblib` cache in `models_store/`, filename encodes commodity + market + horizon + train-end date |
| LSTM / GRU | PRD D10, D14 | Not a cost issue — a **data and time** issue. Honest reason: insufficient history per market, and no time to tune it defensibly. | Documented as future work, with the real reason stated |
| CI / GitHub Actions | Phase 14 | Free, but zero value for a one-night solo build | `pytest` run manually |

**Net effect:** nothing of scientific substance was removed. Everything removed was either infrastructure with no bearing on the forecast's validity, or a paid dependency. The PRD's load-bearing content — real data, chronological evaluation, four-model comparison, leakage prevention, honest metrics — is fully intact and is now the *whole* project rather than 60% of it.

---

## 4. Final free technology stack

| Layer | Tool | License | Cost |
|---|---|---|---|
| Language | Python 3.10+ | PSF | Free |
| Data | pandas, NumPy | BSD | Free |
| Storage | CSV, or Parquet via `pyarrow` when installed (`src/store.py` falls back automatically, so pyarrow is optional) | Apache 2.0 | Free |
| Classical TS | statsmodels (ARIMA) | BSD | Free |
| ML | scikit-learn (RF, GBM) | BSD | Free |
| Charts | Plotly | MIT | Free |
| UI | Streamlit | Apache 2.0 | Free |
| Persistence | joblib | BSD | Free |
| Tests | pytest | MIT | Free |
| Version control | git + GitHub (public repo) | — | Free |
| Data | Agmarknet / DMI via CEDA or data.gov.in | Government open data | Free |

Deliberately **not** added: matplotlib (Plotly covers every chart; a second plotting library is two APIs to debug — add it only if a static PNG is needed for a poster), Prophet, XGBoost/LightGBM (GBM already represents boosting; another library is a new install risk for a marginal metric change), Docker, Poetry, Airflow.

Everything installs with one `pip install -r requirements.txt`. No account, no key, no card, anywhere in the stack.

---

## 5. Final folder structure

```
mandi-price-forecast/
├── data/
│   ├── raw/
│   │   └── agmarknet_raw.csv          # downloaded once, NEVER edited
│   ├── interim/
│   │   └── clean.parquet              # cleaned + calendar-aligned
│   └── processed/
│       └── features.parquet           # Phase 1 deliverable
│
├── docs/
│   ├── 00_PLAN_4_PHASE.md             # this document
│   ├── 01_DATA_SOURCE.md              # provenance: URL, filters, download date
│   ├── 02_METHODOLOGY.md              # leakage, split, metrics, model rationale
│   └── 03_EXHIBITION_SCRIPT.md        # Phase 4 pitch + demo + judge Q&A
│
├── src/
│   ├── __init__.py
│   ├── config.py                      # paths, lags, horizons, test fraction, thresholds
│   ├── data_prep.py                   # load → clean → standardise → calendar-align
│   ├── features.py                    # lags, MAs, volatility, calendar (pure functions)
│   ├── splits.py                      # chronological split + assertions
│   ├── metrics.py                      # MAE, RMSE, MAPE, R²
│   ├── models.py                      # Naive | ARIMA | RF | GBM, one interface
│   ├── evaluate.py                    # run all, compare, pick best, importances
│   └── forecast.py                    # forward h-step forecast
│
├── scripts/
│   ├── inspect_data.py                # Phase 1 verification report
│   └── run_pipeline.py                # Phase 2: one command, end to end
│
├── outputs/
│   ├── model_comparison.csv
│   ├── predictions.csv
│   ├── forecast.csv
│   └── feature_importance.csv
│
├── models_store/                      # joblib cache (not required to run)
│
├── tests/
│   ├── test_features_no_leakage.py
│   ├── test_split_chronology.py
│   └── test_metrics.py
│
├── app.py                             # Streamlit dashboard
├── requirements.txt
├── README.md
└── .gitignore
```

Notes on two deliberate naming choices: `models_store/` rather than `models/` so it can never be confused with `src/models.py` on an import path; and `scripts/` separated from `src/` so `src/` stays pure importable library code with no side effects at import time — which is what makes the future FastAPI option free.

---

## 6. Expected final application

**What you hand over:** a folder that runs on any laptop with Python 3.10+, offline, with two commands.

```bash
pip install -r requirements.txt
python scripts/run_pipeline.py --commodity Onion --market Jaipur
streamlit run app.py
```

**What a judge sees, in order, in about 3 minutes:**

1. A titled dashboard stating the problem and the data source, with commodity and market dropdowns and a visible "Best model: X (selected by test RMSE)" badge.
2. **Price History** — 2–3 years of real daily onion/tomato modal prices for a Rajasthan mandi, with an honest dataset panel: N rows, date span, how many days had no trading, price unit ₹/quintal, and where the data came from.
3. **Model Comparison** — a four-row table (Naive, ARIMA, Random Forest, Gradient Boosting) × four metrics (MAE, RMSE, MAPE, R²), all computed on the same held-out chronological window. An actual-vs-predicted line chart for the best model over that window, and a residual plot. The naive-baseline comparison stated in words, in whichever direction the data actually goes.
4. **Forecast** — a 1–3 day forward forecast with a plain-language trend note, and the tree model's feature importance chart with a stated caveat that importance is not causation.
5. **Methodology** — how the chronological split works, the specific mechanism that prevents leakage (backward-only windows within each group, direct multi-horizon targets so no prediction ever feeds a lag, and an automated truncate-and-compare proof), the limitations, and the future work.

**What it is not**, and what you should say plainly if asked: it is not a trading system, it does not model weather, festivals, MSP announcements, transport costs, arrivals shocks or policy, and it makes no claim about farmer income. It is a decision-support prototype, evaluated honestly on public data, over two commodities and a handful of markets.

That framing is not a weakness at a national exhibition. It is the difference between a project and a demo.

---

## 7. Remaining risks

Ranked by expected damage. The original 20 risks are folded in; these are the ones that actually threaten this plan.

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| **R1** | **Data source has less history than needed, or the download is awkward** | High | Fatal to Phase 1 | Five-source ladder (§2.1), tried in order. Phase 1 gate checks coverage *before* any modelling. Budget 45 minutes; if all five fail, escalate immediately rather than improvising. |
| **R2** | **PRD's 60–90-day minimum is too little** — with 7-day lags and a 20% test split, 90 days leaves ~16 test points and a meaningless MAPE | High | Silently invalid metrics | Target **2–3 years / ≥400 usable rows** per pair. Hard gate. |
| **R3** | **No model beats the naive baseline** | Medium-high | Only fatal if you hide it | Pre-committed honest framing (§0.2). Report h=1/2/3 so you can show where ML does and does not add value. |
| **R4** | **Mandi non-trading days corrupt lag features** | High if ignored | Invalid features, invisible | Calendar reindexing is a mandatory Phase 1 task (1.5), plus an explicit, documented gap policy (1.6) |
| **R5** | **Leakage bug survives to the demo** | Medium | Credibility-fatal | Three defences: backward-only window discipline, direct multi-horizon targets (removes the recursive-lag bug class entirely), and `verify_no_leakage()` — an automated truncate-and-compare proof that runs on every feature build |
| **R6** | **Time** — one day, four phases | High | Scope collapse | Phase order is dependency order. If time runs out mid-Phase 3, you still have a working pipeline and real metrics — a smaller honest project, not a broken big one. |
| **R7** | **ARIMA fails to converge or throws on gappy data** | Medium | Loses one of four models | Depends on Phase 1 task 1.5. Wrap in try/except; if it genuinely fails for a pair, report "ARIMA did not converge for this series" in the table rather than blanking the row or faking a number. |
| **R8** | **R² is misleading on a near-random-walk series** | Certain | Judges may probe it | Report it, but lead with RMSE and MAE. Be ready to say why R² looks flattering on persistent level data. |
| **R9** | **Overfitting on a small dataset** | Medium | Inflated train scores | Near-default hyperparameters, no tuning on the test set, and report train *and* test error side by side so the gap is visible rather than hidden |
| **R10** | **The ₹92,000 crore statistic is uncited** | Certain as written | One judge question sinks the opening | Find and cite the actual source in the README and the script, or soften to "estimates of India's annual post-harvest food loss run into the tens of thousands of crores." Do not lead a national exhibition with a number you cannot attribute. |
| **R11** | **Streamlit crashes on an edge-case selection** | Medium | Visible failure mid-demo | Selectors built only from validated pairs; try/except with readable messages; Phase 4 clicks every combination |
| **R12** | **Laptop / environment failure at the venue** | Low-medium | Total | Full local install, no network dependency, `requirements.txt` pinned, repo pushed to GitHub as a backup, charger packed, plus screenshots of the working dashboard in `docs/` as a last-resort fallback |
| **R13** | **Package install fails at the venue** | Low | Blocks setup | Install and verify **tonight**, not on demo morning. Commit `requirements.txt` with pinned versions. |

**Retired from the original risk list** because the zero-cost restructure removed the cause: FastAPI/Next.js integration overrun (R9 original), API signup friction as a blocker (R2 original — now one of five ranked options), DB setup, and deployment failure.

---

## 8. What I need from you before Phase 1

1. **Confirm the deadline.** Is the exhibition still 15 Sept 2026 (tomorrow), or has it moved? This changes whether Phase 1 uses a manual download or a reproducible scraper.
2. **Confirm Python.** Run `python3 --version` on your laptop and tell me the output.
3. **Accept or reject the two methodology changes I am recommending against the DRD:** (a) direct multi-horizon instead of recursive forecasting (§2.2), and (b) the revised honest success criterion replacing "at least one model beats naive" (§0.2).
4. **Confirm markets.** Jaipur (Bassi / Chomu / Jaipur Grain) plus one more Rajasthan mandi, Onion + Tomato — or do you want different ones? Final selection is subject to what actually clears the Phase 1 data gate.

Reply and I will start **Phase 1** in the format you specified: objective, what we are building, folder structure, exact filenames, complete code, terminal commands, expected output, verification steps, common errors — then stop.
