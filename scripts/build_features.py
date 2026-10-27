"""Phase 1, step 2: raw -> clean -> features, then verify the Phase 1 gate.

    python scripts/build_features.py
    python scripts/build_features.py --markets Jaipur Chomu Bassi

Writes:
    data/interim/clean.parquet
    data/processed/features.parquet

Exits non-zero if the Phase 1 gate fails, so you cannot accidentally
proceed to Phase 2 on a dataset that will not support it.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from src import config
from src.data_prep import build_clean, save_clean
from src.store import format_note, table_exists
from src.features import (
    add_features, drop_incomplete_feature_rows, feature_columns,
    save_features, target_columns, verify_no_leakage,
)

pd.set_option("display.width", 170)


def rule(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def spot_check_lag(clean: pd.DataFrame, feats: pd.DataFrame, n=3, seed=0):
    """Gate item 3: prove lag_1 really is the previous calendar day's price."""
    rng = np.random.default_rng(seed)
    lookup = clean.set_index(["commodity", "market", "date"])[config.PRICE_COL]
    candidates = feats[feats["lag_1"].notna()]
    if candidates.empty:
        return False, []

    picks = candidates.iloc[rng.choice(len(candidates),
                                       size=min(n, len(candidates)),
                                       replace=False)]
    results, ok = [], True
    for row in picks.itertuples():
        prev_day = row.date - pd.Timedelta(days=1)
        try:
            expected = float(lookup.loc[(row.commodity, row.market, prev_day)])
        except KeyError:
            expected = float("nan")
        got = float(row.lag_1)
        match = (np.isnan(expected) and np.isnan(got)) or np.isclose(expected, got)
        ok = ok and match
        results.append({
            "commodity": row.commodity, "market": row.market,
            "date": row.date.date(), "lag_1_in_features": got,
            "price_on_previous_day": expected, "match": match,
        })
    return ok, results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commodities", nargs="*", default=None)
    ap.add_argument("--markets", nargs="*", default=None,
                    help="omit to keep every market in the file")
    ap.add_argument("--min-rows", type=int, default=config.MIN_ROWS_PER_PAIR)
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    commodities = args.commodities or config.TARGET_COMMODITIES

    rule("1. CLEANING")
    clean, report = build_clean(commodities=commodities, markets=args.markets)
    for key, value in report.items():
        print(f"  {key:<32} {value}")
    if clean.empty:
        print("\n  Clean table is empty. Run scripts/inspect_data.py and check")
        print("  the exact commodity / market spellings in your download.")
        return 1
    written = save_clean(clean)
    print(f"\n  storage format: {format_note()}")
    print(f"  wrote {written.relative_to(config.PROJECT_ROOT)}  ({len(clean):,} rows)")
    unobserved = int((~clean["observed"]).sum())
    gaps = int(clean[config.PRICE_COL].isna().sum())
    print(f"  calendar rows not reported by the mandi: {unobserved:,} "
          f"({100 * unobserved / len(clean):.1f}%)")
    print(f"    of which carried forward (usable): {unobserved - gaps:,}")
    print(f"    of which still gaps (dropped at feature stage): {gaps:,}")

    rule("2. LEAKAGE VERIFICATION  (rebuild on truncated data, compare)")
    leak = verify_no_leakage(clean)
    for key, value in leak.items():
        print(f"  {key:<24} {value}")
    if not leak["passed"]:
        print("\n  LEAKAGE CHECK FAILED -- do not proceed. A feature is using")
        print("  information from after its own row. Fix src/features.py.")
        return 1
    print("\n  PASS: every feature before the cutoff is byte-identical when the")
    print("  future is deleted, so no feature can be reading forward in time.")

    rule("3. FEATURE ENGINEERING")
    featured = add_features(clean)
    feats = drop_incomplete_feature_rows(featured)
    print(f"  rows before warm-up trim: {len(featured):,}")
    print(f"  rows after  warm-up trim: {len(feats):,}")
    print(f"  feature columns ({len(feature_columns())}): {feature_columns()}")
    print(f"  target columns:  {target_columns()}")
    written = save_features(feats)
    print(f"\n  wrote {written.relative_to(config.PROJECT_ROOT)}")

    rule("4. COVERAGE PER PAIR  (feature-complete rows)")
    summary = []
    for (commodity, market), g in feats.groupby(config.GROUP_KEYS):
        trainable = {}
        for h in config.HORIZONS:
            usable = g[f"y_h{h}"].notna() & g[f"y_h{h}_observed"]
            trainable[f"usable_h{h}"] = int(usable.sum())
        summary.append({
            "commodity": commodity, "market": market,
            "rows": len(g),
            "first": g["date"].min().date(), "last": g["date"].max().date(),
            "imputed_pct": round(100 * (~g["observed"]).mean(), 1),
            **trainable,
            "passes_gate": trainable["usable_h1"] >= args.min_rows,
        })
    cov = pd.DataFrame(summary).sort_values("rows", ascending=False)
    print(cov.to_string(index=False))

    rule("5. LAG SPOT CHECK  (gate item 3)")
    ok, rows = spot_check_lag(clean, feats)
    print(pd.DataFrame(rows).to_string(index=False) if rows else "  no rows to check")

    rule("6. PHASE 1 GATE")
    passing = cov[cov["passes_gate"]]
    checks = {
        "feature table written, no nulls in feature cols":
            bool(table_exists(config.FEATURES_PATH)
                 and not feats[[c for c in feature_columns()
                                if c in feats.columns
                                and not feats[c].isna().all()]].isna().any().any()),
        f">= {args.min_rows} rows with an OBSERVED h=1 target for >= 1 pair":
            not passing.empty,
        "lag_1 spot check matches previous calendar day": ok,
        "no-leakage verification passed": bool(leak["passed"]),
        "docs/01_DATA_SOURCE.md filled in":
            (config.DOCS / "01_DATA_SOURCE.md").exists()
            and "FILL THIS IN" not in (config.DOCS / "01_DATA_SOURCE.md").read_text(),
    }
    for label, passed in checks.items():
        print(f"  [{'PASS' if passed else 'FAIL'}] {label}")

    if passing.empty:
        print(f"\n  Best pair has {int(cov['usable_h1'].max()):,} usable rows, "
              f"need {args.min_rows}.")
        print("  Download a wider date range, or switch to a market with more history.")

    if all(checks.values()):
        print("\n  PHASE 1 GATE: PASS")
        print(f"  Usable pairs: "
              f"{', '.join(f'{r.commodity}/{r.market} ({r.usable_h1} usable)' for r in passing.itertuples())}")
        return 0

    print("\n  PHASE 1 GATE: FAIL -- do not start Phase 2 yet.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
