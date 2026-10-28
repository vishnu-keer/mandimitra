"""Convert a .pptx to PDF with LibreOffice (headless).

    python presentation/tools/office_to_pdf.py presentation/MandiMitra_Hackathon_Pitch.pptx
"""
import subprocess
import sys
from pathlib import Path

src = Path(sys.argv[1]).resolve()
subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(src.parent), str(src)],
               check=True, timeout=300)
print("wrote", src.with_suffix(".pdf"))
