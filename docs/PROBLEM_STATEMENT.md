# Problem statement

## The problem

Farmers and small traders sell into regulated wholesale markets (mandis) whose
prices can move sharply. In the official series used here, Jaipur's wholesale
onion price went from Rs. 600–900 per quintal in June 2013 to Rs. 4,500 on
21 October 2013 and back to about Rs. 800 by December **[measured,
`data/interim/clean.parquet`]**. Research links Indian onion price volatility
to uncertainty in market arrivals rather than production shocks (Birthal,
Negi and Joshi, 2019, *JADEE* 9(3)).

Tools now offer AI price predictions to these users. Their accuracy claims
are hard to check: it is rarely visible whether the model was compared with
the simplest forecast — "tomorrow's price = today's price" — or whether the
model was chosen using the same data its accuracy is reported on.

## Who is affected

| User | Decision | Risk from a poorly tested forecast |
|---|---|---|
| Farmer | Sell now or hold a few days | Holding or dumping produce on a false signal |
| Trader | How much to buy and hold | Inventory losses on a false trend |
| Student / analyst | Which method to trust or publish | Reproducing an inflated result |

These needs are assumptions until tested with users (`docs/USER_RESEARCH_PLAN.md`).

## Problem we can actually test

Given a daily wholesale price series for one commodity in one mandi, with
missing days, can forecasts 1–3 days ahead be made more accurate than
repeating the last reported price, using price history alone — and how should
the answer, its uncertainty and the data's limitations be shown to a
non-specialist?

## Out of scope (now)

Real-time trading advice; income or welfare claims; markets without enough
reported history; inputs other than prices (arrivals, weather, policy) — the
last is the main item on the roadmap.

## Success criteria

1. A protocol that cannot select on the test period, with automated checks.
2. A clear, significance-tested answer for every series and horizon.
3. A dashboard that a non-specialist reads correctly (to be measured).
4. Every number traceable to a file; ₹0 to run.
