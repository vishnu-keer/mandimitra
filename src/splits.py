"""Chronological splitting with a target embargo. The one thing that must never shuffle.

A random split on a time series lets the model train on Thursday and Saturday
while being scored on Friday, which leaks the answer through both neighbours
and produces metrics that cannot survive a single question. So there is no
`train_test_split` anywhere in this project, and every split function here
asserts its guarantees rather than trusting that they happened.

TWO THINGS THIS FILE ENFORCES
-----------------------------
1. CHRONOLOGY. Earlier dates train, later dates score. Splitting on distinct
   DATES rather than row position means every row sharing a date lands on the
   same side of the cut -- which matters as soon as more than one market is in
   the frame.

2. TARGET EMBARGO (added 2026-10-27, fixing a real defect).
   A feature row is dated t but its target is the price at t + h. Splitting on
   t alone therefore lets the last h rows before a cutoff carry targets that
   fall on the far side of it. Measured on Onion/Jaipur before the fix:

       h=1  1 training row had its target inside the test window
       h=2  1 training row
       h=3  3 training rows

   Small, but it means the trees were fitted on 1-3 actual test-window prices,
   which contradicts the claim that training targets belong to the training
   period. `purge_target_overlap` drops those rows. This is the standard
   "purged" time-series split; the cost is up to h rows per boundary.
"""
from __future__ import annotations

import pandas as pd

from . import config


def purge_target_overlap(df: pd.DataFrame, horizon: int, cutoff,
                         date_col: str = "date") -> pd.DataFrame:
    """Drop rows whose TARGET date (t + horizon) falls on or after `cutoff`.

    Call this on any block that sits before `cutoff`. Without it a block's last
    h rows reach across the boundary through their targets.
    """
    cutoff = pd.Timestamp(cutoff)
    target_date = df[date_col] + pd.Timedelta(days=int(horizon))
    return df[target_date < cutoff].copy()


def _distinct_dates(df: pd.DataFrame, date_col: str) -> pd.Series:
    if df.empty:
        raise ValueError("Cannot split an empty frame.")
    return pd.Series(sorted(df[date_col].unique()))


def split_by_date(df: pd.DataFrame, test_fraction=None, date_col="date",
                  horizon: int | None = None):
    """Last `test_fraction` of the DISTINCT DATES becomes the test set.

    Returns (train, test, cutoff_date).

    Pass `horizon` to apply the target embargo to the training block. It is
    optional only so that the Phase 1/2 diagnostics and the older tests that
    predate the embargo keep working unchanged; the evaluation path always
    passes it.
    """
    test_fraction = config.TEST_FRACTION if test_fraction is None else test_fraction
    dates = _distinct_dates(df, date_col)
    if len(dates) < 10:
        raise ValueError(f"Only {len(dates)} distinct dates; too few to split.")

    cut_idx = int(round(len(dates) * (1.0 - test_fraction)))
    cut_idx = min(max(cut_idx, 1), len(dates) - 1)
    cutoff = dates.iloc[cut_idx]

    train = df[df[date_col] < cutoff].copy()
    test = df[df[date_col] >= cutoff].copy()
    if horizon is not None:
        train = purge_target_overlap(train, horizon, cutoff, date_col)

    _assert_ordered(train, test, date_col, "train", "test")
    return train, test, cutoff


def split_train_valid_test(df: pd.DataFrame, horizon: int,
                           valid_fraction=None, test_fraction=None,
                           date_col="date"):
    """Three chronological blocks, each embargoed against the next.

        |------------ train ------------|-- valid --|-- test --|
                                    ^embargo    ^embargo

    `valid` is what selects the model. `test` is scored once, afterwards, and
    nothing is ever chosen using it. Returns
    (train, valid, test, cut_valid, cut_test).
    """
    valid_fraction = (config.VALID_FRACTION if valid_fraction is None
                      else valid_fraction)
    test_fraction = (config.TEST_FRACTION if test_fraction is None
                     else test_fraction)
    if valid_fraction <= 0 or test_fraction <= 0:
        raise ValueError("valid_fraction and test_fraction must be > 0")
    if valid_fraction + test_fraction >= 0.8:
        raise ValueError("valid + test fractions leave too little training data")

    dates = _distinct_dates(df, date_col)
    n = len(dates)
    if n < 30:
        raise ValueError(f"Only {n} distinct dates; too few for a 3-way split.")

    cut_test_idx = int(round(n * (1.0 - test_fraction)))
    cut_valid_idx = int(round(n * (1.0 - test_fraction - valid_fraction)))
    cut_test_idx = min(max(cut_test_idx, 2), n - 1)
    cut_valid_idx = min(max(cut_valid_idx, 1), cut_test_idx - 1)

    cut_valid = dates.iloc[cut_valid_idx]
    cut_test = dates.iloc[cut_test_idx]

    train = df[df[date_col] < cut_valid].copy()
    valid = df[(df[date_col] >= cut_valid) & (df[date_col] < cut_test)].copy()
    test = df[df[date_col] >= cut_test].copy()

    # Embargo each earlier block against the boundary it sits behind.
    train = purge_target_overlap(train, horizon, cut_valid, date_col)
    valid = purge_target_overlap(valid, horizon, cut_test, date_col)

    _assert_ordered(train, valid, date_col, "train", "valid")
    _assert_ordered(valid, test, date_col, "valid", "test")
    _assert_no_target_crossing(train, horizon, cut_valid, date_col, "train")
    _assert_no_target_crossing(valid, horizon, cut_test, date_col, "valid")
    return train, valid, test, cut_valid, cut_test


def rolling_origin_folds(dev: pd.DataFrame, horizon: int, n_folds=None,
                         initial_fraction=None, date_col="date"):
    """Expanding-window cross-validation folds inside the development block.

    The first `initial_fraction` of distinct dates is never validated on; the
    remainder is cut into `n_folds` consecutive blocks. Fold k fits on every
    row dated before its origin (embargoed so no fitting TARGET reaches the
    origin) and scores on its own block. A model is never scored on a date it
    could have seen.

    Returns a list of dicts: fold, fit, val, origin, end.
    """
    n_folds = config.CV_FOLDS if n_folds is None else int(n_folds)
    initial_fraction = (config.CV_INITIAL_FRACTION if initial_fraction is None
                        else float(initial_fraction))
    if n_folds < 2:
        raise ValueError("rolling-origin CV needs at least 2 folds")
    if not 0.2 <= initial_fraction < 0.9:
        raise ValueError("initial_fraction must be in [0.2, 0.9)")

    dates = _distinct_dates(dev, date_col)
    n = len(dates)
    start = int(round(n * initial_fraction))
    if n - start < n_folds * 10:
        raise ValueError(f"only {n - start} validation dates for {n_folds} folds")
    edges = [int(round(start + (n - start) * k / n_folds)) for k in range(n_folds + 1)]

    folds = []
    for k in range(n_folds):
        origin = dates.iloc[edges[k]]
        end = dates.iloc[edges[k + 1]] if edges[k + 1] < n else None
        fit = purge_target_overlap(dev[dev[date_col] < origin], horizon, origin,
                                   date_col)
        if end is None:
            val = dev[dev[date_col] >= origin].copy()
        else:
            val = dev[(dev[date_col] >= origin) & (dev[date_col] < end)].copy()
        _assert_ordered(fit, val, date_col, f"fold {k + 1} fit", f"fold {k + 1} val")
        _assert_no_target_crossing(fit, horizon, origin, date_col, f"fold {k + 1} fit")
        folds.append({"fold": k + 1, "fit": fit, "val": val,
                      "origin": pd.Timestamp(origin),
                      "end": None if end is None else pd.Timestamp(end)})
    return folds


def _assert_ordered(earlier, later, date_col, a_name, b_name):
    assert not earlier.empty, f"{a_name} split is empty"
    assert not later.empty, f"{b_name} split is empty"
    assert earlier[date_col].max() < later[date_col].min(), (
        f"Chronology violated: {a_name} reaches into the {b_name} window"
    )
    assert set(earlier[date_col]).isdisjoint(set(later[date_col])), (
        f"A date appears in both {a_name} and {b_name}"
    )


def _assert_no_target_crossing(df, horizon, cutoff, date_col, name):
    if df.empty:
        return
    crossing = (df[date_col] + pd.Timedelta(days=int(horizon))) >= pd.Timestamp(cutoff)
    assert not crossing.any(), (
        f"{int(crossing.sum())} {name} rows have a target date on or after "
        f"{pd.Timestamp(cutoff).date()}: the embargo did not hold"
    )


def usable_mask(df: pd.DataFrame, horizon: int) -> pd.Series:
    """Rows that may be trained on or scored for this horizon.

    Requires the target to exist AND the target date to be a day the mandi
    actually reported. Scoring against a carried-forward target would measure
    the imputation, not the forecast -- and would hand the naive baseline free
    perfect hits wherever price_t and the target are the same filled value.
    """
    return df[f"y_h{horizon}"].notna() & df[f"y_h{horizon}_observed"].astype(bool)
