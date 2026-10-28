# Data source and provenance

## What the project uses

| Field | Value |
|---|---|
| Dataset | *Daily wholesale price of Onion upto April 2015* and *… of Tomato upto April 2015* |
| Platform | Open Government Data (OGD) Platform India — data.gov.in |
| Publisher | Department of Consumer Affairs (Price Monitoring Cell), Ministry of Consumer Affairs, Food & Public Distribution, Government of India |
| Files | `https://data.gov.in/sites/default/files/daily_wholesale_price_Onion_upto_apr_2015.csv` and the same path with `Tomato` |
| Resource id (Onion, from the platform API) | `522e708a-8c44-47d5-80c5-b62bf357f2b8` |
| Retrieved | Onion first on 15 Sep 2026; both files re-downloaded untouched on 27 Oct 2026 |
| Schema | `Date,Centre_Name,Commodity_Name,Price`; one row per centre per day; `Date` is `DD-MM-YY` |
| Unit | **Rs. per quintal, wholesale**, as stated by the publisher (1 quintal = 100 kg) |
| Missing-value code | `Price = 0` means *not reported*, not a price of zero |
| Coverage | 1 Jan 2009 – 28 Apr 2015, 73 centres nationally |
| Cost | Rs. 0. Public data, no API key, no account |

The two official files are kept **byte-for-byte untouched** in
`data/raw/source/`, with their SHA-256 hashes in `data/raw/source/SOURCE.md`
and `docs/RUN_MANIFEST.md`. `tests/test_provenance.py` fails if either file
changes.

## How the working file is derived

`scripts/extract_rajasthan.py` reads the two official files and writes
`data/raw/datagovin_daily_wholesale_rajasthan.csv`, keeping only the Rajasthan
centres in the source (Jaipur, Jodhpur, Kota) and the source's own columns. It
does not change a single value.

A provenance test proves this: restricted to Jaipur/Onion, the script
reproduces the project's original Phase 1 file **byte for byte** (SHA-256
`c59e0b91…2c65c`, 40,345 bytes). So the original file was an unaltered extract,
and every number since traces back to the government's own CSV.

## Which series are used, and which are not

The plan named Jaipur, Chomu and Bassi. **Chomu and Bassi do not appear in this
source**, so they are not used. The three Rajasthan centres that do appear were
all put through the same data gate (at least 400 rows with a complete feature
vector and a genuinely reported target), which was set before any of them were
examined:

| Series | Real prices / raw rows | Usable 1-day rows | Gate |
|---|---|---:|---|
| Onion / Jaipur | 1,288 / 1,551 | 1,002 | **used** |
| Tomato / Jaipur | 1,228 / 1,551 | 995 | **used** |
| Onion / Jodhpur | 625 / 1,122 | 315 | excluded |
| Tomato / Jodhpur | 626 / 1,122 | 322 | excluded |
| Onion / Kota | 470 / 1,105 | 241 | excluded |
| Tomato / Kota | 470 / 1,105 | 245 | excluded |

The excluded series are listed in the dashboard with the reason. The gate was
**not** lowered to admit them. The full table, regenerated from the files, is in
`docs/DATA_REPORT.md`.

## Licence and attribution

What was checked on 28 Oct 2026, and what it shows:

- The platform's **Terms of Use** (<https://www.data.gov.in/terms-of-use>)
  say content is available "under terms described in the license metadata
  element of individual dataset records except where otherwise noted", and
  that wherever material is published "the source must be prominently
  acknowledged".
- The platform's catalogue records for both datasets used here (read through
  its public catalogue API) carry **no explicit licence field**.
- The platform has a *Government Open Data License – India* page
  (<https://www.data.gov.in/Godl>); opening it redirected to a government
  sign-in, so its text was not read here.
- Secondary sources describe GODL-India (notified February 2017) as the
  licence for data shared through the platform under NDSAP, permitting use,
  adaptation and publication, commercial or not, **with attribution**, and
  excluding personal or sensitive data (this dataset has none).

So: attribution is required and is done; GODL-India is the applicable licence
according to the platform and secondary sources, but the exact licence text was
not read from an official page in this session.

Attribution used in this project (dashboard footer, README, `DATA_LICENSE.md`):

> Source: Department of Consumer Affairs (Price Monitoring Cell), Government of
> India, via the Open Government Data Platform India (data.gov.in). Licensed
> under the Government Open Data License – India.

The **code licence and the data licence are separate.** Publishing the code
under an open-source licence does not relicense the data.

> **Manual check before a competition submission:** while signed in to
> data.gov.in, open the GODL page and the dataset page and confirm the licence
> wording.

## Current prices (optional, separate from the evaluation)

| Field | Value (checked 28 Oct 2026) |
|---|---|
| Resource | *Current Daily Price of Various Commodities from Various Markets (Mandi)*, id `9ef84268-d588-465a-a308-a864a43d0070` |
| Publisher | Ministry of Agriculture and Farmers Welfare, Directorate of Marketing and Inspection (data from AGMARKNET) |
| Catalogue | Granularity daily; API available; record last changed 2026-10-28 10:01 UTC |
| Access | `https://api.data.gov.in/resource/<id>?api-key=…&format=json` — without a key it answers `{"error": "Authorization field missing"}`. The bulk file behind the resource returned HTTP 403. |
| Key | Free, from a personal data.gov.in account. Set `DATAGOVIN_API_KEY` (environment variable, or Streamlit Cloud *Settings → Secrets*). Never commit it. |
| Fields expected | `state, district, market, commodity, variety, grade, arrival_date (DD/MM/YYYY), min_price, max_price, modal_price` — the API's documented record schema. **Not yet confirmed by a real keyed call**; the validator rejects a snapshot whose fields differ and lists the difference. |

`src/live_data.py` fetches every page, validates each record (fields, dates,
numbers, min ≤ modal ≤ max, plausible range, duplicates), saves the raw
response with its retrieval time, and replaces `data/live/latest.csv` only if
the whole download is valid. A failed or empty download never overwrites the
last good data. Observation date, the source's update time and our retrieval
time are kept as three separate fields, and freshness is judged from the
latest genuine observation date. These prices are observations, not forecasts,
and no model uses them.

## Known limitations of this dataset

- **Historical only.** The series ends on 28 April 2015. Every forecast is for
  the days just after that date, never "today".
- **Gaps.** Jaipur reports a price on about 55% of calendar days.
- **Stale quotes.** On 83–85% of reported Jaipur days the price is identical to
  the previous report. That may partly reflect how prices were recorded.
- One modal price per centre per day; no minimum/maximum, variety or grade.
- No arrivals, weather, MSP, festival or transport data.

## Sources that were tried and rejected (Sept 2026)

| Source | Why not used |
|---|---|
| CEDA Agri Market Data | Serves **monthly** aggregates; this project forecasts 1–3 days ahead |
| Agmarknet 2.0 | Deep report pages required a login and deep links redirected |
| Kaggle Agmarknet mirror | Third-party copy, and about 11 months long — below the gate |
| data.gov.in "current daily price" resource | A rolling snapshot of about one day, not a history |

## The rule that does not bend

No row was fabricated, padded, synthesised or interpolated into the target.
Carried-forward prices are used only as model **inputs**, for at most two days,
and are flagged; a row is scored only if the mandi really reported a price on
the day being forecast.
