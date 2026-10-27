"""The dashboard runs, for every pair, horizon and language, without errors.

Uses Streamlit's AppTest, which executes the real app.py script headlessly
and exposes every element it rendered. A test fails on any uncaught exception
in the script, so these catch the class of bug a screen recording once caught
by hand (an empty multiselect that silently hid a chart).
"""
import pandas as pd
import pytest

from src import config

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = str(config.PROJECT_ROOT / "app.py")
NEED = ["best_model.csv", "model_comparison.csv", "predictions.csv", "forecast.csv"]


def _built():
    return config.FEATURES_PATH.exists() and all(
        (config.OUTPUTS / f).exists() for f in NEED)


pytestmark = pytest.mark.skipif(not _built(), reason="pipeline outputs not built")


def _run(at=None):
    at = at or AppTest.from_file(APP, default_timeout=60)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _text(at):
    parts = [m.value for m in at.markdown] + [c.value for c in at.caption]
    parts += [x.value for x in at.info] + [x.value for x in at.warning]
    parts += [x.value for x in at.success] + [x.value for x in at.error]
    return "\n".join(str(p) for p in parts)


def _pairs():
    b = pd.read_csv(config.OUTPUTS / "best_model.csv")
    return sorted(set(zip(b["commodity"], b["market"])))


def test_app_renders_with_no_exception_and_states_the_data_is_historical():
    at = _run()
    txt = _text(at)
    assert "Historical data" in txt
    assert "28 Apr 2015" in txt
    assert "Not financial" in txt or "not financial" in txt.lower()


@pytest.mark.parametrize("pair", _pairs() if _built() else [])
def test_every_evaluated_pair_renders(pair):
    at = _run()
    at.selectbox(key="commodity").select(pair[0]).run()
    at.selectbox(key="market").select(pair[1]).run()
    assert not at.exception
    assert at.selectbox(key="commodity").value == pair[0]


@pytest.mark.parametrize("h", config.HORIZONS)
def test_every_horizon_renders_and_names_the_selection_protocol(h):
    at = _run()
    at.radio(key="eval_h").set_value(h).run()
    assert not at.exception
    txt = _text(at)
    assert "cross-validation" in txt.lower()


def test_actual_vs_predicted_has_a_non_empty_default_selection():
    """Regression: the default must match an option, or the chart vanishes."""
    at = _run()
    for h in config.HORIZONS:
        at.radio(key="eval_h").set_value(h).run()
        ms = at.multiselect(key=f"pick_{h}")
        assert ms.value, f"h={h}: 'Models to plot' rendered empty"
        assert "Naive" in ms.value


def test_hindi_mode_renders_and_translates_the_plain_language_views():
    at = _run()
    at.radio(key="lang").set_value("हिन्दी").run()
    assert not at.exception
    txt = _text(at)
    assert "ऐतिहासिक आँकड़े" in txt
    assert "सलाह नहीं" in txt


def test_toggles_and_ranges_do_not_break_the_history_view():
    at = _run()
    at.toggle(key="show_cf").set_value(True).run()
    for r in ("6 months", "1 year", "2 years", "All"):
        at.radio(key="hist_range").set_value(r).run()
        assert not at.exception


def test_no_uncertainty_band_is_presented_as_reliable_when_it_failed():
    b = pd.read_csv(config.OUTPUTS / "best_model.csv")
    at = _run()
    txt = _text(at)
    if not b["interval_held_up"].astype(bool).all():
        assert "not presented as a reliable" in txt


def test_excluded_markets_are_listed_with_reasons():
    ex_path = config.OUTPUTS / "excluded.csv"
    if not ex_path.exists() or pd.read_csv(ex_path).empty:
        pytest.skip("nothing excluded")
    at = _run()
    shown = pd.concat([d.value for d in at.dataframe], ignore_index=True,
                      sort=False)
    assert "Reason" in shown.columns
    assert shown["Reason"].dropna().str.contains("gate").any()


def test_missing_outputs_show_an_actionable_error_not_a_traceback(tmp_path, monkeypatch):
    import streamlit as st
    monkeypatch.setattr(config, "OUTPUTS", tmp_path)       # empty outputs dir
    st.cache_data.clear()      # earlier tests cached the real outputs in-process
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    assert not at.exception
    assert any("missing" in e.value.lower() for e in at.error)
    assert "run_pipeline.py" in _text(at)
    st.cache_data.clear()      # do not leak the empty state into later tests
