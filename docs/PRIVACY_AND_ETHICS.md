# Privacy and ethics

## Data the app processes

- Public government price data only. No personal data.
- The app has no accounts, no forms, no analytics and no tracking of its own.
  Streamlit usage statistics are switched off (`gatherUsageStats = false`).
  The hosting platform (Streamlit Community Cloud) has its own terms and logs,
  which the project does not control.
- The optional data.gov.in API key is read from an environment variable or a
  Streamlit secret. It is never written to disk, logged, shown or included in
  an error message (`tests/test_live_data.py` checks this). Fetched snapshots
  are stored in `data/live/`, which is not committed.

## Responsible presentation

- Every screen states that the data is historical and that nothing is
  financial, trading or farming advice.
- Forecasts are shown beside the last reported price and the naive reference.
- Uncertainty ranges are drawn only if they held up on unseen data; they did
  not, so the app shows that finding instead.
- Hindsight winners are shown as a transparency note, never as the answer.
- No impact, user or income claims are made without evidence.

## Risks of misuse

| Risk | Mitigation |
|---|---|
| Someone treats a 2015 forecast as today's | Banner on every screen; forecast dates shown explicitly |
| Over-trust in "AI" | The app shows that the AI did not beat the simple reference |
| Current prices mistaken for forecasts | Separate tab, labelled "observed prices, not forecasts" |
| A future user study collects personal data | Consent-first, no identifiers (`docs/USER_RESEARCH_PLAN.md`) |

## Licences and attribution

Data: Government Open Data License – India, with attribution to the
Department of Consumer Affairs and data.gov.in (`DATA_LICENSE.md`). Code: MIT.
No endorsement by any government body is implied.
