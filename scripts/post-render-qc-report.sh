#!/usr/bin/env bash
set -euo pipefail

if [ -z "${QUARTO_PROJECT_INPUT_PATH:-}" ]; then
    quarto render qc_report.qmd
fi
