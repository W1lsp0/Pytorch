#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
build_dir=$(mktemp -d "${TMPDIR:-/tmp}/ispa-submission.XXXXXX")
trap 'rm -rf -- "$build_dir"' EXIT
export TEXINPUTS="$PWD/Template//:${TEXINPUTS:-}:"
cp ispa2026_references.bib "$build_dir/"
cp Template/IEEEtran.bst "$build_dir/"
pdflatex -interaction=nonstopmode -halt-on-error -output-directory="$build_dir" ispa2026_submission.tex
(cd "$build_dir" && BIBINPUTS=. bibtex ispa2026_submission)
pdflatex -interaction=nonstopmode -halt-on-error -output-directory="$build_dir" ispa2026_submission.tex
pdflatex -interaction=nonstopmode -halt-on-error -output-directory="$build_dir" ispa2026_submission.tex
cp "$build_dir/ispa2026_submission.pdf" ./ispa2026_submission.pdf
