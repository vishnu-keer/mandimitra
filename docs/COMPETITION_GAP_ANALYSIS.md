# Competition gap analysis

Audit date: 28 October 2026. Every "current state" line has its evidence next
to it. "Reported" means a claim from an earlier session that was re-checked
here; anything that could not be re-checked says so.

## 1. Current state, with evidence

| Area | State | Evidence (how it was checked) |
|---|---|---|
| Repository | Public, `vishnu-keer/mandimitra`, branch `main`, HEAD `98c8ce8`, 91 tracked files, clean working tree | `git log`, `git status`, `git ls-files` run on the project folder |
| CI | Green on both pushes (`f15c600`, `98c8ce8`), about 2 min 15 s each | Screenshot of the repository's Actions page supplied by the owner |
| Live app | <https://mandimitra.streamlit.app/> up; both series × all tabs render without an exception; actual-vs-predicted chart renders at 1/2/3 days; Hindi works; no horizontal overflow at 375 px | Driven in a real browser on 28 Oct 2026 (DOM checks inside the app frame) |
| Data | Two official files (Onion, Tomato), 1 Jan 2009 – 28 Apr 2015, untouched with SHA-256; Onion/Jaipur and Tomato/Jaipur pass the 400-row gate; Jodhpur, Kota excluded | `tests/test_provenance.py`, `docs/DATA_REPORT.md` regenerated from files |
| Evaluation | 4-fold rolling-origin CV inside the development period; selection by mean fold RMSE; test (last 20% of dates) scored once; target-date embargo; identical rows per model | Phase 2 gate, `tests/test_evaluation_protocol.py` |
| Headline result | CV-selected model never beats Naive on test (Onion: Naive selected; Tomato −5.66/−0.53/−0.31% RMSE). Naive has the lowest test MAE at every pair-horizon | `outputs/best_model.csv`, `outputs/model_comparison.csv` |
| Tests | 154 passed (Python 3.12, clean install) | `python -m pytest` on 28 Oct 2026 |
| Licence (data) | Platform Terms of Use require prominent acknowledgement and point to per-dataset licence metadata; the dataset records carry **no** licence field; the platform's GODL page exists but redirected to a sign-in | Platform Terms of Use page and catalogue API read 28 Oct 2026 |
| Licence (code) | MIT (`LICENSE`), with a separate `DATA_LICENSE.md` | Files present |

## 2. Defects found during this audit

| # | Severity | Defect | Status |
|---|---|---|---|
| D1 | Medium (tooling) | Installing chart/QR libraries into the project's test environment silently upgraded numpy to 2.5.4 and broke 37 tests with a numpy-2 deprecation. Not a project bug, but it shows the pins only hold in a dedicated environment. | Fixed: project env restored to the pins; presentation tools live in a separate environment. Noted in `docs/TEST_REPORT.md`. |
| D2 | Low | "Longest reporting gap … days without a price" was off by one (the number is days *between* two reports). | Fixed: label corrected (English and Hindi). |
| D3 | Low | Current-price download could have been truncated at 1,000 records (no paging). | Fixed: follows `total` across pages; refuses a download needing more than 20 pages rather than truncating. Tests added. |
| D4 | Low | README's second screenshot path pointed at a renamed file. | Fixed with the screenshot refresh. |
| D5 | Medium (accuracy of a claim) | Published docs said Random Forest-delta's default-settings CV RMSE at Tomato 1-day was 92.8; the file says **91.2** (92.8 is the Onion 1-day value). | Fixed in `docs/02_METHODOLOGY.md`; paper uses 91.2. |
| D6 | Medium (accuracy of a claim) | Published docs said Gradient Boosting's Onion 1-day CV RMSE (229) was "the worst of five"; Random Forest's (275) was worse. | Fixed in `docs/02_METHODOLOGY.md` and `docs/JUDGE_QA.md`: "second-worst, almost four times Naive's 61.5". |

No defect was found in the evaluation code, the leakage defences or the
published result files. D5 and D6 were wording errors in documents already on
GitHub; neither changes a conclusion.

## 3. What was missing for a competition

| Gap | Why it matters | Resolution |
|---|---|---|
| Current data | Judges ask "is this live?" | Ingestion layer built and tested against the official API's contract; **blocked** on the owner's free data.gov.in key. App says "Not connected" until then. A second lead: Ashoka University's CEDA publishes a daily mirror of the *same* Department of Consumer Affairs series from 2009 "to the present", including Jaipur (centre 76), downloadable as CSV — but its terms of use are not stated on the page, so it is not used yet (see `docs/BUDGET_AND_ROADMAP.md`). |
| Significance | "Is the difference real?" | Diebold–Mariano tests with Holm adjustment added (`scripts/experiment_significance.py`). |
| Second baseline | "Why only one baseline?" | Weekly seasonal naive evaluated; far worse than Naive (`scripts/experiment_seasonal_naive.py`). |
| Data-quality view | Freshness and stale quotes were only in docs | Overview now shows latest genuine observation, age, unchanged-price share, longest gap, carried-forward share. |
| Research paper, report, deck, poster, competition documents | Required submission formats | Generated in `research/`, `docs/`, `presentation/`. |
| User evidence | Impact claims need users | **Not available.** A consent-based research plan is provided (`docs/USER_RESEARCH_PLAN.md`); no user claims are made. |
| Licence certainty | Redistribution of government data | Attribution done; GODL applicability needs one manual confirmation (see §4). |

## 4. Competition risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Judges expect "AI beats the baseline" | High | Lead with the protocol and the significance tests; the finding *is* the contribution. Rehearse `docs/JUDGE_QA.md` Q6–Q8. |
| Data ends in 2015 | Certain | Stated on every screen; ingestion layer ready for current data once a key is added. |
| Hosted app sleeps or is slow | Medium | Demo locally; open the hosted link beforehand. |
| Only one mandi | Certain | Shown as a gated, honest scope; scaling path documented. |
| No user validation | Certain until done | Research plan ready; do 5–10 consented conversations before a final round. |
| Licence questioned | Low | Terms of Use quote + attribution; confirm GODL on the dataset page. |

## 5. Plan and definition of done

| Phase | Definition of done | Status |
|---|---|---|
| Audit | This document, with evidence | PASS |
| Current data | Validated ingestion, safe fallback, freshness, tests; app never shows a fake live price | PASS for code; BLOCKED for a real keyed call |
| Forecasting science | Seasonal baseline, DM tests, history of decisions disclosed | PASS |
| Product | Quality/freshness panel, latest-prices tab, all tabs verified in a browser | PASS (local); redeploy pending approval |
| Engineering | Tests for ingestion, schema change, failure recovery, stale data; manifest regenerated | PASS |
| Paper and report | Numbers generated from outputs; references verified | See `docs/RELEASE_CHECKLIST.md` |
| Deck, poster, docs | Files open and render; numbers match outputs | See `docs/RELEASE_CHECKLIST.md` |
| Competitions | Shortlist from official pages with dates | See `docs/COMPETITION_SHORTLIST.md` |
| Release | Diff reviewed, tests re-run, owner approval before any push | Pending approval |
