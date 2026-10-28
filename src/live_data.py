"""Current mandi prices from the official data.gov.in API -- kept separate from
the historical evaluation, and never treated as a forecast.

SOURCE (verified 28 Oct 2026 against the platform's own catalogue API)
    "Current Daily Price of Various Commodities from Various Markets (Mandi)"
    resource id 9ef84268-d588-465a-a308-a864a43d0070, Open Government Data
    Platform India. Published by the Ministry of Agriculture and Farmers
    Welfare, Directorate of Marketing and Inspection (DMI); data originates on
    the AGMARKNET portal. Catalogue frequency: Daily. API available: yes.

ACCESS
    https://api.data.gov.in/resource/<id>?api-key=...&format=json
    Without a key the API answers {"error": "Authorization field missing"}
    (observed 28 Oct 2026). A key is free with a data.gov.in account. The key is
    read from the DATAGOVIN_API_KEY environment variable or Streamlit secrets;
    it is never written to disk, logged, or included in an error message.
    The direct file download behind the resource returned HTTP 403, so the API
    is the only automated route.

WHAT THIS MODULE GUARANTEES
    * Raw responses are snapshotted with retrieval time and source metadata.
    * Records are validated (fields, dates, numbers, min <= modal <= max, range,
      duplicates) and a schema change is reported, not silently absorbed.
    * A failed, empty or invalid download NEVER replaces the last good dataset.
    * Observation date (arrival_date), source update time and our retrieval
      time are three separate fields.
    * Freshness is computed from the latest genuine observation date.

The field list below is the API's documented record schema. It is checked on
every call; if the live API returns something different, the snapshot is
rejected with the difference listed.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from . import config

RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
API_BASE = "https://api.data.gov.in/resource/"
SOURCE_TITLE = ("Current Daily Price of Various Commodities from Various "
                "Markets (Mandi)")
SOURCE_PUBLISHER = ("Ministry of Agriculture and Farmers Welfare, Directorate "
                    "of Marketing and Inspection (AGMARKNET), via data.gov.in")
SOURCE_PAGE = ("https://data.gov.in/resource/"
               "current-daily-price-various-commodities-various-markets-mandi")
SOURCE_LICENCE = "Government Open Data License - India (GODL-India)"

REQUIRED_FIELDS = ["state", "district", "market", "commodity", "variety",
                   "arrival_date", "min_price", "max_price", "modal_price"]
OPTIONAL_FIELDS = ["grade"]
PRICE_FIELDS = ["min_price", "max_price", "modal_price"]
UNIT = "Rs. per quintal (AGMARKNET convention; check against the source)"

LIVE_DIR = config.PROJECT_ROOT / "data" / "live"
RAW_DIR = LIVE_DIR / "raw"
LATEST_PATH = LIVE_DIR / "latest.csv"
STATUS_PATH = LIVE_DIR / "status.json"

FRESH_DAYS = 3        # latest observation at most this old -> "current"
DEFAULT_FILTERS = {"state": "Rajasthan"}
PAGE_SIZE = 1000      # records per API call
MAX_PAGES = 20        # hard stop: a filter set needing more pages is refused,
                      # never silently truncated


class LiveDataError(RuntimeError):
    """Any failure to obtain a VALID snapshot. The message never contains the key."""


@dataclass
class ValidationReport:
    rows_in: int = 0
    rows_valid: int = 0
    missing_fields: list = field(default_factory=list)
    unexpected_fields: list = field(default_factory=list)
    issues: dict = field(default_factory=dict)   # issue name -> row count

    @property
    def schema_ok(self) -> bool:
        return not self.missing_fields

    def as_dict(self) -> dict:
        return {"rows_in": self.rows_in, "rows_valid": self.rows_valid,
                "missing_fields": self.missing_fields,
                "unexpected_fields": self.unexpected_fields,
                "issues": self.issues}


# ------------------------------------------------------------------ key
def get_api_key() -> str | None:
    """Environment first, then Streamlit secrets. Never logged.

    Streamlit Community Cloud also exposes root-level secrets as environment
    variables. st.secrets is consulted only when a secrets file exists:
    touching it without one makes Streamlit draw a "No secrets found" error
    box (with local file paths) on the page.
    """
    key = os.environ.get("DATAGOVIN_API_KEY")
    if key:
        return key.strip()
    try:
        import streamlit as st
        if not st.secrets.load_if_toml_exists():
            return None
        val = st.secrets.get("DATAGOVIN_API_KEY")
        return str(val).strip() if val else None
    except Exception:
        return None


def _redact(text: str, key: str | None) -> str:
    return text.replace(key, "***") if key else text


# ---------------------------------------------------------------- fetch
def build_url(api_key: str, filters: dict | None = None, limit: int = 1000,
              offset: int = 0) -> str:
    params = {"api-key": api_key, "format": "json", "limit": limit,
              "offset": offset}
    for k, v in (filters or {}).items():
        params[f"filters[{k}]"] = v
    return API_BASE + RESOURCE_ID + "?" + urllib.parse.urlencode(params)


def fetch_json(api_key: str, filters: dict | None = None, limit: int = PAGE_SIZE,
               offset: int = 0, timeout: float = 20.0, retries: int = 3,
               backoff: float = 2.0, opener=None) -> dict:
    """GET one page. Retries timeouts, 429 and 5xx with exponential backoff."""
    if not api_key:
        raise LiveDataError("No data.gov.in API key configured "
                            "(set DATAGOVIN_API_KEY).")
    url = build_url(api_key, filters, limit, offset)
    opener = opener or urllib.request.urlopen
    last = None
    for attempt in range(retries):
        try:
            with opener(url, timeout=timeout) as resp:
                body = resp.read().decode("utf-8")
            data = json.loads(body)
            if isinstance(data, dict) and data.get("error"):
                raise LiveDataError(f"API error: {data['error']}")
            return data
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code not in (429, 500, 502, 503, 504):
                break
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last = type(e).__name__
        except json.JSONDecodeError:
            last = "response was not JSON"
            break
        if attempt < retries - 1:
            time.sleep(backoff ** attempt)
    raise LiveDataError(_redact(f"Request failed after {retries} attempt(s): "
                                f"{last}", api_key))


# ------------------------------------------------------------- validate
def validate_records(records: list[dict]) -> tuple[pd.DataFrame, ValidationReport]:
    """Return only rows that pass every check, plus a report of what failed."""
    rep = ValidationReport(rows_in=len(records))
    if not records:
        return pd.DataFrame(columns=REQUIRED_FIELDS), rep
    df = pd.DataFrame(records)
    df.columns = [str(c).strip().lower() for c in df.columns]
    rep.missing_fields = [f for f in REQUIRED_FIELDS if f not in df.columns]
    rep.unexpected_fields = sorted(set(df.columns)
                                   - set(REQUIRED_FIELDS) - set(OPTIONAL_FIELDS))
    if rep.missing_fields:
        return pd.DataFrame(columns=REQUIRED_FIELDS), rep

    for c in ["state", "district", "market", "commodity", "variety"]:
        df[c] = df[c].astype(str).str.strip()
    ok = pd.Series(True, index=df.index)

    def flag(name, bad):
        nonlocal ok
        n = int((bad & ok).sum())
        if n:
            rep.issues[name] = rep.issues.get(name, 0) + n
        ok &= ~bad

    flag("blank text field", (df[["state", "market", "commodity"]]
                              .apply(lambda s: s.isin(["", "nan", "None"]))).any(axis=1))
    df["arrival_date"] = pd.to_datetime(df["arrival_date"], format="%d/%m/%Y",
                                        errors="coerce")
    flag("unparseable arrival_date", df["arrival_date"].isna())
    flag("arrival_date in the future",
         df["arrival_date"] > pd.Timestamp(date.today()) + pd.Timedelta(days=1))
    for c in PRICE_FIELDS:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("float64")
    flag("non-numeric price", df[PRICE_FIELDS].isna().any(axis=1))
    flag("price outside plausible range",
         ((df[PRICE_FIELDS] < config.MIN_PRICE)
          | (df[PRICE_FIELDS] > config.MAX_PRICE)).any(axis=1))
    flag("min > modal or modal > max",
         (df["min_price"] > df["modal_price"]) | (df["modal_price"] > df["max_price"]))
    key = ["arrival_date", "state", "district", "market", "commodity", "variety"]
    flag("duplicate record", df.duplicated(subset=key, keep="first"))

    clean = df[ok].copy()
    rep.rows_valid = len(clean)
    return clean.reset_index(drop=True), rep


# ------------------------------------------------------------ freshness
def freshness(latest_observation, today: date | None = None) -> dict:
    """Status from the latest GENUINE observation date, not the fetch time."""
    today = today or datetime.now(timezone.utc).date()
    if latest_observation is None or pd.isna(latest_observation):
        return {"status": "unavailable", "age_days": None}
    age = (today - pd.Timestamp(latest_observation).date()).days
    return {"status": "current" if age <= FRESH_DAYS else "stale",
            "age_days": int(age)}


# --------------------------------------------------------- store safely
def _read_status() -> dict:
    try:
        return json.loads(STATUS_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _write_status(status: dict):
    LIVE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATUS_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(status, indent=2, default=str))
    tmp.replace(STATUS_PATH)


def _fetch_all_pages(fetch, api_key, filters, fetch_kwargs) -> tuple[list, dict]:
    """Every record for one filter set, following `total` across pages.

    Raises if the API reports more records than MAX_PAGES can hold, so a
    partial download can never be mistaken for a complete one."""
    records, first, offset = [], None, 0
    for _ in range(MAX_PAGES):
        page = fetch(api_key, filters=filters, offset=offset, **fetch_kwargs)
        if not isinstance(page, dict):
            raise LiveDataError("API response was not a JSON object.")
        first = first or page
        recs = page.get("records", []) or []
        records.extend(recs)
        try:
            total = int(page.get("total"))
        except (TypeError, ValueError):
            total = len(records)               # no total reported: one page
        if not recs or len(records) >= total:
            return records, first
        offset += len(recs)
    raise LiveDataError(f"More than {MAX_PAGES} pages for filters {filters}; "
                        f"refusing a partial download. Previous data kept.")


def update_snapshot(api_key: str | None, filters_list: list[dict] | None = None,
                    fetch=fetch_json, now: datetime | None = None,
                    fetch_kwargs: dict | None = None) -> dict:
    """Fetch every filter set, validate, and only then replace latest.csv.

    All-or-nothing: if any request fails, nothing is replaced. Returns the
    status dict. On ANY failure the previous latest.csv is left untouched and
    the failure is recorded with its time.
    """
    filters_list = filters_list or [DEFAULT_FILTERS]
    now = now or datetime.now(timezone.utc)
    status = _read_status()
    status.update({"last_attempt_utc": now.isoformat(timespec="seconds"),
                   "source": SOURCE_TITLE, "resource_id": RESOURCE_ID,
                   "filters": filters_list})
    filters = filters_list
    try:
        records, data = [], {}
        for f in filters_list:
            recs, data = _fetch_all_pages(fetch, api_key, f, fetch_kwargs or {})
            records.extend(recs)
        if not records:
            raise LiveDataError("API returned no records; previous data kept.")
        clean, rep = validate_records(records)
        status["validation"] = rep.as_dict()
        if not rep.schema_ok:
            raise LiveDataError("Schema changed: missing fields "
                                f"{rep.missing_fields}; previous data kept.")
        if clean.empty:
            raise LiveDataError("No record passed validation; previous data kept.")
        stamp = now.strftime("%Y%m%dT%H%M%SZ")
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        meta = {k: data.get(k) for k in ("title", "updated_date", "org",
                                         "source", "total", "count")}
        (RAW_DIR / f"{stamp}.json").write_text(json.dumps(
            {"retrieved_utc": now.isoformat(timespec="seconds"),
             "filters": filters, "source_meta": meta, "records": records},
            indent=1, default=str))
        clean["retrieved_utc"] = now.isoformat(timespec="seconds")
        clean["source_updated"] = meta.get("updated_date")
        tmp = LATEST_PATH.with_suffix(".tmp")
        clean.to_csv(tmp, index=False)
        tmp.replace(LATEST_PATH)
        status.update({"ok": True, "error": None,
                       "last_success_utc": now.isoformat(timespec="seconds"),
                       "source_updated": meta.get("updated_date"),
                       "latest_observation": str(clean["arrival_date"].max().date()),
                       "rows": int(len(clean)), "raw_snapshot": f"{stamp}.json"})
    except LiveDataError as e:
        status.update({"ok": False, "error": _redact(str(e), api_key)})
    _write_status(status)
    return status


def load_latest() -> tuple[pd.DataFrame, dict]:
    """The last GOOD snapshot (possibly empty) and the status record."""
    status = _read_status()
    if LATEST_PATH.exists():
        df = pd.read_csv(LATEST_PATH, parse_dates=["arrival_date"])
    else:
        df = pd.DataFrame()
    latest = df["arrival_date"].max() if not df.empty else None
    status["freshness"] = freshness(latest)
    return df, status
