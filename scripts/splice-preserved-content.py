#!/usr/bin/env python3
"""Graft a previously published page's real content into a freshly rendered
placeholder page, instead of using the previously published page wholesale.

CI can't execute people/demographics.ipynb and people/timeline.ipynb (they
need a private spreadsheet that only exists on a contributor's machine), so
it renders a stub in their place and copies the last manually published
version of the page over the result. That previously published HTML is a
complete, self-contained document from whatever Quarto version and site
theme were current the last time someone ran `quarto publish gh-pages`
locally. Every other page gets the navbar/sidebar/CSS that ships with
*today's* render, so over time the two preserved pages drift further from
the rest of the site (mismatched spacing, stale Bootstrap, etc.) — which is
exactly what shows up as "this page doesn't match the rest of the site".

Instead, keep the freshly rendered page's chrome (head assets, navbar,
left sidebar, footer) and only transplant the parts that actually carry the
private-data-driven content: the main content body and the page's own table
of contents. Any extra CDN script/link tags the old content depends on (e.g.
the Plotly/jQuery includes Jupyter widgets pull in) are copied into the new
page's <head> if the fresh page doesn't already have them.
"""
import sys
from pathlib import Path

from bs4 import BeautifulSoup

GRAFTED_IDS = ["quarto-document-content", "quarto-margin-sidebar"]


def main():
    fresh_path, preserved_path, output_path = (Path(p) for p in sys.argv[1:4])

    fresh = BeautifulSoup(fresh_path.read_text(encoding="utf-8"), "lxml")
    preserved = BeautifulSoup(preserved_path.read_text(encoding="utf-8"), "lxml")

    for el_id in GRAFTED_IDS:
        old_el = preserved.find(id=el_id)
        new_el = fresh.find(id=el_id)
        if old_el is not None and new_el is not None:
            new_el.replace_with(old_el)

    existing_srcs = {
        tag.get("src") or tag.get("href")
        for tag in fresh.head.find_all(["script", "link"])
    }
    for tag in preserved.head.find_all(["script", "link"]):
        src = tag.get("src") or tag.get("href")
        if src and src.startswith("http") and src not in existing_srcs:
            fresh.head.append(tag)
            existing_srcs.add(src)

    output_path.write_text(str(fresh), encoding="utf-8")


if __name__ == "__main__":
    main()
