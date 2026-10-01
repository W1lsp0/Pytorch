#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
export TEXINPUTS="./Template:${TEXINPUTS:-}"
export BIBINPUTS=".:${BIBINPUTS:-}"
latexmk -pdf -interaction=nonstopmode -halt-on-error \
  -outdir=.build-revised ispa2026_submission_revised.tex
cp .build-revised/ispa2026_submission_revised.pdf ispa2026_submission_revised.pdf
