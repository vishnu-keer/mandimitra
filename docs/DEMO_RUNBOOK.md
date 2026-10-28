# Demo runbook

Scripts for 30 seconds to 10 minutes, exact clicks, expected values and
fallbacks. Every number is from the committed results; if the app shows
something different, run `python -m pytest` before presenting. Rehearse each
script against a timer (`docs/RELEASE_CHECKLIST.md` records rehearsal status).

## Before you present (10 minutes)

```bash
cd ~/Downloads/mandi-price-forecast
source .venv/bin/activate
python -m pytest                    # expect: all passed
streamlit run app.py                # http://localhost:8501
```

- The local app needs **no internet**. Use it for the live demo.
- Open <https://mandimitra.streamlit.app/> once ~10 minutes before (it may be
  asleep); keep it as the backup and for judges' phones (QR on slide 1).
- Projector: browser zoom 110–125%. Theme is pinned light.
- Have `presentation/MandiMitra_Hackathon_Pitch.pdf` and `docs/screenshots/`
  open in other windows.

## Expected values (check these on screen)

| Where | Expected |
|---|---|
| Banner | "Historical data … ends on 28 Apr 2015" |
| Overview, Onion/Jaipur | Last reported **Rs. 550** (28 Apr 2015) · **56%** (1,288 of 2,309 days) · Beats "same as today"? **No** · forecasts **Rs. 550** for 29 Apr, 30 Apr, 1 May 2015 |
| Overview, data quality | Latest genuine observation 28 Apr 2015 · price same as previous report **85%** · longest gap **70** days between reports · inputs carried forward **35%** |
| Overview, Tomato/Jaipur | Last reported **Rs. 1,500**; forecasts **Rs. 1,484 / 1,508 / 1,502** |
| Model evaluation, Onion, 1 day | Naive selected; test RMSE **94.27** for Naive; transparency note: Gradient Boosting **87.26** with hindsight |
| Model evaluation, Tomato, 3 days | ARIMA selected; "did not beat Naive" **(−0.31%)**; DM caption p ≈ 0.82 |
| Forecast | Made on 28 Apr 2015, for 29 Apr – 1 May 2015; "Uncertainty: why no band is drawn" — 0 of 3 held up |
| Latest prices | "Not connected" unless an API key is configured |

## 30-second introduction

> "MandiMitra checks whether AI really beats the simplest price forecast —
> tomorrow equals today — for mandi prices, using official government data
> and a test the model can't game. On Jaipur onion and tomato, it doesn't:
> no model chosen in advance beat 'same as today', and 0 of 48 significance
> tests favoured a model. The dashboard shows farmers and traders that honest
> answer, in English and Hindi."

## 90-second pitch

> "Farmers and traders sell into mandis where prices jump — Jaipur onion went
> from about six hundred to four and a half thousand rupees a quintal in four
> months in 2013. Apps now promise AI forecasts. We asked: do they beat the
> simplest forecast, tomorrow equals today, when tested honestly?
>
> MandiMitra uses the Department of Consumer Affairs' official daily wholesale
> prices — onion and tomato in Jaipur, 2009 to 2015. Five methods, from 'same
> as today' to tree models, are chosen on earlier years and scored once on
> fourteen months they never saw.
>
> Our first version broke that rule and claimed a 7% win. Fixed, the win
> disappeared: the model chosen in advance never beat 'same as today', and the
> 7% gap has a p-value of 0.5. On most days the quoted price simply doesn't
> change.
>
> So the product leads with that honest reference, shows how fresh and stale
> the data is, and refuses to draw confidence bands that failed on unseen
> data — in English and Hindi, free to run, every number reproducible."

## 3-minute demo

| Time | Click | Say |
|---|---|---|
| 0:00 | Overview, Onion/Jaipur | Point at the banner: historical, ends 28 Apr 2015 |
| 0:15 | The four cards | Rs. 550 · 56% of days reported · Beats "same as today"? No |
| 0:30 | Forecast cards | Rs. 550 × 3 — "same as the last price", because cross-validation chose it |
| 0:45 | "What this means" | Read the hindsight sentence about Gradient Boosting |
| 1:00 | Scroll to Data quality | 85% of reported days repeat the price; 70-day longest gap |
| 1:15 | Price history → toggle "Show carried-forward days" | Red dots = days the mandi didn't report; never scored |
| 1:35 | Model evaluation, 1 day | Timeline: fit → 4 folds → test once. Table: Naive selected; transparency note |
| 2:00 | Switch to Tomato, 3 days | ARIMA chosen, −0.31%, DM caption: not distinguishable |
| 2:20 | Forecast tab | Dates made-on / made-for; why no band: 0 of 3 ranges held up |
| 2:40 | Latest prices tab | "Not connected" — the official API client is ready; we won't fake a live price |
| 2:50 | हिन्दी | Plain-language views switch to Hindi. Close. |

## 5-minute presentation

Slides 1–4 (problem, evidence, solution) in 90 s → 3-minute demo above →
slide 8 (results) and slide 11 (limitations) in 30 s.

## 10-minute technical walkthrough

1. (1 min) Problem and data — slides 2–3, `docs/01_DATA_SOURCE.md`.
2. (2 min) Pipeline — slide 6; show `src/features.py` decision-point comment
   and `tests/test_features_no_leakage.py`.
3. (2 min) Protocol — slide 7; `src/splits.py` embargo; the Phase 2 gate output
   (`python scripts/run_pipeline.py --all-pairs`, last lines).
4. (2 min) Results and significance — slide 8; `outputs/experiments/dm_test.csv`;
   first version vs now (`outputs/legacy/README.md`).
5. (1 min) Reproducibility — `docs/RUN_MANIFEST.md`, CI tab on GitHub.
6. (1 min) Current data — `src/live_data.py` all-or-nothing update; tests.
7. (1 min) Limitations and next steps — slide 11.

## Fallbacks

| Problem | Do this |
|---|---|
| No Wi-Fi | Nothing — the local app is offline |
| Local app error | Switch to the hosted link; if that fails, the PDF deck and screenshots |
| Hosted app asleep | Wait ~1 minute or use local |
| Port busy | `streamlit run app.py --server.port 8502` |
| "Data has not been built yet" | `python scripts/build_features.py && python scripts/run_pipeline.py --all-pairs` (~1 min) |
| Laptop fails | Deck PDF and screenshots on a phone; QR to the hosted app |

## Never say

"It predicts today's prices." · "Our AI beats the baseline." · "Farmers will
earn more." · "It's live" (unless the Latest prices tab shows real data).
