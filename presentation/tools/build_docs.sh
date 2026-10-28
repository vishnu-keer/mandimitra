#!/usr/bin/env bash
# Rebuild figures, the paper PDF, the report PDF, the deck and the poster.
# Run from the repository root inside the documentation environment
# (pip install -r presentation/requirements-docs.txt), with Node + Playwright
# (deck: pptxgenjs) and LibreOffice available.
set -euo pipefail
python presentation/tools/make_figures.py
python presentation/tools/make_qr.py
md2pdf () {   # $1 = markdown file, $2 = pdf out
  local dir; dir=$(dirname "$1")
  pandoc "$1" -f markdown+tex_math_single_backslash -t html5 --standalone --mathml \
    --css "$(realpath --relative-to="$dir" presentation/tools/paper.css)" \
    --metadata pagetitle="MandiMitra" -o "$dir/_build.html"
  node presentation/tools/html_to_pdf.js "$dir/_build.html" "$2"
  rm -f "$dir/_build.html"
}
md2pdf research/MANDIMITRA_RESEARCH_PAPER.md research/MANDIMITRA_RESEARCH_PAPER.pdf
md2pdf docs/FINAL_TECHNICAL_REPORT.md docs/FINAL_TECHNICAL_REPORT.pdf
node presentation/tools/build_deck.js
python presentation/tools/office_to_pdf.py presentation/MandiMitra_Hackathon_Pitch.pptx
node presentation/tools/html_to_pdf.js presentation/poster.html presentation/MandiMitra_Poster.pdf poster
echo "built"
