# Competitive landscape

Checked 28 October 2026 from the sources linked. "Not verified" means the
claim could not be confirmed from an official page in this session.

## Existing tools and services

| Tool / source | What it offers (as verified) | How MandiMitra differs |
|---|---|---|
| **AGMARKNET** (Ministry of Agriculture & Farmers Welfare) | Daily commodity prices and arrivals reports across mandis; the India.gov.in listing points to the AGMARKNET 2.0 dashboard and the UPAg portal ([India.gov.in page](https://www.india.gov.in/category/agriculture-rural-environment/subcategory/agricultural-produce/details/prices-arrival-reports-agmarknet)) | AGMARKNET publishes prices; it does not evaluate forecasts. MandiMitra is built to consume its daily API and add benchmark-tested, explained forecasts. |
| **e-NAM** (National Agriculture Market) | Online trading platform; 1,389 mandis in 23 states and 4 UTs integrated, 1.77 crore farmers and 2.53 lakh traders registered as of 11 Feb 2024 ([PIB factsheet, 20 Feb 2024](https://www.pib.gov.in/FactsheetDetails.aspx?Id=149061)) | A trading platform, not a forecasting or evaluation tool. Complementary. |
| **TNAU DEMIC** (Domestic and Export Market Intelligence Cell, Tamil Nadu Agricultural University) | Periodic price-forecast press notes for crops including small onion, maize, coconut, cotton ([2019 press notes](https://agritech.tnau.ac.in/demic/demicpn2019.html)) | Expert seasonal outlooks published as notes; method and accuracy not stated on the page. MandiMitra is daily, open-source and publishes its accuracy against a baseline. |
| **CEDA Agri Market Data** (Ashoka University) | AGMARKNET-based prices; the API returned **monthly** aggregates when checked in Sept 2026 ([site](https://agmarknet.ceda.ashoka.edu.in)) | Monthly vs daily; no forecasting. |
| **CEDA Daily Food Prices** (Ashoka University) | Mirror of the Department of Consumer Affairs retail and wholesale daily series from 2009, 180 centres including Jaipur, CSV download ([README](https://dca.ceda.ashoka.edu.in/README.html)) | A data source, not a forecasting tool — and a candidate for MandiMitra's current data, once its terms are confirmed. |
| Commercial mandi-price apps | Several apps show daily mandi prices; forecasting claims, where made, were not reviewed here | Not verified. MandiMitra's differentiator would be published, reproducible evaluation. |

## Research approaches

| Work | Approach | Benchmark against naive? |
|---|---|---|
| Paul et al. (2022), *PLOS ONE* 17(7) e0270553 | GRNN, SVR, RF, GBM vs ARIMA, brinjal, 17 Odisha markets; GRNN best; DM tests | Random-walk benchmark not reported in the abstract |
| Avinash et al. (2024), *Statistics and Applications* 22(2) | HMM–deep-learning hybrids, weekly TOP prices, Azadpur, 2006–2023 | No naive benchmark reported; DM significance only in some cases |
| Makridakis et al. (2018), *PLOS ONE* 13(3) e0194889 | ML vs statistical methods, 1,045 M3 series | ML methods were dominated by statistical ones |
| **MandiMitra** | 5 candidates incl. Naive; selection by rolling-origin CV; test scored once; DM + Holm; leakage tests; hindsight winners disclosed | **Yes — the central question** |

## Honest positioning

MandiMitra does **not** have better forecasts than anyone; on this data no
model beat the naive benchmark. Its contribution is a transparent, tested
evaluation and a user-facing presentation of that result. Its weaknesses
relative to the tools above: historical data only (until an API key is added),
one mandi, no trading features, no user base.
