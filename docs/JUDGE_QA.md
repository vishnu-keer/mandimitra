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
*after* looking at the test data. On the earlier years, the same model's CV
RMSE was 229 — almost four times Naive's 61.5, and second-worst of the five.
A model that is near the bottom in one period and on top in the next is not
one you can rely on. A significance test agrees: the 7% gap has p = 0.505. We show it as a transparency note, not as
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
hundredths of a rupee, and a script checks that tolerance. The repository's
CI workflow rebuilds everything from the government files and runs that check
on every push; both runs so far were green.

### 20. What are the main limitations?

Historical data only; one mandi; prices only (no arrivals, weather, MSP,
festivals); stale quotes on most reported days; about 44–47% of calendar days
missing; no user study, so **no claim about farmer income or decisions**.

### 21. What would you do next?

Add newer Agmarknet data and more markets; add arrivals and rainfall as inputs,
where a real edge is more likely; a rolling re-evaluation that updates monthly;
and a small study with actual traders on whether the explanation is useful.

---

## Harder questions

### 22. Is the difference between a model and Naive statistically real?

We tested it. Diebold–Mariano tests with the Harvey–Leybourne–Newbold
correction, every model against Naive on the identical test days, Holm-adjusted:
under squared error, 0 of 24 comparisons favour a model and 6 favour Naive;
under absolute error, 0 of 24 favour a model and 24 favour Naive. The Tomato
1-day choice is significantly *worse* than Naive (p = 0.007).

### 23. Then is the model useful at all?

As a price predictor, not on this data — and we say so. The product is useful
as a reference and a warning: it shows the strongest simple forecast, how
stale the quotes are, how often the price moves, and that confident bands
failed. Whether that helps real users is the next thing to measure.

### 24. Is the data current?

No. The evaluation uses an official series that ends 28 April 2015, and every
screen says so. For current prices we built and tested a client for the
official AGMARKNET daily price API on data.gov.in. It needs a free personal
key; until one is added, the "Latest prices" tab says "Not connected" rather
than showing anything that looks live.

### 25. Would this generalise to other markets?

Unknown. Jodhpur and Kota report too rarely to evaluate. Two Jaipur series is
a small sample. The method generalises — add the official file, the gate
decides — but the *result* has to be measured market by market.

### 26. What about existing tools like AGMARKNET or e-NAM?

AGMARKNET publishes prices; e-NAM is a trading platform (1,389 mandis
integrated as of Feb 2024, per PIB). Neither evaluates forecasts. TNAU's
market intelligence cell publishes expert price outlooks. MandiMitra's niche is
transparent, reproducible evaluation shown to users. See
`docs/COMPETITIVE_LANDSCAPE.md`.

### 27. Can you legally redistribute the data?

The platform's Terms of Use allow reproduction with prominent acknowledgement
and refer to per-dataset licence metadata; the platform licence is GODL-India.
We attribute the Department of Consumer Affairs and data.gov.in everywhere.
We still need to read the licence text while signed in to the portal — listed
as a manual check.

### 28. What personal data do you collect?

None. No accounts, forms or analytics; Streamlit's usage statistics are off.
The optional API key is never stored, logged or shown (tested).

### 29. What does it cost to run?

₹0: GitHub, GitHub Actions, Streamlit Community Cloud and data.gov.in are free
at this scale. If free tiers change, it runs locally at ₹0.

### 30. Has it been used in the field? What is the economic impact?

Not yet, and we do not claim any. We have a consented study plan for 5–10
Jaipur traders and farmers and will publish the findings, including negative
ones. Economic impact would need a controlled design we have not done.

### 31. What evidence is still missing?

A real call to the current-price API; user evidence; prospective accuracy on
prices published after the forecast; more markets; non-price inputs; and the
licence text read from the official page.

### 32. Did you change anything after seeing results?

Yes, and it is disclosed: the first version picked on the test set (replaced);
the validation design was changed once after seeing validation (not test)
results; the fifth model was admitted by a CV rule written beforehand; the
tree settings date from the first protocol and were audited. Two wording
errors in earlier docs were also found and corrected (`docs/COMPETITION_GAP_ANALYSIS.md`).

