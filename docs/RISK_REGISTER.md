# Risk register

Likelihood / impact: H = high, M = medium, L = low. Reviewed 28 Oct 2026.

| # | Risk | L | I | Mitigation | Owner | Status |
|---|---|---|---|---|---|---|
| R1 | Judges expect "AI beats baseline" and mark down a null result | H | H | Lead with the protocol correction (7.33% → p = 0.505); rehearse JUDGE_QA Q6–Q8, Q22 | Presenter | Open |
| R2 | Data ends 2015; "not current" | Certain | M | Banner on every screen; tested API client ready; get a free key | Owner | Open — needs key |
| R3 | Hosted app asleep or down during judging | M | M | Demo locally; open the link 10 min before; screenshots as fallback | Presenter | Mitigated |
| R4 | Streamlit Cloud default Python changes again and breaks a redeploy | M | M | Python 3.12 chosen explicitly; documented in DEPLOY.md | Owner | Mitigated |
| R5 | Licence questioned | L | M | Attribution everywhere; confirm GODL text while signed in to data.gov.in | Owner | Open — manual check |
| R6 | Official API schema differs from documented | M | L | Validator rejects mismatches and keeps the last good data; first keyed call will confirm | Owner | Open |
| R7 | Free tier terms change | L | M | Everything also runs locally at ₹0; no lock-in | Owner | Accepted |
| R8 | Dependency drift (e.g. numpy 2) breaks tests | M | M | All transitive pins; CI on 3.11/3.12; tooling in a separate env | Owner | Mitigated |
| R9 | Over-trust by a real user | L now | H later | Notices, reference forecast, no bands that failed; user study before any wider use | Owner | Mitigated (design) |
| R10 | Doc/number drift between paper, deck, README | M | M | Numbers generated from outputs into `research/key_numbers.json`; consistency check before release | Owner | Mitigated |
| R11 | User study raises privacy issues | L | M | No identifiers, verbal consent, university check | Owner | Planned |
| R12 | Single developer / bus factor | H | M | Public repo, docs, tests, CI | Owner | Accepted |
