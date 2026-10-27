"""The four forecasters, behind one interface.

Every model answers the same two questions -- fit(train) and predict(rows) --
so `evaluate.py` can score them identically without special-casing. That is
what makes the comparison table fair.

DIRECT MULTI-HORIZON
--------------------
One model instance per horizon. To forecast 3 days ahead we train a model
whose target is price[t+3], using only features known at t. We never feed a
prediction back in as an input. Consequences:
  - errors do not compound across steps, and
  - the recursive-forecast bug (day 2's lag accidentally using day 1's ACTUAL
    price instead of its prediction) cannot exist, because there is no step 2.

WHY THESE FOUR
--------------
  Naive             - yardstick. Daily mandi prices are close to a random walk,
                      so "tomorrow = today" is a genuinely strong forecast. If
                      the ML models cannot beat it, that is a finding to report,
                      not a failure to hide. Its whole job is to make the other
                      three earn their place.
  ARIMA             - the classical time-series reference point. Models the
                      series' own autocorrelation, uses no engineered features.
  Random Forest     - bagged trees; captures non-linear feature interactions,
                      robust on small data, hard to overfit badly at defaults.
  Gradient Boosting - boosted trees; the hypothesis under test, following
                      published Indian agri-price work that finds tree ensembles
                      beating ARIMA on this kind of data.

HYPERPARAMETERS
---------------
Both tree models are depth- and leaf-constrained. Unbounded trees on ~800 rows
of a near-random-walk series will fit the training window almost exactly, which
is a lookup table rather than a model. The limits below are chosen a priori
from the training-set SIZE -- not by searching against the test window -- and
they are the only hyperparameters set anywhere in this project. Everything else
stays at scikit-learn defaults: with this little data, tuning fits noise, and
tuning against the test set would be leakage of the worst kind.

PROVENANCE OF THESE NUMBERS -- CORRECTED 2026-10-27
---------------------------------------------------
An earlier version of this docstring justified the limits above with measured
*test*-RMSE improvements (Random Forest 98.5 -> 93.4, Gradient Boosting
88.3 -> 87.4). Those numbers came from the final test window, so quoting them
as the reason for the choice means the test set informed the configuration --
exactly the contamination the surrounding text claimed to avoid. The claim and
the evidence contradicted each other.

The limits themselves are unchanged (they follow from the training-set size,
not from a search). What changed is where their effect is measured: the
regularised-vs-default comparison now runs on the VALIDATION window only, is
reproduced by scripts/select_models.py, and is reported in
docs/02_METHODOLOGY.md. The test window is scored once, after selection.
"""
from __future__ import annotations

import logging
import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor

from . import config

log = logging.getLogger(__name__)

RANDOM_STATE = 42


class BaseModel:
    name = "base"
    is_tree = False

    def fit(self, train: pd.DataFrame, feature_cols, target_col):
        raise NotImplementedError

    def predict(self, rows: pd.DataFrame, feature_cols) -> np.ndarray:
        raise NotImplementedError

    def importances(self, feature_cols):
        return None


class NaiveModel(BaseModel):
    """Tomorrow's price = today's price. Nothing is fitted."""

    name = "Naive"

    def fit(self, train, feature_cols, target_col):
        return self

    def predict(self, rows, feature_cols):
        return rows["price_t"].to_numpy(dtype=float)


class TreeModel(BaseModel):
    is_tree = True

    def __init__(self, kind: str, target_mode: str = "level"):
        """target_mode="level": predict price[t+h] directly (the original
        design). "delta": predict the CHANGE price[t+h] - price[t], then add
        price[t] back. A tree's output is an average of training targets, so
        a level-target tree can never predict above the highest price it was
        trained on; a delta-target tree only has to have seen changes of a
        similar size. Experimental -- see scripts/experiment_delta_target.py.
        """
        if target_mode not in ("level", "delta"):
            raise ValueError(f"unknown target_mode {target_mode!r}")
        self.kind = kind
        self.target_mode = target_mode
        base = "RandomForest" if kind == "rf" else "GradientBoosting"
        self.name = base if target_mode == "level" else f"{base}-delta"
        self.model = None

    def fit(self, train, feature_cols, target_col):
        X = train[feature_cols].to_numpy(dtype=float)
        y = train[target_col].to_numpy(dtype=float)
        if self.target_mode == "delta":
            y = y - train["price_t"].to_numpy(dtype=float)
        if self.kind == "rf":
            self.model = RandomForestRegressor(
                n_estimators=300,
                max_depth=6,           # unbounded trees memorised the train window
                min_samples_leaf=8,    # no leaf may rest on fewer than 8 days
                max_features="sqrt",
                random_state=RANDOM_STATE,
                # n_jobs=1 deliberately. With n_jobs=-1 the 300 per-tree
                # predictions are reduced in a thread-scheduling-dependent
                # order, so results differed in the ~15th significant figure
                # between runs (58.283382005200146 vs 58.28338200520013).
                # Scientifically irrelevant, but it broke bit-exact
                # reproducibility, which this project claims. At ~800 training
                # rows the parallelism saves milliseconds, so determinism wins.
                n_jobs=1,
            )
        else:
            self.model = GradientBoostingRegressor(
                n_estimators=200,
                learning_rate=0.05,    # slower learning, less variance
                max_depth=3,
                min_samples_leaf=8,
                subsample=0.9,
                random_state=RANDOM_STATE,
            )
        self.model.fit(X, y)
        return self

    def predict(self, rows, feature_cols):
        X = rows[feature_cols].to_numpy(dtype=float)
        pred = self.model.predict(X)
        if self.target_mode == "delta":
            pred = pred + rows["price_t"].to_numpy(dtype=float)
        return pred

    def importances(self, feature_cols):
        if self.model is None:
            return None
        return dict(zip(feature_cols, map(float, self.model.feature_importances_)))


class ArimaModel(BaseModel):
    """ARIMA on the price series itself, with honest h-step-ahead evaluation.

    ARIMA needs a regularly spaced series, which is why Phase 1 aligned every
    market to a continuous daily calendar. Remaining gaps are forward-filled
    for ARIMA's INPUT ONLY -- a requirement of this model that the tree models
    do not have, and one that must be stated in the methodology.

    Evaluation is a genuine expanding-window h-step forecast: parameters are
    estimated on the training window only, then observed test values are
    appended one day at a time with `refit=False`, forecasting h steps ahead
    before each append. So at every test point the model has seen data up to
    t and nothing after -- the same information the tree models get.

    Orders are chosen by AIC on the TRAINING window only.

    TRAINING DIAGNOSTIC -- FIXED 2026-10-27
    ---------------------------------------
    The walk above starts at the end of training, so its cache only ever held
    target dates from train_end + h onward. Asking it for a *training* row's
    prediction therefore missed on every row except the single one dated
    exactly train_end -- which is why every ARIMA train metric in the old
    outputs/ reported n=1. That number was not a training diagnostic at all:
    it was the first out-of-sample forecast, mislabelled, and at h=3 it
    happened to land 98 Rs. off and made ARIMA look like it fit training data
    worse than test data.

    `_build_insample_cache` replaces it with a real one: h-step-ahead
    predictions across the training window, using the training-fitted
    parameters and conditioning each forecast only on prices up to its own
    origin date. Same parameters, in-sample rows -- the direct analogue of
    what the tree models' train metric measures, so the train/test gap now
    compares like with like.
    """

    name = "ARIMA"
    CANDIDATE_ORDERS = [
        (1, 1, 0), (0, 1, 1), (1, 1, 1), (2, 1, 1), (1, 1, 2), (2, 1, 2), (0, 1, 0),
    ]

    def __init__(self, horizon: int):
        self.horizon = horizon
        self.order = None
        self.failed_reason = None
        self._series = None
        self._train_end = None
        self._cache = {}
        self._insample_cache = {}
        self._insample_status = "not computed"
        self._walk_end = None
        self._want_insample = True
        self._fixed_order = None

    def prepare(self, daily_price: pd.Series, train_end: pd.Timestamp,
                walk_end: pd.Timestamp | None = None, insample: bool = True,
                fixed_order: tuple | None = None):
        """daily_price: continuous daily index, ffilled, no NaN.

        walk_end    last forecast ORIGIN needed. Cross-validation folds only
                    need forecasts for their own validation window, so the walk
                    stops there instead of running to the end of the series.
                    Stopping early changes nothing about the forecasts made --
                    each is conditioned only on data up to its own origin.
        insample    build the training-window diagnostic (final fit only).
        fixed_order skip the AIC search and use this order.
        """
        self._series = daily_price.astype(float)
        self._train_end = pd.Timestamp(train_end)
        self._walk_end = None if walk_end is None else pd.Timestamp(walk_end)
        self._want_insample = bool(insample)
        self._fixed_order = fixed_order
        return self

    def fit(self, train, feature_cols, target_col):
        from statsmodels.tsa.arima.model import ARIMA

        if self._series is None:
            self.failed_reason = "prepare() was not called with a price series"
            return self

        endog = self._series.loc[: self._train_end]
        if len(endog) < 40:
            self.failed_reason = f"only {len(endog)} training points"
            return self

        best = (np.inf, None, None)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            orders = ([self._fixed_order] if self._fixed_order
                      else self.CANDIDATE_ORDERS)
            for order in orders:
                try:
                    res = ARIMA(endog, order=order,
                                enforce_stationarity=False,
                                enforce_invertibility=False).fit()
                    if np.isfinite(res.aic) and res.aic < best[0]:
                        best = (res.aic, order, res)
                except Exception as exc:  # noqa: BLE001
                    log.debug("ARIMA%s failed: %s", order, exc)

        if best[2] is None:
            self.failed_reason = "no candidate order converged"
            return self

        self.order = best[1]
        self._build_forecast_cache(best[2])
        if self._want_insample:
            self._build_insample_cache(best[2])
        else:
            self._insample_status = "not computed (cross-validation fold)"
        return self

    def _hstep_forecasts(self, params) -> np.ndarray:
        """h-step-ahead forecasts from EVERY origin, in one Kalman filter pass.

        Element t is the forecast of price[t + h] made at the end of day t,
        using `params` (estimated on the training window only) and prices up to
        and including t. The filter is causal, so a forecast at t can never
        depend on a later price -- tests/test_evaluation_protocol.py perturbs
        later prices to prove it.

        This replaced a walk-forward loop of `res.append(..., refit=False)`
        calls. Same recursion, same parameters, same conditioning: on the
        project's data the two agree to 0.0 (bit-identical) across ~9,000
        forecasts -- but `append` rebuilds the model and re-filters the whole
        series on every step, which made the walk O(n^2) and took ~25 s per
        fit. One pass takes ~0.03 s.
        """
        from statsmodels.tsa.arima.model import ARIMA

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = ARIMA(self._series, order=self.order,
                        enforce_stationarity=False,
                        enforce_invertibility=False).filter(params)
        fr = res.filter_results
        T = fr.transition[:, :, 0]
        Z = fr.design[:, :, 0]
        c = fr.state_intercept[:, 0]
        d = fr.obs_intercept[:, 0]
        a = np.asarray(fr.predicted_state)[:, 1:]       # column t = a(t+1 | t)
        for _ in range(self.horizon - 1):
            a = T @ a + c[:, None]
        return (Z @ a + d[:, None])[0]

    def _build_forecast_cache(self, fitted):
        """Out-of-sample forecasts for every origin from the end of training
        (to `walk_end`, if set). Keyed by TARGET date."""
        h = self.horizon
        dates = self._series.index
        yhat = self._hstep_forecasts(fitted.params)
        start = int(dates.get_indexer([self._train_end])[0])
        stop = len(dates) - h
        if self._walk_end is not None:
            stop = min(stop, int(dates.searchsorted(self._walk_end, side="right")))
        self._cache = {dates[t + h]: float(yhat[t]) for t in range(start, stop)}
        self._yhat_all = yhat

    def _build_insample_cache(self, fitted):
        """h-step-ahead predictions across the TRAINING window.

        Same parameters (the training fit) and the same causal filter as the
        test forecasts, restricted to origins whose TARGET falls on or before
        the end of training. The first `burn` observations only establish the
        filter state, so training dates before that get no diagnostic value and
        are left NaN rather than filled with something unearned.
        """
        h = self.horizon
        train_series = self._series.loc[: self._train_end]
        burn = max(config.ARIMA_INSAMPLE_BURN_IN, 2 * (sum(self.order) + 1))
        if len(train_series) < burn + h + 10:
            self._insample_status = (
                f"unavailable: {len(train_series)} training points is too few "
                f"for a {burn}-observation burn-in")
            return
        try:
            yhat = self._hstep_forecasts(fitted.params)
        except Exception as exc:  # noqa: BLE001
            self._insample_status = f"unavailable: filter failed ({exc})"
            return
        dates = self._series.index
        last = len(train_series) - 1                       # position of train_end
        self._insample_cache = {dates[t + h]: float(yhat[t])
                                for t in range(burn - 1, last - h + 1)}
        self._insample_status = (
            f"in-sample h-step-ahead, training-window parameters, "
            f"{len(self._insample_cache)} origins after a {burn}-observation burn-in")

    def predict(self, rows, feature_cols):
        if self.failed_reason is not None:
            return np.full(len(rows), np.nan)
        # rows are indexed by their OWN date t; the target lands on t + horizon.
        target_dates = rows["date"] + pd.Timedelta(days=self.horizon)
        return np.array(
            [self._cache.get(d, self._insample_cache.get(d, np.nan))
             for d in target_dates],
            dtype=float)

    def forecast_next(self, steps: int) -> float:
        """One h-step-ahead forecast from the very end of the series."""
        from statsmodels.tsa.arima.model import ARIMA

        if self.order is None:
            return float("nan")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                res = ARIMA(self._series, order=self.order,
                            enforce_stationarity=False,
                            enforce_invertibility=False).fit()
                return float(np.asarray(res.forecast(steps=steps))[-1])
            except Exception:  # noqa: BLE001
                return float("nan")


def build_models(horizon: int):
    """The candidate set. Every candidate is scored identically.

    RandomForest-delta (predicts the price CHANGE, then adds price[t] back)
    joined on 2026-10-27 under a rule written down before the experiment ran:
    "a delta variant joins only if it beats Naive on mean per-fold CV RMSE at
    one or more horizons" (scripts/experiment_delta_target.py). It did, on
    Tomato/Jaipur at h=1 and h=3. GradientBoosting-delta beat Naive nowhere and
    was not added. Admitting a candidate on CV and then selecting on CV makes
    the CV scores slightly optimistic; the test window is untouched by both
    steps, so the reported test numbers are not.
    """
    return [NaiveModel(), ArimaModel(horizon), TreeModel("rf"), TreeModel("gbm"),
            TreeModel("rf", "delta")]


CANDIDATE_NAMES = [m.name for m in build_models(1)]
