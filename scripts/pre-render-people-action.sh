#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

# Prevent recursive pre-render execution when this script invokes Quarto.
if [[ "${CARD_LAB_SKIP_PEOPLE_ACTION_PRE_RENDER:-}" == "1" || "${CARD_LAB_SKIP_PEOPLE_NOTEBOOKS_PRE_RENDER:-}" == "1" ]]; then
  exit 0
fi

SPREADSHEET_PATH="private/CARD Group Timeline.xlsx"
STAMP_PATH=".quarto/people-sheet.sha256"

current_hash="$(shasum -a 256 "$SPREADSHEET_PATH" | awk '{print $1}')"
previous_hash=""
if [[ -f "$STAMP_PATH" ]]; then
  previous_hash="$(cat "$STAMP_PATH")"
fi

if [[ "$current_hash" == "$previous_hash" ]]; then
  echo "[pre-render] People spreadsheet unchanged; skipping people notebooks"
  exit 0
fi

NOTEBOOKS=(
  "_people-action.ipynb"
  "people/demographics.ipynb"
  "people/timeline.ipynb"
)

for notebook in "${NOTEBOOKS[@]}"; do
  echo "[pre-render] Executing $notebook"
  CARD_LAB_SKIP_PEOPLE_ACTION_PRE_RENDER=1 CARD_LAB_SKIP_PEOPLE_NOTEBOOKS_PRE_RENDER=1 quarto render "$notebook"
done

mkdir -p "$(dirname "$STAMP_PATH")"
printf '%s\n' "$current_hash" > "$STAMP_PATH"

# The notebook is executed for its side effects only; keep the site root clean.
rm -f _people-action.html
rm -rf _people-action_files