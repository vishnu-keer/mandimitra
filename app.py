"""MandiMitra - explainable mandi price intelligence (Streamlit dashboard).

    streamlit run app.py

Reads files the pipeline already wrote. It trains nothing on page load, so it
is fast in front of a judge, and nothing on screen can differ from outputs/.

Design rules
  * Every model figure is read from outputs/ (see tests/test_dashboard.py).
    The only figures computed here are descriptive statistics of the
    published price series, built in src/dashboard_data.py and labelled.
  * The data is historical. That is stated at the top of every view.
  * Selection is by rolling-origin cross-validation, and every view that
    names a model says so. The test window is never presented as the thing
    that chose it.
  * No forecast is presented as advice.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

from src import config
from src import live_data
from src.dashboard_data import (
    comparison_series, dataset_facts, load_everything, price_history,
    provenance_text, quality_facts, selectable_pairs, yearly_reporting,
)

st.set_page_config(page_title="MandiMitra | Mandi price intelligence",
                   layout="wide", initial_sidebar_state="collapsed")
pio.templates.default = "plotly_white"

# ------------------------------------------------------------------ palette
# Mid-tones that keep contrast on a white page and survive a dark one (the
# theme is pinned light in .streamlit/config.toml; these are the second line
# of defence after a dark-mode bug in an earlier version).
INK = "#1d2430"
MUTED = "#5b6472"
PRIMARY = "#1f6f4a"          # field green
MODEL_COLOUR = {"Naive": "#6b7280", "ARIMA": "#c27c2c",
                "RandomForest": "#3b7dc4", "GradientBoosting": "#2a9d8f",
                "RandomForest-delta": "#8e5ea2"}
ACTUAL_COLOUR = "#4b5563"
CARRIED_COLOUR = "#d1495b"
PAIR_COLOUR = ["#7b4f9d", "#d1495b", "#3b7dc4", "#c27c2c"]
MODELS = ["Naive", "ARIMA", "RandomForest", "GradientBoosting", "RandomForest-delta"]

st.markdown(f"""
<style>
.block-container {{ padding-top: 4.2rem; padding-bottom: 3rem; max-width: 1280px; }}
/* 4.2rem clears Streamlit's fixed top header (~3.75rem). A smaller value put the
   brand and the language switch underneath it, where they could not be clicked. */
h1, h2, h3 {{ color: {INK}; letter-spacing: -0.01em; }}
.mm-brand {{ font-size: 2.0rem; font-weight: 750; color: {PRIMARY}; margin: 0; line-height: 1.1; }}
.mm-tag {{ font-size: 1.02rem; color: {INK}; margin: .15rem 0 .1rem 0; font-weight: 600; }}
.mm-sub {{ font-size: .92rem; color: {MUTED}; margin: 0 0 .6rem 0; max-width: 62rem; }}
.mm-banner {{ border-left: 5px solid #b7791f; background: #fff8eb; color: #5c3d0a;
  padding: .7rem 1rem; border-radius: 6px; margin: .3rem 0 1rem 0; font-size: .95rem; }}
.mm-card {{ border: 1px solid #e3e6ea; border-radius: 10px; padding: .85rem 1rem;
  background: #ffffff; height: 100%; }}
@media (min-width: 641px) {{ .mm-card {{ min-height: 8.2rem; }} }}
.mm-card .k {{ font-size: .78rem; text-transform: uppercase; letter-spacing: .04em;
  color: {MUTED}; margin-bottom: .25rem; }}
.mm-card .v {{ font-size: 1.55rem; font-weight: 700; color: {INK}; line-height: 1.15; }}
.mm-card .s {{ font-size: .82rem; color: {MUTED}; margin-top: .25rem; }}
.mm-card.good .v {{ color: {PRIMARY}; }}
.mm-card.warn .v {{ color: #9a5b00; }}
.mm-fc {{ border: 1px solid #dfe7e2; background: #f6faf7; border-radius: 10px;
  padding: .8rem 1rem; height: 100%; }}
.mm-fc .k {{ font-size: .8rem; color: {MUTED}; }}
.mm-fc .v {{ font-size: 1.45rem; font-weight: 700; color: {INK}; }}
.mm-fc .s {{ font-size: .8rem; color: {MUTED}; }}
.mm-foot {{ color: {MUTED}; font-size: .82rem; border-top: 1px solid #e3e6ea;
  margin-top: 2rem; padding-top: .8rem; }}
@media (max-width: 640px) {{ .mm-brand {{ font-size: 1.6rem; }} .mm-card .v {{ font-size: 1.3rem; }} }}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------- language
# Hindi covers the plain-language views a farmer or trader reads first
# (header, overview, forecast summary). Technical tabs stay in English,
# and say so, rather than risk an imprecise translation of a method.
T = {
    "en": {
        "tagline": "Explainable mandi price intelligence for farmers and traders",
        "sub": "Short-term wholesale price signals from official Government of India "
               "daily mandi records, tested against the simplest possible forecast: "
               "tomorrow's price = today's price.",
        "banner": "<b>Historical data.</b> The official series used here ends on "
                  "<b>{d}</b>. Every forecast is for the days just after that date, "
                  "not for today. Use it to see how the method behaves, not to decide "
                  "today's sale.",
        "commodity": "Commodity", "market": "Market (mandi)", "lang": "Language",
        "tabs": ["Overview", "Price history", "Compare", "Model evaluation",
                 "Forecast", "Latest prices", "Method & data"],
        "q_title": "Data quality and freshness",
        "q_latest": "Latest genuine observation", "q_age": "{n:,} days old",
        "q_unch": "Price same as previous report", "q_unch_s": "of reported days",
        "q_gap": "Longest reporting gap", "q_gap_s": "days between two reports",
        "q_cf": "Model inputs carried forward", "q_cf_s": "never used as targets",
        "k_last": "Last reported price", "k_status": "Data status",
        "k_status_v": "Historical", "k_status_s": "Series ends {d}",
        "k_cov": "Days with a reported price", "k_cov_s": "{n:,} of {t:,} calendar days",
        "k_verdict": "Beats “same as today”?",
        "v_no": "No", "v_no_s": "the model chosen in advance, at 1, 2 or 3 days ahead, on unseen test data",
        "v_yes": "{n} of 3", "v_yes_s": "horizons, on unseen data",
        "next3": "The 3 days after the last date in the data",
        "card": "{h} day ahead · {d}", "card_n": "{h} days ahead · {d}",
        "same": "Same as the last reported price",
        "by": "Method: {m}",
        "means": "What this means",
        "story_naive": "Tested on earlier years, no model beat simply repeating the "
                       "last reported price, at any of the three horizons, so that is "
                       "the forecast shown.",
        "hindsight": " On the later, unseen test period {m} had the lowest error at "
                     "{h} ahead, but that is only visible with hindsight: choosing it "
                     "now would mean picking the winner using the test data.",
        "story_cv": "Cross-validation preferred {m} here, but on the untouched test "
                    "period the chosen model was not more accurate than repeating the "
                    "last reported price at any horizon.",
        "story_win": "{m} was more accurate than repeating the last reported price "
                     "on the untouched test period, by {p}.",
        "story_tail": "That is a genuine result, not a failure. On most reported "
                      "days the quoted price does not change at all, and the big "
                      "jumps cannot be predicted from recent prices alone.",
        "advice": "Decision-support information only. Not financial, trading or "
                  "farming advice.",
        "unit": "Rs. per quintal",
        "tech": "",
    },
    "hi": {
        "tagline": "किसानों और व्यापारियों के लिए समझने योग्य मंडी भाव जानकारी",
        "sub": "भारत सरकार के आधिकारिक दैनिक मंडी आँकड़ों पर आधारित अल्पकालिक थोक भाव "
               "संकेत, जिन्हें सबसे सरल अनुमान के सामने परखा गया है: कल का भाव = आज का भाव।",
        "banner": "<b>ऐतिहासिक आँकड़े।</b> यहाँ उपयोग किए गए आधिकारिक आँकड़े "
                  "<b>{d}</b> को समाप्त होते हैं। हर अनुमान उसी तारीख़ के ठीक बाद के दिनों "
                  "का है, आज का नहीं। इसे पद्धति को समझने के लिए देखें, आज की बिक्री का "
                  "निर्णय लेने के लिए नहीं।",
        "commodity": "फसल", "market": "मंडी", "lang": "भाषा",
        "tabs": ["सारांश", "भाव इतिहास", "तुलना", "मॉडल मूल्यांकन",
                 "अनुमान", "ताज़ा भाव", "पद्धति और स्रोत"],
        "q_title": "आँकड़ों की गुणवत्ता और ताज़गी",
        "q_latest": "अंतिम वास्तविक दर्ज भाव", "q_age": "{n:,} दिन पुराना",
        "q_unch": "भाव पिछली बार जैसा ही", "q_unch_s": "दर्ज दिनों में",
        "q_gap": "सबसे लंबा अंतराल", "q_gap_s": "दिन, दो दर्ज भावों के बीच",
        "q_cf": "आगे बढ़ाए गए इनपुट", "q_cf_s": "कभी लक्ष्य नहीं बने",
        "k_last": "अंतिम दर्ज भाव", "k_status": "आँकड़ों की स्थिति",
        "k_status_v": "ऐतिहासिक", "k_status_s": "आँकड़े {d} तक",
        "k_cov": "जिन दिनों भाव दर्ज हुआ", "k_cov_s": "{t:,} दिनों में से {n:,}",
        "k_verdict": "क्या “आज जैसा ही” से बेहतर?",
        "v_no": "नहीं", "v_no_s": "पहले से चुना गया मॉडल, 1, 2 या 3 दिन आगे, किसी पर भी नहीं (अनदेखे परीक्षण आँकड़ों पर)",
        "v_yes": "3 में से {n}", "v_yes_s": "अवधियों पर (अनदेखे आँकड़ों पर)",
        "next3": "आँकड़ों की अंतिम तारीख़ के बाद के 3 दिन",
        "card": "{h} दिन आगे · {d}", "card_n": "{h} दिन आगे · {d}",
        "same": "अंतिम दर्ज भाव के बराबर",
        "by": "पद्धति: {m}",
        "means": "इसका अर्थ",
        "story_naive": "पिछले वर्षों के आँकड़ों पर परखने पर कोई भी मॉडल अंतिम दर्ज भाव "
                       "को दोहराने से बेहतर नहीं निकला, तीनों अवधियों में से किसी पर भी "
                       "नहीं, इसलिए वही अनुमान दिखाया गया है।",
        "hindsight": " बाद के अनदेखे परीक्षण आँकड़ों पर {h} आगे के लिए {m} की त्रुटि "
                     "सबसे कम रही, पर यह केवल बाद में देखकर पता चलता है: उसे अभी चुनना "
                     "परीक्षण आँकड़ों से विजेता चुनना होगा।",
        "story_cv": "क्रॉस-वैलिडेशन में यहाँ {m} बेहतर लगा, पर अनदेखे परीक्षण आँकड़ों पर "
                    "चुना गया मॉडल किसी भी अवधि में अंतिम दर्ज भाव दोहराने से अधिक सटीक "
                    "नहीं निकला।",
        "story_win": "अनदेखे परीक्षण आँकड़ों पर {m} अंतिम दर्ज भाव दोहराने से {p} अधिक "
                     "सटीक रहा।",
        "story_tail": "यह एक वास्तविक निष्कर्ष है, विफलता नहीं। अधिकतर दर्ज दिनों में "
                      "भाव बिल्कुल नहीं बदलता, और बड़े उछाल केवल हाल के भावों से पहले "
                      "से नहीं जाने जा सकते।",
        "advice": "केवल निर्णय में सहायता के लिए जानकारी। यह वित्तीय, व्यापारिक या खेती "
                  "संबंधी सलाह नहीं है।",
        "unit": "रु. प्रति क्विंटल",
        "tech": "तकनीकी विवरण अंग्रेज़ी में हैं।",
    },
}
NAMES_HI = {"Onion": "प्याज़", "Tomato": "टमाटर", "Jaipur": "जयपुर",
            "Jodhpur": "जोधपुर", "Kota": "कोटा"}
MODEL_LABEL = {"Naive": "Naive (same as last price)", "ARIMA": "ARIMA",
               "RandomForest": "Random Forest", "GradientBoosting": "Gradient Boosting",
               "RandomForest-delta": "Random Forest (predicts change)"}


@st.cache_data(show_spinner="Loading results...")
def _load():
    return load_everything()


def _rs(x, dp=0):
    return "-" if x is None or pd.isna(x) else f"Rs. {float(x):,.{dp}f}"


def _num(x, dp=2):
    return "-" if x is None or pd.isna(x) else f"{float(x):,.{dp}f}"


def _d(ts):
    return pd.Timestamp(ts).strftime("%d %b %Y")


def _card(k, v, s="", cls=""):
    return (f'<div class="mm-card {cls}"><div class="k">{k}</div>'
            f'<div class="v">{v}</div><div class="s">{s}</div></div>')


def _layout(fig, height=420, legend=True):
    fig.update_layout(template="plotly_white", paper_bgcolor="white",
                      plot_bgcolor="white", height=height,
                      margin=dict(l=10, r=10, t=30, b=10),
                      font=dict(color=INK, size=13), hovermode="x unified",
                      showlegend=legend,
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
    fig.update_xaxes(gridcolor="#eef0f3", linecolor="#d5d9de")
    fig.update_yaxes(gridcolor="#eef0f3", linecolor="#d5d9de")
    return fig


def _csv(df):
    return df.to_csv(index=False).encode("utf-8")


# ---------------------------------------------------------------- load/guard
try:
    DATA = _load()
except FileNotFoundError as exc:
    st.error("**The data has not been built yet.**")
    st.code(str(exc), language="text")
    st.markdown("Run these in the project folder, then reload this page:\n\n"
                "```\npython scripts/extract_rajasthan.py\n"
                "python scripts/build_features.py\n"
                "python scripts/run_pipeline.py --all-pairs\n```")
    st.stop()

if DATA["missing_required"]:
    st.error("**Model results are missing:** " + ", ".join(DATA["missing_required"]))
    st.markdown("Run `python scripts/run_pipeline.py --all-pairs`, then reload.")
    st.stop()

features, clean = DATA["features"], DATA["clean"]
comparison, predictions = DATA["comparison"], DATA["predictions"]
best, forecast, folds = DATA["best"], DATA["forecast"], DATA["cv_folds"]
importance, bounds, excluded = DATA["importance"], DATA["boundaries"], DATA["excluded"]

pairs = selectable_pairs(features, best)
if pairs.empty:
    st.error("No commodity/market pair has both enough data and evaluated results.")
    st.stop()

# -------------------------------------------------------------------- header
h1, h2 = st.columns([5, 1.3])
with h2:
    lang_label = st.radio("Language / भाषा", ["English", "हिन्दी"], horizontal=True,
                          label_visibility="collapsed", key="lang")
L = "hi" if lang_label == "हिन्दी" else "en"
t = T[L]


def nm(x):
    return NAMES_HI.get(x, x) if L == "hi" else x


with h1:
    st.markdown('<p class="mm-brand">MandiMitra</p>'
                f'<p class="mm-tag">{t["tagline"]}</p>'
                f'<p class="mm-sub">{t["sub"]}</p>', unsafe_allow_html=True)

last_date = clean["date"].max()
st.markdown(f'<div class="mm-banner">{t["banner"].format(d=_d(last_date))}</div>',
            unsafe_allow_html=True)

s1, s2, _ = st.columns([1, 1, 2])
with s1:
    commodity = st.selectbox(t["commodity"], sorted(pairs["commodity"].unique()),
                             format_func=nm, key="commodity")
with s2:
    markets = sorted(pairs[pairs["commodity"] == commodity]["market"].unique())
    market = st.selectbox(t["market"], markets, format_func=nm, key="market")

key = (commodity, market)


def _sel(df):
    if df.empty:
        return df
    return df[(df["commodity"] == commodity) & (df["market"] == market)]


facts = dataset_facts(features, clean, commodity, market)
p_best, p_comp, p_pred = _sel(best), _sel(comparison), _sel(predictions)
p_fc, p_folds, p_bounds = _sel(forecast), _sel(folds), _sel(bounds)
if not facts or p_best.empty:
    st.warning(f"No evaluated results for {commodity} / {market}. Run "
               f"`python scripts/run_pipeline.py --all-pairs` and reload.")
    st.stop()

tabs = st.tabs(t["tabs"])

# ============================================================== 1. OVERVIEW
with tabs[0]:
    beats = p_best[p_best["beats_naive"].astype(bool)]
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(_card(t["k_last"], _rs(facts["last_observed_price"]),
                      f'{t["unit"]} · {_d(facts["last_observed_date"])}'),
                unsafe_allow_html=True)
    c2.markdown(_card(t["k_status"], t["k_status_v"],
                      t["k_status_s"].format(d=_d(facts["last_date"])), "warn"),
                unsafe_allow_html=True)
    c3.markdown(_card(t["k_cov"], f'{facts["reported_pct"]:.0f}%',
                      t["k_cov_s"].format(n=facts["days_reported"],
                                          t=facts["calendar_days"])),
                unsafe_allow_html=True)
    if beats.empty:
        c4.markdown(_card(t["k_verdict"], t["v_no"], t["v_no_s"]),
                    unsafe_allow_html=True)
    else:
        c4.markdown(_card(t["k_verdict"], t["v_yes"].format(n=len(beats)),
                          t["v_yes_s"], "good"), unsafe_allow_html=True)

    st.markdown(f"#### {t['next3']}")
    fc_cols = st.columns(3)
    for col, h in zip(fc_cols, config.HORIZONS):
        row = p_fc[p_fc["horizon"] == h]
        if row.empty:
            col.markdown(_card(f"{h}", "-", "no forecast"), unsafe_allow_html=True)
            continue
        r = row.iloc[0]
        label = (t["card"] if h == 1 else t["card_n"]).format(
            h=h, d=_d(r["forecast_date"]))
        same = (r["model"] == "Naive")
        delta = r["predicted_price"] - r["last_reported_price"]
        sub = (t["same"] if same else
               f'{delta:+,.0f} vs last reported · '
               f'{t["by"].format(m=MODEL_LABEL.get(r["model"], r["model"]))}')
        col.markdown(f'<div class="mm-fc"><div class="k">{label}</div>'
                     f'<div class="v">{_rs(r["predicted_price"])}</div>'
                     f'<div class="s">{sub}</div></div>', unsafe_allow_html=True)

    st.markdown(f"#### {t['means']}")
    sel_models = sorted(set(p_best["best_model"]))
    # Did any NON-selected model do better on test? Say so, labelled as
    # hindsight, rather than imply the baseline won everything.
    hs = p_best[(p_best["posthoc_lowest_test_rmse_model"] != p_best["best_model"])
                & (p_best["posthoc_lowest_test_rmse_model"] != "Naive")]
    hs_txt = ""
    if not hs.empty:
        h0 = hs.iloc[0]
        hs_txt = t["hindsight"].format(
            m=MODEL_LABEL.get(h0["posthoc_lowest_test_rmse_model"],
                              h0["posthoc_lowest_test_rmse_model"]),
            h=(f'{int(h0["horizon"])} day' if int(h0["horizon"]) == 1
               else f'{int(h0["horizon"])} days') if L == "en"
            else f'{int(h0["horizon"])} दिन')
    if beats.empty and sel_models == ["Naive"]:
        story = t["story_naive"] + hs_txt
    elif beats.empty:
        story = t["story_cv"].format(m=", ".join(MODEL_LABEL.get(m, m)
                                                  for m in sel_models if m != "Naive"))
        story += hs_txt
    else:
        b0 = beats.sort_values("improvement_over_naive_pct").iloc[-1]
        story = t["story_win"].format(m=MODEL_LABEL.get(b0["best_model"]),
                                      p=f'{b0["improvement_over_naive_pct"]:.1f}%')
    st.markdown(f"{story} {t['story_tail']}")
    if L == "hi":
        st.caption(t["tech"])

    with st.expander("The numbers behind this summary", expanded=False):
        show = p_best[["horizon", "best_model", "best_test_mae", "best_test_rmse",
                       "naive_test_rmse", "improvement_over_naive_pct", "n_test"]].copy()
        show.columns = ["Days ahead", "Model selected by cross-validation",
                        "Test MAE (Rs./q)", "Test RMSE (Rs./q)", "Naive test RMSE",
                        "vs Naive (RMSE %)", "Test days scored"]
        st.dataframe(show, hide_index=True, use_container_width=True,
                     column_config={c: st.column_config.NumberColumn(format="%.2f")
                                    for c in show.columns[2:6]})
        st.caption("Positive = more accurate than repeating the last reported price. "
                   "The model was chosen on earlier data; these test numbers were "
                   "computed once, afterwards. See Model evaluation.")

    q = quality_facts(clean, commodity, market)
    if q:
        st.markdown(f"#### {t['q_title']}")
        q1, q2, q3, q4 = st.columns(4)
        q1.markdown(_card(t["q_latest"], _d(q["latest_observation"]),
                          t["q_age"].format(n=q["age_days"]), "warn"),
                    unsafe_allow_html=True)
        q2.markdown(_card(t["q_unch"], f'{q["unchanged_pct"]:.0f}%', t["q_unch_s"]),
                    unsafe_allow_html=True)
        q3.markdown(_card(t["q_gap"], f'{q["longest_gap_days"]:,}', t["q_gap_s"]),
                    unsafe_allow_html=True)
        q4.markdown(_card(t["q_cf"], f'{facts["imputed_pct"]:.0f}%', t["q_cf_s"]),
                    unsafe_allow_html=True)

# ========================================================= 2. PRICE HISTORY
with tabs[1]:
    st.subheader(f"Daily wholesale price — {commodity}, {market}")
    if L == "hi":
        st.caption(t["tech"])
    hist = price_history(features, commodity, market)
    rng = st.radio("Range", ["6 months", "1 year", "2 years", "All"], index=3,
                   horizontal=True, key="hist_range")
    span = {"6 months": 182, "1 year": 365, "2 years": 730}.get(rng)
    show_cf = st.toggle("Show carried-forward days", value=False, key="show_cf",
                        help="Days the mandi did not report. The previous reported "
                             "price was carried forward (at most "
                             f"{config.MAX_FFILL_DAYS} days) as a model input only.")
    rep = hist[hist["observed"]]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=rep["date"], y=rep["price_t"], name="Reported price", mode="lines",
        line=dict(color=ACTUAL_COLOUR, width=1.4),
        hovertemplate="%{x|%d %b %Y}<br>Rs. %{y:,.0f}/quintal<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=hist["date"], y=hist["ma_7"], name="7-day average", mode="lines",
        line=dict(color=MODEL_COLOUR["ARIMA"], width=1.6, dash="dot"),
        hovertemplate="7-day avg Rs. %{y:,.0f}<extra></extra>"))
    if show_cf:
        cf = hist[~hist["observed"]]
        fig.add_trace(go.Scatter(
            x=cf["date"], y=cf["price_t"], name=f"Carried forward ({len(cf):,} days)",
            mode="markers", marker=dict(color=CARRIED_COLOUR, size=4, opacity=.7),
            hovertemplate="%{x|%d %b %Y}<br>not reported (carried forward)<extra></extra>"))
    _layout(fig, 440)
    fig.update_yaxes(title=t["unit"] if L == "en" else "Rs. per quintal")
    if span:
        fig.update_xaxes(range=[hist["date"].max() - pd.Timedelta(days=span),
                                hist["date"].max()])
    st.plotly_chart(fig, use_container_width=True, key="hist_chart")

    a, b = st.columns([1.2, 1])
    with a:
        st.markdown("**Reporting coverage by year**")
        yr = yearly_reporting(clean, commodity, market)
        fy = go.Figure()
        for col_name, colr in (("Reported", PRIMARY), ("Carried forward", "#e3a3ab"),
                               ("No price", "#d5d9de")):
            fy.add_trace(go.Bar(x=yr["year"], y=yr[col_name], name=col_name,
                                marker_color=colr))
        _layout(fy, 300).update_layout(barmode="stack", hovermode="x")
        fy.update_yaxes(title="days")
        st.plotly_chart(fy, use_container_width=True, key="yr_chart")
    with b:
        st.markdown("**Dataset facts**")
        st.dataframe(pd.DataFrame({
            "": ["Date range", "Calendar days", "Days with a reported price",
                 "Feature rows (model inputs)", "of which carried forward",
                 "Usable targets, 1 / 2 / 3 days", "Median price", "Min / max price"],
            "Value": [f'{_d(facts["first_date"])} – {_d(facts["last_date"])}',
                      f'{facts["calendar_days"]:,}',
                      f'{facts["days_reported"]:,} ({facts["reported_pct"]}%)',
                      f'{facts["feature_rows"]:,}', f'{facts["imputed_pct"]}%',
                      " / ".join(f'{facts["usable"][h]:,}' for h in config.HORIZONS),
                      _rs(facts["median_price"]),
                      f'{_rs(facts["min_price"])} / {_rs(facts["max_price"])}']}),
            hide_index=True, use_container_width=True)
        st.caption("Unit: Rs. per quintal, wholesale (as published). A 0 in the "
                   "source means 'not reported' and is treated as missing. Only "
                   "genuinely reported prices are ever used as targets.")
    st.download_button("Download this price history (CSV)", _csv(hist),
                       f"price_history_{commodity}_{market}.csv".lower(),
                       "text/csv", key="dl_hist")

# =============================================================== 3. COMPARE
with tabs[2]:
    st.subheader("Compare validated series")
    plist = list(pairs[["commodity", "market"]].itertuples(index=False, name=None))
    if len(plist) < 2:
        st.info("Only one commodity/market pair has enough verified data, so "
                "there is nothing to compare yet.")
    else:
        cs = comparison_series(clean, plist)
        st.caption(f"Common window: {_d(cs['start'])} – {_d(cs['end'])}. Reported "
                   f"days only. Descriptive statistics of the published prices, not "
                   f"model output. Comparing commodities shows how differently they "
                   f"move; it does not rank them.")
        fi = go.Figure()
        for i, col in enumerate(cs["index"].columns):
            fi.add_trace(go.Scatter(x=cs["index"].index, y=cs["index"][col], name=col,
                                    mode="lines", line=dict(color=PAIR_COLOUR[i % 4], width=1.4),
                                    connectgaps=True))
        _layout(fi, 380)
        fi.update_yaxes(title=f"Price index (100 = {_d(cs['base_date'])})")
        st.plotly_chart(fi, use_container_width=True, key="cmp_index")

        fv = go.Figure()
        for i, col in enumerate(cs["volatility"].columns):
            fv.add_trace(go.Scatter(x=cs["volatility"].index, y=cs["volatility"][col],
                                    name=col, mode="lines",
                                    line=dict(color=PAIR_COLOUR[i % 4], width=1.2)))
        _layout(fv, 300)
        fv.update_yaxes(title="30-day volatility of daily % change")
        st.plotly_chart(fv, use_container_width=True, key="cmp_vol")
        st.dataframe(cs["summary"], use_container_width=True)
        st.caption("Median daily absolute change is 0% for both: on most reported "
                   "days the quoted price did not move at all. That is why "
                   "‘same as yesterday’ is so hard to beat.")

    st.markdown("**Markets in the source that are not shown, and why**")
    if excluded.empty:
        st.caption("None excluded.")
    else:
        ex = excluded[excluded["horizon"].astype(str) == "all"][["commodity", "market", "reason"]]
        st.dataframe(ex.rename(columns={"commodity": "Commodity", "market": "Market",
                                        "reason": "Reason"}),
                     hide_index=True, use_container_width=True)
        st.caption(f"The {config.MIN_ROWS_PER_PAIR}-row gate was set before these "
                   f"markets were examined and was not lowered to admit them.")

# ======================================================= 4. MODEL EVALUATION
with tabs[3]:
    if L == "hi":
        st.caption(t["tech"])
    # Offer only horizons that were actually evaluated for this pair, so the
    # selector can never point at a result that does not exist (and no
    # st.stop() is needed here -- inside a tab it would blank every later tab).
    h_opts = sorted(int(h) for h in p_best["horizon"].unique())
    horizon = st.radio("Days ahead", h_opts, horizontal=True, key="eval_h",
                       format_func=lambda h: f"{h} day" if h == 1 else f"{h} days")
    b = p_best[p_best["horizon"] == horizon].iloc[0]
    bd = p_bounds[p_bounds["horizon"] == horizon]
    hc = p_comp[p_comp["horizon"] == horizon]
    hf = p_folds[p_folds["horizon"] == horizon]

    st.subheader(f"How the {horizon}-day forecast was chosen and scored")
    if not bd.empty:
        r = bd.iloc[0]
        tl = go.Figure()
        segs = [("Fit only", r["train_start"], r["cv_start"], "#cfe3d8"),
                ("Cross-validation folds (choose the model)", r["cv_start"], r["cv_end"], "#8cc0a4"),
                ("Untouched test (scored once)", r["test_start"], r["test_end"], PRIMARY)]
        for name, s, e, colr in segs:
            # On a date axis a bar's length is a duration in MILLISECONDS.
            tl.add_trace(go.Bar(x=[(pd.Timestamp(e) - pd.Timestamp(s)).days * 86_400_000],
                                base=[pd.Timestamp(s)], y=["period"], orientation="h",
                                marker_color=colr, name=name,
                                hovertemplate=f"{name}<br>{_d(s)} – {_d(e)}<extra></extra>"))
        for fdx in hf.drop_duplicates("fold").itertuples():
            tl.add_vline(x=pd.Timestamp(fdx.origin), line=dict(color="white", width=2))
        _layout(tl, 150).update_layout(barmode="overlay", hovermode="closest",
                                       margin=dict(l=10, r=10, t=10, b=10))
        tl.update_yaxes(visible=False)
        tl.update_xaxes(type="date")
        st.plotly_chart(tl, use_container_width=True, key=f"timeline_{horizon}")
        st.caption(f"{int(r['cv_folds'])} expanding folds: each fits on everything "
                   f"before its origin (white lines) and is scored on the next block. "
                   f"Selection rule, fixed in advance: lowest mean RMSE across folds. "
                   f"Test {_d(r['test_start'])} – {_d(r['test_end'])}, "
                   f"{int(r['n_test_scored'])} days scored.")

    v = hc[hc["split"] == "valid"].set_index("model")
    te = hc[hc["split"] == "test"].set_index("model")
    naive_rmse = te.loc["Naive", "rmse"] if "Naive" in te.index else float("nan")
    tbl = pd.DataFrame({
        "Model": [MODEL_LABEL[m] for m in MODELS if m in te.index],
        "CV mean fold RMSE": [v.loc[m, "cv_mean_fold_rmse"] for m in MODELS if m in te.index],
        "Test MAE": [te.loc[m, "mae"] for m in MODELS if m in te.index],
        "Test RMSE": [te.loc[m, "rmse"] for m in MODELS if m in te.index],
        "Test MAPE %": [te.loc[m, "mape"] for m in MODELS if m in te.index],
        "Test RMSE vs Naive %": [100 * (naive_rmse - te.loc[m, "rmse"]) / naive_rmse
                                 for m in MODELS if m in te.index],
        "Test days": [int(te.loc[m, "n"]) for m in MODELS if m in te.index],
        "Selected by CV": ["Selected" if m == b["best_model"] else ""
                           for m in MODELS if m in te.index],
    })
    st.dataframe(tbl, hide_index=True, use_container_width=True,
                 column_config={c: st.column_config.NumberColumn(format="%.2f")
                                for c in ["CV mean fold RMSE", "Test MAE", "Test RMSE",
                                          "Test MAPE %", "Test RMSE vs Naive %"]})
    st.caption("All errors in Rs. per quintal except MAPE. Every model is scored on "
               "the identical test days. MAE = typical miss on an ordinary day; "
               "RMSE = penalises big misses more. R² is in the CSV but not shown: "
               "on a price series that mostly repeats itself it is high for any "
               "model and says little.")

    sel = b["best_model"]
    if b["beats_naive"]:
        st.success(f"**{MODEL_LABEL[sel]}** was selected by cross-validation and was "
                   f"{b['improvement_over_naive_pct']:.2f}% more accurate than Naive "
                   f"(test RMSE) on the untouched test period.")
    elif sel == "Naive":
        st.info(f"**Naive was selected by cross-validation.** No model beat "
                f"‘same as the last reported price’ at {horizon} day(s) "
                f"ahead in cross-validation, so that is what the forecast uses.")
    else:
        st.warning(f"**{MODEL_LABEL[sel]} was selected by cross-validation, but did "
                   f"not beat Naive on the test period** "
                   f"({b['improvement_over_naive_pct']:+.2f}% test RMSE). This is "
                   f"reported as measured.")
    if not b["selection_confirmed_by_test"]:
        st.caption(f"Transparency note: looking at the test period afterwards, "
                   f"{MODEL_LABEL[b['posthoc_lowest_test_rmse_model']]} had the lowest "
                   f"test RMSE ({b['posthoc_lowest_test_rmse']:.2f}). It is shown here "
                   f"only for honesty. Choosing it now would be selecting on the test "
                   f"set, which is the mistake this protocol exists to prevent.")
    if not b["metrics_agree"]:
        st.caption(f"MAE and RMSE disagree: the lowest test MAE belongs to "
                   f"{MODEL_LABEL[b['lowest_mae_model']]} ({b['lowest_mae']:.2f}). "
                   f"MAE measures the typical day; RMSE weights rare large misses "
                   f"more. Both are reported because they answer different questions.")

    dm_df = DATA.get("dm", pd.DataFrame())
    if not dm_df.empty and sel != "Naive":
        r_ = dm_df[(dm_df["commodity"] == commodity) & (dm_df["market"] == market)
                   & (dm_df["horizon"] == horizon) & (dm_df["model"] == sel)
                   & (dm_df["loss"] == "squared")]
        if not r_.empty:
            r_ = r_.iloc[0]
            st.caption(f"Significance (Diebold–Mariano, squared error, test period, "
                       f"{int(r_['n'])} days): {MODEL_LABEL[sel]} vs Naive "
                       f"DM = {r_['dm_stat']:+.2f}, p = {r_['p_value']:.3f} "
                       f"(Holm-adjusted {r_['p_holm']:.3f}). Negative would favour "
                       f"the model.")

    st.markdown("**Error in each cross-validation fold**")
    if not hf.empty:
        log_y = st.toggle("Log scale", value=True, key=f"log_{horizon}",
                          help="One fold contains the October 2013 onion price spike "
                               "and dwarfs the rest on a linear scale.")
        ff = go.Figure()
        for m in MODELS:
            g = hf[hf["model"] == m].sort_values("fold")
            labels = [f"Fold {int(x.fold)}<br>{x.val_start[:7]}–{x.val_end[:7]}"
                      for x in g.itertuples()]
            ff.add_trace(go.Bar(x=labels, y=g["rmse"], name=MODEL_LABEL[m],
                                marker_color=MODEL_COLOUR[m],
                                hovertemplate="%{y:,.1f}<extra>" + MODEL_LABEL[m] + "</extra>"))
        _layout(ff, 360).update_layout(barmode="group", hovermode="x")
        if log_y:      # label powers of ten only; minor-tick labels read as noise
            ff.update_yaxes(title="RMSE (Rs./q), log scale", type="log", dtick=1)
        else:
            ff.update_yaxes(title="RMSE (Rs./q)", type="linear")
        st.plotly_chart(ff, use_container_width=True, key=f"folds_{horizon}")
        spike = hf[hf["val_target_max"] > hf["fit_target_max"]].drop_duplicates("fold")
        if not spike.empty:
            s0 = spike.iloc[0]
            dm = "RandomForest-delta"
            if dm in te.index and pd.notna(naive_rmse):
                d_beats = te.loc[dm, "rmse"] < naive_rmse
                d_txt = (f"On this pair's test period it {'did' if d_beats else 'did not'} "
                         f"beat Naive at {horizon} day(s) "
                         f"({te.loc[dm, 'rmse']:.2f} vs {naive_rmse:.2f} RMSE)"
                         + ("" if not d_beats or sel == dm else
                            ", but it was not the model chosen in advance, so it is "
                            "not what the forecast uses") + ".")
            else:
                d_txt = ""
            st.caption(f"Fold {int(s0['fold'])} contains prices up to "
                       f"Rs. {s0['val_target_max']:,.0f}, above anything in its "
                       f"training data (max Rs. {s0['fit_target_max']:,.0f}). Tree "
                       f"models can only predict averages of training prices, so "
                       f"they cannot follow a spike to a new high. Predicting the "
                       f"price change instead (Random Forest-delta) removes most of "
                       f"this. {d_txt}")

    st.markdown("**Actual vs predicted on the untouched test period**")
    tp = p_pred[(p_pred["horizon"] == horizon) & (p_pred["split"] == "test")]
    opts = [m for m in MODELS if m in set(tp["model"].astype(str))]
    # Default: the selected model and Naive. When Naive IS the selection, add
    # ARIMA (the classical reference) so the chart always compares two methods.
    want = [str(sel), "Naive"] + (["ARIMA"] if str(sel) == "Naive" else [])
    default = [m for m in dict.fromkeys(want) if m in opts] or opts[:1]
    pick = st.multiselect("Models to plot", opts, default=default,
                          format_func=lambda m: MODEL_LABEL[m], key=f"pick_{horizon}")
    if not pick:
        st.info("Choose at least one model to plot.")
    else:
        fa = go.Figure()
        act = tp[tp["model"] == opts[0]].sort_values("date")
        # Actual is solid ink; every forecast is dashed in its model colour. Two
        # greys (actual vs Naive) were indistinguishable in an earlier version.
        fa.add_trace(go.Scatter(x=act["date"], y=act["y_true"], name="Actual price",
                                mode="lines", line=dict(color=INK, width=2.2)))
        for m in pick:
            g = tp[tp["model"] == m].sort_values("date")
            fa.add_trace(go.Scatter(x=g["date"], y=g["y_pred"], name=MODEL_LABEL[m],
                                    mode="lines",
                                    line=dict(color=MODEL_COLOUR[m], width=1.6, dash="dash")))
        _layout(fa, 400)
        fa.update_yaxes(title="Rs. per quintal")
        st.plotly_chart(fa, use_container_width=True, key=f"avp_{horizon}")
        st.caption("x-axis = the date the forecast was made; it is for the price "
                   f"{horizon} day(s) later.")

        fr = go.Figure()
        for m in pick:
            g = tp[tp["model"] == m]
            fr.add_trace(go.Box(y=g["y_pred"] - g["y_true"], name=MODEL_LABEL[m],
                                marker_color=MODEL_COLOUR[m], boxmean=True))
        _layout(fr, 320, legend=False).update_layout(hovermode="closest")
        fr.update_yaxes(title="Predicted minus actual (Rs./q)", zeroline=True)
        st.plotly_chart(fr, use_container_width=True, key=f"resid_{horizon}")

    with st.expander("Training vs test error: is any model memorising?"):
        tr = hc[hc["split"] == "train"].set_index("model")
        rows = []
        for m in MODELS:
            if m not in tr.index or m not in te.index:
                continue
            ok = bool(tr.loc[m, "comparable_train_gap"])
            rows.append({"Model": MODEL_LABEL[m],
                         "What the training number is": tr.loc[m, "diagnostic"],
                         "Train RMSE": tr.loc[m, "rmse"], "Train rows": int(tr.loc[m, "n"]),
                         "Test RMSE": te.loc[m, "rmse"],
                         "Gap": te.loc[m, "rmse"] - tr.loc[m, "rmse"] if ok else None})
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True,
                     column_config={c: st.column_config.NumberColumn(format="%.2f")
                                    for c in ["Train RMSE", "Test RMSE", "Gap"]})
        st.caption("The gap is only shown where it compares like with like. Naive "
                   "fits nothing, so its training number describes how calm that "
                   "period was, not memorisation. ARIMA's is an in-sample h-step "
                   "forecast with training-window parameters (an earlier version "
                   "reported it from a single row, n=1, which was a bug).")

    imp = _sel(importance)
    imp = imp[imp["horizon"] == horizon] if not imp.empty else imp
    if not imp.empty:
        with st.expander("Which inputs the tree models relied on"):
            fim = go.Figure()
            for m in ["RandomForest", "GradientBoosting", "RandomForest-delta"]:
                g = imp[imp["model"] == m].sort_values("importance")
                fim.add_trace(go.Bar(y=g["feature"], x=g["importance"], orientation="h",
                                     name=MODEL_LABEL[m], marker_color=MODEL_COLOUR[m]))
            _layout(fim, 420).update_layout(barmode="group", hovermode="y")
            st.plotly_chart(fim, use_container_width=True, key=f"imp_{horizon}")
            tree_win = [MODEL_LABEL[m] for m in ["RandomForest", "GradientBoosting",
                                                 "RandomForest-delta"]
                        if m in te.index and pd.notna(naive_rmse)
                        and te.loc[m, "rmse"] < naive_rmse]
            win_txt = ("None of these tree models beat Naive on this test period"
                       if not tree_win else
                       f"On this test period {', '.join(tree_win)} had a lower RMSE "
                       f"than Naive")
            st.caption("Impurity-based importance: how much each input was used, not "
                       "a causal effect. Lagged prices dominate because the strongest "
                       f"predictor of a price is the recent price. {win_txt}, so read "
                       "this as 'what the models used', not 'what drives prices'.")

    d1, d2, d3 = st.columns(3)
    d1.download_button("Model comparison (CSV)", _csv(p_comp), "model_comparison.csv",
                       "text/csv", key="dl_comp")
    d2.download_button("Predictions (CSV)", _csv(p_pred), "predictions.csv",
                       "text/csv", key="dl_pred")
    d3.download_button("CV folds (CSV)", _csv(p_folds), "cv_folds.csv",
                       "text/csv", key="dl_folds")

# =============================================================== 5. FORECAST
with tabs[4]:
    st.subheader(f"Forecast — {nm(commodity)}, {nm(market)}")
    if p_fc.empty:
        st.warning("No forecast was produced for this selection.")
    else:
        f = p_fc.sort_values("horizon").copy()
        out = pd.DataFrame({
            "Days ahead": f["horizon"],
            "Forecast made on (last data date)": pd.to_datetime(f["from_date"]).dt.strftime("%d %b %Y"),
            "Forecast for": pd.to_datetime(f["forecast_date"]).dt.strftime("%d %b %Y"),
            "Method (chosen by CV)": f["model"].map(MODEL_LABEL),
            "Forecast (Rs./q)": f["predicted_price"],
            "Last reported (Rs./q)": f["last_reported_price"],
            "Change (Rs./q)": f["predicted_price"] - f["last_reported_price"],
        })
        st.dataframe(out, hide_index=True, use_container_width=True,
                     column_config={c: st.column_config.NumberColumn(format="%.2f")
                                    for c in ["Forecast (Rs./q)", "Last reported (Rs./q)",
                                              "Change (Rs./q)"]})
        st.markdown(f["method_note"].iloc[0] if "method_note" in f else "")
        st.caption(f["trend_note"].iloc[0])

        if "interval_test_coverage" in f.columns:
            st.markdown("**Uncertainty: why no band is drawn**"
                        if not p_best["interval_held_up"].astype(bool).all()
                        else "**Uncertainty ranges**")
            iv = p_best[["horizon", "interval_lo_offset", "interval_hi_offset",
                         "interval_test_coverage", "interval_status"]].copy()
            iv.columns = ["Days ahead", "Range low offset (Rs./q)",
                          "Range high offset (Rs./q)",
                          "Test coverage % (target 80%)", "Result"]
            held = p_best["interval_held_up"].astype(bool)
            if held.all():
                st.success("The 80% ranges held up on the untouched test period.")
            else:
                st.markdown(
                    "We built an 80% range from the selected method's "
                    "cross-validation errors and then checked it once on the "
                    f"untouched test period. It held up at **{int(held.sum())} of "
                    f"{len(held)}** horizons, so it is not presented as a reliable "
                    "band. Showing it anyway would give false confidence.")
            st.dataframe(iv, hide_index=True, use_container_width=True,
                         column_config={**{c: st.column_config.NumberColumn(format="%.1f")
                                       for c in iv.columns[1:4]},
                                    "Result": st.column_config.TextColumn(width="large")})
        st.download_button("Download forecast (CSV)", _csv(f), "forecast.csv",
                           "text/csv", key="dl_fc")
    st.caption(t["advice"])

# ========================================================= 6. LATEST PRICES
@st.cache_data(ttl=6 * 3600, show_spinner="Checking the official API...")
def _refresh_live(_key_present: bool):
    """Try the official API at most every 6 hours; always return the last GOOD
    snapshot plus status. The key is read inside live_data, never shown."""
    if _key_present:
        live_data.update_snapshot(
            live_data.get_api_key(),
            filters_list=[{"state": "Rajasthan", "commodity": c}
                          for c in config.TARGET_COMMODITIES],
            # A page view must not hang on a slow government API.
            fetch_kwargs={"timeout": 10.0, "retries": 2})
    return live_data.load_latest()


with tabs[5]:
    st.subheader("Latest official mandi prices" if L == "en" else "ताज़ा आधिकारिक मंडी भाव")
    st.caption("Observed prices, not forecasts. They are kept separate from the "
               "historical evaluation and are not used by any model here.")
    key_present = bool(live_data.get_api_key())
    live_df, live_status = _refresh_live(key_present)
    fr = live_status.get("freshness", {"status": "unavailable"})
    if live_df.empty:
        st.info(
            "**Not connected.** Current prices come from the official "
            f"*{live_data.SOURCE_TITLE}* API on data.gov.in "
            f"({live_data.SOURCE_PUBLISHER}). It needs a free personal API key, "
            "and none is configured on this deployment, so this app shows "
            "historical data only. Nothing on this page is a live price."
            + (f"\n\nLast attempt: {live_status.get('last_attempt_utc')} UTC — "
               f"{live_status.get('error')}" if live_status.get("error") else ""))
        st.markdown("To connect it, get a free key at data.gov.in. **Locally:** set "
                    "the environment variable `DATAGOVIN_API_KEY` and run "
                    "`python scripts/fetch_current_prices.py`. **On Streamlit "
                    "Cloud:** add `DATAGOVIN_API_KEY` under *Settings → Secrets*; "
                    "the app then checks the API at most every 6 hours. See "
                    "`docs/01_DATA_SOURCE.md`.")
    else:
        badge = {"current": ("Current", "good"), "stale": ("Stale", "warn")}.get(
            fr["status"], ("Unavailable", "warn"))
        a1, a2, a3 = st.columns(3)
        a1.markdown(_card("Status", badge[0],
                          f'latest observation {fr.get("age_days")} day(s) old',
                          badge[1]), unsafe_allow_html=True)
        a2.markdown(_card("Latest observation date",
                          _d(live_df["arrival_date"].max()), "arrival date at the mandi"),
                    unsafe_allow_html=True)
        a3.markdown(_card("Retrieved", str(live_status.get("last_success_utc", "-"))[:16]
                          .replace("T", " "),
                          f'UTC · source updated {live_status.get("source_updated") or "-"}'),
                    unsafe_allow_html=True)
        if live_status.get("ok") is False and live_status.get("error"):
            st.warning(f"The latest refresh failed, so the previous good data is "
                       f"shown: {live_status['error']}")
        show = live_df[["arrival_date", "market", "district", "commodity", "variety",
                        "min_price", "modal_price", "max_price"]].sort_values(
            ["commodity", "market", "arrival_date"])
        show["arrival_date"] = show["arrival_date"].dt.strftime("%d %b %Y")
        st.dataframe(show.rename(columns={
            "arrival_date": "Date", "market": "Market", "district": "District",
            "commodity": "Commodity", "variety": "Variety",
            "min_price": "Min (Rs./q)", "modal_price": "Modal (Rs./q)",
            "max_price": "Max (Rs./q)"}), hide_index=True, use_container_width=True)
        st.caption("Modal = the most common transaction price that day; min and max "
                   "are the day's range. Unit as published by AGMARKNET (Rs. per "
                   "quintal). Source: data.gov.in, GODL-India.")
        st.download_button("Download these prices (CSV)", _csv(live_df),
                           "latest_mandi_prices.csv", "text/csv", key="dl_live")

# ========================================================= 7. METHOD & DATA
with tabs[6]:
    if L == "hi":
        st.caption(t["tech"])
    st.subheader("Data source and attribution")
    st.markdown(f"""
- **Source:** Open Government Data Platform India (data.gov.in), *Daily wholesale
  price* files for Onion and Tomato, published by the Department of Consumer
  Affairs (Price Monitoring Cell), Government of India.
- **Licence:** Government Open Data License – India (GODL-India); attribution
  to the publisher is required. The data licence is separate from this project's
  code licence.
- **Coverage used:** {_d(clean['date'].min())} – {_d(clean['date'].max())}.
  Unit: Rs. per quintal, wholesale.
- **Integrity:** the two official files are kept untouched with SHA-256 hashes;
  the Rajasthan subset is regenerated from them by a script, and a test proves
  it reproduces the project's original file byte for byte.
""")
    st.subheader("How the data is prepared")
    st.markdown(f"""
- A price of **0** is the source's code for *not reported*, so it is treated as
  missing. Prices outside Rs. {config.MIN_PRICE:,.0f}–{config.MAX_PRICE:,.0f}/q
  are rejected as errors.
- Each series is placed on a **continuous daily calendar**, so "yesterday" always
  means the previous calendar day, even when the mandi was closed.
- A missing day may take the last reported price as an **input** for at most
  **{config.MAX_FFILL_DAYS} days**. Longer gaps stay empty.
- **Targets are never carried forward.** A row is scored only if the mandi really
  reported a price on the target day.
- Features use only information available at the end of the forecast day: lags
  of {", ".join(map(str, config.LAGS))} days, {", ".join(map(str, config.MA_WINDOWS))}-day
  averages, {config.VOL_WINDOW}-day volatility, momentum and calendar fields.
""")
    st.subheader("Models and evaluation protocol")
    st.markdown(f"""
- **Five candidates**, one model per horizon (direct, not recursive): Naive
  (tomorrow = today), ARIMA, Random Forest, Gradient Boosting, and Random
  Forest predicting the price *change*. The fifth joined after an experiment,
  under a rule written before it ran (below).
- **Last {int(config.TEST_FRACTION*100)}% of dates = test**, scored once, after
  selection. Nothing is chosen using it.
- **Selection** inside the earlier period by **rolling-origin cross-validation**:
  {config.CV_FOLDS} expanding folds over its second half; lowest mean fold RMSE
  wins. The rule was fixed before results were seen.
- An **embargo** removes any training row whose target date reaches past a
  boundary.
- Every model is scored on **identical rows**.
""")
    st.subheader("What changed since the first version")
    lb = DATA.get("legacy_best", pd.DataFrame())
    st.markdown("""
The first version reported the lowest-**test**-RMSE model as "best". That is
model selection on the test set, and it produced headlines like "Gradient
Boosting beats Naive by 7.33%". Under the corrected protocol the model chosen
in advance does not beat Naive on Onion/Jaipur at any horizon; Gradient
Boosting's lower 1-day test RMSE only appears if the test set is used to pick
the winner. Two further defects were fixed: ARIMA's training metric
came from a single row (n=1), and 1–3 training rows per horizon had targets
inside the test window. The old results are preserved in `outputs/legacy/`.
""")
    if not lb.empty:
        old = lb[["horizon", "best_model", "best_test_rmse", "improvement_over_naive_pct"]]
        new = best[(best["commodity"] == "Onion") & (best["market"] == "Jaipur")][
            ["horizon", "best_model", "best_test_rmse", "improvement_over_naive_pct"]]
        cmp_ = old.merge(new, on="horizon", suffixes=(" (old: picked on test)",
                                                      " (now: picked by CV)"))
        st.dataframe(cmp_, hide_index=True, use_container_width=True)
        st.caption("Onion/Jaipur only (the first version had no other pair).")
    dcv = DATA.get("delta_cv", pd.DataFrame())
    if not dcv.empty:
        st.markdown("**Experiment: can the tree models be fixed? (decided the 5th candidate)**")
        mm = (dcv.groupby(["commodity", "market", "horizon", "model"])["rmse"]
              .mean().unstack().round(1).reset_index())
        st.dataframe(mm, hide_index=True, use_container_width=True)
        st.caption("Mean CV fold RMSE; test data was never used. '-delta' variants "
                   "predict the price change instead of the level, so they can "
                   "follow a price to a new high. The rule, written before the run: "
                   "a variant joins the candidates only if it beats Naive at one or "
                   "more horizons. Random Forest-delta did on Tomato/Jaipur (1 and 3 "
                   "days) and joined; Gradient Boosting-delta did not anywhere. "
                   "Admitting a candidate on CV makes CV scores slightly optimistic; "
                   "the test window is untouched, so test results are not.")
    sea = DATA.get("seasonal", pd.DataFrame())
    if not sea.empty:
        st.markdown("**Experiment: is a weekly seasonal baseline stronger than Naive?**")
        cvm = (sea[sea["block"].str.startswith("cv")]
               .groupby(["commodity", "market", "horizon", "model"])["rmse"].mean()
               .unstack().round(1).reset_index())
        st.dataframe(cvm, hide_index=True, use_container_width=True)
        st.caption("Mean CV fold RMSE on the rows where both baselines exist. "
                   "'Same weekday last week' is far worse than 'same as today' at "
                   "every horizon, so plain Naive stays the reference baseline.")
    dm_all = DATA.get("dm", pd.DataFrame())
    if not dm_all.empty:
        sq = dm_all[dm_all["loss"] == "squared"]
        ab = dm_all[dm_all["loss"] == "absolute"]
        st.markdown("**Are the test differences statistically detectable?**")
        st.markdown(
            f"Diebold–Mariano tests of every model against Naive on the test "
            f"period, Holm-adjusted within each pair and horizon: under squared "
            f"error, **{int(((sq.p_holm < .05) & (sq.dm_stat < 0)).sum())} of "
            f"{len(sq)}** comparisons favour a model and "
            f"{int(((sq.p_holm < .05) & (sq.dm_stat > 0)).sum())} favour Naive; "
            f"under absolute error, Naive is significantly better in "
            f"**{int(((ab.p_holm < .05) & (ab.dm_stat > 0)).sum())} of {len(ab)}**. "
            f"The other differences are not distinguishable from noise on this "
            f"test window (`scripts/experiment_significance.py`).")
    st.subheader("Limitations")
    st.markdown("""
- **Historical only** (ends April 2015). The *Latest prices* tab is separate
  and only shows data when an official API key is configured.
- Two series from one mandi pass the data gate; Jodhpur and Kota report too
  rarely and are excluded rather than forced.
- Prices only: no arrivals, weather, MSP, festivals or transport costs, which is
  where any real predictive edge would have to come from.
- The 80% uncertainty ranges did not hold up on test, so none are drawn.
- The tree settings (depth, leaf size) were fixed under the first protocol,
  when the test window had already been looked at. A check with scikit-learn's
  default settings instead changes one selection (Tomato, 1 day: ARIMA instead
  of Random Forest-delta); neither beats Naive on test, so no conclusion
  changes (`scripts/experiment_hyperparameter_sensitivity.py`).
- On about 83–85% of reported days the quoted Jaipur price is identical to the
  previous report. That may partly reflect how prices were recorded, not only
  how the market moved, and it is a large part of why Naive is hard to beat.
- Results describe this market and period. They are not a general claim that
  machine learning cannot forecast agricultural prices.
""")
    with st.expander("Reproduce every number on this page"):
        st.code("python scripts/extract_rajasthan.py     # official files -> Rajasthan subset\n"
                "python scripts/build_features.py        # clean + features + Phase 1 gate\n"
                "python scripts/run_pipeline.py --all-pairs   # CV, test, forecast + gate\n"
                "python scripts/experiment_delta_target.py    # optional experiment\n"
                "python scripts/experiment_seasonal_naive.py  # optional experiment\n"
                "python scripts/experiment_significance.py    # optional experiment\n"
                "python scripts/data_report.py           # docs/DATA_REPORT.md\n"
                "python -m pytest                        # tests", language="bash")
    with st.expander("Full data provenance record"):
        st.markdown(provenance_text())

st.markdown(f'<div class="mm-foot">{t["advice"]} · Data: data.gov.in, '
            f'Department of Consumer Affairs, Govt. of India (GODL-India) · '
            f'Historical series ending {_d(last_date)}.</div>', unsafe_allow_html=True)
