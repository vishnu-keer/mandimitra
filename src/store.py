"""Table persistence with a graceful fallback.

Parquet is the preferred format -- typed, compact, fast to read. But it
needs pyarrow, a ~27 MB wheel, which is a real problem on a slow
connection the night before a deadline.

So: if pyarrow imports, we use Parquet. If it does not, we transparently
use CSV instead and the whole pipeline runs unchanged. Phase 1 then needs
nothing beyond pandas and numpy.

Nothing scientific depends on the file format. The only thing a CSV
round-trip loses is dtype metadata, so `date` is re-parsed and the
boolean flags are re-coerced on load.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

DATE_COLUMNS = ("date",)
BOOL_COLUMNS = ("observed",)


def parquet_available() -> bool:
    try:
        import pyarrow  # noqa: F401
        return True
    except Exception:
        return False


def resolve_write_path(path) -> Path:
    """Where this table will actually be written, given what is installed."""
    path = Path(path)
    if path.suffix == ".parquet" and not parquet_available():
        return path.with_suffix(".csv")
    return path


def resolve_read_path(path) -> Path | None:
    """Find an existing table, whichever format it was written in."""
    path = Path(path)
    for candidate in (path, path.with_suffix(".parquet"), path.with_suffix(".csv")):
        if candidate.exists():
            return candidate
    return None


def table_exists(path) -> bool:
    return resolve_read_path(path) is not None


def save_table(df: pd.DataFrame, path) -> Path:
    target = resolve_write_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.suffix == ".parquet":
        df.to_parquet(target, index=False)
    else:
        df.to_csv(target, index=False)
    return target


def load_table(path) -> pd.DataFrame:
    source = resolve_read_path(path)
    if source is None:
        raise FileNotFoundError(
            f"No table found at {path} (tried .parquet and .csv).\n"
            "Run: python scripts/build_features.py"
        )

    if source.suffix == ".parquet":
        df = pd.read_parquet(source)
    else:
        df = pd.read_csv(source)
        for col in DATE_COLUMNS:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        for col in BOOL_COLUMNS:
            if col in df.columns and df[col].dtype != bool:
                df[col] = df[col].astype(str).str.lower().isin(("true", "1", "1.0"))
    return df


def format_note() -> str:
    return ("Parquet (pyarrow installed)" if parquet_available()
            else "CSV (pyarrow not installed -- this is fine, nothing is lost)")
