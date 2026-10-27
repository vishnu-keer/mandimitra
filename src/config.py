"""Single source of truth for paths and pipeline parameters.

Nothing secret lives here, so the project needs no .env file at all.
Every tunable the pipeline uses is in this file, in plain Python.
"""
from pathlib import Path

# ---------------------------------------------------------------- paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_INTERIM = PROJECT_ROOT / "data" / "interim"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
OUTPUTS = PROJECT_ROOT / "outputs"
MODELS_STORE = PROJECT_ROOT / "models_store"
DOCS = PROJECT_ROOT / "docs"

# Untouched official downloads. NOT read by the loader (which only reads files
# directly inside data/raw/); scripts/extract_rajasthan.py derives the subset.
DATA_RAW_SOURCE = DATA_RAW / "source"
RAW_SUBSET_PATH = DATA_RAW / "datagovin_daily_wholesale_rajasthan.csv"

CLEAN_PATH = DATA_INTERIM / "clean.parquet"
FEATURES_PATH = DATA_PROCESSED / "features.parquet"

for _p in (DATA_RAW, DATA_INTERIM, DATA_PROCESSED, OUTPUTS, MODELS_STORE, DOCS):
    _p.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- scope
TARGET_COMMODITIES = ["Onion", "Tomato"]

# Rajasthan centres present in the official data.gov.in daily wholesale files
# (verified 2026-10-27 against the national files' 73 centres). The original
# plan named Chomu and Bassi; neither appears in this source, so they are not
# listed. The data-coverage gate then decides which of these are usable -- a
# market without enough real history is reported and dropped, never forced.
RAW_CENTRES = ["JAIPUR", "JODHPUR", "KOTA"]
PREFERRED_MARKETS = ["Jaipur", "Jodhpur", "Kota"]

# ------------------------------------------------------ canonical columns
PRICE_COL = "modal_price"
GROUP_KEYS = ["commodity", "market"]

# -------------------------------------------------- cleaning parameters
# Prices are Rs./quintal. Anything outside this band is a data error,
# not a market event.
MIN_PRICE = 50.0
MAX_PRICE = 100_000.0

# Mandis do not trade every day. We reindex each series to a continuous
# daily calendar and carry the last *observed* price forward for at most
# this many days. Forward-fill only ever looks backwards in time, so it
# cannot leak. Gaps longer than this stay NaN and those rows are dropped.
#
# Set to 2 deliberately, measured on Jaipur/Onion 2009-2015 (usable = rows
# with a complete feature vector AND a genuinely reported h=1 target):
#
#   ffill=1 -> 894 rows, 30.8% carried forward,  391 usable   <- too thin
#   ffill=2 -> 1666 rows, 35.3% carried forward, 1002 usable  <- chosen
#   ffill=3 -> 1892 rows, 37.8% carried forward, 1145 usable
#
# 2 days spans a weekend closure, which is defensible. 3 days starts spanning
# real holidays for a marginal gain. Target quality is protected separately by
# the y_h{h}_observed mask, so every scored row has a real reported target.
MAX_FFILL_DAYS = 2

# --------------------------------------------- feature-engineering knobs
LAGS = [1, 3, 7]
MA_WINDOWS = [3, 7]
VOL_WINDOW = 7

# Rolling windows are measured in CALENDAR days, but a mandi does not trade
# every calendar day (it closes weekly, plus holidays). Demanding 7 consecutive
# reported days makes a 7-day window nearly unsatisfiable -- it dropped the
# Jaipur/Onion series from 1,288 usable rows to 211.
#
# So a window of w days requires at least ceil(w * this) reported prices inside
# it, not all w. This is the ordinary convention for a "7-day average" on a
# market that trades ~5-6 days a week, and it is stated in the methodology.
# Windows that fall below the threshold stay NaN and those rows are dropped.
ROLLING_MIN_PERIODS_FRAC = 0.6

# Direct multi-horizon targets: one model per horizon, target = price at t+h.
# No prediction is ever fed back in as an input, so the recursive-forecast
# leakage bug cannot exist in this design.
HORIZONS = [1, 2, 3]

# ------------------------------------------------------------- the gate
# Rows with a complete feature vector AND an observed (not carried-forward)
# h=1 target, per (commodity, market) pair. Scoring against an imputed target
# is scoring against a number the market never printed.
MIN_ROWS_PER_PAIR = 400

# ------------------------------------------------- evaluation protocol
# Development block (everything before the test cutoff) and a final test
# block, by distinct date. Selection happens INSIDE development, by
# rolling-origin cross-validation; test is scored once, afterwards.
#
#   |------------------ development 80% ------------------|-- test 20% --|
#   |--- initial 50% ---|-f1-|-f2-|-f3-|-f4-|
#                         each fold: fit on everything before its origin,
#                         score on the fold, embargoed at the origin.
#
# Why rolling origin and not one validation block: the first version of this
# protocol used a single 20% validation block, which on Onion/Jaipur fell
# squarely on the October 2013 price spike (Rs.4,500/q against a training
# maximum of Rs.3,300). One year then decided everything. Several folds spread
# across the whole development period stop a single regime from choosing the
# model on its own.
#
# The selection rule was fixed BEFORE the cross-validation results were seen:
#   lowest MEAN per-fold RMSE (each fold weighted equally)
# Pooled RMSE was rejected for the same reason as the single block -- squared
# errors from one spike fold would dominate it.
#
# Before 2026-10-27 the project reported the lowest-TEST-RMSE model, which is
# selection on the test set. Those results are preserved in outputs/legacy/.
TEST_FRACTION = 0.2
CV_FOLDS = 4
CV_INITIAL_FRACTION = 0.5

# Retained for src/splits.py::split_train_valid_test (a tested utility); the
# pipeline itself selects by rolling-origin CV, above.
VALID_FRACTION = 0.2

# ARIMA in-sample diagnostic: how many observations to estimate the initial
# filter state from before the walk-forward begins. Earlier training dates get
# no diagnostic value and are reported as such rather than filled in.
ARIMA_INSAMPLE_BURN_IN = 60

# ------------------------------------------- manual name normalisation
# Populated after running scripts/inspect_data.py, if that report shows the
# same market or commodity spelled more than one way in the raw download.
# Keys and values are compared AFTER whitespace collapsing and title-casing.
NAME_OVERRIDES = {
    "commodity": {
        # "Onion (Big)": "Onion",
    },
    "market": {
        # "Jaipur (F&V)": "Jaipur",
    },
}
