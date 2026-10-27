"""Chronological splitting, and the observed-target rule.

These guard the two things that would silently invalidate every metric in the
project: a train/test overlap, and scoring against a target the mandi never
reported.
"""
import numpy as np
import pandas as pd
import pytest

from src.features import add_features, drop_incomplete_feature_rows
from src.splits import split_by_date, usable_mask


def _featured(df):
    return drop_incomplete_feature_rows(add_features(df))


def test_train_strictly_precedes_test(straight_line):
    f = _featured(straight_line)
    train, test, cutoff = split_by_date(f, test_fraction=0.2)
    assert train["date"].max() < test["date"].min()
    assert train["date"].max() < cutoff <= test["date"].min()


def test_no_date_appears_in_both_splits(straight_line):
    f = _featured(straight_line)
    train, test, _ = split_by_date(f, test_fraction=0.2)
    assert set(train["date"]).isdisjoint(set(test["date"]))


def test_split_is_not_shuffled(straight_line):
    """Rows must stay in date order; a shuffle here would leak neighbours."""
    f = _featured(straight_line)
    train, test, _ = split_by_date(f, test_fraction=0.2)
    assert train["date"].is_monotonic_increasing
    assert test["date"].is_monotonic_increasing


def test_split_covers_every_row_exactly_once(straight_line):
    f = _featured(straight_line)
    train, test, _ = split_by_date(f, test_fraction=0.2)
    assert len(train) + len(test) == len(f)


def test_test_fraction_is_respected(straight_line):
    f = _featured(straight_line)
    for frac in (0.1, 0.2, 0.3):
        train, test, _ = split_by_date(f, test_fraction=frac)
        share = test["date"].nunique() / f["date"].nunique()
        assert abs(share - frac) < 0.05


def test_empty_frame_raises(straight_line):
    with pytest.raises(ValueError, match="empty"):
        split_by_date(straight_line.iloc[0:0])


def test_too_few_dates_raises(straight_line):
    with pytest.raises(ValueError, match="too few"):
        split_by_date(straight_line.head(5))


def test_both_sides_are_non_empty_at_extreme_fractions(straight_line):
    f = _featured(straight_line)
    for frac in (0.001, 0.999):
        train, test, _ = split_by_date(f, test_fraction=frac)
        assert len(train) > 0 and len(test) > 0


def test_usable_mask_requires_an_observed_target(gappy_series):
    """The rule that stops us scoring against carried-forward numbers."""
    f = _featured(gappy_series)
    for h in (1, 2, 3):
        mask = usable_mask(f, h)
        assert mask.sum() > 0
        # Every selected row must have a real target AND an observed flag.
        assert f.loc[mask, f"y_h{h}"].notna().all()
        assert f.loc[mask, f"y_h{h}_observed"].all()
        # And the mask must actually exclude something, or it proves nothing.
        assert mask.sum() < len(f)


def test_unobserved_targets_are_excluded_even_when_present(gappy_series):
    f = _featured(gappy_series)
    excluded = f[~usable_mask(f, 1) & f["y_h1"].notna()]
    assert len(excluded) > 0
    assert not excluded["y_h1_observed"].any()
