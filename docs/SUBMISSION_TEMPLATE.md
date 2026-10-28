# Submission template

Reusable answers for competition forms. Copy, then cut to each form's word
limits. Every claim here is in the paper and the result files. Tailor to the
event's own judging criteria — one format does not fit every competition.

**Project name:** MandiMitra — Explainable mandi price intelligence

**Team:** Vishnu Keer (Vivekananda Global University, Jaipur). *Add members and
roles if the event requires a team; SIH, for example, requires six students.*

**Links:** Live app <https://mandimitra.streamlit.app/> · Code and data
<https://github.com/vishnu-keer/mandimitra> · Video: *(add after recording)*

**Theme / track:** Agriculture, FoodTech & Rural Development · Open data · Applied AI/ML

**One-line summary (≤ 25 words):** An open, bilingual dashboard that tests
whether AI beats "tomorrow's price = today's" for mandi prices — honestly — and
shows farmers the answer.

**Problem (≤ 100 words):** Mandi prices jump without warning (Jaipur onion:
Rs. 600–900 to Rs. 4,500 a quintal in four months of 2013). AI price
predictions are offered to farmers and traders, but whether they beat the
simplest forecast, or were tested on data they never saw, is rarely visible.
A confident but poorly tested forecast can push someone to sell or hold at
the wrong time.

**Solution (≤ 150 words):** MandiMitra evaluates five forecasting methods on
official Department of Consumer Affairs daily wholesale prices (Onion and
Tomato, Jaipur, 2009–2015) with a protocol that chooses the model on earlier
years and scores unseen data once, with leakage tests and significance tests.
A Streamlit dashboard in English and Hindi shows the reference forecast, data
freshness, stale-quote rates and uncertainty only where it held up. A tested
client for the official AGMARKNET daily price API is ready for current data.
Everything is reproducible and free to run.

**Results (≤ 100 words):** The model chosen in advance never beat "same as
today" on unseen data; 0 of 48 Diebold–Mariano tests favoured any model; our
first version's "+7.33%" came from selecting on the test set (p = 0.505).
83–85% of reported days repeat the previous price; 80% ranges covered only
55–74% of outcomes, so none are drawn.

**Innovation:** Not a new model — a transparent, tested evaluation turned into
a user-facing product that shows when AI does *not* help.

**Feasibility:** Working and deployed; 154 automated tests; CI; ₹0 running cost;
government open data (GODL-India, with attribution).

**Impact (honest):** Not yet measured. A consented user study with 5–10 Jaipur
traders and farmers is planned (`docs/USER_RESEARCH_PLAN.md`).

**Scalability:** New markets run through the same data gate; the ML core is
independent of the dashboard.

**Limitations:** Historical data; one mandi; prices only; back-test only; no
user evidence yet.

**Technology:** Python, pandas, scikit-learn, statsmodels, Streamlit, Plotly,
pytest, GitHub Actions.
