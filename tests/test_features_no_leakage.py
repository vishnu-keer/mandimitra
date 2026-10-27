"""Leakage tests - the most important file in this suite.

Four independent angles on the same question: can any feature see the future?

  1. Truncate-and-compare  - delete the future, rebuild, demand identical rows.
  2. Perturbation          - change a future price, demand nothing earlier moves.
  3. Exact lag arithmetic  - lag_k must be the price k CALENDAR days earlier.
  4. Target direction      - every target must be strictly later than its row.

A single one of these passing could be luck. Together they close the door.
"""
import numpy as np
import pandas as pd
import pytest

from src import config
from src.features import (
    add_features, drop_incomplete_feature_rows, feature_columns,
    target_columns, verify_no_leakage,
)


def test_truncate_and_compare_passes(gappy_series):
    report = verify_no_leakage(gappy_series)
    assert report["passed"], report["mismatched_columns"]
    assert report["rows_compared"] > 0
    assert report["columns_compared"] == len(feature_columns())
    assert report["mismatched_columns"] == {}


def test_perturbing_the_future_changes_nothing_in_the_past(straight_line):
    """The sharpest test. Spike a late price; early features must not move."""
    base = add_features(straight_line)
    cut = 60

    tampered = straight_line.copy()
    tampered.loc[tampered.index >= cut, "modal_price"] *= 10.0   # huge change
    after = add_features(tampered)

    feats = [c for c in feature_columns() if c in base.columns]
    early_base = base[base["date"] < straight_line.loc[cut, "date"]]
    early_after = after[after["date"] < straight_line.loc[cut, "date"]]

    assert len(early_base) == len(early_after) > 0
    for col in feats:
        a = early_base[col].to_numpy(dtype=float)
        b = early_after[col].to_numpy(dtype=float)
        assert np.allclose(a, b, equal_nan=True), (
            f"{col} changed when only FUTURE prices were altered -- leakage")


def test_lag_equals_the_price_that_many_calendar_days_earlier(straight_line):
    """On a contiguous series price = 100 + i, so lag_k = price_t - k exactly."""
    f = drop_incomplete_feature_rows(add_features(straight_line))
    for k in config.LAGS:
        expected = f["price_t"] - k
        assert np.allclose(f[f"lag_{k}"], expected), f"lag_{k} is wrong"


def test_moving_average_matches_a_hand_computed_window(straight_line):
    """A 3-day mean ending at t on price = 100 + i is price_t - 1."""
    f = drop_incomplete_feature_rows(add_features(straight_line))
    assert np.allclose(f["ma_3"], f["price_t"] - 1.0)


def test_targets_are_strictly_in_the_future(straight_line):
    f = add_features(straight_line).sort_values("date").reset_index(drop=True)
    for h in config.HORIZONS:
        shifted = f["price_t"].shift(-h)
        valid = f[f"y_h{h}"].notna()
        assert np.allclose(f.loc[valid, f"y_h{h}"], shifted[valid])
        # And on this increasing series, every target must exceed price_t.
        assert (f.loc[valid, f"y_h{h}"] > f.loc[valid, "price_t"]).all()


def test_no_target_column_is_used_as_a_feature():
    assert set(feature_columns()).isdisjoint(set(target_columns()))


def test_last_rows_have_features_but_no_target(straight_line):
    """The forward forecast is made from exactly these rows."""
    f = drop_incomplete_feature_rows(add_features(straight_line))
    last = f.iloc[-1]
    for col in feature_columns():
        if col in f.columns and not f[col].isna().all():
            assert pd.notna(last[col]), f"{col} missing on the final row"
    assert pd.isna(last["y_h1"]) or not bool(last["y_h1_observed"])


def test_target_observed_flag_shifts_with_the_horizon(gappy_series):
    f = add_features(gappy_series).sort_values("date").reset_index(drop=True)
    obs = f["observed"].to_numpy(dtype=bool)
    for h in config.HORIZONS:
        expected = np.zeros(len(f), dtype=bool)
        expected[: len(f) - h] = obs[h:]
        assert np.array_equal(f[f"y_h{h}_observed"].to_numpy(dtype=bool),
                              expected)


def test_no_backfill_or_interpolation_anywhere_in_src():
    """Static guard: these calls would leak the future by construction.

    Scans real CODE only -- docstrings and comments are stripped first, so the
    methodology prose that *names* these calls in order to rule them out does
    not trip the guard. The one permitted exception is back-filling static
    labels (state, district), which are not time series.
    """
    import io
    import pathlib
    import tokenize

    banned = ("bfill(", "backfill(", ".interpolate(", "center=True")
    src = pathlib.Path(config.PROJECT_ROOT) / "src"
    offenders = []

    for path in sorted(src.glob("*.py")):
        source = path.read_text()
        # Blank out every comment and string literal, keeping line numbers.
        lines = source.splitlines()
        keep = [list(line) for line in lines]
        try:
            for tok in tokenize.generate_tokens(io.StringIO(source).readline):
                if tok.type in (tokenize.COMMENT, tokenize.STRING):
                    (r0, c0), (r1, c1) = tok.start, tok.end
                    for r in range(r0, r1 + 1):
                        row = keep[r - 1]
                        lo = c0 if r == r0 else 0
                        hi = c1 if r == r1 else len(row)
                        for c in range(lo, min(hi, len(row))):
                            row[c] = " "
        except tokenize.TokenError:
            pass

        for line_no, chars in enumerate(keep, 1):
            code = "".join(chars)
            for token in banned:
                if token in code and "static label" not in lines[line_no - 1]:
                    offenders.append(
                        f"{path.name}:{line_no}: {lines[line_no - 1].strip()}")

    assert not offenders, "Future-looking calls found:\n" + "\n".join(offenders)
