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
   + Work products now use a repository cache file at `files/zotero-items.json`.
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

## Usage

Generally, just:

`quarto publish gh-pages`

## TO DO

* Overview of what the group does instead of photos
* About UC page
* Improved site map
* Broken links checker
* Create a common blocked words list for all word clouds
* Order the pages by number of publications, presentations, and citations
* New "group roles" visualization with the number of MS, PhD, and undergraduates working in the group as a treemap.
* Add AMCC to the facilities
* Add regional facilities and shared facilities