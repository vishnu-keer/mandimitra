# Test report

## Release of 28 October 2026 (competition package)

Every result below was observed on 28 Oct 2026. Where something was **not**
tested, it says so. The 27 October report follows below for history.

| Check | Command / method | Result |
|---|---|---|
| Clean clone, CPython 3.11 | `pip install -r requirements.txt && pip check && python -m pytest` | install OK, no broken requirements, **154 passed** (28.0 s) |
| Clean clone, CPython 3.12 | same | **154 passed** (29.2 s) |
| Pipeline gates (clean clone, both versions) | `extract_rajasthan.py`, `build_features.py`, `run_pipeline.py --all-pairs` | PHASE 1 GATE: PASS · PHASE 2 GATE: PASS |
| Rebuild vs committed results | `check_reproducible.py` | PASS; `git status` shows **0** tracked files changed (byte-identical) |
| Experiment outputs | re-ran `experiment_seasonal_naive.py`, `experiment_significance.py` | byte-identical to the committed CSVs |
| Browser, local | Playwright, 33 checks: 2 series × 7 tabs, 3 horizons, Hindi, dark OS preference, 375 px | **33/33**, no console or page errors, first load 2.5 s |
| Browser, live app | <https://mandimitra.streamlit.app/>, DOM checks inside the app frame | both series × 6 tabs (before this update) render without exception; actual-vs-predicted at 1/2/3 days; Hindi; no overflow at 375 px |
| CI on GitHub | owner's screenshot of the Actions page | runs #1 and #2 green |
| Deck | `validate.py`, LibreOffice render, placeholder scan | passed; 12 slides rendered and inspected |
| QR codes | decoded from the rendered poster PDF and deck PDF with OpenCV | both decode to `https://mandimitra.streamlit.app/` and `https://github.com/vishnu-keer/mandimitra`; both URLs opened and checked |

### New tests in this release (33)

| File | Tests | Guarantees |
|---|---:|---|
| `test_live_data.py` | 25 | record validation (fields, dates, numbers, min ≤ modal ≤ max, range, duplicates); a schema change is rejected and reported; empty, failed, invalid or partial downloads never replace the last good data; paging follows `total` and refuses a truncated download; the API key never appears in errors, status or files; freshness is computed from the observation date |
| `test_significance.py` | 5 | identical forecasts give no statistic; a clearly better model is significant with a negative sign; swapping models flips the sign; equal-quality noise is usually not significant; missing values are dropped pairwise |
| `test_dashboard.py` | +3 | Latest-prices tab says "Not connected" without a key; a stale snapshot is labelled stale; the overview's freshness comes from the observation date |

### An environment problem found during testing

Installing the chart and QR libraries into the project's test environment
upgraded numpy to 2.5.4 and broke 37 tests with a numpy-2 deprecation error.
The project code was not at fault; the environment was restored to the pins
and the presentation tools now live in a separate environment
(`presentation/requirements-docs.txt`).

### Not tested

- A real call to the data.gov.in current-price API (needs the owner's key).
- The redeployed app after this update (not deployed — pending approval).
- The Mac's own environment for this update (run `python -m pytest` there).

---

## Release of 27 October 2026

## Environments

| Where | Python | How |
|---|---|---|
| Clean clone, fresh virtualenv | CPython 3.11 and 3.12, Linux | `git clone` → `pip install -r requirements.txt` → every CI step |
| Development copy | CPython 3.12, Linux | pipeline, tests, browser checks |
| Your laptop's project folder (via the desktop link) | CPython 3.10, Linux VM | pipeline + tests on the actual folder |
| **Your Mac's own `.venv` (CPython 3.11.9, macOS)** | — | **Not run by me.** See "Manual checks". |

## 1. Install from a clean clone

```bash
git clone <repo> && cd <repo>
python3.11 -m venv .venv && . .venv/bin/activate      # and again with 3.12
pip install -r requirements.txt && pip check
```

Result on 3.11 and 3.12: install succeeded, `pip check` → *No broken
requirements found.* The transitive pins (`scipy==1.15.3` etc.) were added
after an unpinned install pulled scipy 1.17.1, which raised a
`DeprecationWarning` inside statsmodels and failed the strict test run.

## 2. Test suite

```bash
python -m pytest
```

| Environment | Result |
|---|---|
| Clean clone, 3.11 | **121 passed** in 20.5 s |
| Clean clone, 3.12 | **121 passed** in 20.7 s |
| Development copy, 3.12 | **121 passed** in 17.2 s |
| Your project folder after the update, 3.10 (desktop link) | **121 passed** in 7.4 s |

`FutureWarning` and `DeprecationWarning` are errors (`pytest.ini`). No test is
skipped when the data is present.

| File | Tests | What it guarantees |
|---|---:|---|
| `test_features_no_leakage.py` | 9 | no feature can see the future; no `bfill`/`interpolate` in `src/` |
| `test_splits_chronology.py` | 10 | chronological, disjoint, date-based splits |
| `test_evaluation_protocol.py` | 33 | CV folds expand and never overlap test; embargo on target dates; identical rows per model; selection never reads test; ARIMA train diagnostic has a real sample and only uses the past |
| `test_forecast_validation.py` | 17 | forecast dates strictly after the last data date; every candidate present; Naive retained |
| `test_data_validation.py` | 19 | zeros → missing; range filter; duplicates; observed-target masks; gate |
| `test_metrics.py` | 10 | MAE/RMSE/MAPE/R² against hand-computed values and undefined cases |
| `test_provenance.py` | 5 | government files unaltered (SHA-256); extract reproduces the original file byte for byte |
| `test_manifest.py` | 6 | every hash in the run manifest matches its file; manifest matches results; the dashboard and its data layer cannot import a model library |
| `test_dashboard.py` | 12 | the real `app.py` (Streamlit AppTest) renders every pair, horizon, language and toggle without an exception; the comparison chart's default selection is never empty; missing outputs give an actionable message |
| `conftest.py` fixtures | — | synthetic inputs for unit tests only, never project data |

## 3. Pipeline gates

```bash
python scripts/extract_rajasthan.py
python scripts/build_features.py            # PHASE 1 GATE: PASS
python scripts/run_pipeline.py --all-pairs  # PHASE 2 GATE: PASS
```

Phase 1: Onion/Jaipur 1,002 and Tomato/Jaipur 995 usable 1-day rows; Jodhpur
and Kota excluded by the 400-row gate. Phase 2 gate checks (all PASS): all
outputs written; identical rows per CV fold, pooled CV and test; all 5
candidates present; no fitting target crosses a fold origin or the test cutoff;
selection by CV not test; ARIMA training diagnostic has n ≥ 100 or is null;
every train metric labelled; forecast dates after the last observed date.
Runtime about 20–60 s.

## 4. Determinism and reproducibility

| Check | Result |
|---|---|
| Same environment, rebuilt twice from the government files | all 11 data/output files **byte-identical** |
| CPython 3.11 vs 3.12 (Linux) | **byte-identical** |
| Clean clone: rebuild, then `git status` | no tracked file changed |
| CPython 3.10 vs 3.12 | ARIMA predictions differ by ≤ 0.042 Rs./q, ARIMA RMSE by ≤ 0.002; everything else identical; **same selected models** |
| `scripts/check_reproducible.py` against the 3.10 build | PASS |
| Negative controls: flip one selected model; nudge one RMSE by 0.1 | both correctly **FAIL** |

## 5. The real app in a browser

Streamlit server (`streamlit run app.py`, headless) driven by Playwright
Chromium — `verify_ui.js`, 31 checks, **31 passed**:

- first load 2.3 s (nothing is trained on page load; also enforced by a test);
- Onion and Tomato × all six tabs: no Streamlit exception;
- Model evaluation × 1, 2, 3 days × both pairs: the *Actual vs predicted* chart
  renders with two models pre-selected, and the selection protocol is named;
- Forecast tab: origin date, target dates and the "not advice" notice present;
- Hindi mode renders;
- browser console and page errors: **none**;
- OS dark-mode preference: page stays light (`rgb(255, 255, 255)`);
- 390 px phone width: no horizontal overflow.

Error states (AppTest): missing `features.parquet` → "The data has not been
built yet" plus the exact command; missing `outputs/` → "Model results are
missing" plus the command; no traceback in either. Server health endpoint
answered in under 5 s.

## 6. Repository contents

Simulated `git init && git add -A` on a copy containing a `.venv`, `.bak`
files, `_to_delete/`, `.DS_Store`, `__pycache__`, a `.env` and a
`.streamlit/secrets.toml`: **90 files tracked (7.9 MB; 91 with this report), none of those
included**, and every file `app.py` reads is tracked. A scan of tracked text
files for keys, tokens, passwords, private keys and personal paths found none.

## 7. Live deployment (28 Oct 2026)

<https://mandimitra.streamlit.app/>, deployed from `vishnu-keer/mandimitra`,
branch `main`, Python 3.12. Checked in a browser against the live app: both
series × all six tabs with no Streamlit exception; Model evaluation × 1, 2, 3
days for both series with the *Actual vs predicted* chart rendered and two
models pre-selected; Onion overview Rs. 550 / 56% / "No"; Tomato overview
Rs. 1,500 with forecasts Rs. 1,484 / 1,508 / 1,502; Forecast tab shows origin
and target dates; Hindi mode renders; 375 px phone width with no horizontal
overflow. The only browser console errors are 404s from Streamlit Cloud's own
`/api/v2/user/details` (the viewer is not signed in to Streamlit), not from
the app; every app asset loaded with status 200.

The first deployment attempt failed because the platform's default interpreter
was Python 3.14; redeploying with Python 3.12 fixed it (`docs/DEPLOY.md`).

## Manual checks (not done by me)

1. **Your Mac:** `source .venv/bin/activate && python -m pytest` — expect
   121 passed. If you rebuild the pipeline on the Mac, ARIMA's last digits may
   change; then run `python scripts/make_manifest.py`, and `test_manifest.py`
   will pass again.
2. **Licence:** open the dataset page on data.gov.in and confirm it shows
   GODL-India (the site blocks automated reading).
3. **Hindi wording:** have a native speaker read the overview once.
4. **Projector:** check colours and font size on the actual projector.
5. GitHub Actions: confirm the CI run is green on the repository's Actions tab.

## Known limitations of the testing

- I cannot read the repository's Actions results from here; the workflow's
  steps were executed by hand in clean environments.
- No accessibility audit beyond contrast-conscious colours and the phone check.
- No load testing; a single-user demo app.
