# Demo script

Numbers below are what the app shows with the committed results. If any differ
on the day, stop and run `python -m pytest` — something has changed.

## Before you present (5 minutes)

```bash
cd mandi-price-forecast
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pytest                   # expect: all passed
streamlit run app.py               # opens http://localhost:8501
```

- The app needs **no internet**. It reads files on your laptop.
- Open it once before the judges arrive (first load takes a few seconds).
- Projector: browser zoom 110–125%. The theme is fixed to light on purpose.
- Keep `docs/screenshots/` open in a second window as a backup.

## The 90-second pitch

> "Farmers and traders sell into mandis where prices move every day. Lots of
> projects claim AI can predict those prices. We wanted to know whether that's
> actually true, on real government data, tested properly.
>
> MandiMitra uses the official Department of Consumer Affairs daily wholesale
> prices from data.gov.in — Onion and Tomato in Jaipur, 2009 to 2015. We
> compared four forecasting methods plus one improved variant against the
> simplest possible forecast: *tomorrow's price equals today's*.
>
> The important part is how we tested. Models were chosen on earlier years
> only, and then scored once on fourteen months they had never seen. Our first
> version broke that rule — it picked the winner using the test data and
> claimed a 7% win. When we fixed it, the win disappeared.
>
> So our honest result is: on this data, no model chosen in advance beat
> 'same as today'. On most days the quoted price simply doesn't change. That's
> a useful thing to know before anyone trusts a price-prediction app — and the
> dashboard shows every number behind it."

## The 3-minute demo

| Time | Do this | Say / point at |
|---|---|---|
| 0:00 | Overview tab, **Onion / Jaipur** | The amber **Historical data** banner: "Data ends 28 Apr 2015 — this is not a live price." |
| 0:15 | Point at the four cards | Last reported **Rs. 550** on 28 Apr 2015 · **56%** of days have a price (1,288 of 2,309) · Beats "same as today"? **No** |
| 0:30 | Forecast cards | 29 Apr, 30 Apr, 1 May 2015: **Rs. 550** each — "same as the last reported price", because that's what cross-validation chose. |
| 0:45 | Read "What this means" aloud | Includes the hindsight note: Gradient Boosting scored better at 1 day *only if you look at the test data afterwards*. |
| 1:00 | **Price history** tab, toggle **Show carried-forward days** | Red dots = days the mandi didn't report. "We never score a forecast against a day the market didn't print." |
| 1:20 | **Model evaluation** tab, **1 day** | The green timeline: fit → 4 cross-validation folds → untouched test. Table: Naive selected; test RMSE 94.27 for both. The transparency note under it. |
| 1:45 | Scroll to **Error in each cross-validation fold** | The tall fold: "The October 2013 onion spike. Tree models can't predict above prices they've seen — that's why we added a version that predicts the *change*." |
| 2:05 | Switch commodity to **Tomato**, stay on Model evaluation, **3 days** | ARIMA selected; amber box: "did not beat Naive on test (−0.31%)". Reported as measured. |
| 2:25 | **Forecast** tab | Forecast *made on* 28 Apr 2015, *for* 29 Apr–1 May. "Why no uncertainty band": 80% ranges covered only 55–74% on test, so we don't draw them. |
| 2:45 | Click **हिन्दी** (top right) | The plain-language views switch to Hindi for farmers. |
| 2:55 | Close | "Real data, a strict test, and an honest answer. It's built to add more markets and inputs like arrivals and rainfall." |

Tomato numbers if asked: last reported **Rs. 1,500**; forecasts Rs. 1,484
(1 day, Random Forest-delta), Rs. 1,508 (2 days, ARIMA), Rs. 1,502 (3 days,
ARIMA).

## If something goes wrong

| Problem | Do this |
|---|---|
| No Wi-Fi | Nothing to do. The app runs fully offline on your laptop. |
| The hosted link is down or slow | Use the local app. Never rely on the hosted link for the live demo. |
| Port 8501 busy | `streamlit run app.py --server.port 8502` |
| "The data has not been built yet" | `python scripts/build_features.py` then `python scripts/run_pipeline.py --all-pairs` (about a minute) |
| A traceback on screen | Switch to `docs/screenshots/` and keep talking; fix it afterwards. |
| Laptop fails | Screenshots on your phone (copy `docs/screenshots/` there beforehand), plus the hosted link if it was deployed and tested. |

## Three sentences to never say

- "It predicts today's prices." (Data ends in 2015.)
- "Our AI beats the baseline." (The model chosen in advance does not.)
- "Farmers will earn more with this." (Not measured. No user study was done.)
