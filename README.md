# Critical Alloy Research and Discovery Laboratory Website

<https://card-lab.github.io>

This repository contains the source code for the Critical Alloy Research and Discovery Laboratory (CARD Lab) website, developed using [Quarto](https://quarto.org/). 

The CARD Lab is part of the [University of Cincinnati](https://www.uc.edu)'s [Department of Mechanical and Materials Engineering](https://ceas.uc.edu/academics/departments/mechanical-materials-engineering.html), in the [College of Engineering and Applied Science](https://ceas.uc.edu/).

# Vision

Academic websites often become outdated because they require manual updates, and faculty have limited time to maintain them.

My vision for this site is to:

* Be able to have dynamic content simply by keeping **an Excel file**, **a shared pictures folder**, and **a Zotero library** up-to-date.
    + From a private Excel file, we pull in the lists of advisees, mentees, and students on whose committees I have served. I need to maintain this list anyway for annual reviews, my CV, and my reappointment, promotion, and tenure (RPT) dossier.
    + From the shared pictures folder, we create a revealjs slide show. I would like to keep a folder of photos documenting our group activities, outreach events, and conferences.
    + From the Zotero library, we pull in work products. I need to maintain this anyway for my CV, RPT dossier, and grant writing.
* Be able to re-use this content for CV, Annual Performance Reviews and RPT dossier.
* Be able to re-use this content for grant writing and evidence of broader impacts.

# Status of achieving the vision

* The people section is working. When the xlsx is updated, the necessary notebooks are executed via a pre-render script.
* The section that pulls from Zotero works for the work products section of the website but not from the people section.
   + Work products now use a repository cache file at `files/zotero-group-library.json`.
   + The cache refreshes weekly (and on demand) via the GitHub Action workflow `.github/workflows/fetch-zotero-items.yml`.
   + To force a refresh, run the `Fetch Zotero Items` workflow from the Actions tab.
* Group member profile photos now sync from `private/Group Member Photos/` into `files/photos/People/` during pre-render.
* Timeline slideshow photos now sync from `private/Timeline Slideshow Photos/` into `files/photos/Timeline Slideshow Photos/` during pre-render.
* A remaining challenge for re-use is reverse chronological ordering of items from Zotero, as well as display of all authors from presentations.

# CARD Lab Website Python and Quarto Environments

1. `quarto add mcanouil/quarto-iconify`
   - This command adds the Iconify package to your Quarto project, allowing you to use a wide range of icons in your documents.
2. Python environment
   - `conda install geopandas shapely cartogram ipykernel pandas matplotlib requests pycountry pyzotero numpy jupyter datetime pathlib xattr mendeleev bibtexparser wordcloud openpyxl`
   - `pip install pycountry usaddress`
   - To add an environment to the ipykernel, use `python -m ipykernel install --name myenv`

# Private People Spreadsheet in Repo

The people-generation notebooks now read from:

- `_people-action.ipynb` → `private/CARD Group Timeline.xlsx`
- `people/demographics.ipynb` → `../private/CARD Group Timeline.xlsx`
- `people/timeline.ipynb` → `../private/CARD Group Timeline.xlsx`

These notebooks are executed during Quarto pre-render via `scripts/pre-render-people-action.sh`, and run only when the spreadsheet content hash changes.

Recommended workflow for privacy in a public repo:

1. Keep the decrypted spreadsheet only locally at `private/CARD Group Timeline.xlsx` (ignored by git).
2. Commit only the encrypted file `private/CARD Group Timeline.xlsx.gpg`.
3. Decrypt locally before rendering pages, and re-encrypt before committing updates.

Helper scripts are provided:

- `scripts/encrypt-people-spreadsheet.sh`
- `scripts/decrypt-people-spreadsheet.sh`

Automatic encryption on render is also enabled via `_quarto.yaml`:

- `scripts/post-render-encrypt-private.sh` runs after `quarto render`.
- It updates `private/CARD Group Timeline.xlsx.gpg` when both the decrypted `.xlsx` file exists and `CARD_LAB_PEOPLE_SHEET_PASSPHRASE` is set.
- If either is missing, rendering still succeeds and encryption is skipped with a console message.

Use an environment variable for the passphrase:

- `export CARD_LAB_PEOPLE_SHEET_PASSPHRASE='your-passphrase'`

# GitHub Actions Render Behavior Without Private Resources

When publishing from GitHub Actions, this repository now sets
`CARD_LAB_SKIP_PRIVATE_RENDER_PATHS=1` in
`.github/workflows/publish.yml`.

This skips the private-dependent people pre-render path in
`scripts/pre-render-people-action.sh`, which would otherwise execute:

- `_people-action.ipynb`
- `people/demographics.ipynb`
- `people/timeline.ipynb`

Private-dependent inputs include:

- `private/CARD Group Timeline.xlsx`
- `private/Group Member Photos/*`
- `../private/hometown_coordinates.txt` (used by demographics notebook)

Result in CI (no private folder available):

- These private-dependent notebook steps are skipped.
- These private-dependent standard render documents are temporarily hidden from Quarto during CI:
   - `_people-action.ipynb`
   - `people/demographics.ipynb`
   - `people/timeline.ipynb`
   - `files/Research_Group_Timeline_Slideshow.qmd`
- Existing rendered resources already present in `docs/` remain unchanged.
- The timeline photo pre-render sync already exits cleanly when
   `private/Timeline Slideshow Photos` is missing, so it does not overwrite
   generated output with empty content.

## Usage

Generally, just:

`quarto publish gh-pages`

## TO DO

* Reduce redundancy in writing and modifying photos. If there is no change, don't re-write.
* quarto publish gh-pages giving the "Individual file render detected" error.
* Error on publishing: ```[post-render] qc_report.html not found; skipping copy
-z: -c: line 0: unexpected EOF while looking for matching `''
-z: -c: line 1: syntax error: unexpected end of file```
* Remove redundancy in writing people pages. If there is no change, don't re-write.
* Restore card-lab authorship name and add alt-text to flag images on people pages
* Overview of what the group does instead of photos
* Add alt text the flags. Requires resolving country code into a country name.
* Create a map and list of PI's references, for completeness
* make pre-uc.json download programmatically for automatic updates, and remove capitalization
* Improved site map
* Order the pages by number of publications, presentations, and citations
* New "group roles" visualization with the number of MS, PhD, and undergraduates working in the group as a treemap.
* Add AMCC to the facilities
* Add regional facilities and shared facilities