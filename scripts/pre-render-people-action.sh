#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

# Prevent recursive pre-render execution when this script invokes Quarto.
if [[ "${CARD_LAB_SKIP_PEOPLE_ACTION_PRE_RENDER:-}" == "1" || "${CARD_LAB_SKIP_PEOPLE_NOTEBOOKS_PRE_RENDER:-}" == "1" ]]; then
  exit 0
fi

# Resolve the top Quarto render command from this script's process ancestry.
find_quarto_render_command() {
  local pid="$PPID"
  local cmd=""
  local i

  for i in {1..10}; do
    if [[ -z "$pid" || "$pid" -le 1 ]]; then
      break
    fi

    cmd="$(ps -o command= -p "$pid" 2>/dev/null || true)"
    if [[ "$cmd" == *"quarto render"* ]]; then
      echo "$cmd"
      return 0
    fi

    pid="$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d '[:space:]')"
  done

  return 1
}

quarto_render_cmd="$(find_quarto_render_command || true)"
if [[ -n "$quarto_render_cmd" ]]; then
  if [[ "${CARD_LAB_DEBUG_PRE_RENDER_CONTEXT:-}" == "1" ]]; then
    echo "[pre-render][debug] detected quarto command: $quarto_render_cmd"
  fi

  render_tail="${quarto_render_cmd#*quarto render}"
  render_tail="$(echo "$render_tail" | sed 's/^[[:space:]]*//')"
  first_render_arg="${render_tail%% *}"

  # If 'quarto render' has a positional input target, this is a single-file render.
  if [[ -n "$first_render_arg" && "$first_render_arg" != -* ]]; then
    if [[ "${CARD_LAB_DEBUG_PRE_RENDER_CONTEXT:-}" == "1" ]]; then
      echo "[pre-render][debug] single-file render detected via command arg: $first_render_arg"
    fi
    echo "[pre-render] Individual file render detected; skipping people action pre-render"
    exit 0
  fi
fi

SPREADSHEET_PATH="private/CARD Group Timeline.xlsx"
STAMP_PATH=".quarto/people-sheet.sha256"
PRIVATE_PHOTOS_DIR="private/Group Member Photos"
PUBLIC_PHOTOS_DIR="files/photos/People"
NOTEBOOKS=(
  "_people-action.ipynb"
  "people/demographics.ipynb"
  "people/timeline.ipynb"
)
CACHE_KEY_FILES=(
  "_people-action.ipynb"
  "scripts/pre-render-people-action.sh"
)

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

compute_files_hash() {
  local files=("$@")
  if [[ ${#files[@]} -eq 0 ]]; then
    echo "none"
    return
  fi

  local hash_input=""
  local f
  for f in "${files[@]}"; do
    if [[ -f "$f" ]]; then
      hash_input+="$(shasum -a 256 -- "$f")"$'\n'
    else
      hash_input+="$f missing"$'\n'
    fi
  done

  printf '%s' "$hash_input" | shasum -a 256 | awk '{print $1}'
}

current_sheet_hash="$(shasum -a 256 "$SPREADSHEET_PATH" | awk '{print $1}')"
current_photos_hash="$(compute_photos_hash "$PRIVATE_PHOTOS_DIR")"
current_notebooks_hash="$(compute_files_hash "${CACHE_KEY_FILES[@]}")"
previous_sheet_hash=""
previous_photos_hash=""
previous_notebooks_hash=""
if [[ -f "$STAMP_PATH" ]]; then
  previous_sheet_hash="$(sed -n '1p' "$STAMP_PATH")"
  previous_photos_hash="$(sed -n '2p' "$STAMP_PATH")"
  previous_notebooks_hash="$(sed -n '3p' "$STAMP_PATH")"
fi

if [[ "$current_sheet_hash" == "$previous_sheet_hash" && "$current_photos_hash" == "$previous_photos_hash" && "$current_notebooks_hash" == "$previous_notebooks_hash" ]]; then
  echo "[pre-render] People spreadsheet, photos, and notebooks unchanged; skipping people notebooks"
  exit 0
fi

for notebook in "${NOTEBOOKS[@]}"; do
  echo "[pre-render] Executing $notebook"
  CARD_LAB_SKIP_PEOPLE_ACTION_PRE_RENDER=1 CARD_LAB_SKIP_PEOPLE_NOTEBOOKS_PRE_RENDER=1 quarto render "$notebook"
done

mkdir -p "$(dirname "$STAMP_PATH")"
printf '%s\n%s\n%s\n' "$current_sheet_hash" "$current_photos_hash" "$current_notebooks_hash" > "$STAMP_PATH"

# The notebook is executed for its side effects only; keep the site root clean.
rm -f _people-action.html
rm -rf _people-action_files