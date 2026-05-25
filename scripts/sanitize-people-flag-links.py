#!/usr/bin/env python3
import re
from pathlib import Path

US_STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming",
    "DC": "District of Columbia", "PR": "Puerto Rico", "GU": "Guam", "VI": "United States Virgin Islands",
}


def _country_name_from_code(code: str):
    try:
        import pycountry
        country = pycountry.countries.get(alpha_2=code.upper())
        return country.name if country else None
    except Exception:
        return None


def _normalize_flag_url(url: str) -> str:
    text = str(url or "").strip()
    match_state = re.search(r"https://flagcdn\.com/us-([a-z]{2})[^/]*\.svg", text, flags=re.I)
    if match_state:
        return f"https://flagcdn.com/us-{match_state.group(1).lower()}.svg"

    match_country = re.search(r"https://flagcdn\.com/([a-z]{2})\.svg", text, flags=re.I)
    if match_country:
        return f"https://flagcdn.com/{match_country.group(1).lower()}.svg"

    return text


def _flag_alt_from_url(url: str) -> str:
    normalized = _normalize_flag_url(url)
    match_state = re.search(r"https://flagcdn\.com/us-([a-z]{2})\.svg", normalized, flags=re.I)
    if match_state:
        code = match_state.group(1).upper()
        state_name = US_STATE_NAMES.get(code)
        return f"Flag of {state_name}" if state_name else "US state flag"

    match_country = re.search(r"https://flagcdn\.com/([a-z]{2})\.svg", normalized, flags=re.I)
    if match_country:
        code = match_country.group(1).upper()
        country_name = _country_name_from_code(code)
        return f"Flag of {country_name}" if country_name else f"Flag of {code}"

    return "Flag"


def sanitize_profile(path: Path) -> bool:
    original = path.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)
    out = []
    i = 0
    changed = False

    while i < len(lines):
        line = lines[i]

        if "flagcdn.com" in line and "- text:" in line:
            next_line = lines[i + 1] if i + 1 < len(lines) else ""
            has_url_line = bool(re.match(r"^\s*url:\s*", next_line))

            if has_url_line and re.match(r"^\s*url:\s*None\s*$", next_line):
                changed = True
                i += 2
                continue

            match_url = re.search(r"https://flagcdn\.com/[^)\"]+", line)
            if match_url:
                old_url = match_url.group(0)
                clean_url = _normalize_flag_url(old_url)
                alt_text = _flag_alt_from_url(clean_url)
                line2 = re.sub(
                    r"!\[[^\]]*\]\([^)]*\)\{width=0\.25in\}",
                    f"![{alt_text}]({clean_url}){{width=0.25in}}",
                    line,
                )
                if line2 != line:
                    changed = True
                    line = line2

            out.append(line)
            if has_url_line:
                out.append(next_line)
                i += 2
            else:
                i += 1
            continue

        out.append(line)
        i += 1

    updated = "".join(out)
    if changed and updated != original:
        path.write_text(updated, encoding="utf-8")
        return True
    return False


def main() -> None:
    updated = 0
    checked = 0
    for pattern in ("people/current/*.qmd", "people/alumni/*.qmd"):
        for path in Path(".").glob(pattern):
            checked += 1
            if sanitize_profile(path):
                updated += 1
    print(f"[sanitize-people-flags] checked={checked} updated={updated}")


if __name__ == "__main__":
    main()