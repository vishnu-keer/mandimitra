# Poster content

The printable poster is `presentation/MandiMitra_Poster.pdf` (A2 portrait,
one page), built from `presentation/poster.html`. Both QR codes were decoded
from the rendered PDF and point to the intended URLs (checked 28 Oct 2026).

| Panel | Content |
|---|---|
| Header | MandiMitra · Explainable mandi price intelligence · the research question · author · QR codes: live app, code + data |
| Warning | Historical data, ends 28 April 2015; not advice |
| Problem | Rs. 600–900 → Rs. 4,500/q (Jaipur onion, June → 21 Oct 2013); 84.8% of reported days repeat the price; ~55% of days reported |
| Solution | Overview screenshot; bilingual dashboard with reference forecast, freshness, honest uncertainty, CSV, phone-ready, ₹0 |
| Architecture and data | Official CSVs → clean → features ≤ t → choose by CV → test once → read-only dashboard; Onion and Tomato, Jaipur, 2009–2015; gate; GODL-India; 154 tests |
| Evaluation | Five candidates; reported days only; identical days; embargo; Diebold–Mariano + Holm |
| Verified results | Table of the six pair-horizons: chosen model, test RMSE, Naive RMSE, vs Naive |
| Significance | 0 of 48 tests favour a model; first version's "+7.33%" has p = 0.505 |
| Limitations / Next | As in `docs/02_METHODOLOGY.md` §12 and `docs/BUDGET_AND_ROADMAP.md` |

Print: A2 (420 × 594 mm), "actual size", no scaling. Check the QR codes with
two phones after printing.
