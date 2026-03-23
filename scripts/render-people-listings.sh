#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

CARD_LAB_SKIP_PEOPLE_ACTION_PRE_RENDER=1 quarto render _people-action.ipynb
CARD_LAB_SKIP_PEOPLE_ACTION_PRE_RENDER=1 quarto render people/current.qmd
CARD_LAB_SKIP_PEOPLE_ACTION_PRE_RENDER=1 quarto render people/alumni.qmd

echo "Rendered people listing pages: people/current.qmd and people/alumni.qmd"
