"""QR codes for the live app and the repository, each decoded back to verify it.

    python presentation/tools/make_qr.py

Writes presentation/qr_live_app.png and presentation/qr_repository.png and
fails if a code does not decode to exactly its URL.
"""
from pathlib import Path

import cv2
import qrcode

ROOT = Path(__file__).resolve().parents[2]
CODES = {"qr_live_app.png": "https://mandimitra.streamlit.app/",
         "qr_repository.png": "https://github.com/vishnu-keer/mandimitra"}

for name, url in CODES.items():
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,
                       box_size=12, border=3)
    qr.add_data(url)
    qr.make(fit=True)
    path = ROOT / "presentation" / name
    qr.make_image(fill_color="#1d2430", back_color="white").save(path)
    decoded, _, _ = cv2.QRCodeDetector().detectAndDecode(cv2.imread(str(path)))
    assert decoded == url, f"{name}: decoded {decoded!r}, expected {url!r}"
    print(f"OK  {name} -> {decoded}")
