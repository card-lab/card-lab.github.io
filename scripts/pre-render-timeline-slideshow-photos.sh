#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

PRIVATE_TIMELINE_PHOTOS_DIR="private/Timeline Slideshow Photos"
PUBLIC_TIMELINE_PHOTOS_DIR="files/photos/Timeline Slideshow Photos"

mkdir -p "$PUBLIC_TIMELINE_PHOTOS_DIR"

if [[ ! -d "$PRIVATE_TIMELINE_PHOTOS_DIR" ]]; then
  echo "[pre-render] Timeline slideshow photo source not found; skipping sync: $PRIVATE_TIMELINE_PHOTOS_DIR"
  exit 0
fi

# The slideshow (files/Research_Group_Timeline_Slideshow.qmd) makes the public
# copies: downsampled, captioned, and without GPS. Copying the originals here
# would replace those with full-size, uncaptioned files on any render that
# skips the slideshow, so only remove copies whose original was deleted.
removed=0
while IFS= read -r -d '' public_path; do
  rel_path="${public_path#"$PUBLIC_TIMELINE_PHOTOS_DIR"/}"
  if [[ ! -e "$PRIVATE_TIMELINE_PHOTOS_DIR/$rel_path" ]]; then
    rm -f "$public_path"
    removed=$((removed + 1))
  fi
done < <(find "$PUBLIC_TIMELINE_PHOTOS_DIR" -type f ! -name '.DS_Store' -print0)

photo_count="$(find "$PUBLIC_TIMELINE_PHOTOS_DIR" -type f ! -name '.DS_Store' | wc -l | tr -d ' ')"
echo "[pre-render] Timeline slideshow photos: $photo_count in $PUBLIC_TIMELINE_PHOTOS_DIR ($removed removed; the slideshow render adds and updates them)"