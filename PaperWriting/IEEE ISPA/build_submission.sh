#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p .build
cp ispa2026_references.bib .build/
cp Template/IEEEtran.bst .build/
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=.build ispa2026_submission.tex
(cd .build && BIBINPUTS=. bibtex ispa2026_submission)
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=.build ispa2026_submission.tex
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=.build ispa2026_submission.tex
cp .build/ispa2026_submission.pdf ./ispa2026_submission.pdf
