#!/usr/bin/env python3
"""Choose which copy of a private-data page CI should graft into the site.

CI can't render people/demographics.ipynb or people/timeline.ipynb (they need
the private spreadsheet), so it reuses an earlier render. Two copies may exist:

- the one committed to main under docs/ (rendered locally, then pushed), and
- the one on the live gh-pages branch (from the last publish).

Print the path of the copy with the later "Updated" date from its title block,
preferring the committed copy on a tie. Print nothing if neither exists.

Usage: pick-newer-private-page.py <committed.html> <published.html>
"""
import sys
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup

DATE_FORMATS = ("%d %B %Y", "%B %d, %Y", "%Y-%m-%d", "%d %b %Y", "%b %d, %Y")


def updated_date(path):
    """The page's rendered date, or None if the file is missing or the date can't be read."""
    if not path.is_file():
        return None
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    node = soup.select_one(".quarto-title-meta .date") or soup.select_one("p.date")
    if node is None:
        return None
    text = node.get_text(strip=True)
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def main():
    committed, published = Path(sys.argv[1]), Path(sys.argv[2])
    committed_date, published_date = updated_date(committed), updated_date(published)

    if committed.is_file() and (published_date is None or (committed_date and committed_date >= published_date)):
        print(committed)
    elif published.is_file():
        print(published)


if __name__ == "__main__":
    main()
