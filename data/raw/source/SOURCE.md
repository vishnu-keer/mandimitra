# Official source files — untouched

These two files are exactly as served by the Open Government Data Platform
India. They are never edited. `scripts/extract_rajasthan.py` derives
`data/raw/datagovin_daily_wholesale_rajasthan.csv` from them.

| File | Bytes | SHA-256 | Rows |
|---|---:|---|---:|
| `daily_wholesale_price_Onion_upto_apr_2015.csv` | 2,083,645 | `e0b5171b81bc93983104990728a45d271f30c794bcc3c53f73553cf91fd1335a` | 73,311 |
| `daily_wholesale_price_Tomato_upto_apr_2015.csv` | 2,140,492 | `fb872513c2113ae3ec39f5a18ecba8eced089d9545e55f91382530b2cebb88c1` | 73,311 |

- **URLs:** `https://data.gov.in/sites/default/files/daily_wholesale_price_Onion_upto_apr_2015.csv`
  and the same path with `Tomato` (served from `www.data.gov.in`).
- **Retrieved:** 27 October 2026, via the browser, with the hash computed
  in-browser from the server response and re-checked on disk after download
  (both matched).
- **Publisher:** Department of Consumer Affairs, Ministry of Consumer Affairs,
  Food & Public Distribution, Government of India (Price Monitoring Cell).
- **Schema:** `Date,Centre_Name,Commodity_Name,Price` — one row per centre per
  day; `Date` is `DD-MM-YY`; `Price` is Rs. per quintal, wholesale; `0` is the
  source's missing-value code. CRLF line endings.
- **Coverage:** 01-01-2009 to 28-04-2015, 73 centres nationally.
- **Licence:** published on data.gov.in under the Government Open Data
  License – India (GODL-India), which permits use, adaptation and
  redistribution with attribution. Check the licence statement on the
  dataset's catalog page before redistributing; it applies to the data, not
  to this project's code.

## Rajasthan coverage in these files (raw rows / non-zero prices)

| Centre | Onion | Tomato | First date |
|---|---|---|---|
| JAIPUR | 1,551 / 1,288 | 1,551 / 1,228 | 01-01-2009 |
| JODHPUR | 1,122 / 625 | 1,122 / 626 | 31-08-2010 |
| KOTA | 1,105 / 470 | 1,105 / 470 | 31-08-2010 |

## Provenance check

Restricted to `JAIPUR` / `Onion`, the extraction script reproduces the
project's original raw file byte for byte
(`c59e0b91a38dec188a88f0d33f270615a878a702dfa1aceb97feb3fc99e2c65c`, 40,345
bytes). The original file was therefore an unaltered extract of this source.
That is enforced by `tests/test_provenance.py`.
