#!/usr/bin/env python3
"""Update publication sections for people profile pages.

This script updates only these sections in each profile file:
- # Thesis/Dissertation
- # Publications
- # Presentations
- # Contributions
- # Code & Datasets

It does not require the private spreadsheet. It prefers the per-profile
authorship comment written by _people-action.ipynb:
<!-- card-lab-authorship-name: ... -->
"""

from __future__ import annotations

import html
import json
import re
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup, NavigableString


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ZOTERO_GROUP_ID = "5985739"
LOCAL_ZOTERO_ITEMS_PATH = PROJECT_ROOT / "files" / "zotero-items.json"
CITATION_FORMAT = "ieee"

PROFILE_GLOBS = ("people/current/*.qmd", "people/alumni/*.qmd")
TARGET_HEADINGS = (
    "Thesis/Dissertation",
    "Publications",
    "Presentations",
    "Contributions",
    "Code & Datasets",
)

_LOCAL_ZOTERO_ITEMS_CACHE = None


def load_local_zotero_items(path: Path = LOCAL_ZOTERO_ITEMS_PATH) -> list[dict]:
    global _LOCAL_ZOTERO_ITEMS_CACHE
    if _LOCAL_ZOTERO_ITEMS_CACHE is not None:
        return _LOCAL_ZOTERO_ITEMS_CACHE

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            _LOCAL_ZOTERO_ITEMS_CACHE = data
            return _LOCAL_ZOTERO_ITEMS_CACHE
    except Exception as exc:
        print(f"Warning: failed to load local Zotero items from {path}: {exc}")

    _LOCAL_ZOTERO_ITEMS_CACHE = []
    return _LOCAL_ZOTERO_ITEMS_CACHE


def matches_author(creators: list[dict], search_last: str, search_initials: str) -> bool:
    for creator in creators:
        last = str(creator.get("lastName", "")).lower()
        first = str(creator.get("firstName", "")).lower()
        if not first:
            continue

        first_initials = "".join(part[0] for part in first.split() if part)
        if last == search_last.lower() and first_initials.upper().startswith(search_initials.upper()):
            return True
    return False


def get_zotero_items_by_author_and_type(author_name: str, allowed_types: list[str]) -> list[dict]:
    search_initials = ""
    try:
        search_last, search_initials = author_name.split(",", 1)
        search_last = search_last.strip()
        search_initials = search_initials.strip()
    except Exception:
        search_last = author_name.strip()

    local_items = load_local_zotero_items()
    items = []
    if local_items:
        for item in local_items:
            creator_summary = str(item.get("meta", {}).get("creatorSummary", "")).lower()
            title = str(item.get("data", {}).get("title", "")).lower()
            creators = item.get("data", {}).get("creators", [])
            has_last = search_last.lower() in creator_summary or search_last.lower() in title
            if not has_last:
                has_last = any(search_last.lower() in str(c.get("lastName", "")).lower() for c in creators)
            if has_last:
                items.append(item)

    filtered_items = []
    for item in items:
        data = item.get("data", {})
        item_type = data.get("itemType", "")
        creators = data.get("creators", [])

        if item_type not in allowed_types:
            continue

        if search_initials:
            if matches_author(creators, search_last, search_initials):
                filtered_items.append(item)
        else:
            if any(search_last.lower() in str(c.get("lastName", "")).lower() for c in creators):
                filtered_items.append(item)

    return filtered_items


def get_formatted_citations(item_keys: list[str], style: str) -> str:
    if not item_keys:
        return ""

    keys_csv = ",".join(item_keys)
    url = f"https://api.zotero.org/groups/{ZOTERO_GROUP_ID}/items"
    headers = {"Accept": "text/html"}
    params = {
        "itemKey": keys_csv,
        "format": "bib",
        "style": style,
        "sort": "date",
        "direction": "desc",
    }

    response = requests.get(url, headers=headers, params=params, timeout=60)
    if response.status_code != 200:
        fallback_params = {"itemKey": keys_csv, "format": "bib", "style": style}
        response = requests.get(url, headers=headers, params=fallback_params, timeout=60)

    if response.status_code != 200:
        return ""

    month_map = {
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }

    def entry_sort_key(entry_text: str) -> tuple[int, int, int]:
        iso_match = re.search(r"(19|20)\d{2}-(\d{2})-(\d{2})", entry_text)
        if iso_match:
            return (int(iso_match.group(0)[0:4]), int(iso_match.group(2)), int(iso_match.group(3)))

        month_year_match = re.search(
            r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+((?:19|20)\d{2})",
            entry_text,
            re.IGNORECASE,
        )
        if month_year_match:
            return (int(month_year_match.group(2)), month_map[month_year_match.group(1).lower()], 0)

        year_match = re.search(r"(19|20)\d{2}", entry_text)
        if year_match:
            return (int(year_match.group(0)), 0, 0)

        return (0, 0, 0)

    soup = BeautifulSoup(response.text, "html.parser")
    bib_body = soup.select_one("div.csl-bib-body")
    if bib_body is None:
        return response.text

    entries = bib_body.find_all("div", class_="csl-entry", recursive=False)
    total_entries = len(entries)
    if total_entries == 0:
        return response.text

    doi_pattern = re.compile(r"(10\.\d{4,9}/[-._;()/:A-Z0-9]+)", re.IGNORECASE)
    url_pattern = re.compile(r"(https?://[^\s<>\"]+)", re.IGNORECASE)
    online_available_pattern = re.compile(r"\[Online\]\.\s*Available:\s*", re.IGNORECASE)

    def linkify_doi_text(entry) -> None:
        for text_node in list(entry.find_all(string=True)):
            parent_name = getattr(text_node.parent, "name", None)
            if parent_name in {"a", "script", "style"}:
                continue

            text = str(text_node)
            if "10." not in text:
                continue

            matches = list(doi_pattern.finditer(text))
            if not matches:
                continue

            last_index = 0
            replacement_nodes = []
            for match in matches:
                start, end = match.span(1)
                if start > last_index:
                    replacement_nodes.append(NavigableString(text[last_index:start]))

                doi = match.group(1)
                link = BeautifulSoup("", "html.parser").new_tag("a", href=f"https://doi.org/{doi}")
                link.string = doi
                replacement_nodes.append(link)
                last_index = end

            if last_index < len(text):
                replacement_nodes.append(NavigableString(text[last_index:]))

            for replacement_node in reversed(replacement_nodes):
                text_node.insert_after(replacement_node)
            text_node.extract()

    def linkify_url_text(entry) -> None:
        for text_node in list(entry.find_all(string=True)):
            parent_name = getattr(text_node.parent, "name", None)
            if parent_name in {"a", "script", "style"}:
                continue

            text = str(text_node)
            if "http://" not in text and "https://" not in text:
                continue

            matches = list(url_pattern.finditer(text))
            if not matches:
                continue

            last_index = 0
            replacement_nodes = []
            for match in matches:
                start, end = match.span(1)
                if start > last_index:
                    replacement_nodes.append(NavigableString(text[last_index:start]))

                link_url = match.group(1).rstrip(".,;")
                trailing = match.group(1)[len(link_url):]
                link = BeautifulSoup("", "html.parser").new_tag("a", href=link_url)
                link.string = link_url
                replacement_nodes.append(link)
                if trailing:
                    replacement_nodes.append(NavigableString(trailing))
                last_index = end

            if last_index < len(text):
                replacement_nodes.append(NavigableString(text[last_index:]))

            for replacement_node in reversed(replacement_nodes):
                text_node.insert_after(replacement_node)
            text_node.extract()

    def strip_online_available_text(entry) -> None:
        for text_node in list(entry.find_all(string=True)):
            parent_name = getattr(text_node.parent, "name", None)
            if parent_name in {"a", "script", "style"}:
                continue

            text = str(text_node)
            cleaned = online_available_pattern.sub("", text)
            if cleaned != text:
                text_node.replace_with(NavigableString(cleaned))

    ordered_entries = sorted(
        entries,
        key=lambda entry: entry_sort_key(entry.get_text(" ", strip=True)),
        reverse=True,
    )

    for entry in entries:
        entry.extract()

    for index, entry in enumerate(ordered_entries):
        display_index = total_entries - index
        left_margin = entry.select_one("div.csl-left-margin")
        if left_margin:
            left_margin.clear()
            left_margin.append(f"[{display_index}]")
        strip_online_available_text(entry)
        linkify_doi_text(entry)
        linkify_url_text(entry)
        bib_body.append(entry)

    rendered = str(soup)
    rendered = re.sub(r"^<\?xml[^>]*>\s*", "", rendered)
    return rendered


def creator_display_name(creator: dict) -> str:
    if creator.get("name"):
        return str(creator.get("name"))

    first = str(creator.get("firstName", "")).strip()
    last = str(creator.get("lastName", "")).strip()
    first_parts = [part for part in first.replace("-", " ").split() if part]
    initials = " ".join([f"{part[0].upper()}." for part in first_parts])

    if initials and last:
        return f"{initials} {last}"
    if last:
        return last
    if initials:
        return initials
    return f"{first} {last}".strip()


def get_presentation_citations_all_authors(items: list[dict], person_name: str | None = None) -> tuple[str, str]:
    def presentation_sort_key(raw_date: str) -> tuple[int, int, int]:
        text = str(raw_date or "").strip()
        if not text:
            return (0, 0, 0)

        formats = [
            "%Y-%m-%d",
            "%Y-%m",
            "%Y",
            "%B %d, %Y",
            "%b %d, %Y",
            "%B %Y",
            "%b %Y",
        ]
        for fmt in formats:
            try:
                parsed = datetime.strptime(text, fmt)
                return (parsed.year, parsed.month, parsed.day)
            except ValueError:
                continue

        year_match = re.search(r"(19|20)\d{2}", text)
        if year_match:
            return (int(year_match.group(0)), 0, 0)
        return (0, 0, 0)

    def format_entries_list(entries_list: list[tuple[tuple[int, int, int], str]]) -> str:
        if not entries_list:
            return ""

        entries_list.sort(key=lambda pair: pair[0], reverse=True)
        rendered = []
        total_entries = len(entries_list)
        for index, (_, entry_text) in enumerate(entries_list):
            display_index = total_entries - index
            rendered.append(
                "  <div class=\"csl-entry\" style=\"clear: left; \">\n"
                f"    <div class=\"csl-left-margin\" style=\"float: left; padding-right: 0.5em; text-align: right; width: 2em;\">[{display_index}]</div>"
                f"<div class=\"csl-right-inline\" style=\"margin: 0 .4em 0 2.5em;\">{entry_text}</div>\n"
                "  </div>"
            )

        return '<div class="csl-bib-body" style="line-height: 1.35; ">\n' + "\n".join(rendered) + "\n</div>"

    presenter_entries = []
    contributor_entries = []
    normalized_person_name = str(person_name or "").strip().lower()

    def creator_matches_person(creator: dict, display_name: str) -> bool:
        target = str(display_name or "").strip()
        if not target:
            return False

        target_parts = [part for part in target.replace("-", " ").split() if part]
        if not target_parts:
            return False

        target_last = target_parts[-1].lower()
        target_initial = target_parts[0][0].lower()

        creator_last = str(creator.get("lastName", "") or "").strip().lower()
        creator_first = str(creator.get("firstName", "") or "").strip()
        if creator_last:
            if creator_last != target_last:
                return False
            if creator_first:
                return creator_first[0].lower() == target_initial

        parsed_name = creator_display_name(creator)
        parsed_parts = [part for part in str(parsed_name or "").replace("-", " ").split() if part]
        if len(parsed_parts) < 2:
            return False

        parsed_last = parsed_parts[-1].lower()
        parsed_first_token = parsed_parts[0].replace(".", "")
        if not parsed_first_token:
            return False

        return parsed_last == target_last and parsed_first_token[0].lower() == target_initial

    for item in items:
        data = item.get("data", {})
        ordered_creators = []
        person_role = None

        for creator in data.get("creators", []):
            display_name = creator_display_name(creator)
            if not display_name:
                continue

            safe_name = html.escape(display_name)
            creator_type = str(creator.get("creatorType", "")).lower()
            if creator_type == "presenter":
                ordered_creators.append(f"<em>{safe_name}</em> (presenter)")
            else:
                ordered_creators.append(safe_name)

            if normalized_person_name and creator_matches_person(creator, person_name or ""):
                person_role = creator_type

        authors_text = ", ".join(ordered_creators) if ordered_creators else "Unknown author"

        raw_date = data.get("date", "n.d.")
        date_text = html.escape(str(raw_date))
        title = html.escape(str(data.get("title", "Untitled")))

        meeting_name = data.get("meetingName") or data.get("proceedingsTitle") or ""
        meeting_name = html.escape(str(meeting_name))
        if meeting_name:
            entry = f"{authors_text}. ({date_text}). {title}. <em>{meeting_name}</em>."
        else:
            entry = f"{authors_text}. ({date_text}). {title}."

        presentation_url = str(data.get("url") or "").strip()
        if presentation_url:
            safe_url = html.escape(presentation_url, quote=True)
            entry = entry.rstrip()
            if entry.endswith("."):
                entry = entry[:-1]
            entry += f'. <a href="{safe_url}" target="_blank">{safe_url}</a>.'

        bucket = presenter_entries
        if normalized_person_name:
            if person_role == "presenter":
                bucket = presenter_entries
            else:
                bucket = contributor_entries

        bucket.append((presentation_sort_key(str(raw_date)), entry))

    presenter_html = format_entries_list(presenter_entries)
    contributor_html = format_entries_list(contributor_entries)
    return presenter_html, contributor_html


def extract_title(text: str) -> str:
    match = re.search(r"^title:\s*\"?(.*?)\"?\s*$", text, flags=re.MULTILINE)
    return (match.group(1).strip() if match else "")


def extract_authorship_name(text: str, title: str) -> str:
    comment_match = re.search(r"<!--\s*card-lab-authorship-name:\s*(.*?)\s*-->", text)
    if comment_match:
        value = comment_match.group(1).strip()
        if value:
            return value

    # Fallback used in notebook when Authorship Name is missing.
    title_parts = [part for part in title.split() if part]
    if title_parts:
        return title_parts[-1]
    return ""


def build_publication_sections(author_lookup: str, display_name: str) -> str:
    publications = ""

    thesis_items = get_zotero_items_by_author_and_type(author_lookup, ["thesis"])
    thesis_keys = [item.get("key", "") for item in thesis_items if item.get("key")]
    if thesis_keys:
        publications += "# Thesis/Dissertation\n\n"
        publications += "```{=html}\n"
        publications += get_formatted_citations(thesis_keys, CITATION_FORMAT)
        publications += "```\n\n"

    pub_items = get_zotero_items_by_author_and_type(
        author_lookup,
        ["journalArticle", "book", "bookSection", "conferencePaper", "report"],
    )
    pub_keys = [item.get("key", "") for item in pub_items if item.get("key")]
    if pub_keys:
        publications += "# Publications\n\n"
        publications += "```{=html}\n"
        publications += get_formatted_citations(pub_keys, CITATION_FORMAT)
        publications += "```\n\n"

    presentation_items = get_zotero_items_by_author_and_type(author_lookup, ["presentation"])
    if presentation_items:
        presenter_html, contributor_html = get_presentation_citations_all_authors(presentation_items, display_name)
        if presenter_html:
            publications += "# Presentations\n\n"
            publications += "```{=html}\n"
            publications += presenter_html + "\n"
            publications += "```\n\n"
        if contributor_html:
            publications += "# Contributions\n\n"
            publications += "```{=html}\n"
            publications += contributor_html + "\n"
            publications += "```\n\n"

    code_items = get_zotero_items_by_author_and_type(author_lookup, ["computerProgram"])
    code_keys = [item.get("key", "") for item in code_items if item.get("key")]
    if code_keys:
        publications += "# Code & Datasets\n\n"
        publications += "```{=html}\n"
        publications += get_formatted_citations(code_keys, CITATION_FORMAT)
        publications += "```\n\n"

    return publications.rstrip() + "\n" if publications else ""


def replace_publication_sections(text: str, new_sections: str) -> str:
    heading_pattern = re.compile(
        r"^# (Thesis/Dissertation|Publications|Presentations|Contributions|Code & Datasets)\s*$",
        flags=re.MULTILINE,
    )
    match = heading_pattern.search(text)
    if match:
        prefix = text[: match.start()].rstrip() + "\n\n"
        return prefix + new_sections if new_sections else prefix.rstrip() + "\n"

    if not new_sections:
        return text

    return text.rstrip() + "\n\n" + new_sections


def update_profile(path: Path) -> bool:
    original = path.read_text(encoding="utf-8")
    title = extract_title(original)
    if not title:
        title = path.stem.replace("_", " ")

    author_lookup = extract_authorship_name(original, title)
    if not author_lookup:
        return False

    new_sections = build_publication_sections(author_lookup=author_lookup, display_name=title)
    updated = replace_publication_sections(original, new_sections)
    if updated != original:
        path.write_text(updated, encoding="utf-8")
        return True
    return False


def main() -> None:
    changed = 0
    checked = 0
    for pattern in PROFILE_GLOBS:
        for path in sorted(PROJECT_ROOT.glob(pattern)):
            checked += 1
            try:
                if update_profile(path):
                    changed += 1
            except Exception as exc:
                print(f"Warning: failed to update {path}: {exc}")

    print(f"[update-people-publications] checked={checked} changed={changed}")


if __name__ == "__main__":
    main()
