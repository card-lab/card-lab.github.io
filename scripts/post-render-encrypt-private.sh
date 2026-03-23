#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PLAIN="$ROOT_DIR/private/CARD Group Timeline.xlsx"
ENCRYPTED="$ROOT_DIR/private/CARD Group Timeline.xlsx.gpg"
ENCRYPT_SCRIPT="$ROOT_DIR/scripts/encrypt-people-spreadsheet.sh"

if [[ ! -f "$PLAIN" ]]; then
  echo "[post-render] Skipping spreadsheet encryption: missing $PLAIN"
  exit 0
fi

if [[ -z "${CARD_LAB_PEOPLE_SHEET_PASSPHRASE:-}" ]]; then
  echo "[post-render] Skipping spreadsheet encryption: CARD_LAB_PEOPLE_SHEET_PASSPHRASE is not set"
  exit 0
fi

if [[ ! -x "$ENCRYPT_SCRIPT" ]]; then
  echo "[post-render] Skipping spreadsheet encryption: script is not executable: $ENCRYPT_SCRIPT"
  exit 0
fi

if ! command -v gpg >/dev/null 2>&1; then
  echo "[post-render] Skipping spreadsheet encryption: gpg is not installed (macOS: brew install gnupg)"
  exit 0
fi

if ! "$ENCRYPT_SCRIPT" >/dev/null; then
  echo "[post-render] Skipping spreadsheet encryption: encryption script returned an error"
  exit 0
fi

echo "[post-render] Updated encrypted spreadsheet: $ENCRYPTED"
