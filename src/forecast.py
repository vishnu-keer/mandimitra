"""Forward forecast: predict the days after the last date in the dataset.

The forecast is made from the most recent row that has a complete feature
vector. For horizon h that row's features are all known at time t, so the
prediction lands on t + h days. Each horizon uses the model SELECTED BY
ROLLING-ORIGIN CROSS-VALIDATION for that horizon (src/evaluate.py) -- not a
single model imposed on all three, not the test-window winner, and not a
model chosen by hand.

The selected model is re-fit on ALL usable rows before forecasting forward,
which is standard practice once selection is finished. The reported metrics
remain the held-out ones -- they are never recomputed on data the final model
has seen.

When the selected model is Naive the forecast equals the last reported price
by construction. That is not a bug or a placeholder: it means no model beat
"tomorrow = today" in cross-validation, and the forecast says so in words.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from . import config
from .models import ArimaModel, build_models
from .splits import usable_mask

log = logging.getLogger(__name__)


def _rule_based_trend(last_price: float, predicted: float, ma7: float) -> str:
    """Plain-language note. A rule, not a model and not an API call."""
    if not np.isfinite(predicted) or not np.isfinite(last_price):
        return "No forecast available for this selection."
    change = predicted - last_price
    pct = (change / last_price * 100.0) if last_price else float("nan")
    ref = ma7 if np.isfinite(ma7) and ma7 else last_price

    if abs(pct) < 1.0:
        lead = f"Forecast is broadly flat against the last reported price ({pct:+.1f}%)"
    else:
        word = ("higher" if pct < 5 else "sharply higher") if pct > 0 else \
               ("lower" if pct > -5 else "sharply lower")
        lead = f"Forecast is {word} than the last reported price ({pct:+.1f}%)"

    if np.isclose(predicted, ref):
        vs_avg = "level with"
    else:
        vs_avg = "above" if predicted > ref else "below"
    return (f"{lead}, and {vs_avg} the recent 7-day average. "
            f"This is a short-term statistical signal, not advice.")


def _method_note(model: str) -> str:
    if model == "Naive":
        return ("Naive method: the forecast repeats the last reported price. "
                "No model beat this in cross-validation, so it is what we "
                "report rather than a more complicated model that tested worse.")
    return (f"{model} was the most accurate method in cross-validation for "
            f"this horizon.")


def forecast_forward(features: pd.DataFrame, clean: pd.DataFrame,
                     commodity: str, market: str, best: pd.DataFrame,
                     feature_cols, horizons=None) -> pd.DataFrame:
    from .evaluate import _daily_price_series

    horizons = config.HORIZONS if horizons is None else horizons
    pair = features[(features["commodity"] == commodity)
                    & (features["market"] == market)].sort_values("date").copy()
    if pair.empty:
        return pd.DataFrame()

    last_row = pair.iloc[[-1]]
    last_date = pd.Timestamp(last_row["date"].iloc[0])
    last_price = float(last_row["price_t"].iloc[0])
    ma7 = float(last_row["ma_7"].iloc[0]) if "ma_7" in last_row else float("nan")
    daily = _daily_price_series(clean, commodity, market)

    out = []
    for h in horizons:
        sel = best[best["horizon"] == h]
        if sel.empty:
            continue
        chosen = str(sel["best_model"].iloc[0])

        usable = pair[usable_mask(pair, h)]
        if usable.empty:
            continue

        model = next((m for m in build_models(h) if m.name == chosen), None)
        if model is None:
            continue
        if isinstance(model, ArimaModel):
            model.prepare(daily, daily.index.max())
            model.fit(usable, feature_cols, f"y_h{h}")
            pred = model.forecast_next(h)
        else:
            model.fit(usable, feature_cols, f"y_h{h}")
            pred = float(model.predict(last_row, feature_cols)[0])

        out.append({
            "commodity": commodity, "market": market, "horizon": h,
            "model": chosen,
            "from_date": last_date.date().isoformat(),
            "forecast_date": (last_date + pd.Timedelta(days=h)).date().isoformat(),
            "last_reported_price": round(last_price, 2),
            "predicted_price": round(pred, 2) if np.isfinite(pred) else None,
            "trend_note": _rule_based_trend(last_price, pred, ma7),
            "method_note": _method_note(chosen),
            "data_is_historical": True,
        })
    return pd.DataFrame(out)
