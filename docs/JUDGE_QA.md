# Judge Q&A

Short answers first; the detail is underneath when you need it. Every number
is from the committed results (`docs/RUN_MANIFEST.md`).

---

### 1. What problem does this solve, and for whom?

Farmers and small traders decide when and where to sell with little view of
where prices are heading, and many apps now claim AI can tell them. MandiMitra
asks a prior question: **on real official data, tested properly, does a
forecasting model actually beat "tomorrow = today"?** Intended users are
farmers, traders, and anyone evaluating a price-prediction tool — including
the people who build them.

### 2. Why does it matter?

Onion and tomato prices in India swing hard: in our data, Jaipur onion went
from Rs. 600–900 a quintal in June 2013 to Rs. 4,500 on 21 October 2013, and
back to about Rs. 800 by December. A forecast that
looks good because it was tested badly can push someone into a worse sale. An
honest, explainable evaluation is the useful product here, not a confident
number.

### 3. Where does the data come from? Is any of it made up?

Official Department of Consumer Affairs daily wholesale prices, published on
data.gov.in under the Government Open Data License – India. The two government
CSVs are stored untouched with SHA-256 hashes; a test proves our working file
is an exact extract of them. **No row is fabricated.** Days the mandi didn't
report stay missing; they are never used as a forecast target.

### 4. Why does it stop in 2015? Can it tell me today's price?

**No.** That official daily series ends on 28 April 2015. The app says so in a
banner on every screen, and forecasts the three days after that date. The
method would run on newer data; the conclusions are about 2009–2015.

### 5. What is the "Naive baseline"?

"Tomorrow's price = today's price." It needs no training, and it is the bar
every model must clear. If a model can't beat it, the model adds nothing.

### 6. So which model won?

Chosen in advance by cross-validation: **Naive** for Onion at 1, 2 and 3 days;
**Random Forest-delta** (1 day) and **ARIMA** (2, 3 days) for Tomato. On the
unseen test period none of the Tomato choices beat Naive (−5.66%, −0.53%,
−0.31% RMSE). Naive also had the lowest MAE everywhere. The honest headline:
**no model chosen in advance beat "same as today" on this data.**

### 7. Isn't that a failed project?

No — it is the result. Most student projects report the model with the lowest
test error, which quietly uses the test data to pick the winner. Our first
version did exactly that and claimed "Gradient Boosting beats Naive by 7.33%".
When we fixed the protocol, the win disappeared. Showing that, with evidence,
is more useful than a number that wouldn't survive the next month.

### 8. But Gradient Boosting *did* have a lower test error at 1 day?

Yes — 87.26 against Naive's 94.27 on Onion, 1 day. But you only know that
*after* looking at the test data. On the earlier years, the same model was the
worst of five (CV RMSE 229). A model that is worst in one period and best in
the next is not one you can rely on. We show it as a transparency note, not as
the answer.

### 9. Why do MAE and RMSE disagree?

MAE is the typical miss on an ordinary day; RMSE squares errors, so a few big
misses dominate. On most days the price doesn't change, so Naive is right on
the ordinary day (lowest MAE). Models that partly react to trends sometimes
reduce a big miss (lower RMSE). They answer different questions; we show both.

### 10. How do you prevent data leakage?

Five layers: features use only data up to the forecast day; one model per
horizon so no prediction is fed back in; an automated truncate-and-compare
proof on every feature build; an embargo that removes any training row whose
*target date* crosses a boundary; and ARIMA forecasts that provably only see
the past (a test changes future prices and checks nothing earlier moves). A
code scan also fails the tests if anyone adds `bfill` or `interpolate`.

### 11. How do you handle missing prices?

A `0` in the source means "not reported" and becomes missing. Every series is
put on a full daily calendar so "yesterday" always means the previous calendar
day. A missing day may borrow the last price **as an input** for at most two
days; longer gaps stay empty. **A row is only scored if the mandi actually
reported a price on the forecast day.** About 35% of input rows use a
carried-forward price, and the dashboard shows that.

### 12. How was the model chosen without touching the test set?

The last 20% of dates (Feb 2014 – Apr 2015) is the test set, scored once. Inside
the earlier 80%, four expanding cross-validation folds each fit on the past and
score the next block. The rule — lowest average fold RMSE — was fixed before the
results were seen.

### 13. Did you ever look at the test set and change something?

Yes, and we say where. (a) The tree settings (depth, leaf size) were set under
the first protocol and checked on the old test window. We re-ran with
scikit-learn defaults: one selection changes (Tomato 1-day becomes ARIMA), and
it still doesn't beat Naive, so no conclusion changes. (b) We redesigned the
validation from one block to rolling folds after seeing that the single block
landed on one spike — that used validation results, not test. (c) The fifth
model was admitted by a rule written before its experiment, using CV only.

### 14. Why these models?

Naive is the yardstick. ARIMA is the classical time-series reference. Random
Forest and Gradient Boosting are the standard machine-learning choices for
tabular features. Random Forest-delta predicts the *change* in price, because
level-predicting trees can't forecast above prices they've already seen.

### 15. Why not deep learning (LSTM)?

About 1,000 usable days per series is too little to train and honestly validate
a sequence model without eating into the test set. It would most likely do
worse and be harder to defend. With more markets and years, it's future work.

### 16. Why is there no confidence band?

We built 80% ranges from the cross-validation errors and checked them once on
test. They covered only 55–74% of outcomes. Drawing them would give false
confidence, so the app shows that finding instead.

### 17. Why only Jaipur? What about Jodhpur and Kota?

They are in the same government file, but they report far less often (315 and
241 usable 1-day rows against our 400-row minimum, set before we looked).
We list them as excluded with the reason rather than lowering the bar.

### 18. How would this scale to more markets?

Add the official file, add the centre name in `src/config.py`, re-run the
pipeline. The data gate decides whether the series is usable, and the
dashboard's selectors are built from whatever passes. The ML code has no
dashboard dependency, so it can sit behind an API later.

### 19. How do we know your numbers are reproducible?

Every input and output file is hashed in `docs/RUN_MANIFEST.md`, and a test
fails if any file stops matching. Rebuilding from the government files gives
byte-identical results on the same setup; on other setups only ARIMA moves, by
hundredths of a rupee, and a script checks that tolerance. Once the repository
is on GitHub, its CI workflow rebuilds everything and runs that check on every
push.

### 20. What are the main limitations?

Historical data only; one mandi; prices only (no arrivals, weather, MSP,
festivals); stale quotes on most reported days; about 45% of calendar days
missing; no user study, so **no claim about farmer income or decisions**.

### 21. What would you do next?

Add newer Agmarknet data and more markets; add arrivals and rainfall as inputs,
where a real edge is more likely; a rolling re-evaluation that updates monthly;
and a small study with actual traders on whether the explanation is useful.
