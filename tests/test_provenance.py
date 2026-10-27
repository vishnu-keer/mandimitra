"""Provenance: every raw number traces to an untouched government file.

These tests skip (rather than fail) when the official source files are not
present, so a fresh clone without data/raw/source/ still runs the rest of the
suite. When the files ARE present they must match the recorded hashes exactly.
"""
import hashlib
import sys
from pathlib import Path

import pytest

from src import config

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from extract_rajasthan import extract  # noqa: E402

SOURCE_SHA256 = {
    "Onion": "e0b5171b81bc93983104990728a45d271f30c794bcc3c53f73553cf91fd1335a",
    "Tomato": "fb872513c2113ae3ec39f5a18ecba8eced089d9545e55f91382530b2cebb88c1",
}
ORIGINAL_JAIPUR_ONION_SHA256 = (
    "c59e0b91a38dec188a88f0d33f270615a878a702dfa1aceb97feb3fc99e2c65c")


def _src(c):
    return config.DATA_RAW_SOURCE / f"daily_wholesale_price_{c}_upto_apr_2015.csv"


def _need_sources():
    missing = [c for c in SOURCE_SHA256 if not _src(c).exists()]
    if missing:
        pytest.skip(f"official source files not present: {missing}")


@pytest.mark.parametrize("commodity", sorted(SOURCE_SHA256))
def test_official_source_files_are_unaltered(commodity):
    _need_sources()
    got = hashlib.sha256(_src(commodity).read_bytes()).hexdigest()
    assert got == SOURCE_SHA256[commodity], (
        f"{_src(commodity).name} has changed since it was downloaded")


def test_extraction_reproduces_the_original_jaipur_onion_file_byte_for_byte():
    _need_sources()
    text = extract(centres=["JAIPUR"], commodities=["Onion"])
    assert hashlib.sha256(text.encode()).hexdigest() == ORIGINAL_JAIPUR_ONION_SHA256


def test_committed_subset_is_exactly_what_the_extraction_script_produces():
    _need_sources()
    if not config.RAW_SUBSET_PATH.exists():
        pytest.skip("raw subset not generated")
    assert config.RAW_SUBSET_PATH.read_text() == extract()


def test_extraction_keeps_only_configured_centres_and_source_columns():
    _need_sources()
    lines = extract().splitlines()
    assert lines[0] == "Date,Centre_Name,Commodity_Name,Price"
    centres = {l.split(",")[1] for l in lines[1:]}
    assert centres == set(config.RAW_CENTRES)
    assert all(len(l.split(",")) == 4 for l in lines)
