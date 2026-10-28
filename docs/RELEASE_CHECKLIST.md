# Release checklist — master status

Status as of 28 October 2026. **PASS** = verified with evidence ·
**FAIL** = a real defect exists · **BLOCKED** = needs external access or the
owner's input · **NOT STARTED** = no work done.

## Product and science

| # | Item | Status | Evidence |
|---|---|---|---|
| 1 | Product works locally | PASS | 33/33 browser checks; `docs/TEST_REPORT.md` |
| 2 | Deployed version verified | PASS (previous version) · BLOCKED (this update) | Live app checked 28 Oct; this update needs the owner to push, then a smoke test |
| 3 | Data freshness represented accurately | PASS | Banner on every screen; freshness panel; "Not connected" live tab |
| 4 | Current data ingested | BLOCKED | Needs the owner's free data.gov.in API key |
| 5 | Evaluation protocol defensible | PASS | `docs/02_METHODOLOGY.md`; 33 protocol tests; DM tests |
| 6 | Development history disclosed | PASS | Methodology §7, §11; paper §7; JUDGE_QA Q32 |
| 7 | Test suite passes | PASS | 154 passed on clean 3.11 and 3.12 |
| 8 | Reproducible outputs | PASS | Byte-identical rebuild; `check_reproducible.py` PASS |

## Licensing and security

| # | Item | Status | Evidence |
|---|---|---|---|
| 9 | Code licence | PASS | MIT (`LICENSE`) — copyright line is a proposal; change if wanted |
| 10 | Data licence and attribution | PASS (attribution) · BLOCKED (licence text) | Terms of Use read; GODL page needs a signed-in read |
| 11 | No secrets or personal data tracked | PASS | Tracked-file scan; `.gitignore` covers `.env`, secrets, `data/live/` |

## Documents and artifacts

| # | Item | Status | Evidence |
|---|---|---|---|
| 12 | Paper (MD + PDF), references verified | PASS | `research/`; every reference checked against Crossref or publisher pages; FPP3 year is the standard citation year (page shows none) |
| 13 | Technical report (MD + PDF) | PASS | `docs/FINAL_TECHNICAL_REPORT.*` |
| 14 | Deck PPTX opens and renders; PDF checked | PASS | Validator passed; 12 slides rendered and inspected |
| 15 | Poster PDF, QR codes tested | PASS | Both QR codes decoded from the rendered PDFs; URLs opened |
| 16 | Screenshots reflect the product | PASS | Regenerated from the current app, 28 Oct |
| 17 | Results agree across README, paper, report, deck, poster | PASS | Numbers generated into `research/key_numbers.json`; stale-claim scan; two earlier doc errors fixed (gap analysis D5, D6) |
| 18 | Competition docs (15) | PASS | `docs/` |
| 19 | Competition shortlist from official pages | PASS (researched) · no verified open event | `docs/COMPETITION_SHORTLIST.md` |
| 20 | Event-specific rules satisfied | NOT STARTED | Depends on the chosen event (e.g. Pune: ≤ 10 slides) |

## People

| # | Item | Status | Evidence |
|---|---|---|---|
| 21 | Pitch rehearsed against a timer | NOT STARTED | Owner to do — `docs/DEMO_RUNBOOK.md` |
| 22 | User validation | NOT STARTED | Plan ready; no claims made |
| 23 | Hindi wording checked by a native speaker | NOT STARTED | Owner |
| 24 | Owner reviewed and approved this release | BLOCKED | Pending — nothing has been pushed |

## Before pushing

```bash
cd ~/Downloads/mandi-price-forecast
git status                       # review the list of changed files
git diff --stat
source .venv/bin/activate && python -m pytest
```
