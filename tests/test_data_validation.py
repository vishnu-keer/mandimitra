"""Data cleaning, insufficient data, missing data, invalid selections.

These are the crash paths. Every one of them must produce a clear message or a
clean exclusion -- never a traceback, and never a plausible-looking number
built on nothing.
"""
import numpy as np
import pandas as pd
import pytest

from src import config
from src.data_prep import (
    build_clean, calendar_align, coerce_prices, deduplicate,
    drop_impossible_rows, load_raw, parse_dates, standardise_text,
)
from src.evaluate import evaluate_pair
from src.features import add_features, drop_incomplete_feature_rows
from src.schema import build_rename_map


# ------------------------------------------------------------ schema mapping
def test_schema_maps_every_known_source_spelling():
    for header, canon in [
        ("Modal Price (Rs./Quintal)", "modal_price"),
        ("Modal_x0020_Price", "modal_price"),
        ("Model Price", "modal_price"),
        ("Price", "modal_price"),
        ("Centre_Name", "market"),
        ("Market Name", "market"),
        ("Arrival_Date", "date"),
        ("Price Date", "date"),
    ]:
        rename, _ = build_rename_map([header])
        assert rename.get(header) == canon, f"{header} did not map to {canon}"


def test_unknown_headers_are_reported_not_silently_dropped():
    rename, unmapped = build_rename_map(["Date", "Price", "SomeNewColumn"])
    assert "SomeNewColumn" in unmapped
    assert "Date" in rename and "Price" in rename


def test_missing_required_column_raises_a_useful_message(tmp_path):
    raw = tmp_path / "raw"; raw.mkdir()
    (raw / "bad.csv").write_text("Foo,Bar\n1,2\n")
    with pytest.raises(ValueError) as err:
        load_raw(raw)
    msg = str(err.value)
    assert "required column" in msg
    assert "Foo" in msg and "schema.py" in msg   # tells you how to fix it


# ------------------------------------------------------------ dirty raw data
def test_zero_prices_are_dropped_as_the_sources_na_code(raw_csv_with_dirt):
    df = coerce_prices(parse_dates(standardise_text(load_raw(raw_csv_with_dirt))))
    n_zero = int((df[config.PRICE_COL] == 0).sum())
    assert n_zero > 0, "fixture should contain zeros"
    kept, report = drop_impossible_rows(df)
    assert report["dropped_price_out_of_range"] >= n_zero
    assert (kept[config.PRICE_COL] >= config.MIN_PRICE).all()


def test_unparseable_dates_are_dropped_and_counted(raw_csv_with_dirt):
    df = coerce_prices(parse_dates(standardise_text(load_raw(raw_csv_with_dirt))))
    kept, report = drop_impossible_rows(df)
    assert report["dropped_unparseable_date"] >= 1
    assert kept["date"].notna().all()


def test_absurd_prices_are_dropped(raw_csv_with_dirt):
    df = coerce_prices(parse_dates(standardise_text(load_raw(raw_csv_with_dirt))))
    kept, _ = drop_impossible_rows(df)
    assert (kept[config.PRICE_COL] <= config.MAX_PRICE).all()


def test_duplicate_dates_collapse_to_one_row(raw_csv_with_dirt):
    df = coerce_prices(parse_dates(standardise_text(load_raw(raw_csv_with_dirt))))
    kept, _ = drop_impossible_rows(df)
    out, report = deduplicate(kept)
    keys = ["commodity", "market", "date"]
    assert not out.duplicated(keys).any()
    assert report["rows_out"] <= report["rows_in"]


def test_dates_are_parsed_day_first():
    """13-01-20 is 13 January, not an error and not 1 December."""
    df = pd.DataFrame({"date": ["13-01-20"], "commodity": ["Onion"],
                       "market": ["Jaipur"], "modal_price": ["800"]})
    out = parse_dates(df)
    assert out["date"].iloc[0] == pd.Timestamp("2020-01-13")


# -------------------------------------------------------- calendar alignment
def test_calendar_alignment_produces_a_contiguous_daily_index():
    """The guard against shift(1) meaning 'previous ROW' instead of 'day'."""
    dates = [pd.Timestamp("2020-01-01"), pd.Timestamp("2020-01-02"),
             pd.Timestamp("2020-01-09")]          # a 6-day hole
    df = pd.DataFrame({"commodity": "Onion", "market": "Jaipur",
                       "date": dates, "modal_price": [100.0, 110.0, 120.0]})
    out = calendar_align(df, max_ffill_days=2)
    span = (out["date"].max() - out["date"].min()).days + 1
    assert len(out) == span, "index is not contiguous"
    assert out["date"].diff().dropna().eq(pd.Timedelta(days=1)).all()


def test_gaps_longer_than_the_limit_stay_empty():
    dates = [pd.Timestamp("2020-01-01"), pd.Timestamp("2020-01-09")]
    df = pd.DataFrame({"commodity": "Onion", "market": "Jaipur",
                       "date": dates, "modal_price": [100.0, 120.0]})
    out = calendar_align(df, max_ffill_days=2)
    assert out[config.PRICE_COL].isna().any(), (
        "a 6-day hole must not be fully filled by a 2-day limit")


def test_carried_forward_days_are_flagged_not_hidden():
    dates = [pd.Timestamp("2020-01-01"), pd.Timestamp("2020-01-03")]
    df = pd.DataFrame({"commodity": "Onion", "market": "Jaipur",
                       "date": dates, "modal_price": [100.0, 120.0]})
    out = calendar_align(df, max_ffill_days=2)
    filled = out[~out["observed"]]
    assert len(filled) == 1
    assert filled["date"].iloc[0] == pd.Timestamp("2020-01-02")
    assert filled[config.PRICE_COL].iloc[0] == 100.0     # carried FORWARD


def test_no_carry_forward_when_the_limit_is_zero():
    dates = [pd.Timestamp("2020-01-01"), pd.Timestamp("2020-01-03")]
    df = pd.DataFrame({"commodity": "Onion", "market": "Jaipur",
                       "date": dates, "modal_price": [100.0, 120.0]})
    out = calendar_align(df, max_ffill_days=0)   # must not raise
    assert out[config.PRICE_COL].isna().sum() == 1


# ------------------------------------------------------- insufficient data
def test_evaluate_refuses_a_series_that_is_too_short(straight_line):
    """Too few rows must raise a clear error, not return a flattering number."""
    short = straight_line.head(30)
    feats = drop_incomplete_feature_rows(add_features(short))
    with pytest.raises(ValueError, match="scoreable"):
        evaluate_pair(feats, short, "Onion", "Testmarket")


def test_evaluate_refuses_an_unknown_pair(straight_line):
    feats = drop_incomplete_feature_rows(add_features(straight_line))
    with pytest.raises(ValueError, match="No feature rows"):
        evaluate_pair(feats, straight_line, "Banana", "Nowhere")


def test_all_nan_optional_feature_does_not_empty_the_dataset():
    """spread_pct is NaN when the source has no min/max. Must not delete all."""
    dates = pd.date_range("2020-01-01", periods=60, freq="D")
    df = pd.DataFrame({"commodity": "Onion", "market": "Jaipur", "date": dates,
                       "modal_price": 500.0 + np.arange(len(dates)),
                       "observed": True, "days_since_obs": 0.0})
    f = drop_incomplete_feature_rows(add_features(df))
    assert f["spread_pct"].isna().all()      # no min/max in the input
    assert len(f) > 0, "an all-NaN optional feature wiped the dataset"


# ---------------------------------------------------- invalid selections
def test_pairs_below_the_gate_are_never_selectable(straight_line):
    """The dashboard builds its selectors from selectable_pairs, so a bad pair
    is unselectable rather than merely handled. available_pairs now returns
    every pair WITH its gate status (so exclusions can be listed with reasons);
    the guarantee moved to selectable_pairs and is asserted on both."""
    from src.dashboard_data import available_pairs, selectable_pairs
    feats = drop_incomplete_feature_rows(add_features(straight_line.head(40)))
    allp = available_pairs(feats)
    assert len(allp) == 1 and not bool(allp.iloc[0]["qualifies"])
    # Even if a result file wrongly listed it, it must not be offered.
    fake_best = pd.DataFrame({"commodity": ["Onion"], "market": ["Testmarket"]})
    assert selectable_pairs(feats, fake_best).empty, (
        "a pair with too few rows was offered as selectable")


def test_a_qualifying_pair_without_results_is_not_selectable():
    """Selectable = passes the gate AND has evaluated results."""
    from src.dashboard_data import selectable_pairs
    dates = pd.date_range("2018-01-01", periods=900, freq="D")
    df = pd.DataFrame({"commodity": "Onion", "market": "Jaipur", "date": dates,
                       "modal_price": 800.0 + np.arange(len(dates)) % 300,
                       "min_price": 760.0, "max_price": 840.0,
                       "observed": True, "days_since_obs": 0.0})
    feats = drop_incomplete_feature_rows(add_features(df))
    assert selectable_pairs(feats, pd.DataFrame()).empty
    best = pd.DataFrame({"commodity": ["Onion"], "market": ["Jaipur"]})
    assert len(selectable_pairs(feats, best)) == 1


def test_available_pairs_includes_a_qualifying_pair():
    from src.dashboard_data import available_pairs
    dates = pd.date_range("2018-01-01", periods=900, freq="D")
    df = pd.DataFrame({"commodity": "Onion", "market": "Jaipur", "date": dates,
                       "modal_price": 800.0 + np.arange(len(dates)) % 300,
                       "min_price": 760.0, "max_price": 840.0,
                       "observed": True, "days_since_obs": 0.0})
    feats = drop_incomplete_feature_rows(add_features(df))
    pairs = available_pairs(feats)
    assert len(pairs) == 1
    assert bool(pairs.iloc[0]["qualifies"])


def test_end_to_end_clean_runs_on_dirty_raw_data(raw_csv_with_dirt):
    clean, report = build_clean(raw_dir=raw_csv_with_dirt,
                                commodities=["Onion"], verbose=False)
    assert not clean.empty
    assert clean[config.PRICE_COL].notna().sum() > 0
    assert report["loaded_rows"] > len(clean[clean["observed"]])
