#!/usr/bin/env python3
"""
Recycle stale profile .qmd files from people/current/ and people/alumni/.

Reads the people spreadsheet to determine the expected set of profile filenames,
then sends any .qmd files that no longer have a corresponding data row to the
system Trash / Recycle Bin via send2trash.

Run from the project root, or as a Quarto pre-render script.
Exits cleanly (code 0) if the spreadsheet is not available.
"""
import sys
from pathlib import Path

# Work relative to the project root, regardless of where the script is invoked.
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
SPREADSHEET = PROJECT_ROOT / "private" / "CARD Group Timeline.xlsx"


def to_profile_filename(display_name: str) -> str:
    return f"{str(display_name).replace(' ', '_')}.qmd"


def recycle_stale(category: str, expected_files: set, send2trash_fn) -> list:
    from pathlib import Path
    base_dir = PROJECT_ROOT / "people" / category
    base_dir.mkdir(parents=True, exist_ok=True)

    recycled = []
    for profile_file in sorted(base_dir.glob("*.qmd")):
        if profile_file.name not in expected_files:
            send2trash_fn(str(profile_file))
            recycled.append(profile_file.name)

    if recycled:
        print(f"  Trashed {len(recycled)} stale {category} profile(s): {', '.join(recycled)}")
    else:
        print(f"  No stale {category} profiles found.")

    return recycled


def main():
    if not SPREADSHEET.exists():
        print(
            f"[recycle-stale-people] Spreadsheet not found at {SPREADSHEET}. "
            "Skipping stale profile cleanup.",
            file=sys.stderr,
        )
        sys.exit(0)

    import warnings
    warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

    try:
        import pandas as pd
    except ImportError:
        print(
            "[recycle-stale-people] pandas is not available. Skipping stale profile cleanup.",
            file=sys.stderr,
        )
        sys.exit(0)

    try:
        from send2trash import send2trash
    except ImportError:
        print(
            "[recycle-stale-people] send2trash is not available "
            "(install: conda install send2trash). Skipping stale profile cleanup.",
            file=sys.stderr,
        )
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
    alumni_mask = ~current_mask

    expected_current = {
        to_profile_filename(name)
        for name in df.loc[current_mask, "Display Name"].dropna().tolist()
    }
    expected_alumni = {
        to_profile_filename(name)
        for name in df.loc[alumni_mask, "Display Name"].dropna().tolist()
    }

    print("[recycle-stale-people] Checking for stale profile files...")
    recycled_current = recycle_stale("current", expected_current, send2trash)
    recycled_alumni = recycle_stale("alumni", expected_alumni, send2trash)
    total = len(recycled_current) + len(recycled_alumni)
    print(f"[recycle-stale-people] Done. Total recycled: {total}")


if __name__ == "__main__":
    main()
