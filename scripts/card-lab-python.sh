#!/usr/bin/env bash
# Run Python from the card-lab conda env, whichever env is first on PATH.
#
# Neither `python3` nor `conda run -n card-lab python` is reliable for this: both
# resolve to whatever env is first on PATH (e.g. the interpreter VS Code
# activates for its terminal), which may lack this project's packages, such as
# pycountry for the flag alt text.
#
# Usage: scripts/card-lab-python.sh <script.py | -c code> [args...]
# Set CARD_LAB_PYTHON to override the interpreter.
set -euo pipefail

python_bin="${CARD_LAB_PYTHON:-}"

if [[ -z "$python_bin" ]] && command -v conda >/dev/null 2>&1; then
  env_dir="$(conda env list --json 2>/dev/null | grep -o '"[^"]*/card-lab"' | tr -d '"' | head -n 1 || true)"
  if [[ -n "$env_dir" && -x "$env_dir/bin/python" ]]; then
    python_bin="$env_dir/bin/python"
  fi
fi

# Without conda (or the env), fall back to the PATH; CI puts card-lab's bin first.
if [[ -z "$python_bin" ]]; then
  python_bin="$(command -v python3 || command -v python || true)"
fi

if [[ -z "$python_bin" ]]; then
  echo "[card-lab-python] No Python interpreter found" >&2
  exit 1
fi

exec "$python_bin" "$@"
