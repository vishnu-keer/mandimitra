> **SUPERSEDED — kept for the project history only.** This document was
> written under the first evaluation protocol (Sept 2026), which selected the
> "best" model on the test set. Its results and claims (for example "Gradient
> Boosting beats Naive by 7.33%") are withdrawn. Current results:
> `docs/02_METHODOLOGY.md`; current demo material: `docs/DEMO_SCRIPT.md`,
> `docs/JUDGE_QA.md`.

# Exhibition Script — Mandi Price Forecast

Everything you need to present and defend this project. Every number here is
measured and appears in `outputs/`. Nothing is rounded up in your favour.

**Read this first:** your strongest asset is not accuracy. It is that you can
explain exactly how accurate it is, why, and where it fails. A student who says
"96% accurate" and cannot define the metric loses to one who says "₹87 RMSE at
one day ahead, 7% better than the naive baseline, and no better at three days."

---

## 1. The 30-second pitch

> Government mandi price data is free and public, but it's raw daily numbers —
> not something a farmer can act on. I built a forecasting system on six years
> of official daily onion prices from Jaipur mandi. It trains four different
> models, compares them honestly on data they've never seen, and forecasts one
> to three days ahead.
>
> The interesting result isn't that machine learning won. It's *by how much,
> and for how long*. Gradient Boosting beats a "tomorrow equals today" baseline
> by 7% at one day ahead. By three days out, nothing beats it. That tells you
> something real about how predictable these prices actually are.

## 2. The 1-minute explanation

> **The problem.** Agmarknet and data.gov.in publish daily mandi prices for
> thousands of markets. It's free, it's official, and it's unusable as a
> decision tool — just rows of numbers. A trader deciding whether to sell today
> or wait has no statistically grounded signal, and no way to know how much to
> trust one.
>
> **The data.** Official daily wholesale onion prices for Jaipur mandi,
> Department of Consumer Affairs, January 2009 to April 2015. 1,551 raw
> records. 263 of them have a price of zero — that's the source's
> missing-value code, not a real price, so I drop them. That leaves 1,288
> genuine observations over 2,309 calendar days, so the mandi reported about
> 56% of days.
>
> **The method.** I align every market to a continuous daily calendar first —
> without that, a "1-day lag" silently means "the previous trading day," which
> might be nine days back, and every feature is quietly wrong. Then lags,
> moving averages, volatility. I train four models — a naive baseline, ARIMA,
> Random Forest, Gradient Boosting — on the first 80% of dates and test on the
> last 20%, which the models never see. Nothing is ever shuffled.
>
> **The result.** At one day ahead, Gradient Boosting gets RMSE ₹87 against the
> baseline's ₹94 — about 7% better. At two days the edge drops to 1%. At three
> days the baseline wins. And the baseline actually has the *lowest* average
> error at every horizon; the tree model only wins on the metric that punishes
> big misses. I report both, because reporting one would misrepresent it.

## 3. The 3-minute demo script

**[0:00–0:20] Open with the problem, not the tech.**
> "This is a price forecasting system for Indian agricultural mandis, built
> entirely on free government data. The problem it addresses: that data is
> public but it's raw — nobody can act on a spreadsheet of daily prices."

**[0:20–0:50] Price history tab.**
> "Six years of official daily wholesale onion prices for Jaipur mandi,
> 2009 to 2015. You can see the 2013 spike — prices went from ₹1,000 to ₹4,500
> a quintal."
>
> *Point at the dataset panel.* "And here's what I want you to notice: the
> mandi only reported on 56% of calendar days. I show that number rather than
> hiding it. If I click this legend entry, it marks every day where I carried
> the previous price forward."
>
> *Click "Carried forward."* "That's 35% of the rows. Being upfront about it
> matters, because it constrains what I can honestly claim."

**[0:50–1:40] Model comparison tab. This is your credibility moment.**
> "Four models, all trained on the same rows, all scored on the same 200
> held-out days. The test period is strictly after the training period — the
> code asserts that, it doesn't just intend it."
>
> *Point at the table.* "Gradient Boosting has the best RMSE, ₹87 against the
> naive baseline's ₹94. That's a 7% improvement."
>
> *Point at the blue callout.* "But look at this. MAE and RMSE disagree. The
> naive baseline — literally 'tomorrow's price equals today's' — has the lowest
> average error, ₹40 against Gradient Boosting's ₹50. RMSE punishes large
> misses harder, so the tree model handles the spikes better. On an ordinary
> day, the baseline is closer. I show both, because showing only the one that
> flatters my model would misrepresent it."

**[1:40–2:15] Actual vs predicted, then the horizon selector.**
> "Here's the best model against reality on data it never saw. The residuals
> sit around zero with no drift, which is what you want."
>
> *Change the horizon selector to 3 days.* "Now watch what happens at three
> days ahead — the naive baseline wins outright. That's my most interesting
> finding. Daily mandi prices are close to a random walk, so predictability
> decays fast. Rather than hide that, I measured it."

**[2:15–2:40] Forecast tab.**
> "The forward forecast — one to three days after the last date in the data.
> Each horizon uses the model that actually won on that horizon's test window,
> not one model imposed on all three."
>
> "Feature importance shows `price_t` at 0.90 — today's price carries almost
> all the signal. That's the random-walk property showing up inside the model.
> And I flag that importance isn't causation: it shows what the model leaned
> on, not what moves onion prices."

**[2:40–3:00] Close on honesty and scope.**
> "The dataset ends April 2015, so this forecasts the days after that, not
> today — I'm explicit about that on screen. Limitations are on the
> methodology tab: one market, no weather, no festivals, no MSP. Everything
> runs offline on my laptop at zero cost. 61 tests, including an automated
> proof that no feature can see the future."

**If you have 30 seconds more:** open the Methodology tab and show the
leakage section. Nothing else you can show reads as more competent.

## 4. Problem statement

Government mandi price data covers thousands of regulated markets and is
published free. But it is raw daily numbers, not decision support. A
smallholder farmer or small trader choosing between selling today and waiting
has no free, statistically grounded forecast — and critically, no way to judge
how much confidence a forecast deserves.

This project builds that forecast for one commodity and market, and measures
honestly how much it is worth. The measurement is the contribution.

## 5. Dataset explanation

- **Source:** data.gov.in, "Daily wholesale price of Onion upto April - 2015",
  resource `522e708a-8c44-47d5-80c5-b62bf357f2b8`, Department of Consumer
  Affairs, Government of India.
- **Schema:** `Date, Centre_Name, Commodity_Name, Price` — 73,312 rows across
  73 market centres nationally.
- **In use:** Onion, Jaipur, 1 Jan 2009 – 28 Apr 2015, ₹/quintal wholesale.
- **Cleaning:** 263 of 1,551 rows have `Price = 0` — the source's missing-value
  code — dropped. 1,288 genuine observations remain over 2,309 calendar days
  (55.8% reporting density).
- **Usable for modelling:** 1,002 rows at h=1, where "usable" means the day
  being forecast was a day the mandi actually reported.
- **Cost:** ₹0, no API key, no account.

## 6. Why a Naive baseline

**Because without it, none of the other numbers mean anything.**

Daily mandi prices behave close to a random walk. "Tomorrow's price equals
today's" is therefore not a strawman — it is a genuinely strong forecast, and
in this project it has the lowest MAE at all three horizons.

Its job is to answer the only question that matters: *does machine learning add
value here at all?* A model reporting RMSE ₹87 sounds good until you learn the
baseline gets ₹94 — then you know the real contribution is 7%, not
"₹87 of accuracy."

Any agricultural price forecasting paper without a naive baseline cannot be
evaluated. That is why it is the first model in this project, not an
afterthought.

## 7. Why ARIMA

ARIMA is the **classical reference point** for time-series forecasting, and the
model the published agri-price literature is usually benchmarked against. It
models the series' own autocorrelation structure — it uses no engineered
features at all.

Including it answers "have you compared against the standard method?" with a
measurement instead of an opinion. Here it wins at two days ahead (RMSE 108.94
vs the baseline's 110.29), which the tree models do not.

Orders come from a 7-candidate grid selected by AIC **on the training window
only**. Evaluation uses a genuine expanding window: parameters are fixed on
train, then observed test days are appended one at a time without refitting,
forecasting h steps before each append. So at every test point ARIMA has seen
data up to *t* and nothing after — exactly the information the tree models get.

## 8. Why Random Forest

Random Forest is **bagged decision trees**: many trees on bootstrapped samples,
averaged. Three reasons it belongs here:

1. It captures **non-linear interactions** between features that ARIMA cannot —
   for example, that a high 7-day volatility changes how much weight today's
   price deserves.
2. It is **robust on small datasets** and hard to overfit catastrophically,
   because averaging many decorrelated trees reduces variance.
3. It gives **feature importances**, which make the model inspectable rather
   than a black box.

Configured with `max_depth=6`, `min_samples_leaf=8`, `max_features='sqrt'` —
chosen a priori from the training-set size, not tuned against the test window.

## 9. Why Gradient Boosting

Gradient Boosting builds trees **sequentially**, each one fitting the errors
the previous ones left behind, rather than averaging independent trees. That
usually extracts more signal from a small dataset — and here it does: it is the
best model at one day ahead, RMSE ₹87.36 against the baseline's ₹94.27.

It is also the **hypothesis under test**. Published Indian agri-price research
reports tree ensembles outperforming ARIMA on this kind of data. This project
tests that claim on fresh data rather than only citing it — and finds it holds
at one day, marginally at two, and not at three.

Configured with 200 stages, `learning_rate=0.05`, `max_depth=3`,
`min_samples_leaf=8`, `subsample=0.9`.

## 10. Why LSTM / GRU is future work

Two honest reasons, neither of them avoidance:

1. **Data volume.** Sequence models need far more history per series than 1,002
   usable rows. An LSTM here would very likely underperform Gradient Boosting
   while being much harder to defend.
2. **Defensibility.** Tuning one properly — architecture, sequence length,
   regularisation, early stopping — needs a validation budget this dataset
   cannot provide without eating into the test window, which would be leakage.

The literature does report LSTM/GRU as the strongest performer on agri-price
forecasting *given sufficient data*. That condition is not met here. Saying
otherwise would be dishonest.

**If a judge pushes:** "I'd rather ship four models I can fully defend than
five where one is indefensible. With three to five years of daily data across
multiple markets, LSTM becomes the obvious next step."

## 11. How data leakage was prevented

Three independent defences, plus a fourth check in the tests:

**1. Backward-only windows.** No `center=True`, no `bfill`, no `interpolate`,
no statistic computed over the whole series. `pct_change` uses
`fill_method=None` so a gap cannot invent a return. A unit test tokenises every
file in `src/`, strips comments and docstrings, and fails if any of those calls
appear in real code.

**2. Direct multi-horizon targets.** One model per horizon. To forecast 3 days
ahead I train a model whose target is `price[t+3]` using only features known at
*t*. No prediction is ever fed back as an input — so the classic
recursive-forecast bug, where day 2's lag accidentally uses day 1's *actual*
price instead of its prediction, **cannot exist**, because there is no step 2.

**3. An automated proof.** `verify_no_leakage()` builds every feature on the
full series, rebuilds them on a copy truncated partway through, and asserts
every value before the cut is byte-identical. A feature reading forward would
change once the future was deleted. It runs on every feature build: 1,616 rows,
13 columns, zero mismatches.

**4. A perturbation test.** The suite multiplies future prices by 10 and
asserts no earlier feature moves.

**Say this if asked:** "I don't assert there's no leakage — I test for it, four
different ways, and one of those tests found a real latent leak in my ARIMA
input series, which I fixed."

## 12. How chronological evaluation works

The last **20% of distinct dates** are held out. Splitting on dates rather than
row positions keeps every row sharing a date on the same side of the cut.

At h=1: **train 802 rows** (25 Mar 2009 → 16 Feb 2014), **test 200 rows**
(17 Feb 2014 → 27 Apr 2015), cutoff **17 Feb 2014**.

The code **asserts** `max(train.date) < min(test.date)` and that the date sets
are disjoint. There is no `train_test_split` anywhere in this project and
nothing is ever shuffled.

**Why a random split would be fatal:** the model would train on Thursday and
Saturday while being scored on Friday — the answer leaks in from both
neighbours. Metrics from a shuffled time-series split are meaningless and
inflated.

**Fairness:** every model at a given horizon is scored on the intersection of
rows all four could predict — 200 / 201 / 205 at h=1/2/3. If ARIMA cannot
predict a row, that row is dropped for everyone. The Phase 2 gate asserts the
counts match.

## 13. MAE, RMSE and MAPE explained

| Metric | Plain meaning | Value at h=1 (best model) |
|---|---|---|
| **MAE** | Average error in rupees. "Typically off by ₹X per quintal." | ₹50.34 (GBM) · **₹39.75 (Naive — lowest)** |
| **RMSE** | Like MAE but big misses count much more. Used for selection. | **₹87.36 (GBM — lowest)** · ₹94.27 (Naive) |
| **MAPE** | Error as a % of the actual price. Comparable across commodities. | 5.62% (GBM) · **4.34% (Naive — lowest)** |
| **R²** | Share of variance explained. | 0.90 (GBM) |

**Why RMSE for selection:** squaring the errors means one ₹300 miss costs more
than ten ₹30 misses. For a price signal, a single large error is worse than
several small ones.

**Why MAE is also shown:** it is what a farmer actually experiences day to day,
and here it picks a *different winner*. Presenting only RMSE would overstate
how accurate the forecast feels.

**On R² — be ready for this one:** "R² looks flattering on any persistent price
series. A model that just repeats today's price scores 0.88 purely from level
persistence, without predicting any of the *change* that actually matters. I
report it, but I read RMSE and MAE first."

## 14. Limitations

1. **Data ends 28 April 2015.** Real, official, but historical. The forecast is
   for the days after that date, not today.
2. **One commodity, one market.** Broader coverage is data acquisition, not
   modelling; the pipeline already supports multiple pairs.
3. **55.8% reporting density.** 35.3% of feature rows rest on a carried-forward
   input price. Targets are always real reported prices.
4. **Near-random-walk prices.** The baseline is hard to beat; the ML edge
   decays to zero by three days out.
5. **RMSE and MAE disagree** on the winner.
6. **R² flatters every model** on this kind of series.
7. **Regime change across the split.** Training years are flatter; the test
   window follows the 2013 spike. Correct split, but the distributions differ.
8. **No external drivers** — no weather, rainfall, festivals, MSP, arrivals
   volume, transport costs or policy. Real spikes often come from exactly those.
9. **Point forecasts only**, no prediction intervals.
10. **Not financial advice.** No claim about income, profit, or any single
    forecast being right.

## 15. Future roadmap

**Near term (weeks).** More markets and commodities — Jodhpur and Kota onion
data are already in the same source file. Prediction intervals instead of point
forecasts; a farmer needs to know how wrong this could be. Cross-market
features, since neighbouring mandis lead each other.

**Medium term (months).** Replace the static download with a scheduled pull
from a live source, plus automated retraining. Add exogenous drivers — rainfall,
arrivals volume, festival calendar, MSP announcements — which is where real
price shocks originate. Expose the ML core through a REST API; it already has
no knowledge of the interface, so this needs no rewrite.

**Longer term.** LSTM/GRU once there is enough history per market to tune one
defensibly. SMS or voice delivery for low-literacy users — a dashboard is the
wrong interface for the actual end user. Multi-state coverage.

---

## 16. Top 20 judge questions, with honest answers

**Q1. What's your accuracy?**
> I don't report a single accuracy number, because for a regression problem it
> would be meaningless. At one day ahead, RMSE ₹87.36 per quintal, MAE ₹50.34,
> MAPE 5.62% — on 200 held-out days the model never saw. The naive baseline
> gets RMSE ₹94.27, so the real improvement is 7.33%.

**Q2. How do I know you didn't leak future data?**
> Three defences and a test. Every window is backward-only. Targets are direct
> multi-horizon, so no prediction ever feeds a lag. And `verify_no_leakage()`
> rebuilds all features on truncated data and asserts nothing before the cut
> changed — it runs on every build. There's also a test that multiplies future
> prices by 10 and checks no earlier feature moves. That suite found a real
> latent leak in my ARIMA input, which I fixed.

**Q3. Did you use a random train/test split?**
> No, and that would have invalidated everything. Chronological — last 20% of
> dates held out. The code asserts train and test share no dates. A random
> split would let the model train on Thursday and Saturday while being scored
> on Friday.

**Q4. Why is the naive baseline so hard to beat?**
> Because daily mandi prices are close to a random walk. Today's price carries
> almost all the information about tomorrow's — you can see it in the feature
> importances, `price_t` at 0.90. That's a property of the data. I'd rather
> measure it than pretend otherwise.

**Q5. So did machine learning actually help?**
> At one day ahead, yes — 7.33% better RMSE. At two days, marginally, 1.23%.
> At three days, no: the baseline wins outright. And the baseline has the lowest
> MAE at every horizon. So: a real but modest and rapidly decaying advantage.

**Q6. Your RMSE winner and MAE winner are different. Which is it?**
> Both, and that's the honest answer. Gradient Boosting has the lowest RMSE,
> which means it handles large price swings better. The naive baseline has the
> lowest MAE, which means it's closer on an ordinary day. RMSE squares the
> errors, so the two metrics reward different things. I show both rather than
> pick the flattering one.

**Q7. Is this data live?**
> No. It ends 28 April 2015. It's real official government data, but
> historical. The forecast is for the days after the last date in the file, and
> the dashboard says so on screen. Making it live means a scheduled pull and
> retraining — that's on the roadmap, not in this build.

**Q8. Why only one market?**
> Time. Getting clean data was the hard part, and I chose to make one market
> fully defensible rather than four superficially. The pipeline handles
> multiple pairs — there's an `--all-pairs` flag — and Jodhpur and Kota are in
> the same source file.

**Q9. Why didn't you use deep learning / LSTM?**
> Two reasons. Data volume — 1,002 usable rows is far too few for a sequence
> model; it would likely underperform Gradient Boosting. And defensibility —
> tuning one properly needs a validation budget this dataset can't give without
> eating into the test window. The literature does report LSTM as best given
> enough data. That condition isn't met here.

**Q10. What's R² and why is yours 0.90?**
> Variance explained. But I'd caution against reading it as 90% accuracy — on a
> persistent price series, a model that just repeats today's price scores 0.88
> purely from level persistence. It's flattering by construction. RMSE and MAE
> are the honest numbers.

**Q11. 35% of your data is filled in. Isn't that a problem?**
> It's a real limitation and I show it on the dashboard. Two things contain it:
> gaps longer than two days are dropped, not filled. And critically, a row is
> only scored if the day it forecasts was actually reported — so every *target*
> is a real market price. Some inputs are carried forward; no target is.

**Q12. What if the mandi didn't report for a week?**
> Those rows are dropped. I forward-fill at most two days, which spans a
> weekend closure. Anything longer stays empty and the row is removed. I tested
> 1, 2 and 3 days and picked 2 — the numbers are in the methodology doc.

**Q13. Why RMSE for model selection and not MAE?**
> Squaring means one ₹300 miss costs more than ten ₹30 misses. For a price
> signal, a single large error does more damage — a farmer acting on a badly
> wrong forecast loses more than one acting on several slightly wrong ones.
> But I report MAE too, precisely because it disagrees here.

**Q14. Could a farmer actually use this?**
> Not in this form, honestly. A dashboard is the wrong interface for the actual
> end user — SMS or voice would be right, and that's on the roadmap. What this
> demonstrates is that the underlying signal is real but modest, and exactly
> how modest. That's the prerequisite for building the real thing.

**Q15. What happens if I pick a commodity with no data?**
> You can't. The selectors are built only from pairs that pass the data gate,
> so an unsupported combination isn't offered. If a pair has data but hasn't
> been evaluated, you get a message with the exact command to run — not a crash
> and not a fabricated number.

**Q16. How much did this cost to build?**
> Nothing. Free government data, all open-source libraries, runs offline on my
> laptop. No API key, no cloud service, no database, no hosting.

**Q17. Did you tune the models on the test set?**
> No. The only hyperparameters set anywhere are tree depth and leaf size, and
> those were chosen from the *training* set size before I looked at any test
> result. Everything else is at library defaults. Tuning against the test set
> would be the worst kind of leakage.

**Q18. How do I know the dashboard numbers match your actual results?**
> The dashboard trains nothing — it reads the five CSVs the pipeline wrote.
> There's a test that asserts every headline number on screen exists in
> `outputs/` with matching values and row counts. If they diverged, the test
> fails.

**Q19. What's the single biggest weakness?**
> That it models the price series in isolation. Real onion price spikes — like
> the 2013 one in my data — are driven by rainfall, crop failure, transport
> disruption and policy. None of that is in the model. So it can extrapolate a
> trend but it will never anticipate a shock, which is exactly when a farmer
> needs it most.

**Q20. Why should I believe any of this?**
> Because you can check all of it. The data source is a public URL with a
> resource ID. Every number on the dashboard traces to a generated CSV. There
> are 61 tests including four independent leakage checks. Each phase has a gate
> that fails loudly. And where the results are unflattering — the baseline
> winning at three days, MAE disagreeing with RMSE — I show that too. A project
> that only reports what makes it look good isn't one you should believe.

---

## 17. Pre-demo checklist

- [ ] Laptop charged, charger packed
- [ ] `pytest` — 61 passing
- [ ] `python scripts/build_features.py` — PHASE 1 GATE: PASS
- [ ] `python scripts/run_pipeline.py` — PHASE 2 GATE: PASS
- [ ] `streamlit run app.py` opens, all four tabs render
- [ ] **Tested with Wi-Fi off**
- [ ] Rehearsed the 3-minute script twice with a timer
- [ ] Can answer Q2, Q5 and Q6 without notes — they are the ones that decide it

## 18. Three things never to say

1. **"It's 90% accurate."** R² is not accuracy. Say the RMSE and the
   baseline comparison.
2. **"It predicts today's prices."** The data ends April 2015. Say so first,
   before a judge finds it.
3. **"Machine learning beats traditional methods."** Here it beats the baseline
   at one day by 7%, and loses at three. Say the measured numbers.
