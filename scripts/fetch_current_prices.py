"""Fetch the latest official mandi prices (data.gov.in / AGMARKNET).

    export DATAGOVIN_API_KEY=...        # free key from a data.gov.in account
    python scripts/fetch_current_prices.py                 # Rajasthan, all commodities
    python scripts/fetch_current_prices.py --commodity Onion --commodity Tomato

Writes data/live/latest.csv ONLY if the download is non-empty and passes
validation; otherwise the previous file is kept and data/live/status.json
records why. The key is never printed or saved. These are observations, not
forecasts, and they are not used by the historical evaluation.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import live_data  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--state", default="Rajasthan")
    ap.add_argument("--commodity", action="append", default=[])
    args = ap.parse_args(argv)
    key = live_data.get_api_key()
    if not key:
        print("No API key. Set DATAGOVIN_API_KEY (free from data.gov.in). "
              "Nothing was changed.")
        return 2
    flist = [{"state": args.state, **({"commodity": c} if c else {})}
             for c in (args.commodity or [None])]
    s = live_data.update_snapshot(key, filters_list=flist)
    _, status = live_data.load_latest()
    print(f"  ok={s.get('ok')}  rows={s.get('rows') if s.get('ok') else 0}  "
          f"error={s.get('error')}")
    fr = status["freshness"]
    print(f"Latest genuine observation: {status.get('latest_observation')} "
          f"({fr['status']}, {fr['age_days']} days old)")
    return 0 if s.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
