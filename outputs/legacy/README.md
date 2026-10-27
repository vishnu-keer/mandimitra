# Legacy results — superseded 2026-10-27

These are the Phase 2 outputs produced by the **two-way split** protocol
(train / test only), kept deliberately rather than overwritten.

They are **not comparable** with the current `outputs/*.csv`, for two reasons:

1. **Selection.** The old protocol reported the lowest-**test**-RMSE model as
   "best". That is model selection on the test set, so the headline number was
   also the number that chose the winner. The current protocol selects on a
   separate validation window and scores test once, afterwards.

2. **Target embargo.** The old split cut on the feature row's own date `t`,
   not on its target date `t + h`, so 1–3 training rows per horizon carried
   targets that fell inside the test window. The current split purges them.

One further difference, which is *not* a methodology change: the old
`ARIMA … split=train` rows show `n=1`. That was a defect — the ARIMA
evaluation only ever built forecasts for the test window, so a lookup for a
training row missed on every row but the last. It is fixed in
`src/models.py::ArimaModel._build_insample_cache`, and the fix was verified to
leave ARIMA's **test** predictions unchanged to within 5e-13.

Generated on macOS / CPython 3.11. See `docs/RUN_MANIFEST.md` for why these
files are not bit-identical to a Linux run.
