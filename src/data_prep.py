"""Raw download -> clean, calendar-aligned daily price table.

Pipeline order matters and is deliberate:

    read files -> normalise headers -> standardise text -> parse dates
    -> coerce prices -> drop impossible rows -> de-duplicate
    -> align to a continuous daily calendar

The calendar-alignment step is the one most student projects skip. Mandis
do not trade every day (holidays, no arrivals, no reporting). Without
reindexing, `price.shift(1)` silently means "the previous *trading* day",
which may be 1 day ago or 9 days ago depending on the row. Every lag,
moving average and volatility feature built on that is quietly wrong.
"""
from __future__ import annotations

import io
import logging

import numpy as np
import pandas as pd

from . import config
from .schema import REQUIRED_COLUMNS, build_rename_map
from .store import load_table, save_table

log = logging.getLogger(__name__)

SUPPORTED_SUFFIXES = {".csv", ".txt", ".xlsx", ".xls", ".html", ".htm"}
PRICE_COLUMNS = ["min_price", "max_price", "modal_price", "arrivals"]


# --------------------------------------------------------------- reading
def _read_html_tables(path):
    """Agmarknet often serves an HTML table with a .xls extension."""
    text = path.read_text(errors="replace")
    tables = pd.read_html(io.StringIO(text))
    if not tables:
        raise ValueError(f"No HTML tables found in {path.name}")
    # The price grid is the widest table on the page.
    return max(tables, key=lambda t: (t.shape[1], t.shape[0]))


def _read_any(path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in {".csv", ".txt"}:
        return pd.read_csv(path, dtype=str, encoding_errors="replace")
    if suffix in {".html", ".htm"}:
        return _read_html_tables(path)
    if suffix in {".xlsx", ".xls"}:
        try:
            return pd.read_excel(path, dtype=str)
        except Exception as exc:  # noqa: BLE001 - fall back to the HTML case
            log.warning("%s is not a real spreadsheet (%s); trying HTML", path.name, exc)
            return _read_html_tables(path)
    raise ValueError(f"Unsupported file type: {path.name}")


def load_raw(raw_dir=None) -> pd.DataFrame:
    """Read and concatenate every raw file in data/raw/.

    Multiple files are fine and expected -- one per commodity, or one per
    year if your source caps the export date range. Headers may differ
    between files; each is normalised independently before concatenation.
    """
    raw_dir = raw_dir or config.DATA_RAW
    files = sorted(
        p for p in raw_dir.iterdir()
        if p.is_file()
        and p.suffix.lower() in SUPPORTED_SUFFIXES
        and not p.name.startswith((".", "~$"))
    )
    if not files:
        raise FileNotFoundError(
            f"No data files in {raw_dir}.\n"
            "Download the mandi price export first (see docs/01_DATA_SOURCE.md) "
            "and save it into data/raw/."
        )

    frames = []
    for path in files:
        df = _read_any(path)
        rename, unmapped = build_rename_map(df.columns)
        df = df.rename(columns=rename)
        df = df.loc[:, ~df.columns.duplicated()]

        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(
                f"{path.name}: could not find required column(s) {missing}.\n"
                f"  Columns present in the file: {list(df.columns)}\n"
                f"  Unmapped headers: {unmapped}\n"
                "Add the right spelling to COLUMN_ALIASES in src/schema.py."
            )
        if unmapped:
            log.info("%s: ignoring unmapped columns %s", path.name, unmapped)

        keep = [c for c in df.columns if c in set(REQUIRED_COLUMNS) | set(PRICE_COLUMNS)
                | {"state", "district", "variety", "grade"}]
        df = df[keep].copy()
        df["source_file"] = path.name
        frames.append(df)
        log.info("%s: %d rows", path.name, len(df))

    return pd.concat(frames, ignore_index=True)


# ----------------------------------------------------------- cleaning
def _clean_text(series: pd.Series) -> pd.Series:
    return (
        series.astype("string")
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
        .str.title()
    )


def standardise_text(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ("state", "district", "market", "commodity", "variety", "grade"):
        if col in df.columns:
            df[col] = _clean_text(df[col])

    # Apply manual spelling fixes discovered during inspection.
    for col, mapping in config.NAME_OVERRIDES.items():
        if col in df.columns and mapping:
            df[col] = df[col].replace(mapping)
    return df


def parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Indian mandi exports are day-first (dd/mm/yyyy or dd-Mon-yyyy)."""
    df = df.copy()
    raw = df["date"].astype("string").str.strip()
    parsed = pd.to_datetime(raw, errors="coerce", dayfirst=True, format="mixed")

    still_bad = parsed.isna() & raw.notna()
    if still_bad.any():
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%d-%b-%Y", "%Y-%m-%d"):
            retry = pd.to_datetime(raw[still_bad], errors="coerce", format=fmt)
            parsed.loc[still_bad] = parsed.loc[still_bad].fillna(retry)
            still_bad = parsed.isna() & raw.notna()
            if not still_bad.any():
                break

    df["date"] = parsed.dt.normalize()
    return df


def coerce_prices(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in PRICE_COLUMNS:
        if col in df.columns:
            cleaned = (
                df[col].astype("string")
                .str.replace(r"[^0-9.\-]", "", regex=True)
                .replace("", pd.NA)
            )
            df[col] = pd.to_numeric(cleaned, errors="coerce")
    return df


def drop_impossible_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    n0 = len(df)
    report = {"rows_in": n0}

    df = df[df["date"].notna()]
    report["dropped_unparseable_date"] = n0 - len(df)

    n1 = len(df)
    df = df[df[config.PRICE_COL].notna()]
    report["dropped_missing_price"] = n1 - len(df)

    n2 = len(df)
    df = df[df[config.PRICE_COL].between(config.MIN_PRICE, config.MAX_PRICE)]
    report["dropped_price_out_of_range"] = n2 - len(df)

    if {"min_price", "max_price"}.issubset(df.columns):
        bad = (df["min_price"] > df["max_price"]) & df["min_price"].notna() & df["max_price"].notna()
        report["flagged_min_above_max"] = int(bad.sum())

    report["rows_out"] = len(df)
    return df.copy(), report


def deduplicate(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Collapse to one row per (commodity, market, date).

    A single mandi reports several varieties and grades on the same day.
    We take the MEDIAN modal price across them -- robust to one odd variety
    -- and SUM arrivals, which are additive. This choice is documented in
    docs/02_METHODOLOGY.md because it is an analyst decision, not a fact.
    """
    report = {"rows_in": len(df)}
    df = df.drop_duplicates()
    report["exact_duplicates_removed"] = report["rows_in"] - len(df)

    keys = ["commodity", "market", "date"]
    report["multi_variety_days_collapsed"] = int(len(df) - len(df.drop_duplicates(keys)))

    agg = {c: "median" for c in ("min_price", "max_price", "modal_price") if c in df.columns}
    if "arrivals" in df.columns:
        agg["arrivals"] = "sum"
    for col in ("state", "district"):
        if col in df.columns:
            agg[col] = "first"

    out = df.groupby(keys, as_index=False).agg(agg)
    report["rows_out"] = len(out)
    return out, report


def calendar_align(df: pd.DataFrame, max_ffill_days=None) -> pd.DataFrame:
    """Reindex every (commodity, market) series to a continuous daily index.

    Adds two transparency columns:
      observed        - True if a real reported price exists for this date
      days_since_obs  - days since the last real observation (0 if observed)

    Forward-fill is strictly backward-looking, so it cannot leak future
    information. bfill / interpolate WOULD leak and are never used.
    """
    max_ffill_days = config.MAX_FFILL_DAYS if max_ffill_days is None else max_ffill_days
    pieces = []

    for (commodity, market), group in df.groupby(config.GROUP_KEYS, sort=True):
        group = group.sort_values("date").set_index("date")
        full_index = pd.date_range(group.index.min(), group.index.max(), freq="D")
        group = group.reindex(full_index)

        group["commodity"] = commodity
        group["market"] = market
        group["observed"] = group[config.PRICE_COL].notna().to_numpy()

        for col in PRICE_COLUMNS:
            if col in group.columns and max_ffill_days > 0:
                group[col] = group[col].ffill(limit=max_ffill_days)
        for col in ("state", "district"):
            if col in group.columns:
                group[col] = group[col].ffill().bfill()  # static labels, not prices

        positions = np.arange(len(group), dtype=float)
        last_obs = pd.Series(np.where(group["observed"], positions, np.nan),
                             index=group.index).ffill()
        group["days_since_obs"] = positions - last_obs

        pieces.append(group.rename_axis("date").reset_index())

    out = pd.concat(pieces, ignore_index=True)

    # NOTE: rows whose price is still NaN (gaps longer than the ffill limit)
    # are deliberately KEPT here. Dropping them would leave a non-contiguous
    # date index, and `price.shift(1)` on a gappy frame silently means "the
    # previous ROW" rather than "the previous CALENDAR DAY" -- which is the
    # exact bug calendar alignment exists to prevent. They carry NaN features
    # and are removed by features.drop_incomplete_feature_rows() instead,
    # after every lag and window has been computed on a continuous index.
    return out.sort_values(config.GROUP_KEYS + ["date"]).reset_index(drop=True)


# ------------------------------------------------------------ pipeline
def build_clean(raw_dir=None, commodities=None, markets=None, verbose=True):
    """Full raw -> clean pipeline. Returns (clean_df, report_dict)."""
    reports = {}
    df = load_raw(raw_dir)
    reports["loaded_rows"] = len(df)

    df = standardise_text(df)
    df = parse_dates(df)
    df = coerce_prices(df)

    if commodities:
        wanted = {c.title() for c in commodities}
        df = df[df["commodity"].isin(wanted)]
        reports["rows_after_commodity_filter"] = len(df)
    if markets:
        wanted = {m.title() for m in markets}
        df = df[df["market"].isin(wanted)]
        reports["rows_after_market_filter"] = len(df)

    df, reports["drop"] = drop_impossible_rows(df)
    df, reports["dedupe"] = deduplicate(df)
    df = calendar_align(df)
    reports["clean_rows"] = len(df)

    if verbose:
        log.info("clean report: %s", reports)
    return df, reports


def save_clean(df: pd.DataFrame, path=None):
    return save_table(df, path or config.CLEAN_PATH)


def load_clean(path=None) -> pd.DataFrame:
    return load_table(path or config.CLEAN_PATH)
