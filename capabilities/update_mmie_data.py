#!/usr/bin/env python3
"""
update_mmie_data.py
===================
Run this script once or twice a year (before re-rendering the site) to
refresh the statistics and highlights in `_mmie_data.yml`.

Requirements
------------
    pip install anthropic requests beautifulsoup4 pyyaml

Usage
-----
    export ANTHROPIC_API_KEY="sk-ant-..."
    python update_mmie_data.py

The script will:
  1. Fetch content from the key UC / CEAS / MMIE pages.
  2. Send the scraped text to Claude with a prompt asking it to extract
     up-to-date facts in YAML format matching the _mmie_data.yml schema.
  3. Write the result back to `_mmie_data.yml`.
  4. Print a diff summary so you can sanity-check the changes.
"""

import os
import sys
import json
import datetime
import re
import pathlib

import yaml
import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# 1. Pages to scrape
# ---------------------------------------------------------------------------

PAGES = [
    # UC-level facts
    "https://www.uc.edu/about/factsheet.html",
    "https://research.uc.edu/facts-figures",
    # CEAS
    "https://www.ceas.uc.edu/about.html",
    "https://www.ceas.uc.edu/research.html",
    "https://www.ceas.uc.edu/about/deans-report2025/community-impact.html",
    # MMIE department
    "https://www.ceas.uc.edu/academics/departments/mechanical-materials-engineering.html",
    "https://www.ceas.uc.edu/academics/departments/mechanical-materials-engineering/research.html",
    "https://www.ceas.uc.edu/academics/departments/mechanical-materials-engineering/materials-science-and-engineering/research.html",
    "https://www.ceas.uc.edu/academics/departments/mechanical-materials-engineering/degrees-programs.html",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; UC-MMIE-PageUpdater/1.0; "
        "+https://ceas.uc.edu)"
    )
}


def scrape_text(url: str, max_chars: int = 4000) -> str:
    """Fetch a URL and return a plain-text excerpt."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        # Remove nav, footer, scripts, styles
        for tag in soup(["nav", "footer", "script", "style", "header"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        # Collapse whitespace
        text = re.sub(r"\s{2,}", " ", text)
        return text[:max_chars]
    except Exception as exc:
        print(f"  [warn] Could not fetch {url}: {exc}")
        return ""


# ---------------------------------------------------------------------------
# 2. Build the prompt
# ---------------------------------------------------------------------------

SCHEMA_EXAMPLE = """
last_updated: "Month YYYY"

uc_facts:
  founded: "1819"
  enrollment: "~53,000"
  research_expenditure: "$XXX million"
  nsf_rank_public: "Nth among public universities"
  coop_rank: "Top N (U.S. News & World Report)"
  student_coop_earnings: "$XX million/year"
  carnegie_class: "R1 — Very High Research Activity"

ceas_facts:
  undergrad_enrollment: "~X,XXX"
  grad_enrollment: "~X,XXX"
  annual_grants: "$XX+ million"
  coop_founded: "1906"

mmie_facts:
  research_centers: "N"
  degree_programs: "N"
  research_areas_count: "N+"

highlights:
  - "Fact one"
  - "Fact two"
  # ... (6–10 short, factual bullet-points about UC/CEAS/MMIE)

research_areas:
  - "Area One"
  # ... (list of 10–14 active research themes in MMIE)

degree_list:
  - "B.S. Mechanical Engineering"
  # ... (all current degree offerings)

industry_partners:
  - "GE Aerospace"
  # ... (notable industrial research partners / sponsors)
"""


def build_prompt(scraped: str) -> str:
    today = datetime.date.today().strftime("%B %Y")
    return f"""You are a research assistant helping maintain a Quarto-based
academic web page for the University of Cincinnati Department of Mechanical,
Materials, and Industrial Engineering (MMIE) in the College of Engineering
and Applied Science (CEAS).

Today's date is {today}.

Below is raw text scraped from the UC / CEAS / MMIE websites.  Using only
information present in this text (do not invent numbers), produce an updated
YAML document that matches the schema shown.  Where you cannot find a current
value, keep the previous value from the schema example.  Return ONLY valid
YAML — no markdown fences, no prose before or after.

--- SCRAPED TEXT (may be truncated) ---
{scraped}

--- TARGET YAML SCHEMA ---
{SCHEMA_EXAMPLE}
"""


# ---------------------------------------------------------------------------
# 3. Call Claude
# ---------------------------------------------------------------------------

def call_claude(prompt: str) -> str:
    try:
        import anthropic
    except ImportError:
        sys.exit(
            "ERROR: 'anthropic' package not installed.  "
            "Run:  pip install anthropic"
        )

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit(
            "ERROR: ANTHROPIC_API_KEY environment variable not set.\n"
            "       Export it before running this script."
        )

    client = anthropic.Anthropic(api_key=api_key)

    print("  Calling Claude claude-sonnet-4-20250514 …")
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


# ---------------------------------------------------------------------------
# 4. Main
# ---------------------------------------------------------------------------

def main():
    print("=== MMIE data updater ===")

    # --- scrape ---
    all_text_parts = []
    for url in PAGES:
        print(f"  Fetching {url} …")
        chunk = scrape_text(url)
        if chunk:
            all_text_parts.append(f"[SOURCE: {url}]\n{chunk}")

    combined = "\n\n".join(all_text_parts)
    print(f"  Scraped ~{len(combined):,} characters total.")

    # --- prompt Claude ---
    prompt = build_prompt(combined)
    raw_yaml = call_claude(prompt)

    # --- validate YAML ---
    try:
        new_data = yaml.safe_load(raw_yaml)
    except yaml.YAMLError as e:
        print(f"ERROR: Claude returned invalid YAML:\n{e}")
        print("--- Raw response ---")
        print(raw_yaml)
        sys.exit(1)

    if not isinstance(new_data, dict):
        print("ERROR: Parsed YAML is not a dict.  Aborting.")
        sys.exit(1)

    # Ensure last_updated is stamped
    new_data["last_updated"] = datetime.date.today().strftime("%B %Y")

    # --- write ---
    out_path = pathlib.Path(__file__).parent / "_mmie_data.yml"
    header = (
        "# _mmie_data.yml  —  auto-generated by update_mmie_data.py\n"
        f"# Last run: {datetime.datetime.now().isoformat(timespec='seconds')}\n"
        "# Edit manually OR re-run:  python update_mmie_data.py\n\n"
    )
    with open(out_path, "w") as f:
        f.write(header)
        yaml.dump(new_data, f, allow_unicode=True, sort_keys=False)

    print(f"\n✓ Wrote updated data to {out_path}")
    print("  Re-render the site with:  quarto render uc_mmie_overview.qmd")


if __name__ == "__main__":
    main()
