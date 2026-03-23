#!/usr/bin/env python3
"""
Patch existing people profile .qmd files to display membership dates with proper labels.

For current member profiles: adds date-format + language override so the Quarto
title block shows "Member since: Jan 2022" instead of "Published: 2022-01-15".

For alumni profiles: adds date-modified (= start date), date-format, and language
overrides so the title block shows:
  Member to:    Jun 2023
  Member from:  Jan 2020

Run from the project root. Safe to re-run — already-patched files are skipped.
"""
import sys
import re
from pathlib import Path
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
SPREADSHEET = PROJECT_ROOT / "private" / "CARD Group Timeline.xlsx"


def to_profile_filename(display_name: str) -> str:
    return f"{str(display_name).replace(' ', '_')}.qmd"


def format_date(value) -> str:
    import pandas as pd
    if pd.isna(value):
        return ""
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def has_fm_field(content: str, field: str) -> bool:
    """Return True if `field:` already exists in the YAML frontmatter."""
    fm_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not fm_match:
        return False
    return bool(re.search(rf"^{re.escape(field)}:", fm_match.group(1), re.MULTILINE))


def inject_after_date_line(content: str, injection: str) -> str:
    """
    Inject extra YAML lines immediately after the bare `date:` line in frontmatter.
    Avoids false matches on `date-format:` or `date-modified:`.
    """
    lines = content.split("\n")
    fm_start = fm_end = -1
    for i, line in enumerate(lines):
        if line.strip() == "---":
            if fm_start == -1:
                fm_start = i
            else:
                fm_end = i
                break

    result = []
    for i, line in enumerate(lines):
        result.append(line)
        if fm_start < i < fm_end and re.match(r"^date:\s", line):
            result.extend(injection.split("\n"))
    return "\n".join(result)


def patch_current(path: Path) -> None:
    content = path.read_text()
    if has_fm_field(content, "date-format"):
        return  # Already patched
    injection = (
        'date-format: "MMM YYYY"\n'
        "language:\n"
        '  title-block-published: "Member since"'
    )
    patched = inject_after_date_line(content, injection)
    path.write_text(patched)
    print(f"  Patched {path.name}")


def patch_alumni(path: Path, start_date: str) -> None:
    content = path.read_text()
    if has_fm_field(content, "date-format"):
        return  # Already patched
    injection = (
        f"date-modified: {start_date}\n"
        'date-format: "MMM YYYY"\n'
        "language:\n"
        '  title-block-published: "Member to"\n'
        '  title-block-modified: "Member from"'
    )
    patched = inject_after_date_line(content, injection)
    path.write_text(patched)
    print(f"  Patched {path.name}")


def main():
    if not SPREADSHEET.exists():
        print(
            f"[patch-profile-dates] Spreadsheet not found at {SPREADSHEET}. Skipping.",
            file=sys.stderr,
        )
        sys.exit(0)

    try:
        import pandas as pd
    except ImportError:
        print("[patch-profile-dates] pandas not available. Skipping.", file=sys.stderr)
        sys.exit(0)

    df = pd.read_excel(SPREADSHEET, sheet_name="People")
    df.drop(0, inplace=True)
    df.reset_index(inplace=True, drop=True)

    finish_series = df["Ultimate Role Finish"]
    finish_text = finish_series.astype(str).str.strip().str.lower()
    current_mask = (
        finish_series.isna()
        | finish_text.isin(["", "nan", "nat"])
        | finish_text.str.contains("current", na=False)
    )

    print("[patch-profile-dates] Patching current member profiles...")
    for _, row in df[current_mask].iterrows():
        path = PROJECT_ROOT / "people" / "current" / to_profile_filename(str(row["Display Name"]).strip())
        if path.exists():
            patch_current(path)

    print("[patch-profile-dates] Patching alumni profiles...")
    for _, row in df[~current_mask].iterrows():
        path = PROJECT_ROOT / "people" / "alumni" / to_profile_filename(str(row["Display Name"]).strip())
        if path.exists():
            start = format_date(row["Ultimate Role Start"])
            if start:
                patch_alumni(path, start)

    print("[patch-profile-dates] Done.")


if __name__ == "__main__":
    main()
