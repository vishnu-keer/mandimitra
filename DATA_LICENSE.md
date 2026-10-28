# Data licence and attribution

The code in this repository is MIT-licensed (see `LICENSE`). **The data is not
covered by that licence.**

## Source data

`data/raw/source/daily_wholesale_price_Onion_upto_apr_2015.csv` and
`data/raw/source/daily_wholesale_price_Tomato_upto_apr_2015.csv` are unaltered
copies of files published on the Open Government Data (OGD) Platform India
(data.gov.in) by the Department of Consumer Affairs (Price Monitoring Cell),
Ministry of Consumer Affairs, Food & Public Distribution, Government of India.

Data on data.gov.in is made available under the **Government Open Data License –
India (GODL-India)**, which permits use, adaptation and publication, for
commercial and non-commercial purposes, with attribution to the data provider.
The platform's licence page is <https://www.data.gov.in/Godl>, and its Terms
of Use (<https://www.data.gov.in/terms-of-use>) require that the source be
prominently acknowledged. (On 28 Oct 2026 the licence page redirected to a
sign-in, so confirm its wording there before relying on this summary.)

Current prices fetched with `scripts/fetch_current_prices.py` come from the
*Current Daily Price of Various Commodities from Various Markets (Mandi)*
resource (Directorate of Marketing and Inspection / AGMARKNET) on the same
platform and carry the same attribution duty. They are stored only in
`data/live/`, which is not committed.

## Derived data

Everything in `data/raw/datagovin_daily_wholesale_rajasthan.csv`,
`data/interim/`, `data/processed/` and `outputs/` is derived from those files
by the scripts in this repository and is shared on the same terms, with the
same attribution.

## Attribution statement

> Source: Department of Consumer Affairs (Price Monitoring Cell), Government of
> India, via the Open Government Data Platform India (data.gov.in). Licensed
> under the Government Open Data License – India. Processed by MandiMitra.

No endorsement by the Government of India or the Department of Consumer Affairs
is implied. The data is historical (it ends on 28 April 2015) and is provided
as published, without warranty.
