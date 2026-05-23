#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

sync_dir() {
  local src="$1"
  local dst="$2"

  if [[ ! -d "$src" ]]; then
    echo "[post-render] Asset source not found; skipping sync: $src"
    return 0
  fi

  mkdir -p "$dst"
  rsync -a --delete "$src/" "$dst/"

  local count
  count="$(find "$dst" -type f | wc -l | tr -d ' ')"
  echo "[post-render] Synced $count asset(s) from $src to $dst"
}

sync_dir "files/photos/People" "docs/files/photos/People"
sync_dir "files/photos/Timeline Slideshow Photos" "docs/files/photos/Timeline Slideshow Photos"