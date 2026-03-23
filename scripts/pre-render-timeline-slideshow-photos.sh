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

rsync -a --delete "$PRIVATE_TIMELINE_PHOTOS_DIR/" "$PUBLIC_TIMELINE_PHOTOS_DIR/"

photo_count="$(find "$PUBLIC_TIMELINE_PHOTOS_DIR" -type f | wc -l | tr -d ' ')"
echo "[pre-render] Synced $photo_count timeline slideshow photo(s) to $PUBLIC_TIMELINE_PHOTOS_DIR"