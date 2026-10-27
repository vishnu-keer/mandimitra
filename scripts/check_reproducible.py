"""Check a fresh rebuild against the committed results.

    cp -r outputs /tmp/committed_outputs          # before rebuilding
    python scripts/extract_rajasthan.py
    python scripts/build_features.py
    python scripts/run_pipeline.py --all-pairs
    python scripts/check_reproducible.py --reference /tmp/committed_outputs

Exit 0 = the rebuild reproduces the published results; exit 1 = it does not.

What must match EXACTLY: every non-numeric value -- which model was selected,
beats_naive, dates, pair and model names, PASS/FAIL style flags -- and the set
and order of rows and columns.

What may differ, and by how much: numbers, by at most
    |a - b| <= ATOL + RTOL * |b|
with ATOL = 0.5 Rs./quintal for individual predictions and interval offsets and
0.05 for every metric. These limits come from a measurement, not a guess: the
same code on CPython 3.10 vs 3.12 moved ARIMA predictions by at most
0.042 Rs./quintal and RMSEs by at most 0.002, through floating-point
differences inside statsmodels' optimiser. Everything else was bit-identical.
The limits are about ten times the measured drift and still far below any
difference that could change a conclusion (the smallest non-zero test-RMSE gap
between a selected model and Naive is 0.31%, about 0.7 Rs./quintal).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from src import config

FILES = ["best_model.csv", "model_comparison.csv", "predictions.csv", "forecast.csv",
         "cv_folds.csv", "feature_importance.csv", "split_boundaries.csv",
         "excluded.csv"]
RTOL = 1e-4
ATOL_METRIC = 0.05
ATOL_PRICE = 0.5
PRICE_COLS = {"y_pred", "predicted_price", "interval_lo_offset", "interval_hi_offset"}


def compare(ref: pd.DataFrame, new: pd.DataFrame, name: str) -> list[str]:
    problems = []
    if list(ref.columns) != list(new.columns):
        return [f"{name}: columns differ: {sorted(set(ref.columns) ^ set(new.columns))}"]
    if len(ref) != len(new):
        return [f"{name}: {len(ref)} rows committed vs {len(new)} rebuilt"]
    for c in ref.columns:
        a, b = new[c], ref[c]
        if pd.api.types.is_numeric_dtype(b) and pd.api.types.is_numeric_dtype(a) \
                and not pd.api.types.is_bool_dtype(b):
            x, y = a.to_numpy(float), b.to_numpy(float)
            if not np.array_equal(np.isnan(x), np.isnan(y)):
                problems.append(f"{name}.{c}: missing values in different rows")
                continue
            atol = ATOL_PRICE if c in PRICE_COLS else ATOL_METRIC
            ok = np.isnan(y) | (np.abs(x - y) <= atol + RTOL * np.abs(y))
            if not ok.all():
                i = int(np.argmax(~ok))
                problems.append(f"{name}.{c}: {int((~ok).sum())} value(s) outside "
                                f"tolerance, e.g. row {i}: {x[i]!r} vs {y[i]!r}")
        else:
            if not a.astype(str).equals(b.astype(str)):
                i = int(np.argmax((a.astype(str) != b.astype(str)).to_numpy()))
                problems.append(f"{name}.{c}: values differ, e.g. row {i}: "
                                f"{a.iloc[i]!r} vs {b.iloc[i]!r}")
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--reference", required=True, type=Path,
                    help="directory holding the committed outputs/*.csv")
    ap.add_argument("--rebuilt", type=Path, default=config.OUTPUTS)
    args = ap.parse_args(argv)
    problems = []
    for f in FILES:
        r, n = args.reference / f, args.rebuilt / f
        if not r.exists() or not n.exists():
            problems.append(f"{f}: missing ({'reference' if not r.exists() else 'rebuild'})")
            continue
        problems += compare(pd.read_csv(r), pd.read_csv(n), f)
    for p in problems:
        print("  FAIL", p)
    print(f"REPRODUCIBILITY: {'PASS' if not problems else 'FAIL'} "
          f"({len(FILES)} files, rtol={RTOL}, atol={ATOL_METRIC} metrics / "
          f"{ATOL_PRICE} Rs. prices)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
