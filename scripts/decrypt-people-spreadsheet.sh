#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PLAIN="$ROOT_DIR/private/CARD Group Timeline.xlsx"
ENCRYPTED="$ROOT_DIR/private/CARD Group Timeline.xlsx.gpg"

if [[ ! -f "$ENCRYPTED" ]]; then
  echo "Missing encrypted spreadsheet: $ENCRYPTED" >&2
  exit 1
fi

if [[ -z "${CARD_LAB_PEOPLE_SHEET_PASSPHRASE:-}" ]]; then
  echo "Set CARD_LAB_PEOPLE_SHEET_PASSPHRASE before running." >&2
  exit 1
fi

if ! command -v gpg >/dev/null 2>&1; then
  echo "gpg is not installed. Install with: brew install gnupg" >&2
  exit 1
fi

gpg --batch --yes --decrypt \
  --pinentry-mode loopback --passphrase "$CARD_LAB_PEOPLE_SHEET_PASSPHRASE" \
  --output "$PLAIN" "$ENCRYPTED"

echo "Decrypted spreadsheet written to: $PLAIN"
