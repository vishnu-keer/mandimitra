"""Derive the Rajasthan subset from the untouched official downloads.

    python scripts/extract_rajasthan.py

Input  : data/raw/source/daily_wholesale_price_<Commodity>_upto_apr_2015.csv
         (official data.gov.in files; hashes recorded in data/raw/source/SOURCE.md)
Output : data/raw/datagovin_daily_wholesale_rajasthan.csv

The transformation is deliberately minimal and fully reversible to the source:
  * keep rows whose Centre_Name is one of config.RAW_CENTRES
  * keep the source's four columns, names and values exactly as published
  * keep the source's row order (commodity files in the order listed below)
  * normalise CRLF line endings to LF
Nothing is cleaned, imputed or re-typed here; that happens in src/data_prep.py,
where every decision is logged. Zero prices (the source's missing-value code)
are therefore still present in the output, as published.

The check that matters: restricted to JAIPUR/Onion, this script reproduces the
project's original raw file byte for byte (SHA-256 c59e0b91...), proving the
original was an unaltered extract of the government file.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config

COMMODITY_FILES = ["Onion", "Tomato"]
HEADER = "Date,Centre_Name,Commodity_Name,Price"


def source_path(commodity: str) -> Path:
    return config.DATA_RAW_SOURCE / f"daily_wholesale_price_{commodity}_upto_apr_2015.csv"


def extract(centres=None, commodities=None, source_dir=None) -> str:
    centres = set(centres or config.RAW_CENTRES)
    commodities = commodities or COMMODITY_FILES
    out = [HEADER]
    for c in commodities:
        path = (Path(source_dir) if source_dir else config.DATA_RAW_SOURCE) / \
            f"daily_wholesale_price_{c}_upto_apr_2015.csv"
        if not path.exists():
            raise FileNotFoundError(
                f"{path} not found. Download it from "
                f"https://data.gov.in/sites/default/files/{path.name} "
                f"(see data/raw/source/SOURCE.md).")
        lines = path.read_text(encoding="utf-8").splitlines()
        if lines[0].strip() != HEADER:
            raise ValueError(f"{path.name}: unexpected header {lines[0]!r}")
        out.extend(l for l in lines[1:] if l.split(",")[1:2] and
                   l.split(",")[1] in centres)
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-only", action="store_true",
                    help="verify source hashes and print counts; write nothing")
    args = ap.parse_args()

    for c in COMMODITY_FILES:
        p = source_path(c)
        if p.exists():
            print(f"  source {p.name:<52} sha256={hashlib.sha256(p.read_bytes()).hexdigest()}")
    text = extract()
    rows = text.count("\n") - 1
    print(f"  extracted {rows:,} rows for centres {', '.join(config.RAW_CENTRES)}")
    if args.check_only:
        return 0
    config.RAW_SUBSET_PATH.write_text(text, encoding="utf-8", newline="")
    print(f"  wrote {config.RAW_SUBSET_PATH.relative_to(config.PROJECT_ROOT)}  "
          f"sha256={hashlib.sha256(text.encode()).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
