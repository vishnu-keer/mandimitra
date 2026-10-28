"""Current-price ingestion: validation, schema change, failure recovery, freshness.

Every record here is a hand-written TEST FIXTURE shaped like the documented
data.gov.in API response. None of it is project data and none is shown in the
app. No test touches the network.
"""
import io
import json
import urllib.error
from datetime import date, datetime, timezone

import pandas as pd
import pytest

from src import live_data as ld

KEY = "test-key-NOT-REAL-1234567890"


def rec(**over):
    r = {"state": "Rajasthan", "district": "Jaipur", "market": "Jaipur (F&V)",
         "commodity": "Onion", "variety": "Red", "grade": "FAQ",
         "arrival_date": "27/10/2026", "min_price": "1800", "max_price": "2400",
         "modal_price": "2100"}
    r.update(over)
    return r


@pytest.fixture
def live_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(ld, "LIVE_DIR", tmp_path)
    monkeypatch.setattr(ld, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(ld, "LATEST_PATH", tmp_path / "latest.csv")
    monkeypatch.setattr(ld, "STATUS_PATH", tmp_path / "status.json")
    return tmp_path


def fake_fetch(payload):
    def f(api_key, filters=None, **kw):
        if isinstance(payload, Exception):
            raise payload
        return payload
    return f


NOW = datetime(2026, 10, 28, 9, 0, tzinfo=timezone.utc)


# ------------------------------------------------------------ validation
def test_valid_records_pass_and_prices_become_numbers():
    df, rep = ld.validate_records([rec(), rec(commodity="Tomato")])
    assert rep.schema_ok and rep.rows_valid == 2 and not rep.issues
    assert df["modal_price"].dtype.kind == "f"
    assert df["arrival_date"].iloc[0] == pd.Timestamp("2026-10-27")


@pytest.mark.parametrize("bad, issue", [
    (rec(arrival_date="2026-10-27"), "unparseable arrival_date"),
    (rec(modal_price="abc"), "non-numeric price"),
    (rec(min_price="2500"), "min > modal or modal > max"),
    (rec(max_price="2000"), "min > modal or modal > max"),
    (rec(min_price="5", modal_price="6", max_price="7"), "price outside plausible range"),
    (rec(market=""), "blank text field"),
    (rec(arrival_date="01/01/2099"), "arrival_date in the future"),
])
def test_each_kind_of_bad_record_is_rejected_and_counted(bad, issue):
    df, rep = ld.validate_records([rec(), bad])
    assert rep.rows_valid == 1
    assert rep.issues.get(issue) == 1, rep.issues


def test_duplicates_are_dropped_once():
    df, rep = ld.validate_records([rec(), rec(), rec(commodity="Tomato")])
    assert rep.rows_valid == 2 and rep.issues == {"duplicate record": 1}


def test_schema_change_is_reported_not_absorbed():
    broken = [{k: v for k, v in rec().items() if k != "modal_price"}]
    df, rep = ld.validate_records(broken)
    assert not rep.schema_ok and rep.missing_fields == ["modal_price"]
    assert df.empty


def test_new_unexpected_fields_are_listed():
    _, rep = ld.validate_records([rec(new_col="x")])
    assert rep.unexpected_fields == ["new_col"] and rep.rows_valid == 1


# ------------------------------------------------- never overwrite good data
def test_good_fetch_writes_snapshot_latest_and_status(live_dir):
    payload = {"records": [rec(), rec(commodity="Tomato")], "updated_date": "2026-10-28",
               "title": ld.SOURCE_TITLE, "total": 2}
    st = ld.update_snapshot(KEY, fetch=fake_fetch(payload), now=NOW)
    assert st["ok"] and st["rows"] == 2 and st["latest_observation"] == "2026-10-27"
    assert (live_dir / "latest.csv").exists()
    raw = json.loads((live_dir / "raw" / "20261028T090000Z.json").read_text())
    assert raw["retrieved_utc"].startswith("2026-10-28T09:00")
    assert raw["source_meta"]["updated_date"] == "2026-10-28"


@pytest.mark.parametrize("bad_payload", [
    {"records": []},                                             # empty
    {"records": [{k: v for k, v in rec().items() if k != "market"}]},  # schema change
    {"records": [rec(modal_price="n/a")]},                       # nothing valid
    ld.LiveDataError("Request failed after 3 attempt(s): HTTP 503"),  # outage
])
def test_failed_update_keeps_the_previous_good_dataset(live_dir, bad_payload):
    ld.update_snapshot(KEY, fetch=fake_fetch({"records": [rec()]}), now=NOW)
    before = (live_dir / "latest.csv").read_bytes()
    st = ld.update_snapshot(KEY, fetch=fake_fetch(bad_payload), now=NOW)
    assert st["ok"] is False and st["error"]
    assert (live_dir / "latest.csv").read_bytes() == before
    assert st["last_success_utc"].startswith("2026-10-28")


def test_no_key_fails_cleanly_without_touching_files(live_dir):
    st = ld.update_snapshot(None, now=NOW)       # real fetch_json, no network used
    assert st["ok"] is False and "API key" in st["error"]
    assert not (live_dir / "latest.csv").exists()


# ----------------------------------------------------------- the key stays secret
def test_api_key_never_appears_in_errors_status_or_files(live_dir):
    def leaky(api_key, filters=None, **kw):
        raise ld.LiveDataError(f"boom for {api_key}")
    st = ld.update_snapshot(KEY, fetch=leaky, now=NOW)
    assert KEY not in json.dumps(st)
    ld.update_snapshot(KEY, fetch=fake_fetch({"records": [rec()]}), now=NOW)
    for p in live_dir.rglob("*"):
        if p.is_file():
            assert KEY not in p.read_text(), p


def test_fetch_retries_then_reports_without_the_key():
    calls = []

    def opener(url, timeout):
        calls.append(url)
        raise urllib.error.HTTPError(url, 503, "busy", {}, io.BytesIO(b""))
    with pytest.raises(ld.LiveDataError) as e:
        ld.fetch_json(KEY, opener=opener, retries=3, backoff=0)
    assert len(calls) == 3 and KEY not in str(e.value) and "503" in str(e.value)


def test_fetch_does_not_retry_an_auth_error():
    calls = []

    def opener(url, timeout):
        calls.append(url)
        raise urllib.error.HTTPError(url, 403, "forbidden", {}, io.BytesIO(b""))
    with pytest.raises(ld.LiveDataError):
        ld.fetch_json(KEY, opener=opener, retries=3, backoff=0)
    assert len(calls) == 1


def test_api_error_payload_is_an_error_not_data():
    class R(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False
    with pytest.raises(ld.LiveDataError, match="Authorization field missing"):
        ld.fetch_json(KEY, opener=lambda url, timeout: R(
            b'{"error": "Authorization field missing"}'), retries=1)


# --------------------------------------------------------------- freshness
def test_freshness_uses_the_observation_date():
    assert ld.freshness("2026-10-27", today=date(2026, 10, 28))["status"] == "current"
    assert ld.freshness("2026-10-20", today=date(2026, 10, 28))["status"] == "stale"
    old = ld.freshness("2015-04-28", today=date(2026, 10, 28))
    assert old["status"] == "stale" and old["age_days"] > 4000
    assert ld.freshness(None)["status"] == "unavailable"


def test_load_latest_with_nothing_fetched_is_unavailable(live_dir):
    df, st = ld.load_latest()
    assert df.empty and st["freshness"]["status"] == "unavailable"


def test_pagination_follows_total_and_keeps_every_page(live_dir):
    pages = {0: {"total": 3, "records": [rec(market="A"), rec(market="B")]},
             2: {"total": 3, "records": [rec(market="C")]}}
    calls = []

    def paged(api_key, filters=None, offset=0, **kw):
        calls.append(offset)
        return pages[offset]
    st = ld.update_snapshot(KEY, fetch=paged, now=NOW)
    assert st["ok"] and st["rows"] == 3 and calls == [0, 2]


def test_a_download_needing_too_many_pages_is_refused_not_truncated(live_dir, monkeypatch):
    monkeypatch.setattr(ld, "MAX_PAGES", 2)
    ld.update_snapshot(KEY, fetch=fake_fetch({"records": [rec()]}), now=NOW)

    def endless(api_key, filters=None, offset=0, **kw):
        return {"total": 10_000, "records": [rec(market=f"M{offset}")]}
    st = ld.update_snapshot(KEY, fetch=endless, now=NOW)
    assert st["ok"] is False and "partial" in st["error"]
    df, _ = ld.load_latest()
    assert len(df) == 1          # the previous good snapshot survives
