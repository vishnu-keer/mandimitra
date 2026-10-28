# Budget and roadmap

## Budget

| Item | Status | Cost now | Constraints / future cost |
|---|---|---|---|
| GitHub public repository + Actions | Confirmed in use | ₹0 | Free for public repos; terms can change |
| Streamlit Community Cloud | Confirmed in use | ₹0 | Public apps; up to 2.7 GB RAM; sleeps after 12 h idle (Streamlit docs, read Oct 2026) |
| data.gov.in data and API key | Data confirmed; key not yet obtained | ₹0 | Free account; rate limits unknown until a key is used |
| Domain name (optional) | Not bought | ₹0 | **[Estimate]** a `.in` domain is typically a few hundred rupees a year — only if wanted |
| User study | Planned | ₹0 | Travel to a mandi; no participant payment |
| Paid hosting | Not needed | ₹0 | **[Estimate]** only if usage outgrows the free tier |

No paid service is required for anything in this project.

## Roadmap (week by week, from 2 Nov 2026)

| Week | Goal | Done when |
|---|---|---|
| 1 | Release this update | Owner reviews diff, pushes, CI green, app redeployed and smoke-tested |
| 1 | Licence confirmation | GODL wording confirmed on data.gov.in while signed in; noted in `docs/01_DATA_SOURCE.md` |
| 2 | Current data | Free data.gov.in key added as a Streamlit secret; first keyed call validates the schema; "Latest prices" tab shows real observations |
| 2 | Second current source | CEDA daily mirror's terms confirmed (or rejected) in writing |
| 3–4 | User study | 5–10 consented sessions at a Jaipur mandi; anonymised findings published |
| 4 | Competition | Package tailored to the chosen event (`docs/COMPETITION_SHORTLIST.md`) |
| 5–6 | More markets | National centres run through the gate; results table per series |
| 7–8 | Better inputs | Arrivals data source identified and evaluated under the same protocol |
| 9+ | Prospective scoring | Forecasts logged daily and scored against later published prices |
