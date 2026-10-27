"""Phase 1, step 1: look at the raw download before trusting it.

Run this BEFORE cleaning. It tells you what you actually downloaded:
row counts, real date coverage, how many trading days are missing, price
units, and -- critically -- every distinct spelling of every market and
commodity name, so you can spot "Jaipur" vs "Jaipur (F&V)" before it
splits one series into two.

    python scripts/inspect_data.py
    python scripts/inspect_data.py --all-commodities
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src import config
from src.data_prep import (
    coerce_prices, drop_impossible_rows, load_raw, parse_dates, standardise_text,
)

pd.set_option("display.width", 160)
pd.set_option("display.max_rows", 200)


def rule(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all-commodities", action="store_true",
                    help="do not filter to Onion/Tomato")
    ap.add_argument("--top", type=int, default=25,
                    help="how many markets to list in the coverage table")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    rule("1. FILES FOUND IN data/raw/")
    files = sorted(p.name for p in config.DATA_RAW.iterdir()
                   if p.is_file() and not p.name.startswith("."))
    if not files:
        print("  NOTHING. Download the data first -- see docs/01_DATA_SOURCE.md")
        return 1
    for f in files:
        size_kb = (config.DATA_RAW / f).stat().st_size / 1024
        print(f"  {f:<55} {size_kb:>10,.0f} KB")

    raw = load_raw()
    rule("2. RAW SHAPE AND COLUMNS (after header normalisation)")
    print(f"  rows: {len(raw):,}")
    print(f"  columns: {list(raw.columns)}")
    print("\n  first 3 rows:")
    print(raw.head(3).to_string(index=False))

    df = coerce_prices(parse_dates(standardise_text(raw)))

    rule("3. DATE PARSING")
    bad_dates = int(df["date"].isna().sum())
    print(f"  unparseable dates: {bad_dates:,} of {len(df):,}")
    if df["date"].notna().any():
        print(f"  date range: {df['date'].min().date()} -> {df['date'].max().date()}")
        span = (df["date"].max() - df["date"].min()).days + 1
        print(f"  calendar span: {span:,} days")

    rule("4. DISTINCT COMMODITY NAMES  (watch for duplicate spellings)")
    print(df["commodity"].value_counts().head(40).to_string())

    rule("5. PRICE SANITY  (Rs./quintal expected)")
    for col in ("min_price", "max_price", "modal_price"):
        if col in df.columns:
            s = df[col].dropna()
            if len(s):
                print(f"  {col:<12} n={len(s):>7,}  min={s.min():>10,.0f}  "
                      f"median={s.median():>10,.0f}  max={s.max():>10,.0f}")
    out_of_band = int((~df[config.PRICE_COL].between(config.MIN_PRICE, config.MAX_PRICE)
                       & df[config.PRICE_COL].notna()).sum())
    print(f"  outside [{config.MIN_PRICE:,.0f}, {config.MAX_PRICE:,.0f}]: {out_of_band:,}")

    rule("6. MISSING VALUES PER COLUMN")
    nulls = df.isna().sum()
    print(nulls[nulls > 0].to_string() if nulls.any() else "  none")

    rule("7. DUPLICATES")
    print(f"  fully duplicated rows: {int(df.duplicated().sum()):,}")
    keys = ["commodity", "market", "date"]
    dup_days = int(df.duplicated(keys).sum())
    print(f"  extra rows sharing (commodity, market, date): {dup_days:,}")
    print("    (expected -- these are separate varieties/grades, collapsed by median)")

    if not args.all_commodities:
        wanted = {c.title() for c in config.TARGET_COMMODITIES}
        df = df[df["commodity"].isin(wanted)]
        print(f"\n  filtered to {sorted(wanted)}: {len(df):,} rows")
        if df.empty:
            print("  !! No rows left. Check section 4 for the exact spelling used")
            print("     in your file, then set config.TARGET_COMMODITIES to match.")
            return 1

    df, drop_report = drop_impossible_rows(df)
    rule("8. ROWS DROPPED AS IMPOSSIBLE")
    for k, v in drop_report.items():
        print(f"  {k:<32} {v:,}")

    rule("9. COVERAGE PER (COMMODITY, MARKET) -- THIS DECIDES THE GATE")
    collapsed = df.groupby(["commodity", "market", "date"], as_index=False)[
        config.PRICE_COL].median()

    rows = []
    for (commodity, market), g in collapsed.groupby(["commodity", "market"]):
        d0, d1 = g["date"].min(), g["date"].max()
        span = (d1 - d0).days + 1
        observed = len(g)
        rows.append({
            "commodity": commodity,
            "market": market,
            "observed_days": observed,
            "first": d0.date(),
            "last": d1.date(),
            "span_days": span,
            "reported_pct": round(100 * observed / span, 1) if span else 0.0,
            "median_price": round(float(g[config.PRICE_COL].median()), 0),
        })

    cov = pd.DataFrame(rows).sort_values(
        ["commodity", "observed_days"], ascending=[True, False])
    print(cov.head(args.top).to_string(index=False))

    rule("10. GATE PREVIEW")
    need = config.MIN_ROWS_PER_PAIR
    print(f"  Gate needs >= {need} rows with a complete feature vector per pair.")
    print(f"  Warm-up loss from the longest window is ~{max(max(config.LAGS), max(config.MA_WINDOWS), config.VOL_WINDOW)} rows,")
    print("  and calendar alignment can only add rows, never remove real ones.\n")

    qualifying = cov[cov["observed_days"] >= need]
    if qualifying.empty:
        print("  NO PAIR QUALIFIES YET.")
        print("  -> Widen the downloaded date range, or pick markets from the")
        print("     top of section 9 instead of the preferred list.")
    else:
        print("  Pairs that look likely to pass:")
        print(qualifying.to_string(index=False))

    prefer = {m.title() for m in config.PREFERRED_MARKETS}
    hit = cov[cov["market"].isin(prefer)]
    print(f"\n  Preferred markets {sorted(prefer)}:")
    print("    " + ("not present in this download"
                    if hit.empty else "\n    ".join(
                        f"{r.commodity} / {r.market}: {r.observed_days} observed days"
                        for r in hit.itertuples())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
