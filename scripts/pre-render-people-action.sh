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
PRIVATE_PHOTOS_DIR="private/Group Member Photos"
PUBLIC_PHOTOS_DIR="files/photos/People"

sync_group_member_photos() {
  mkdir -p "$PUBLIC_PHOTOS_DIR"

  if [[ ! -d "$PRIVATE_PHOTOS_DIR" ]]; then
    echo "[pre-render] Group member photo source not found; skipping sync: $PRIVATE_PHOTOS_DIR"
    return
  fi

  shopt -s nullglob
  local copied=0
  for src in "$PRIVATE_PHOTOS_DIR"/*.jpg "$PRIVATE_PHOTOS_DIR"/*.JPG; do
    cp -f "$src" "$PUBLIC_PHOTOS_DIR/"
    copied=$((copied + 1))
  done
  shopt -u nullglob

  echo "[pre-render] Synced $copied group member photo(s) to $PUBLIC_PHOTOS_DIR"
}

sync_group_member_photos

compute_photos_hash() {
  local dir="$1"
  if [[ ! -d "$dir" ]]; then
    echo "none"
    return
  fi
  find "$dir" -type f | sort | while IFS= read -r f; do
    shasum -a 256 -- "$f"
  done | shasum -a 256 | awk '{print $1}'
}

current_sheet_hash="$(shasum -a 256 "$SPREADSHEET_PATH" | awk '{print $1}')"
current_photos_hash="$(compute_photos_hash "$PRIVATE_PHOTOS_DIR")"
previous_sheet_hash=""
previous_photos_hash=""
if [[ -f "$STAMP_PATH" ]]; then
  previous_sheet_hash="$(sed -n '1p' "$STAMP_PATH")"
  previous_photos_hash="$(sed -n '2p' "$STAMP_PATH")"
fi

if [[ "$current_sheet_hash" == "$previous_sheet_hash" && "$current_photos_hash" == "$previous_photos_hash" ]]; then
  echo "[pre-render] People spreadsheet and photos unchanged; skipping people notebooks"
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
printf '%s\n%s\n' "$current_sheet_hash" "$current_photos_hash" > "$STAMP_PATH"

# The notebook is executed for its side effects only; keep the site root clean.
rm -f _people-action.html
rm -rf _people-action_files