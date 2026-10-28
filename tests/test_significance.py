"""The Diebold-Mariano implementation behaves as the test is defined."""
import numpy as np

from src.significance import dm_test


def test_identical_forecasts_give_no_statistic():
    y = np.arange(50.0)
    r = dm_test(y, y + 1, y + 1)
    assert r["n"] == 50 and np.isnan(r["dm_stat"]) and r["mean_loss_diff"] == 0


def test_clearly_better_model_is_significant_and_negative():
    rng = np.random.default_rng(0)
    y = rng.normal(1000, 50, 300)
    good = y + rng.normal(0, 5, 300)
    bad = y + rng.normal(0, 50, 300)
    r = dm_test(y, good, bad, h=1)
    assert r["dm_stat"] < -5 and r["p_value"] < 1e-6


def test_symmetry_swapping_models_flips_the_sign():
    rng = np.random.default_rng(1)
    y = rng.normal(0, 1, 200)
    a, b = y + rng.normal(0, 1, 200), y + rng.normal(0, 1.2, 200)
    r1, r2 = dm_test(y, a, b, h=2), dm_test(y, b, a, h=2)
    assert np.isclose(r1["dm_stat"], -r2["dm_stat"])
    assert np.isclose(r1["p_value"], r2["p_value"])


def test_equal_quality_noise_is_usually_not_significant():
    rng = np.random.default_rng(2)
    hits = 0
    for _ in range(200):
        y = rng.normal(0, 1, 200)
        r = dm_test(y, y + rng.normal(0, 1, 200), y + rng.normal(0, 1, 200))
        hits += r["p_value"] < 0.05
    assert hits / 200 < 0.10          # nominal 5% size, with slack


def test_missing_values_are_dropped_pairwise():
    y = np.r_[np.arange(30.0), np.nan]
    r = dm_test(y, y + 1, y + 2)
    assert r["n"] == 30
