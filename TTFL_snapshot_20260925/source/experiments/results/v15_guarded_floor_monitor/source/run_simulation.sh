#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")"
exec "${PYTHON_BIN:-python}" experiments/launch_run.py "$@"
