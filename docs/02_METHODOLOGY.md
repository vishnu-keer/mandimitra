# Methodology

Everything a technically literate reviewer needs to check this project's
validity. Where a choice was a judgement call, the reasoning and its measured
consequence are both recorded. Numbers below are from the committed
`outputs/*.csv` (hashes in `docs/RUN_MANIFEST.md`).

---

## 1. Data

Official Government of India daily wholesale prices (data.gov.in, Department of
Consumer Affairs), Onion and Tomato, 1 Jan 2009 – 28 Apr 2015, Rs. per quintal.
Two series pass the data gate: **Onion/Jaipur** and **Tomato/Jaipur**.
Jodhpur and Kota report too rarely and are excluded, with reasons, rather than
forced. Full provenance: `docs/01_DATA_SOURCE.md`. Per-series counts:
`docs/DATA_REPORT.md`.

**Historical, not live.** No forecast in this project is about today.

## 2. Cleaning

| Step | Rule | Onion / Jaipur | Tomato / Jaipur |
|---|---|---|---|
| Header normalisation | `src/schema.py` maps source spellings to one schema | — | — |
| Date parsing | day-first (`13-01-10` = 13 Jan 2010) | 0 unparseable | 0 unparseable |
| **Zero prices** | `0` is the source's *not reported* code → missing | 263 of 1,551 | 323 of 1,551 |
| Range filter | outside Rs. 50 – 100,000 /q rejected as errors | — | — |
| De-duplication | one row per commodity, market, date | 0 duplicates | 0 duplicates |
| **Result** | genuine reported prices | **1,288** | **1,228** |

## 3. Calendar alignment

Each series is reindexed to a **continuous daily calendar** before any feature
is built. On a frame with gaps, `shift(1)` means "the previous row", which may
be yesterday or nine days ago. An earlier version had exactly this bug (gap
rows dropped too early); the Phase 1 gate's lag spot-check caught it. Gap rows
are now kept through feature engineering and removed only afterwards.

**Gap policy.** A gap of up to `MAX_FFILL_DAYS = 2` may carry the last reported
price forward **as an input**. Longer gaps stay empty. Forward-fill only looks
backwards, so it cannot leak. Measured on Onion/Jaipur:

| `MAX_FFILL_DAYS` | Feature rows | Carried forward | Usable at h=1 |
|---|---|---|---|
| 1 | 894 | 30.8% | 391 — too thin |
| **2** | **1,666** | **35.3%** | **1,002 — chosen** |
| 3 | 1,892 | 37.8% | 1,145 |

## 4. Features

**Decision point = end of day *t*.** A feature may use anything up to and
including *t*; every target is strictly after *t*.

Twelve features: `price_t`, `lag_1`, `lag_3`, `lag_7`, `ma_3`, `ma_7`, `vol_7`,
`ret_1`, `dev_from_ma`, `days_since_obs`, `dow`, `month`. (A thirteenth,
`spread_pct`, needs min/max prices this source does not have; it is all-empty
and dropped automatically.)

A window of *w* calendar days needs at least `ceil(0.6 w)` reported prices,
because a mandi that closes weekly can never supply 7 consecutive reports.
Demanding all 7 cut the usable series from 1,288 rows to 211.

## 5. Leakage defences

1. **Backward-only windows.** No `center=True`, `bfill` or `interpolate`
   anywhere in `src/`; a test tokenises the source and fails if one appears.
   That test caught a real latent leak once (ARIMA's input was back-filled from
   a later price) — fixed.
2. **Direct multi-horizon targets.** One model per horizon, target
   `price[t+h]`. No prediction is ever fed back as an input, so the classic
   recursive-forecast leak cannot exist.
3. **Truncate-and-compare proof.** `verify_no_leakage()` rebuilds every feature
   on data cut at the 70th-percentile date and asserts every earlier value is
   identical. A second test multiplies future prices by 10 and asserts no
   earlier feature moves.
4. **Target embargo** at every boundary (section 7).
5. **Causal ARIMA.** ARIMA forecasts come from a Kalman filter that only sees
   prices up to the forecast origin; a test perturbs later prices to prove it.

## 6. Targets must be real

A row is trained on or scored **only if the mandi actually reported a price on
the day being forecast** (`y_h{h}_observed`). Before this rule, 40% of 1-day
targets were carried-forward values, which would have handed the Naive
baseline free perfect hits. Usable rows at h = 1 / 2 / 3: Onion 1,002 / 1,005 /
1,026; Tomato 995 / 1,003 / 1,021.

## 7. Evaluation protocol

```
|---------------------- development 80% of dates ----------------------|-- test 20% --|
|----- initial 50% -----|- fold 1 -|- fold 2 -|- fold 3 -|- fold 4 -|
   each fold: fit on everything before its origin, score on the block after it
```

- **Final test:** the last 20% of distinct dates (Feb 2014 – Apr 2015, about
  200 scored days per horizon). It is scored **once, after selection**. Nothing
  is chosen, tuned or admitted using it.
- **Selection:** rolling-origin cross-validation inside the development period,
  4 expanding folds over its second half. **Rule, fixed before the results were
  seen: lowest mean per-fold RMSE.** Mean of folds rather than pooled RMSE, so
  one spike fold cannot decide alone.
- **Embargo:** a training row whose *target date* reaches past a fold origin or
  the test cutoff is removed. (The first version split on the feature date and
  let 1–3 rows per horizon carry targets inside the test window.)
- **Identical rows:** within a fold and on test, every candidate is scored on
  exactly the same rows. The Phase 2 gate asserts it.
- **Final models** are refitted on the whole development block and scored once
  on test.

**Why rolling origin and not one validation block.** The first redesign used a
single 20% validation block. On Onion/Jaipur that block fell on the October
2013 price spike (Rs. 4,500/q against a training maximum of Rs. 3,300) and one
year decided everything. This change was made after seeing those validation
results — the test window was not consulted — and it is disclosed here because
it was a choice made with knowledge of validation behaviour.

## 8. Metrics

| Metric | Meaning | How to read it here |
|---|---|---|
| **MAE** | mean absolute error, Rs./q | "Typically off by Rs. X on an ordinary day" |
| **RMSE** | root mean squared error, Rs./q | Punishes big misses more. **The selection metric.** |
| **MAPE** | mean absolute % error | Comparable across commodities; actuals below Rs. 1 excluded |
| **R²** | variance explained | In the CSV, not on screen: on a series that mostly repeats itself it is high for any model |

When RMSE and MAE pick different winners, both are shown and the difference is
explained (MAE = the ordinary day, RMSE = the rare big miss).

## 9. Candidates

| Model | Role | Settings |
|---|---|---|
| **Naive** | Tomorrow = today. The yardstick. | Nothing fitted |
| **ARIMA** | Classical reference | Order by AIC on the fitting window from 7 candidates; causal h-step forecasts |
| **Random Forest** | Non-linear trees | 300 trees, depth 6, min leaf 8, `max_features="sqrt"` |
| **Gradient Boosting** | Boosted trees | 200 stages, learning rate 0.05, depth 3, min leaf 8, subsample 0.9 |
| **Random Forest-delta** | Predicts the price *change*, then adds today's price | as Random Forest |

**Why the fifth candidate exists.** Level-target trees can only predict averages
of training prices, so they cannot follow a spike to a new high (in the
October 2013 fold they could not predict above Rs. 2,197/q). A delta target
fixes that. It was tested in `scripts/experiment_delta_target.py` under a rule
written before the run: *join the candidates only if it beats Naive on mean CV
RMSE at one or more horizons*. Random Forest-delta did on Tomato/Jaipur (1 and
3 days) and joined; Gradient Boosting-delta did not anywhere. Admitting a
candidate on CV and then selecting on CV makes CV scores slightly optimistic;
the test window is untouched by both steps.

### Audit: did the test window leak in through the tree settings?

Yes, partly, and it was measured. The depth and leaf limits were fixed in
Phase 2 under the old protocol, and their effect was at the time checked
**on the test window** (Random Forest 98.5 → 93.4 RMSE at h=1). Keeping a
setting after seeing its test error is mild test-set tuning.

`scripts/experiment_hyperparameter_sensitivity.py` re-ran every tree candidate
with scikit-learn's **default** settings (which nobody chose) on the same CV
folds, under a rule written before it ran: report the result; do not switch
the pipeline either way.

| Pair | h | Selected (project settings) | Selected (sklearn defaults) |
|---|---:|---|---|
| Onion/Jaipur | 1, 2, 3 | Naive | Naive |
| Tomato/Jaipur | 1 | Random Forest-delta | **ARIMA** |
| Tomato/Jaipur | 2, 3 | ARIMA | ARIMA |

One selection changes. Under the defaults, ARIMA would be the Tomato 1-day
choice; its test RMSE is 122.16 against Naive's 120.51, so it would not beat
Naive either. **No reported conclusion changes.** Random Forest-delta's
admission does depend on the regularised settings (with defaults its mean CV
RMSE at Tomato h=1 is 92.8, worse than Naive's 76.9).

## 10. Results — as measured

Selected by CV; test computed once, afterwards. Rs. per quintal.

| Pair | h | Selected by CV | Test RMSE | Naive test RMSE | vs Naive | Lowest test MAE |
|---|---:|---|---:|---:|---:|---|
| Onion/Jaipur | 1 | Naive | 94.27 | 94.27 | 0.00% | Naive (39.75) |
| Onion/Jaipur | 2 | Naive | 110.29 | 110.29 | 0.00% | Naive (53.23) |
| Onion/Jaipur | 3 | Naive | 127.93 | 127.93 | 0.00% | Naive (65.85) |
| Tomato/Jaipur | 1 | Random Forest-delta | 127.33 | 120.51 | −5.66% | Naive (54.27) |
| Tomato/Jaipur | 2 | ARIMA | 179.10 | 178.16 | −0.53% | Naive (90.55) |
| Tomato/Jaipur | 3 | ARIMA | 227.38 | 226.68 | −0.31% | Naive (123.77) |

**Finding 1 — the model chosen in advance never beats "same as today".** At six
of six pair-horizons it either *is* Naive or is slightly worse than Naive on
the unseen test period.

**Finding 2 — Naive has the lowest test MAE everywhere.** On an ordinary day,
repeating the last price is closest.

**Finding 3 — hindsight winners exist, and are not used.** Looking at test
afterwards, Gradient Boosting had the lowest Onion 1-day RMSE (87.26), ARIMA the
lowest Onion 2-day (108.94), and Random Forest-delta the lowest Tomato 2- and
3-day (176.91, 219.18). They are shown in the dashboard as a transparency note.
Choosing any of them now would be selecting on the test set — the mistake the
first version made, which produced its "Gradient Boosting beats Naive by 7.33%"
headline. Note how unstable that winner is: Gradient Boosting's *CV* RMSE at
Onion h=1 was 229, the worst of all five.

**Finding 4 — why Naive is hard to beat here.** On 84.8% (Onion) and 82.8%
(Tomato) of reported days the quoted price is identical to the previous report.

**Finding 5 — uncertainty ranges did not hold up.** 80% ranges built from CV
errors covered 55–74% of test outcomes, so none are drawn (`src/intervals.py`).

**No general claim is made.** This describes one mandi, two commodities,
2009–2015, horizons of 1–3 days. It is not evidence that machine learning
cannot forecast agricultural prices with better inputs.

## 11. What changed from the first version, and why

| | First version (Sept 2026) | Now |
|---|---|---|
| Selection | lowest **test** RMSE | lowest mean CV RMSE; test scored once |
| Split | train/test on feature date | train/CV/test, embargoed on target date |
| ARIMA train metric | from **1 row** (bug) | in-sample h-step forecasts, ~800 rows |
| Pairs | Onion/Jaipur | + Tomato/Jaipur; 4 excluded with reasons |
| Headline | "GBM beats Naive by 7.33%" | the chosen model does not beat Naive |

The old outputs are preserved, not overwritten, in `outputs/legacy/`, with a
README explaining why they are not comparable.

**The ARIMA n=1 bug, traced.** The old ARIMA evaluation only built forecasts
for the test window. The training-metric lookup therefore missed on every
training row except the last, so "train RMSE" came from one row. It now
builds genuine h-step in-sample forecasts across the training window, using
training-window parameters and only prices up to each origin — the direct
analogue of the tree models' in-sample fit. Test predictions were verified
unchanged (to 5e-13) by the fix. A gap between train and test error is shown
only where the two numbers measure the same thing; Naive's "training error"
describes how calm the period was, not memorisation, and is labelled so.

## 12. Threats to validity

- **Regime change.** Development (2009–early 2014) contains long flat stretches;
  the test window follows the 2013 onion spike and is more volatile.
- **35% of feature rows** rest on a carried-forward input price.
- **About 55% reporting density**; stale quotes on most reported days.
- **One mandi.** Two commodities, no cross-market validation.
- **Researcher degrees of freedom** that are disclosed above: the validation
  redesign (section 7), the fifth candidate (section 9), the tree settings
  (section 9 audit).
- **No exogenous inputs** (arrivals, weather, MSP, festivals), which is where
  any real edge would come from.

## 13. Why not LSTM / GRU

About 1,000 usable rows per series is far too little to train and honestly
validate a sequence model without eating into the test window. It would very
likely do worse than the trees while being much harder to defend. Future work,
given more markets and longer history.

## 14. Reproduce every number

```bash
python scripts/extract_rajasthan.py          # official files -> Rajasthan subset
python scripts/build_features.py             # PHASE 1 GATE
python scripts/run_pipeline.py --all-pairs   # PHASE 2 GATE
python scripts/experiment_delta_target.py    # optional: the 5th-candidate experiment
python scripts/experiment_hyperparameter_sensitivity.py   # optional: settings audit
python scripts/data_report.py                # docs/DATA_REPORT.md
python scripts/make_manifest.py              # docs/RUN_MANIFEST.md
python -m pytest
```

`RANDOM_STATE = 42`, dependencies pinned. The same environment produces
byte-identical files; other platforms reproduce them within the tolerance in
`scripts/check_reproducible.py` (only ARIMA moves, by hundredths of a rupee).
