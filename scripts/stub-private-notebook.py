#!/usr/bin/env python3
"""Write a placeholder notebook that keeps a private-dependent notebook's
YAML front matter (title, jupyter engine, format, ordering, etc.) but drops
every code cell.

CI hides notebooks like people/demographics.ipynb and people/timeline.ipynb
before `quarto render` because they need private data files that aren't
available on the runner. But the site sidebar links to these pages by
source path, and Quarto can only rewrite that link to the published .html
path if it can resolve a project input file at that path. With nothing
there, Quarto leaves the raw .ipynb href in the published site, which 404s
for every visitor. Leaving this stub behind lets Quarto resolve the link;
the placeholder's rendered output is then overwritten by the previously
published page later in the workflow.
"""
import json
import sys

PLACEHOLDER_TEXT = (
    "_Content temporarily unavailable during this automated build; "
    "the previously published version of this page will be restored "
    "after rendering._"
)


def main():
    source_path, dest_path = sys.argv[1], sys.argv[2]
    with open(source_path) as f:
        notebook = json.load(f)

    frontmatter_cell = next(
        cell for cell in notebook["cells"] if cell.get("cell_type") == "raw"
    )

    notebook["cells"] = [
        frontmatter_cell,
        {
            "cell_type": "markdown",
            "id": "placeholder",
            "metadata": {},
            "source": [PLACEHOLDER_TEXT],
        },
    ]

    with open(dest_path, "w") as f:
        json.dump(notebook, f, indent=1)
        f.write("\n")


if __name__ == "__main__":
    main()
