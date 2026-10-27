"""Metric arithmetic, checked against values computed by hand."""
import math

import numpy as np
import pytest

from src.metrics import all_metrics, mae, mape, r2, rmse


def test_mae_hand_computed():
    # errors: 2, 2, 2, 2 -> mean 2
    assert mae([10, 20, 30, 40], [12, 18, 32, 38]) == pytest.approx(2.0)


def test_rmse_hand_computed():
    # errors 0, 3, 4 -> squares 0, 9, 16 -> mean 25/3 -> sqrt
    assert rmse([1, 2, 3], [1, 5, 7]) == pytest.approx(math.sqrt(25 / 3))


def test_rmse_penalises_large_errors_more_than_mae():
    """The reason model selection uses RMSE. One big miss must cost more."""
    spread = ([100, 100, 100], [110, 110, 110])   # three errors of 10
    spike = ([100, 100, 100], [100, 100, 130])    # one error of 30
    assert mae(*spread) == pytest.approx(mae(*spike))
    assert rmse(*spike) > rmse(*spread)


def test_mape_hand_computed():
    # |10-11|/10 = 10%, |100-90|/100 = 10% -> 10%
    assert mape([10, 100], [11, 90]) == pytest.approx(10.0)


def test_mape_excludes_near_zero_actuals():
    """A zero actual would make MAPE infinite; those rows are dropped."""
    assert mape([0.0, 100.0], [5.0, 110.0]) == pytest.approx(10.0)
    assert math.isnan(mape([0.0, 0.0], [5.0, 5.0]))


def test_r2_perfect_and_mean_predictor():
    y = [1.0, 2.0, 3.0, 4.0]
    assert r2(y, y) == pytest.approx(1.0)
    assert r2(y, [2.5] * 4) == pytest.approx(0.0)      # predicting the mean


def test_r2_is_nan_when_actuals_are_constant():
    assert math.isnan(r2([5.0, 5.0, 5.0], [4.0, 5.0, 6.0]))


def test_nan_pairs_are_dropped_not_propagated():
    m = all_metrics([10, np.nan, 30], [12, 99, 32])
    assert m["n"] == 2
    assert m["mae"] == pytest.approx(2.0)


def test_empty_input_is_nan_not_a_crash():
    m = all_metrics([], [])
    assert m["n"] == 0
    assert math.isnan(m["mae"]) and math.isnan(m["rmse"])


def test_all_metrics_reports_row_count():
    m = all_metrics([1, 2, 3], [1, 2, 3])
    assert m["n"] == 3
    assert set(m) == {"n", "mae", "rmse", "mape", "r2"}
