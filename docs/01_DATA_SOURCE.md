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

Datasets on data.gov.in are published under the **Government Open Data
License – India (GODL-India)**, notified in February 2017. It permits use,
adaptation and publication, commercial or not, **with attribution** to the
data provider. It excludes personal and sensitive data, which this dataset does
not contain.

Attribution used in this project (dashboard footer, README, `DATA_LICENSE.md`):

> Source: Department of Consumer Affairs (Price Monitoring Cell), Government of
> India, via the Open Government Data Platform India (data.gov.in). Licensed
> under the Government Open Data License – India.

The **code licence and the data licence are separate.** Publishing the code
under an open-source licence does not relicense the data.

> **Check before publishing.** The licence page
> `https://data.gov.in/government-open-data-license-india` could not be read
> automatically from here (the site blocks automated access). Before making
> the repository public, open the dataset page on data.gov.in in a browser and
> confirm that it shows GODL-India.

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
