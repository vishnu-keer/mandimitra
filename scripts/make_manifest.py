"""Write the run manifest from the files actually on disk.

    python scripts/make_manifest.py

Produces two files, both generated, never hand-edited:
  docs/RUN_MANIFEST.md        human-readable
  outputs/run_manifest.json   machine-readable; tests/test_manifest.py checks
                              that every hash in it still matches its file

Nothing is copied from an earlier log. Every hash is computed here, from the
bytes the dashboard and the tests actually read. Re-run it after any rebuild.

The code revision is recorded as a SHA-256 over the source files rather than a
git commit id, because a manifest that is committed cannot contain the id of
the commit it is part of. If the project is a git checkout, the HEAD commit at
generation time is recorded as well, for information.
"""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import date
from importlib import metadata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src import config
from src.models import CANDIDATE_NAMES, RANDOM_STATE

ROOT = config.PROJECT_ROOT
JSON_PATH = config.OUTPUTS / "run_manifest.json"
MD_PATH = config.DOCS / "RUN_MANIFEST.md"

SOURCE = {
    "publisher": "Department of Consumer Affairs (Price Monitoring Cell), "
                 "Ministry of Consumer Affairs, Food & Public Distribution, "
                 "Government of India",
    "platform": "Open Government Data (OGD) Platform India, data.gov.in",
    "files": {
        "Onion": "https://data.gov.in/sites/default/files/"
                 "daily_wholesale_price_Onion_upto_apr_2015.csv",
        "Tomato": "https://data.gov.in/sites/default/files/"
                  "daily_wholesale_price_Tomato_upto_apr_2015.csv",
    },
    "retrieved": "2026-10-27",
    "coverage": "2009-01-01 to 2015-04-28",
    "unit": "Rs. per quintal, wholesale (as published)",
    "licence": "Government Open Data License - India (GODL-India); "
               "attribution to the publisher required",
}

# Inputs: the untouched official files, and everything derived from them.
INPUT_FILES = [
    "data/raw/source/daily_wholesale_price_Onion_upto_apr_2015.csv",
    "data/raw/source/daily_wholesale_price_Tomato_upto_apr_2015.csv",
    "data/raw/datagovin_daily_wholesale_rajasthan.csv",
    "data/interim/clean.parquet",
    "data/processed/features.parquet",
]
# Outputs the dashboard reads, plus the preserved experiment and legacy files.
OUTPUT_GLOBS = ["outputs/*.csv", "outputs/experiments/*.csv", "outputs/legacy/*.csv"]
CODE_GLOBS = ["app.py", "src/*.py", "scripts/*.py"]
PACKAGES = ["pandas", "numpy", "scipy", "scikit-learn", "statsmodels",
            "streamlit", "plotly", "pyarrow"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _files(globs):
    out = []
    for g in globs:
        out.extend(sorted(ROOT.glob(g)))
    return [p for p in out if p.is_file() and p.name != JSON_PATH.name]


def code_hash() -> str:
    """One hash over every source file: path and contents, in sorted order."""
    h = hashlib.sha256()
    for p in sorted(_files(CODE_GLOBS)):
        h.update(p.relative_to(ROOT).as_posix().encode() + b"\0")
        h.update(p.read_bytes() + b"\0")
    return h.hexdigest()


def git_head() -> str | None:
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
                           capture_output=True, timeout=5)
        return r.stdout.strip() if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def build() -> dict:
    best = pd.read_csv(config.OUTPUTS / "best_model.csv")
    bounds = pd.read_csv(config.OUTPUTS / "split_boundaries.csv")
    excluded = pd.read_csv(config.OUTPUTS / "excluded.csv")
    clean = pd.read_parquet(config.CLEAN_PATH)
    last = str(pd.to_datetime(clean["date"]).max().date())
    versions = {}
    for pkg in PACKAGES:
        try:
            versions[pkg] = metadata.version(pkg)
        except metadata.PackageNotFoundError:
            versions[pkg] = None
    return {
        "generated": str(date.today()),
        "status": f"HISTORICAL. The source ends on {last}; nothing here is "
                  f"current or live.",
        "source": SOURCE,
        "environment": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(terse=True),
            "packages": versions,
        },
        "code_sha256": code_hash(),
        "git_head_at_generation": git_head(),
        "configuration": {
            "commodities": config.TARGET_COMMODITIES,
            "raw_centres": config.RAW_CENTRES,
            "min_price": config.MIN_PRICE, "max_price": config.MAX_PRICE,
            "max_ffill_days": config.MAX_FFILL_DAYS,
            "lags": config.LAGS, "ma_windows": config.MA_WINDOWS,
            "vol_window": config.VOL_WINDOW,
            "rolling_min_periods_frac": config.ROLLING_MIN_PERIODS_FRAC,
            "horizons": config.HORIZONS,
            "min_rows_per_pair": config.MIN_ROWS_PER_PAIR,
            "test_fraction": config.TEST_FRACTION,
            "cv_folds": config.CV_FOLDS,
            "cv_initial_fraction": config.CV_INITIAL_FRACTION,
            "selection_rule": "lowest mean per-fold CV RMSE; test scored once, after",
            "candidates": CANDIDATE_NAMES,
            "random_state": RANDOM_STATE,
        },
        "evaluated_pairs": sorted({f"{c}/{m}" for c, m in
                                   zip(best["commodity"], best["market"])}),
        "excluded": excluded.to_dict(orient="records"),
        "boundaries": bounds.to_dict(orient="records"),
        "selected": best[["commodity", "market", "horizon", "best_model",
                          "best_test_rmse", "naive_test_rmse",
                          "improvement_over_naive_pct", "beats_naive",
                          "n_test"]].to_dict(orient="records"),
        "inputs": {p.relative_to(ROOT).as_posix(): {"sha256": sha256(p),
                                                     "bytes": p.stat().st_size}
                   for p in (ROOT / f for f in INPUT_FILES) if p.exists()},
        "outputs": {p.relative_to(ROOT).as_posix(): {"sha256": sha256(p),
                                                      "bytes": p.stat().st_size}
                    for p in _files(OUTPUT_GLOBS)},
    }


def to_markdown(m: dict) -> str:
    env, cfg = m["environment"], m["configuration"]
    L = ["# Run manifest", "",
         f"_Generated by `scripts/make_manifest.py` on {m['generated']} from the "
         f"files on disk. Do not edit by hand. Machine-readable copy: "
         f"`outputs/run_manifest.json`; `tests/test_manifest.py` fails if any "
         f"hash below stops matching its file._", "",
         f"**Status:** {m['status']}", "",
         "## Source data", "",
         f"- Publisher: {m['source']['publisher']}",
         f"- Platform: {m['source']['platform']}",
         *[f"- {k}: <{u}>" for k, u in m["source"]["files"].items()],
         f"- Retrieved: {m['source']['retrieved']}",
         f"- Coverage: {m['source']['coverage']}; unit: {m['source']['unit']}",
         f"- Licence: {m['source']['licence']}", "",
         "## Environment that produced these files", "",
         f"- Python {env['python']} ({env['implementation']}), {env['platform']}",
         "- " + ", ".join(f"{k} {v}" for k, v in env["packages"].items()), "",
         f"- Code SHA-256 (app.py, src/, scripts/): `{m['code_sha256']}`",
         f"- git HEAD at generation: `{m['git_head_at_generation'] or 'not a git checkout'}`",
         "",
         "## Configuration", "",
         "| Setting | Value |", "|---|---|",
         *[f"| {k} | {v} |" for k, v in cfg.items()], "",
         "## Pairs", "",
         f"Evaluated: {', '.join(m['evaluated_pairs'])}.", "",
         "| Commodity | Market | Horizon | Excluded because |", "|---|---|---|---|",
         *[f"| {e['commodity']} | {e['market']} | {e['horizon']} | {e['reason']} |"
           for e in m["excluded"]], "",
         "## Evaluation boundaries", "",
         "| Pair | h | Train | CV scored | Test | n train / cv / test |",
         "|---|---:|---|---|---|---|",
         *[f"| {b['commodity']}/{b['market']} | {b['horizon']} | {b['train_start']} – "
           f"{b['train_end']} | {b['cv_start']} – {b['cv_end']} | {b['test_start']} – "
           f"{b['test_end']} | {b['n_train']} / {b['n_cv_scored']} / {b['n_test_scored']} |"
           for b in m["boundaries"]], "",
         "## Selected models (chosen by CV; test scored once, afterwards)", "",
         "| Pair | h | Selected | Test RMSE | Naive test RMSE | vs Naive | Beats Naive | n test |",
         "|---|---:|---|---:|---:|---:|---|---:|",
         *[f"| {s['commodity']}/{s['market']} | {s['horizon']} | {s['best_model']} | "
           f"{s['best_test_rmse']:.2f} | {s['naive_test_rmse']:.2f} | "
           f"{s['improvement_over_naive_pct']:+.2f}% | {bool(s['beats_naive'])} | {s['n_test']} |"
           for s in m["selected"]], "",
         "## File hashes (SHA-256)", "",
         "| File | Bytes | SHA-256 |", "|---|---:|---|",
         *[f"| `{k}` | {v['bytes']:,} | `{v['sha256']}` |"
           for k, v in {**m["inputs"], **m["outputs"]}.items()], "",
         "## Reproducibility, measured", "",
         "- The same environment produces **byte-identical** files on every run "
         "(checked by rebuilding from the official files twice).",
         "- CPython 3.11 and 3.12 on Linux with the pinned requirements produce "
         "byte-identical files to each other.",
         "- A different interpreter or platform (measured: CPython 3.10 on Linux) "
         "changes only the ARIMA numbers, by at most about 0.04 Rs./quintal in a "
         "prediction and 2e-3 in an RMSE, through floating-point differences in "
         "statsmodels' optimiser. The tree models, Naive, the selected models and "
         "every PASS/FAIL decision are unchanged. `scripts/check_reproducible.py` "
         "checks a rebuild against these files with exactly that tolerance.",
         ""]
    return "\n".join(L)


def main():
    m = build()
    JSON_PATH.write_text(json.dumps(m, indent=2, default=str) + "\n")
    MD_PATH.write_text(to_markdown(m))
    print(f"wrote {JSON_PATH.relative_to(ROOT)} and {MD_PATH.relative_to(ROOT)}")
    print(f"  {len(m['inputs'])} input files, {len(m['outputs'])} output files hashed")
    print(f"  code sha256 {m['code_sha256'][:16]}...  python {m['environment']['python']}")


if __name__ == "__main__":
    main()
