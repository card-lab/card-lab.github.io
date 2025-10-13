# Critical Alloy Research and Discovery Laboratory Website

<https://card-lab.github.io>

This repository contains the source code for the Critical Alloy Research and Discovery Laboratory (CARD Lab) website, developed using [Quarto](https://quarto.org/). 

The CARD Lab is part of the [University of Cincinnati](https://www.uc.edu)'s [Department of Mechanical and Materials Engineering](https://ceas.uc.edu/academics/departments/mechanical-materials-engineering.html), in the [College of Engineering and Applied Science](https://ceas.uc.edu/).

# Vision

Academic websites often become outdated because they require manual updates, and faculty have limited time to maintain them.

My vision for this site is to:

* Be able to have dynamic content simply by keeping **an Excel file**, **a shared pictures folder**, and **a Zotero library** up-to-date.
    + From the Excel file, we pull in the lists of advisees, mentees, and students on whose committees I have served. I need to maintain this list anyway for annual reviews, my CV, and my reappointment, promotion, and tenure (RPT) dossier.
    + From the shared pictures folder, we create a revealjs slide show. I would like to keep a folder of photos documenting our group activities, outreach events, and conferences.
    + From the Zotero library, we pull in work products. I need to maintain this anyway for my CV, RPT dossier, and grant writing.
* Be able to re-use this content for CV, Annual Performance Reviews and RPT dossier.
* Be able to re-use this content for grant writing and evidence of broader impacts.

# Status of achieving the vision
* The people section is mostly working. It requires re-rendering in quarto when the Excel file is updated, but a github action could be set up to do this automatically.
* The section that pulls from Zotero works for the work products section of the website but not from the people section.
* The pictures section does not yet pull from a private shared folder, but does pull from a local folder. This requires manual re-rendering in quarto for now.
* A remaining challenge for re-use is reverse chronological ordering of items from Zotero, as well as display of all authors from presentations.

# CARD Lab Website Python and Quarto Environments

1. `quarto add mcanouil/quarto-iconify`
   - This command adds the Iconify package to your Quarto project, allowing you to use a wide range of icons in your documents.
2. Python environment
   - `conda install geopandas shapely cartogram ipykernel pandas matplotlib requests pycountry pyzotero numpy jupyter datetime pathlib xattr mendeleev bibtexparser wordcloud openpyxl`
   - `pip install pycountry usaddress`
   - To add an environment to the ipykernel, use `python -m ipykernel install --name myenv`