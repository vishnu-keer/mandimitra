"""Crop the real dashboard screenshots to the frames the deck and poster use.

    python presentation/tools/crop_shots.py
"""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SRC, DST = ROOT / "docs" / "screenshots", ROOT / "presentation" / "assets"
DST.mkdir(parents=True, exist_ok=True)
# name: (source file, top y in px at 1366 wide, aspect w/h)
CROPS = {
    "overview.png": ("01-overview.png", 60, 6.6 / 4.9),
    "history.png": ("02-price-history.png", 440, 5.9 / 2.27),
    "evaluation.png": ("04-model-evaluation.png", 440, 5.9 / 2.27),
    "forecast.png": ("05-forecast.png", 440, 5.9 / 2.27),
    "hindi.png": ("09-overview-hindi.png", 60, 5.9 / 2.27),
    "poster_overview.png": ("01-overview.png", 60, 1.25),
}
for out, (src, top, aspect) in CROPS.items():
    im = Image.open(SRC / src).convert("RGB")
    w = im.width
    h = round(w / aspect)
    im.crop((0, top, w, min(im.height, top + h))).save(DST / out, optimize=True)
    print("wrote", out)
