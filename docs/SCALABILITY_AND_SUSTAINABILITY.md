# Scalability and sustainability

## Scaling the data

- **More markets.** Add the official file for a centre, add the centre to
  `config.RAW_CENTRES`, run the pipeline. The 400-row gate decides whether a
  series is evaluated; the dashboard's selectors are built from whatever
  passes. The national files used here cover 73 centres.
- **More commodities.** The same code path; one model per series and horizon.
- **Current data.** `src/live_data.py` already pages through the official
  daily API with all-or-nothing writes. Scaling it is a matter of filter sets
  (state, commodity) and the API's rate limits (to be confirmed with a key).

## Scaling the compute

**[Measured]** The full pipeline for two series takes 20–60 s on a laptop
because ARIMA uses a single Kalman pass per series. **[Estimate]** It grows
roughly linearly with the number of series; hundreds of series would need
minutes, not hours, and could run nightly on free CI minutes. The dashboard
reads files and trains nothing, so serving cost does not grow with model
count.

## Scaling the product

- The ML core (`src/`) has no Streamlit dependency, so the same outputs can be
  served by an API or another front end later without changing the science.
- Hindi is already supported for the plain-language views; adding Rajasthani
  or other languages is a dictionary addition.

## Sustainability

| Item | Today | If it grows |
|---|---|---|
| Hosting | Streamlit Community Cloud, free (public apps) | Any small VM or a free-tier container host |
| CI | GitHub Actions, free for public repos | Same |
| Data | data.gov.in, free | Same; API key is free |
| Maintenance | One developer; tests + CI catch regressions | Contributors via GitHub |

Free tiers can change; the project runs entirely locally at ₹0 if they do.
