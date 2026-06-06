#!/usr/bin/env bash
set -euo pipefail

# Walk the process tree looking for a 'quarto render <file>' invocation.
# Quarto does not reliably set QUARTO_PROJECT_INPUT_PATH in post-render hooks
# for subprocess renders, so we use process-tree inspection (matching the
# fallback logic in qc_check.py / post-render-generate-sitemap.py).
_parent_is_single_file_render() {
    local pid=$PPID
    for _ in 1 2 3 4 5 6 7 8 9 10 11 12; do
        [[ "$pid" -le 1 ]] && return 1
        local cmd
        cmd=$(ps -o command= -p "$pid" 2>/dev/null || true)
        [[ -z "$cmd" ]] && return 1

        if [[ "$cmd" == *"quarto render"* ]]; then
            # Extract the first token after 'quarto render '
            local remainder first_arg
            remainder="${cmd#*quarto render }"
            first_arg="${remainder%% *}"
            # Non-empty and not a flag → single-file render
            [[ -n "$first_arg" && "$first_arg" != -* ]] && return 0
            return 1
        fi

        local ppid
        ppid=$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d '[:space:]' || true)
        [[ -z "$ppid" || "$ppid" == "0" ]] && return 1
        pid=$ppid
    done
    return 1
}

if [[ -n "${QUARTO_PROJECT_INPUT_PATH:-}" ]] || _parent_is_single_file_render; then
    echo "[post-render] Individual file render detected; skipping qc_report render"
    exit 0
fi

quarto render qc_report.qmd
