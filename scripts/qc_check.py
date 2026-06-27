#!/usr/bin/env python3
"""
qc_check.py — Quarto Website Quality Control Tool
==================================================
Scans a rendered Quarto website (_site/ directory by default) and produces
a QC report covering:

  • Broken internal and external hyperlinks
  • Missing / unrenderable images (img src that 404 or point to missing files)
  • Figures with empty alt text (accessibility)
  • Quarto render warnings and errors (parsed from _quarto_render.log if present)
  • Pages containing raw LaTeX / unfenced code (sign of failed rendering)
  • Empty <section> or <div class="cell"> blocks (sign of failed code cells)
  • Large pages (potential performance issue)

OUTPUT MODES
------------
The script supports two output modes, selected with --mode:

  --mode qmd  (DEFAULT)
      Writes a `qc_report.qmd` in your project root, then Quarto renders it
      as a normal site page during the NEXT render.  The report gets your
      full site theme, navbar, TOC, and sidebar — it looks like it belongs.

      Recommended _quarto.yml setup:

        project:
          type: website
          post-render:
            - python qc_check.py          # writes qc_report.qmd after each render

        website:
          navbar:
            right:
              - text: "QC Report"
                href: qc_report.html

      The qmd is committed to version control so your published site always
      has the report from the most recent render.

  --mode html
      Writes a self-contained `qc_report.html` with its own styling.
      Does NOT require a second Quarto render; useful for quick local
      checks or CI pipelines where you just want to open the file directly.

      python qc_check.py --mode html

Usage
-----
  # Render your site (capturing the log), then the post-render hook fires:
  quarto render 2>&1 | tee _quarto_render.log

  # Or run manually at any time:
  python qc_check.py                       # qmd mode, internal links only
  python qc_check.py --external            # also checks external URLs
  python qc_check.py --mode html           # standalone HTML output
  python qc_check.py --site _site --log _quarto_render.log

Dependencies
------------
  pip install requests beautifulsoup4 rich
  (rich is optional — used for a pretty terminal output)
"""

import argparse
import datetime
import json
import os
import re
import shlex
import subprocess
import sys
import time
import urllib.parse
from collections import defaultdict
from pathlib import Path

# ── optional dependencies ──────────────────────────────────────────────────
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

try:
    from rich.console import Console
    from rich.table import Table
    from rich import print as rprint
    HAS_RICH = True
    console = Console()
except ImportError:
    HAS_RICH = False

# ── constants ──────────────────────────────────────────────────────────────
VERSION = "1.2.0"
FALLBACK_SITE_DIR = "_site"
DEFAULT_LOG_FILE = "_quarto_render.log"   # pipe `quarto render 2>&1 | tee _quarto_render.log`
DEFAULT_QMD_FILE = "qc_report.qmd"        # written to project root; rendered by Quarto
DEFAULT_HTML_FILE = "qc_report.html"      # standalone fallback
DEFAULT_MODE     = "qmd"                  # "qmd" or "html"
LARGE_PAGE_THRESHOLD_KB = 500
EXTERNAL_TIMEOUT = 10   # seconds
EXTERNAL_CONCURRENCY = 8

# Patterns that indicate a LaTeX/code block failed to render
RAW_LATEX_RE = re.compile(r"\\\[|\\\(|\\begin\{|\\frac\{|\\mathbf\{")
UNFENCED_CODE_RE = re.compile(r"```[a-zA-Z0-9]*\n")   # raw fences in HTML = render failure

# Quarto log patterns
LOG_WARNING_RE = re.compile(r"\bWARN(?:ING)?\b", re.IGNORECASE)
LOG_ERROR_RE   = re.compile(r"\bERROR\b",         re.IGNORECASE)


def _filter_expected_ci_private_skip_issues(issues: list["Issue"]) -> list["Issue"]:
    """Suppress expected QC errors when private-dependent render paths are skipped in CI."""
    if os.environ.get("CARD_LAB_SKIP_PRIVATE_RENDER_PATHS") != "1":
        return issues

    filtered: list[Issue] = []
    suppressed = 0

    for iss in issues:
        is_expected_missing_image = (
            iss.category == "image"
            and "../files/photos/People/" in iss.detail
        )

        if is_expected_missing_image:
            suppressed += 1
            continue

        filtered.append(iss)

    if suppressed:
        filtered.append(Issue(
            "info",
            "render",
            "(ci-private-skip)",
            f"Suppressed {suppressed} expected issue(s) from private-skip CI mode",
        ))

    return filtered


def detect_quarto_output_dir(project_root: Path) -> str:
    """Best-effort parse of project.output-dir from _quarto.yaml/_quarto.yml."""
    candidates = [project_root / "_quarto.yaml", project_root / "_quarto.yml"]
    for cfg in candidates:
        if not cfg.is_file():
            continue

        in_project = False
        project_indent = 0
        try:
            lines = cfg.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue

        for raw in lines:
            # Ignore blank/comment-only lines for simple structure tracking.
            if not raw.strip() or raw.lstrip().startswith("#"):
                continue

            indent = len(raw) - len(raw.lstrip(" "))
            stripped = raw.strip()

            if not in_project:
                if re.match(r"^project\s*:\s*$", stripped):
                    in_project = True
                    project_indent = indent
                continue

            # Leaving the project block when a new top-level key starts.
            if indent <= project_indent and re.match(r"^[A-Za-z0-9_-]+\s*:", stripped):
                in_project = False
                continue

            m = re.match(r"^output-dir\s*:\s*(.+)\s*$", stripped)
            if m:
                val = m.group(1).strip().strip('"\'')
                if val:
                    return val

    return FALLBACK_SITE_DIR


DEFAULT_SITE_DIR = detect_quarto_output_dir(Path.cwd())

# ── data structures ────────────────────────────────────────────────────────

class Issue:
    LEVELS = {"error": 0, "warning": 1, "info": 2}

    def __init__(self, level: str, category: str, page: str, detail: str, url: str = ""):
        self.level    = level       # "error" | "warning" | "info"
        self.category = category
        self.page     = page        # relative path inside _site
        self.detail   = detail
        self.url      = url         # relevant href / src, if any

    def __repr__(self):
        return f"[{self.level.upper()}] {self.page}: {self.detail}"


# ── helpers ────────────────────────────────────────────────────────────────

def _rel(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def _size_kb(path: Path) -> float:
    return path.stat().st_size / 1024


def _is_external(href: str) -> bool:
    return href.startswith("http://") or href.startswith("https://")


def _normalise_href(href: str, page_path: Path, site_dir: Path) -> Path | None:
    """Resolve a relative/absolute href to an absolute filesystem path."""
    href = href.split("#")[0].split("?")[0]   # strip fragment & query
    if not href:
        return None
    parsed = urllib.parse.urlparse(href)
    if parsed.scheme:
        # Ignore non-filesystem URI schemes (e.g., data:, mailto:, javascript:).
        return None
    if _is_external(href):
        return None
    if href.startswith("/"):
        return site_dir / href.lstrip("/")
    return (page_path.parent / href).resolve()


# ── checkers ──────────────────────────────────────────────────────────────

def collect_html_pages(site_dir: Path) -> list[Path]:
    return sorted(site_dir.rglob("*.html"))


def check_links_and_images(
    pages: list[Path],
    site_dir: Path,
    check_external: bool,
    external_timeout: int,
) -> list[Issue]:
    issues: list[Issue] = []
    external_cache: dict[str, int | None] = {}   # url -> status code or None=error

    # Collect all external URLs first (for batch checking)
    external_urls: set[str] = set()

    for page in pages:
        rel_page = _rel(page, site_dir)
        try:
            soup = BeautifulSoup(page.read_text(encoding="utf-8", errors="replace"), "html.parser")
        except Exception as exc:
            issues.append(Issue("error", "parse", rel_page, f"Could not parse HTML: {exc}"))
            continue

        # ── hyperlinks ──────────────────────────────────────────────────
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith("mailto:") or href.startswith("javascript:") or href == "#":
                continue
            if _is_external(href):
                external_urls.add(href)
            else:
                target = _normalise_href(href, page, site_dir)
                if target is None:
                    continue
                try:
                    exists = target.exists()
                except OSError:
                    exists = False
                if not exists:
                    issues.append(Issue(
                        "error", "broken-link", rel_page,
                        f"Internal link target not found: <code>{href}</code>",
                        url=href,
                    ))

        # ── images ──────────────────────────────────────────────────────
        for img in soup.find_all("img"):
            src = img.get("src", "").strip()
            alt = img.get("alt", "").strip()

            if not src:
                issues.append(Issue(
                    "warning", "image", rel_page,
                    "Image tag has no <code>src</code> attribute",
                ))
                continue

            if _is_external(src):
                external_urls.add(src)
            else:
                target = _normalise_href(src, page, site_dir)
                if target:
                    try:
                        exists = target.exists()
                    except OSError:
                        exists = False
                else:
                    exists = True
                if target and not exists:
                    issues.append(Issue(
                        "error", "image", rel_page,
                        f"Missing image file: <code>{src}</code>",
                        url=src,
                    ))

            if not alt:
                issues.append(Issue(
                    "info", "accessibility", rel_page,
                    f"Image missing alt text: <code>{src}</code>",
                    url=src,
                ))

        # ── render quality ───────────────────────────────────────────────
        text = soup.get_text()

        if RAW_LATEX_RE.search(text):
            issues.append(Issue(
                "warning", "render", rel_page,
                "Page may contain un-rendered LaTeX math (raw \\[ or \\begin{ found in body text)",
            ))

        if UNFENCED_CODE_RE.search(str(soup)):
            issues.append(Issue(
                "warning", "render", rel_page,
                "Page contains raw code fences (``` in HTML) — possible Quarto rendering failure",
            ))

        # Empty Quarto cell output blocks
        for cell in soup.find_all("div", class_=lambda c: c and "cell" in c.split()):
            if not cell.get_text(strip=True):
                issues.append(Issue(
                    "warning", "render", rel_page,
                    "Empty code-cell output block detected (cell executed but produced no output)",
                ))
                break  # one warning per page is enough

        # ── page size ────────────────────────────────────────────────────
        size = _size_kb(page)
        if size > LARGE_PAGE_THRESHOLD_KB:
            issues.append(Issue(
                "info", "performance", rel_page,
                f"Large page: {size:.0f} KB (threshold {LARGE_PAGE_THRESHOLD_KB} KB) — "
                "consider lazy-loading images or splitting content",
            ))

    # ── external link checks ─────────────────────────────────────────────
    if check_external and HAS_REQUESTS and external_urls:
        _check_external_urls(
            external_urls, external_cache, issues, pages, site_dir, external_timeout
        )

    return issues


def _check_external_urls(
    urls: set[str],
    cache: dict,
    issues: list[Issue],
    pages: list[Path],
    site_dir: Path,
    timeout: int,
) -> None:
    """Check external URLs — one at a time, with a simple cache."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; QuartoQC/1.0; link-checker)"
    })

    # Build a reverse map: url -> list of pages that link to it
    url_to_pages: dict[str, list[str]] = defaultdict(list)
    for page in pages:
        rel_page = _rel(page, site_dir)
        try:
            soup = BeautifulSoup(page.read_text(encoding="utf-8", errors="replace"), "html.parser")
        except Exception:
            continue
        for tag in soup.find_all(["a", "img"]):
            href = tag.get("href") or tag.get("src") or ""
            if _is_external(href) and href in urls:
                url_to_pages[href].append(rel_page)

    total = len(urls)
    print(f"\n  Checking {total} external URL(s) …", flush=True)

    for i, url in enumerate(sorted(urls), 1):
        if url in cache:
            status = cache[url]
        else:
            try:
                resp = session.head(url, timeout=timeout, allow_redirects=True)
                status = resp.status_code
                # Some servers reject HEAD; fall back to GET
                if status in (405, 403):
                    resp = session.get(url, timeout=timeout, stream=True)
                    status = resp.status_code
            except requests.exceptions.SSLError:
                status = "SSL_ERROR"
            except requests.exceptions.ConnectionError:
                status = "CONNECTION_ERROR"
            except requests.exceptions.Timeout:
                status = "TIMEOUT"
            except Exception as exc:
                status = f"ERROR: {exc}"
            cache[url] = status
            time.sleep(0.15)   # polite crawl delay

        pages_ref = url_to_pages.get(url, ["(unknown)"])
        ref_str = pages_ref[0] if len(pages_ref) == 1 else f"{pages_ref[0]} (+{len(pages_ref)-1} more)"

        if isinstance(status, int) and status < 400:
            pass  # ok
        elif status in ("TIMEOUT", "SSL_ERROR", "CONNECTION_ERROR") or (
            isinstance(status, int) and status >= 400
        ):
            issues.append(Issue(
                "error", "broken-link", ref_str,
                f"External URL returned {status}: <code>{url}</code>",
                url=url,
            ))
        if i % 10 == 0:
            print(f"    … {i}/{total}", flush=True)


def check_render_log(log_path: Path, site_dir: Path) -> list[Issue]:
    """Parse a Quarto render log for warnings and errors."""
    issues: list[Issue] = []
    if not log_path.exists():
        issues.append(Issue(
            "info", "log",
            "(no log)",
            f"Render log not found at <code>{log_path}</code>. "
            "To capture it, run: <code>quarto render 2&gt;&amp;1 | tee _quarto_render.log</code>",
        ))
        return issues

    current_file = "(preamble)"
    file_re = re.compile(r"(?:rendering|processing|compiling)\s+([^\s]+\.(?:qmd|Rmd|ipynb))",
                         re.IGNORECASE)

    with open(log_path, encoding="utf-8", errors="replace") as f:
        for lineno, raw_line in enumerate(f, 1):
            line = raw_line.rstrip()

            # Track which file is being rendered
            m = file_re.search(line)
            if m:
                current_file = m.group(1)

            if LOG_ERROR_RE.search(line):
                issues.append(Issue(
                    "error", "render-log", current_file,
                    f"Line {lineno}: <code>{_escape(line)}</code>",
                ))
            elif LOG_WARNING_RE.search(line):
                issues.append(Issue(
                    "warning", "render-log", current_file,
                    f"Line {lineno}: <code>{_escape(line)}</code>",
                ))

    if not any(i.category == "render-log" for i in issues):
        issues.append(Issue(
            "info", "render-log",
            "(log)",
            f"No errors or warnings found in render log ({log_path.stat().st_size} bytes)",
        ))

    return issues


def check_missing_source_files(site_dir: Path) -> list[Issue]:
    """Look for _files/ directories that have no matching HTML page — sign of orphaned resources."""
    issues: list[Issue] = []
    for files_dir in site_dir.rglob("*_files"):
        if files_dir.is_dir():
            stem = files_dir.name.replace("_files", "")
            sibling_html = files_dir.parent / f"{stem}.html"
            if not sibling_html.exists():
                issues.append(Issue(
                    "info", "orphaned-assets",
                    _rel(files_dir, site_dir),
                    f"Resource folder <code>{files_dir.name}/</code> has no matching .html page "
                    "(possibly from a renamed/deleted source file)",
                ))
    return issues


# ── HTML report ────────────────────────────────────────────────────────────

def _escape(text: str) -> str:
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


LEVEL_STYLE = {
    "error":   ("🔴", "#b91c1c", "#fef2f2", "#fee2e2"),
    "warning": ("🟡", "#92400e", "#fffbeb", "#fef3c7"),
    "info":    ("🔵", "#1e40af", "#eff6ff", "#dbeafe"),
}

CATEGORY_LABELS = {
    "broken-link":      "Broken Link",
    "image":            "Missing / Bad Image",
    "accessibility":    "Accessibility",
    "render":           "Render Quality",
    "render-log":       "Build Log",
    "performance":      "Performance",
    "orphaned-assets":  "Orphaned Assets",
    "log":              "Build Log",
    "parse":            "Parse Error",
}


def build_qmd_report(
    issues: list[Issue],
    site_dir: Path,
    pages: list[Path],
    generated_at: datetime.datetime,
    check_external: bool,
) -> str:
    """
    Write a Quarto Markdown (.qmd) file that Quarto will render as a normal
    site page on the NEXT `quarto render` call.  The file uses only standard
    Quarto markdown + callout blocks + raw HTML tables — no Python execution
    required at render time, so it works in any Quarto project regardless of
    the engine (knitr, jupyter, or none).
    """

    by_level: dict[str, list[Issue]] = {"error": [], "warning": [], "info": []}
    for iss in issues:
        by_level[iss.level].append(iss)

    n_errors   = len(by_level["error"])
    n_warnings = len(by_level["warning"])
    n_info     = len(by_level["info"])
    n_pages    = len(pages)
    n_total    = len(issues)

    ts = generated_at.strftime("%Y-%m-%d %H:%M:%S")
    date_iso = generated_at.strftime("%Y-%m-%d")

    # Overall status callout
    if n_errors > 0:
        status_type = "important"   # renders red in most Quarto themes
        status_icon = "🔴"
        status_text = f"**{n_errors} error{'s' if n_errors != 1 else ''} found.** Review the Broken Links and/or Render Quality sections below."
    elif n_warnings > 0:
        status_type = "warning"
        status_icon = "🟡"
        status_text = f"**{n_warnings} warning{'s' if n_warnings != 1 else ''} found.** No hard errors, but some issues need attention."
    else:
        status_type = "tip"
        status_icon = "🟢"
        status_text = "**All clear.** No errors or warnings detected."

    ext_note = (
        "External links were **checked**."
        if check_external
        else "External links were **skipped** — re-run with `--external` to include them."
    )

    # ── summary stat table ────────────────────────────────────────────────
    stat_table = f"""\
| Metric | Value |
|:-------|------:|
| Pages scanned | {n_pages} |
| 🔴 Errors | {n_errors} |
| 🟡 Warnings | {n_warnings} |
| 🔵 Notes | {n_info} |
| Total issues | {n_total} |
| Checked | {ts} |
"""

    # ── per-category sections ─────────────────────────────────────────────
    by_cat: dict[str, list[Issue]] = defaultdict(list)
    for iss in issues:
        by_cat[iss.category].append(iss)

    LEVEL_EMOJI = {"error": "🔴", "warning": "🟡", "info": "🔵"}
    LEVEL_BADGE_COLOR = {
        "error":   "background:#fee2e2;color:#b91c1c",
        "warning": "background:#fef3c7;color:#92400e",
        "info":    "background:#dbeafe;color:#1e40af",
    }

    def make_issue_table(iss_list: list[Issue]) -> str:
        rows = []
        for iss in iss_list:
            badge_style = LEVEL_BADGE_COLOR[iss.level]
            badge = (
                f'<span style="{badge_style};'
                f'padding:1px 7px;border-radius:9px;font-size:.75rem;'
                f'font-weight:700;text-transform:uppercase;">'
                f'{iss.level}</span>'
            )
            rows.append(
                f"<tr>"
                f'<td style="padding:6px 10px;border-bottom:1px solid #e5e7eb;'
                f'white-space:nowrap;">{badge}</td>'
                f'<td style="padding:6px 10px;border-bottom:1px solid #e5e7eb;'
                f'font-family:monospace;font-size:.8rem;word-break:break-all;">'
                f"{_escape(iss.page)}</td>"
                f'<td style="padding:6px 10px;border-bottom:1px solid #e5e7eb;'
                f'font-size:.85rem;">{iss.detail}</td>'
                f"</tr>"
            )
        header = (
            '<table style="width:100%;border-collapse:collapse;font-size:.85rem;">'
            '<thead><tr style="background:#f3f4f6;">'
            '<th style="padding:6px 10px;text-align:left;font-size:.72rem;'
            'text-transform:uppercase;letter-spacing:.05em;color:#6b7280;'
            'border-bottom:2px solid #e5e7eb;white-space:nowrap;">Level</th>'
            '<th style="padding:6px 10px;text-align:left;font-size:.72rem;'
            'text-transform:uppercase;letter-spacing:.05em;color:#6b7280;'
            'border-bottom:2px solid #e5e7eb;">Page / Source</th>'
            '<th style="padding:6px 10px;text-align:left;font-size:.72rem;'
            'text-transform:uppercase;letter-spacing:.05em;color:#6b7280;'
            'border-bottom:2px solid #e5e7eb;">Detail</th>'
            "</tr></thead><tbody>"
        )
        return header + "\n".join(rows) + "</tbody></table>"

    cat_sections_md: list[str] = []
    for cat_key in sorted(by_cat.keys()):
        iss_list = by_cat[cat_key]
        label = CATEGORY_LABELS.get(cat_key, cat_key)
        n_e = sum(1 for i in iss_list if i.level == "error")
        n_w = sum(1 for i in iss_list if i.level == "warning")
        n_i = sum(1 for i in iss_list if i.level == "info")
        counts = []
        if n_e: counts.append(f"🔴 {n_e}")
        if n_w: counts.append(f"🟡 {n_w}")
        if n_i: counts.append(f"🔵 {n_i}")
        count_str = "  ·  ".join(counts) if counts else "0"

        table_html = make_issue_table(iss_list)

        cat_sections_md.append(f"""\
### {label} {{#{cat_key}}}

{count_str}

{table_html}
""")

    if not cat_sections_md:
        cat_sections_md = ["*No issues detected.*\n"]

    categories_block = "\n".join(cat_sections_md)

    # ── assemble the .qmd ─────────────────────────────────────────────────
    # The YAML front matter uses `date` so the page timestamp is correct
    # without any Python execution at Quarto render time.
    return f"""\
---
title: "Site QC Report"
subtitle: "Automated quality-control scan · {ts}"
date: "{date_iso}"
date-format: "MMMM D, YYYY"
toc: true
toc-depth: 2
toc-title: "Checks"
---

<!-- AUTO-GENERATED by qc_check.py — do not edit by hand.
     Re-run `python qc_check.py` (or let the post-render hook do it)
     and then `quarto render` to refresh this page. -->

::: {{.callout-{status_type}}}
## {status_icon} Overall Status

{status_text}
:::

## Summary

{stat_table}

{ext_note}

## Issues by Category

{categories_block}

---

::: {{.callout-note collapse="true"}}
## How to refresh this report

This page is generated automatically by `qc_check.py` after each full site
render.  To refresh it:

```bash
# Render site and capture the log (post-render hook writes qc_report.qmd)
quarto render 2>&1 | tee _quarto_render.log

# The next render picks up the updated qc_report.qmd automatically.
# Or render just this page:
quarto render qc_report.qmd
```

To also check external links (slower):

```bash
python qc_check.py --external
quarto render qc_report.qmd
```
:::
"""


# ── HTML report ────────────────────────────────────────────────────────────

def build_html_report(
    issues: list[Issue],
    site_dir: Path,
    pages: list[Path],
    generated_at: datetime.datetime,
    check_external: bool,
) -> str:

    by_level: dict[str, list[Issue]] = {"error": [], "warning": [], "info": []}
    for iss in issues:
        by_level[iss.level].append(iss)

    n_errors   = len(by_level["error"])
    n_warnings = len(by_level["warning"])
    n_info     = len(by_level["info"])
    n_pages    = len(pages)

    status_color = "#16a34a" if n_errors == 0 and n_warnings == 0 else (
        "#b91c1c" if n_errors > 0 else "#d97706"
    )
    status_label = "All Clear ✓" if n_errors == 0 and n_warnings == 0 else (
        f"{n_errors} Error{'s' if n_errors != 1 else ''}" if n_errors > 0
        else f"{n_warnings} Warning{'s' if n_warnings != 1 else ''}"
    )

    # Group issues by category for the detail sections
    by_cat: dict[str, list[Issue]] = defaultdict(list)
    for iss in issues:
        by_cat[iss.category].append(iss)

    def issue_rows(iss_list: list[Issue]) -> str:
        rows = []
        for iss in iss_list:
            icon, fg, bg, border = LEVEL_STYLE[iss.level]
            rows.append(f"""
            <tr>
              <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;">
                <span style="font-size:0.7rem;font-weight:700;color:{fg};
                             background:{border};padding:2px 7px;border-radius:9px;
                             text-transform:uppercase;letter-spacing:.05em;">
                  {iss.level}
                </span>
              </td>
              <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;
                         font-size:0.82rem;color:#374151;font-family:monospace;">
                {_escape(iss.page)}
              </td>
              <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;
                         font-size:0.83rem;color:#111827;">
                {iss.detail}
              </td>
            </tr>""")
        return "\n".join(rows)

    def section(cat_key: str, iss_list: list[Issue]) -> str:
        label = CATEGORY_LABELS.get(cat_key, cat_key)
        n_e = sum(1 for i in iss_list if i.level == "error")
        n_w = sum(1 for i in iss_list if i.level == "warning")
        n_i = sum(1 for i in iss_list if i.level == "info")
        badges = []
        if n_e: badges.append(f'<span style="background:#fca5a5;color:#7f1d1d;padding:1px 6px;border-radius:8px;font-size:.7rem;">{n_e} error{"s" if n_e!=1 else ""}</span>')
        if n_w: badges.append(f'<span style="background:#fde68a;color:#78350f;padding:1px 6px;border-radius:8px;font-size:.7rem;">{n_w} warning{"s" if n_w!=1 else ""}</span>')
        if n_i: badges.append(f'<span style="background:#bfdbfe;color:#1e3a8a;padding:1px 6px;border-radius:8px;font-size:.7rem;">{n_i} note{"s" if n_i!=1 else ""}</span>')

        return f"""
  <details {"open" if n_e > 0 else ""} style="margin-bottom:1.25rem;
             border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;">
    <summary style="padding:12px 16px;cursor:pointer;background:#f9fafb;
                    font-weight:600;font-size:0.95rem;display:flex;
                    align-items:center;gap:8px;list-style:none;">
      {label}
      <span style="display:flex;gap:5px;margin-left:auto;">
        {"".join(badges)}
      </span>
    </summary>
    <div style="overflow-x:auto;">
      <table style="width:100%;border-collapse:collapse;font-size:0.85rem;">
        <thead>
          <tr style="background:#f3f4f6;">
            <th style="padding:8px 12px;text-align:left;font-size:0.72rem;
                       text-transform:uppercase;letter-spacing:.05em;color:#6b7280;
                       border-bottom:2px solid #e5e7eb;white-space:nowrap;">Level</th>
            <th style="padding:8px 12px;text-align:left;font-size:0.72rem;
                       text-transform:uppercase;letter-spacing:.05em;color:#6b7280;
                       border-bottom:2px solid #e5e7eb;">Page / Source</th>
            <th style="padding:8px 12px;text-align:left;font-size:0.72rem;
                       text-transform:uppercase;letter-spacing:.05em;color:#6b7280;
                       border-bottom:2px solid #e5e7eb;">Detail</th>
          </tr>
        </thead>
        <tbody>
          {issue_rows(iss_list)}
        </tbody>
      </table>
    </div>
  </details>"""

    sections_html = "\n".join(
        section(cat, iss_list)
        for cat, iss_list in sorted(by_cat.items())
    ) if by_cat else '<p style="color:#6b7280;font-style:italic;">No issues found.</p>'

    ext_note = (
        "External links were <strong>checked</strong>."
        if check_external
        else "External links were <strong>skipped</strong> (run with <code>--external</code> to check them)."
    )
    if not HAS_REQUESTS and check_external:
        ext_note = "External link checking requires <code>pip install requests</code>."

    ts = generated_at.strftime("%Y-%m-%d %H:%M:%S")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Quarto Site QC Report</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #f3f4f6;
    color: #111827;
    line-height: 1.5;
  }}
  header {{
    background: #111827;
    color: white;
    padding: 24px 40px;
    display: flex;
    align-items: center;
    gap: 20px;
  }}
  header h1 {{ margin: 0; font-size: 1.3rem; font-weight: 700; letter-spacing: -.01em; }}
  header p  {{ margin: 2px 0 0; font-size: .82rem; color: #9ca3af; }}
  .status-pill {{
    margin-left: auto;
    background: {status_color};
    color: white;
    padding: 6px 16px;
    border-radius: 20px;
    font-weight: 700;
    font-size: 0.88rem;
    white-space: nowrap;
  }}
  main {{ max-width: 1100px; margin: 32px auto; padding: 0 24px 60px; }}
  .summary-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 14px;
    margin-bottom: 28px;
  }}
  .card {{
    background: white;
    border-radius: 8px;
    padding: 16px 18px;
    border: 1px solid #e5e7eb;
    text-align: center;
  }}
  .card-value {{ font-size: 2rem; font-weight: 800; }}
  .card-label {{ font-size: 0.72rem; text-transform: uppercase;
                  letter-spacing: .05em; color: #6b7280; margin-top: 2px; }}
  .section-title {{
    font-size: 1.05rem; font-weight: 700; margin: 28px 0 12px;
    padding-bottom: 8px; border-bottom: 2px solid #e5e7eb;
  }}
  details summary::-webkit-details-marker {{ display: none; }}
  details summary::before {{ content: "▶ "; font-size: .7rem; }}
  details[open] summary::before {{ content: "▼ "; }}
  code {{ background: #f3f4f6; padding: 1px 5px; border-radius: 3px;
           font-size: 0.85em; word-break: break-all; }}
  footer {{
    text-align: center;
    font-size: 0.75rem;
    color: #9ca3af;
    padding: 20px;
    border-top: 1px solid #e5e7eb;
    margin-top: 40px;
  }}
  @media (max-width: 640px) {{
    header {{ flex-wrap: wrap; padding: 16px 20px; }}
    main {{ padding: 0 14px 40px; }}
  }}
</style>
</head>
<body>
<header>
  <div>
    <h1>📋 Quarto Site QC Report</h1>
    <p>Site: <code style="color:#d1d5db;">{_escape(str(site_dir))}</code> &nbsp;·&nbsp; Generated: {ts}</p>
  </div>
  <div class="status-pill">{status_label}</div>
</header>

<main>
  <div class="summary-grid">
    <div class="card">
      <div class="card-value" style="color:#111827;">{n_pages}</div>
      <div class="card-label">Pages scanned</div>
    </div>
    <div class="card">
      <div class="card-value" style="color:#b91c1c;">{n_errors}</div>
      <div class="card-label">Errors</div>
    </div>
    <div class="card">
      <div class="card-value" style="color:#d97706;">{n_warnings}</div>
      <div class="card-label">Warnings</div>
    </div>
    <div class="card">
      <div class="card-value" style="color:#2563eb;">{n_info}</div>
      <div class="card-label">Notes</div>
    </div>
    <div class="card">
      <div class="card-value" style="color:#059669;">{len(issues)}</div>
      <div class="card-label">Total issues</div>
    </div>
  </div>

  <p style="font-size:0.82rem;color:#6b7280;margin-bottom:24px;">
    {ext_note}
    Click any section header to expand/collapse.
    Errors are expanded by default.
  </p>

  <div class="section-title">Issues by Category</div>
  {sections_html}

</main>

<footer>
  Quarto Site QC Tool v{VERSION} &nbsp;·&nbsp;
  <a href="https://quarto.org" style="color:#6b7280;">quarto.org</a>
  &nbsp;·&nbsp; Report generated {ts}
</footer>
</body>
</html>
"""


# ── terminal summary ───────────────────────────────────────────────────────

def print_terminal_summary(issues: list[Issue], pages: list[Path]) -> None:
    n_e = sum(1 for i in issues if i.level == "error")
    n_w = sum(1 for i in issues if i.level == "warning")
    n_i = sum(1 for i in issues if i.level == "info")

    if HAS_RICH:
        t = Table(title=f"QC Summary — {len(pages)} pages scanned", show_header=True)
        t.add_column("Level",    style="bold")
        t.add_column("Category")
        t.add_column("Page",     style="dim")
        t.add_column("Detail",   max_width=70)
        for iss in issues:
            colour = {"error": "red", "warning": "yellow", "info": "blue"}[iss.level]
            t.add_row(
                f"[{colour}]{iss.level.upper()}[/{colour}]",
                CATEGORY_LABELS.get(iss.category, iss.category),
                iss.page,
                re.sub(r"<[^>]+>", "", iss.detail),
            )
        console.print(t)
        if n_e:
            console.print(f"\n[bold red]✗ {n_e} error(s) found.[/bold red]")
        elif n_w:
            console.print(f"\n[bold yellow]△ {n_w} warning(s) found.[/bold yellow]")
        else:
            console.print("\n[bold green]✓ No errors or warnings.[/bold green]")
    else:
        print(f"\n{'='*60}")
        print(f"QC Summary — {len(pages)} pages, "
              f"{n_e} errors, {n_w} warnings, {n_i} notes")
        print('='*60)
        for iss in issues:
            tag = {"error": "[ERR]", "warning": "[WRN]", "info": "[NFO]"}[iss.level]
            detail_plain = re.sub(r"<[^>]+>", "", iss.detail)
            print(f"{tag} {iss.page} :: {detail_plain}")
        print('='*60)


# ── CLI ────────────────────────────────────────────────────────────────────

def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Quarto website quality-control checker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--site",     default=DEFAULT_SITE_DIR,
                   help="Rendered site directory (default: _site)")
    p.add_argument("--log",      default=DEFAULT_LOG_FILE,
                   help="Quarto render log (default: _quarto_render.log)")
    p.add_argument("--mode",     default=DEFAULT_MODE, choices=["qmd", "html"],
                   help="Output mode: 'qmd' (default) writes qc_report.qmd for Quarto "
                        "to render as a site page; 'html' writes a standalone HTML file")
    p.add_argument("--out",      default=None,
                   help="Override output path (default: qc_report.qmd or qc_report.html "
                        "depending on --mode)")
    p.add_argument("--external", action="store_true",
                   help="Check external URLs (slower; skipped by default)")
    p.add_argument("--no-external", dest="external", action="store_false")
    p.add_argument("--timeout",  type=int, default=EXTERNAL_TIMEOUT,
                   help="Timeout in seconds for external requests (default: 10)")
    p.set_defaults(external=False)
    return p.parse_args(argv)


def _find_quarto_render_command() -> str | None:
    pid = os.getppid()
    for _ in range(12):
        if pid <= 1:
            break

        try:
            cmd = subprocess.check_output(
                ["ps", "-o", "command=", "-p", str(pid)],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
        except Exception:
            break

        if "quarto render" in cmd:
            return cmd

        try:
            ppid = subprocess.check_output(
                ["ps", "-o", "ppid=", "-p", str(pid)],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
            pid = int(ppid)
        except Exception:
            break

    return None


def _is_single_file_render(quarto_cmd: str) -> bool:
    try:
        tokens = shlex.split(quarto_cmd)
    except Exception:
        return False

    for idx, tok in enumerate(tokens):
        if tok == "render":
            if idx + 1 >= len(tokens):
                return False
            arg = tokens[idx + 1]
            return bool(arg) and not arg.startswith("-")
    return False


def main(argv=None):
    args = parse_args(argv)

    # Skip QC when Quarto is rendering a single input file.
    # Full-site renders should still run and gate on errors.
    input_path = os.environ.get("QUARTO_PROJECT_INPUT_PATH")
    if input_path:
        print(
            "[post-render] Individual file render detected; "
            f"skipping QC checks ({input_path})"
        )
        sys.exit(0)

    quarto_cmd = _find_quarto_render_command()
    if quarto_cmd and _is_single_file_render(quarto_cmd):
        print("[post-render] Individual file render detected; skipping QC checks")
        sys.exit(0)

    site_dir = Path(args.site)
    log_path = Path(args.log)

    # Resolve output path based on mode
    if args.out:
        out_path = Path(args.out)
    else:
        out_path = Path(DEFAULT_QMD_FILE if args.mode == "qmd" else DEFAULT_HTML_FILE)

    if not HAS_BS4:
        print("ERROR: beautifulsoup4 is required.  Run:  pip install beautifulsoup4")
        sys.exit(1)

    if not site_dir.is_dir():
        print(f"ERROR: Site directory '{site_dir}' does not exist.")
        print("       Run 'quarto render' first, or pass --site <path>.")
        sys.exit(1)

    print(f"\n{'─'*55}")
    print(f"  Quarto Site QC  v{VERSION}")
    print(f"  Site:   {site_dir}")
    print(f"  Log:    {log_path}")
    print(f"  Mode:   {args.mode}  →  {out_path}")
    print(f"  Ext:    {'yes' if args.external else 'no (pass --external to enable)'}")
    print(f"{'─'*55}\n")

    pages = collect_html_pages(site_dir)
    print(f"  Found {len(pages)} HTML page(s).")

    all_issues: list[Issue] = []

    print("  Checking links, images, and render quality …")
    all_issues += check_links_and_images(
        pages, site_dir, args.external, args.timeout
    )

    print("  Checking render log …")
    all_issues += check_render_log(log_path, site_dir)

    print("  Checking for orphaned assets …")
    all_issues += check_missing_source_files(site_dir)

    all_issues = _filter_expected_ci_private_skip_issues(all_issues)

    now = datetime.datetime.now()

    if args.mode == "qmd":
        print("  Writing QMD report …")
        content = build_qmd_report(all_issues, site_dir, pages, now, args.external)
        out_path.write_text(content, encoding="utf-8")
        print(f"\n  ✓ QMD report written to {out_path}")
        print("    Quarto will render it into your site on the next `quarto render`.")
        print("    Make sure qc_report.qmd is listed (or auto-discovered) in your project.\n")
    else:
        print("  Building standalone HTML report …")
        content = build_html_report(all_issues, site_dir, pages, now, args.external)
        out_path.write_text(content, encoding="utf-8")
        print(f"\n  ✓ HTML report written to {out_path}\n")

    print_terminal_summary(all_issues, pages)

    # Exit code 1 on any errors — useful as a CI gate
    n_errors = sum(1 for i in all_issues if i.level == "error")
    sys.exit(1 if n_errors else 0)


if __name__ == "__main__":
    main()
