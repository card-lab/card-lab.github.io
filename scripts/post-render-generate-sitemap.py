#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse


class AnchorHrefParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[override]
        if tag.lower() != "a":
            return
        for key, value in attrs:
            if key.lower() == "href" and value:
                self.hrefs.append(value.strip())
                break


def read_title(html_text: str) -> str:
    match = re.search(r"<title>(.*?)</title>", html_text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return re.sub(r"\s+", " ", match.group(1)).strip()


def page_id_for_path(path: Path, docs_dir: Path) -> str:
    rel = path.relative_to(docs_dir).as_posix()
    if rel == "index.html":
        return "/"
    if rel.endswith("/index.html"):
        return "/" + rel[: -len("index.html")]
    return "/" + rel


def normalize_internal_target(href: str, src_page: str) -> str | None:
    href = (href or "").strip()
    if not href:
        return None

    parsed = urlparse(href)
    if parsed.scheme or parsed.netloc:
        return None

    clean, _frag = urldefrag(href)
    if not clean or clean.startswith("mailto:") or clean.startswith("tel:"):
        return None

    # Convert relative href into a root-like path using src_page as base.
    base = src_page if src_page.endswith(".html") else f"{src_page}index.html"
    joined = urljoin(base, clean)
    joined_clean = urldefrag(joined)[0]

    if joined_clean.endswith("/"):
        return joined_clean
    if joined_clean.endswith(".html"):
        if joined_clean == "/index.html":
            return "/"
        if joined_clean.endswith("/index.html"):
            return joined_clean[: -len("index.html")]
        return joined_clean

    return None


def find_quarto_render_command() -> str | None:
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


def is_single_file_render(quarto_cmd: str) -> bool:
    try:
        tokens = shlex.split(quarto_cmd)
    except Exception:
        return False

    # Find the token after `render` and treat it as a file when positional.
    for idx, tok in enumerate(tokens):
        if tok == "render":
            if idx + 1 >= len(tokens):
                return False
            arg = tokens[idx + 1]
            return bool(arg) and not arg.startswith("-")
    return False


def main() -> int:
    # Only run on full-site render, not single-file render.
    input_path = os.environ.get("QUARTO_PROJECT_INPUT_PATH")
    if input_path:
        print(
            "[post-render] Individual file render detected; skipping sitemap generation "
            f"({input_path})"
        )
        return 0

    quarto_cmd = find_quarto_render_command()
    if quarto_cmd and is_single_file_render(quarto_cmd):
        print("[post-render] Individual file render detected; skipping sitemap generation")
        return 0

    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    docs_dir = project_root / "docs"

    if not docs_dir.exists():
        print(f"[post-render] Docs output directory not found: {docs_dir}")
        return 0

    excluded_roots = {
        "site_libs",
        "files",
        "private",
        ".quarto",
    }

    html_pages = sorted(
        p
        for p in docs_dir.rglob("*.html")
        if p.is_file()
        and not any(part in excluded_roots for part in p.relative_to(docs_dir).parts)
    )

    pages: dict[str, dict[str, str]] = {}
    for page in html_pages:
        page_id = page_id_for_path(page, docs_dir)
        text = page.read_text(encoding="utf-8", errors="ignore")
        title = read_title(text) or page_id
        pages[page_id] = {
            "id": page_id,
            "title": title,
            "path": page.relative_to(docs_dir).as_posix(),
        }

    edges_set: set[tuple[str, str]] = set()
    for page in html_pages:
        source_id = page_id_for_path(page, docs_dir)
        text = page.read_text(encoding="utf-8", errors="ignore")
        parser = AnchorHrefParser()
        parser.feed(text)

        for href in parser.hrefs:
            target = normalize_internal_target(href, source_id)
            if not target:
                continue
            if target in pages and target != source_id:
                edges_set.add((source_id, target))

    edges = [
        {"source": src, "target": dst}
        for src, dst in sorted(edges_set)
    ]

    indegree: dict[str, int] = {k: 0 for k in pages}
    outdegree: dict[str, int] = {k: 0 for k in pages}
    for e in edges:
        outdegree[e["source"]] += 1
        indegree[e["target"]] += 1

    nodes = []
    for page_id, page in sorted(pages.items()):
        nodes.append(
            {
                "id": page_id,
                "label": page["title"],
                "path": page["path"],
                "indegree": indegree[page_id],
                "outdegree": outdegree[page_id],
                "degree": indegree[page_id] + outdegree[page_id],
            }
        )

    output = {
        "generated": True,
        "nodeCount": len(nodes),
        "edgeCount": len(edges),
        "nodes": nodes,
        "edges": edges,
    }

    out_path = docs_dir / "files" / "site" / "sitemap-data.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print(
        "[post-render] Sitemap data written "
        f"({len(nodes)} pages, {len(edges)} links): {out_path.relative_to(project_root)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
