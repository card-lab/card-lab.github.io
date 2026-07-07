# TODO

* Please help resolve this error in the github action:
```Run eval "$($HOME/miniforge/bin/conda shell.bash hook)"
  eval "$($HOME/miniforge/bin/conda shell.bash hook)"
  conda run -n card-lab quarto render people/current.qmd --to html --no-execute
  conda run -n card-lab quarto render people/alumni.qmd --to html --no-execute
  conda run -n card-lab quarto render people/principal-investigator.qmd --to html
  conda run -n card-lab quarto render research/bibliometrics.ipynb --to html
  conda run -n card-lab quarto render research/scientometrics.ipynb --to html
  shell: /usr/bin/bash -e {0}
  env:
    FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true
    BUNDLE_EXT: linux-amd64.deb

[pre-render] Timeline slideshow photo source not found; skipping sync: private/Timeline Slideshow Photos
[pre-render] Individual file render detected; skipping people action pre-render

pandoc 
  to: html
  output-file: current.html
  standalone: true
  title-prefix: Critical Alloy Research & Discovery Lab
  section-divs: true
  html-math-method: mathjax
  wrap: none
  default-image-extension: png
  css:
    - ../styles.css
  toc: true
  email-obfuscation: javascript
  variables: {}
  
metadata
  document-css: false
  link-citations: true
  date-format: long
  lang: en
  engines:
    - path: /opt/quarto/share/extension-subtrees/julia-engine/_extensions/julia-engine/julia-engine.js
  theme:
    - cosmo
    - brand
  description-meta: The Critical Alloy Research & Discovery Lab (CARD Lab) at the University of Cincinnati develops and designs metallic materials critical for future economic and energy security.
  date: last-modified
  title: Current Group Members
  listing:
    type: grid
    contents: current
    template: _partials/people-listing.ejs.md
    sort: date asc
    image-placeholder: files/images/anon.jpg
    date-format: MMM YYYY
    categories: numbered
    image-height: 250px
    grid-columns: 4
    max-items: 100
    filter-ui:
      - categories
      - date
      - title
  
[post-render] Synced 31 asset(s) from files/photos/People to docs/files/photos/People
[post-render] Synced 19 asset(s) from files/photos/Timeline Slideshow Photos to docs/files/photos/Timeline Slideshow Photos
[post-render] Individual file render detected; skipping sitemap generation
[post-render] Individual file render detected; skipping QC checks
[post-render] qc_report.html not found; skipping copy
[post-render] Individual file render detected; skipping qc_report render

Output created: ../docs/people/current.html

[pre-render] Timeline slideshow photo source not found; skipping sync: private/Timeline Slideshow Photos
[pre-render] Individual file render detected; skipping people action pre-render

pandoc 
  to: html
  output-file: alumni.html
  standalone: true
  title-prefix: Critical Alloy Research & Discovery Lab
  section-divs: true
  html-math-method: mathjax
  wrap: none
  default-image-extension: png
  css:
    - ../styles.css
  toc: true
  email-obfuscation: javascript
  variables: {}
  
metadata
  document-css: false
  link-citations: true
  date-format: long
  lang: en
  engines:
    - path: /opt/quarto/share/extension-subtrees/julia-engine/_extensions/julia-engine/julia-engine.js
  theme:
    - cosmo
    - brand
  description-meta: The Critical Alloy Research & Discovery Lab (CARD Lab) at the University of Cincinnati develops and designs metallic materials critical for future economic and energy security.
  date: last-modified
  title: Alumni
  listing:
    type: grid
    contents: alumni
    template: _partials/people-listing.ejs.md
    sort: member-to desc
    image-placeholder: files/images/anon.jpg
    date-format: MMM YYYY
    image-height: 250px
    grid-columns: 4
    page-size: 100
    categories: numbered
    filter-ui:
      - categories
      - date
      - title
  
[post-render] Synced 31 asset(s) from files/photos/People to docs/files/photos/People
[post-render] Synced 19 asset(s) from files/photos/Timeline Slideshow Photos to docs/files/photos/Timeline Slideshow Photos
[post-render] Individual file render detected; skipping sitemap generation
[post-render] Individual file render detected; skipping QC checks
[post-render] qc_report.html not found; skipping copy
[post-render] Individual file render detected; skipping qc_report render

Output created: ../docs/people/alumni.html

[pre-render] Timeline slideshow photo source not found; skipping sync: private/Timeline Slideshow Photos
[pre-render] Individual file render detected; skipping people action pre-render


Starting card-lab kernel...[IPKernelApp] WARNING | Kernel is running over TCP without encryption. All communication (including code and outputs) is sent in plain text and is susceptible to eavesdropping. Use IPC transport or launch with kernel manager-provisioned CurveZMQ keys to enable transport encryption.
Done

Executing 'principal-investigator.quarto_ipynb'
  Cell 1/6: ''...Done
  Cell 2/6: ''...Done
  Cell 3/6: ''...Done
  Cell 4/6: ''...Done
  Cell 5/6: ''...Done
  Cell 6/6: ''...Done

pandoc 
  to: html
  output-file: principal-investigator.html
  standalone: true
  title-prefix: Critical Alloy Research & Discovery Lab
  section-divs: true
  html-math-method: mathjax
  wrap: none
  default-image-extension: png
  css:
    - ../styles.css
  toc: true
  email-obfuscation: javascript
  variables: {}
  
metadata
  document-css: false
  link-citations: true
  lang: en
  engines:
    - path: /opt/quarto/share/extension-subtrees/julia-engine/_extensions/julia-engine/julia-engine.js
  theme:
    - cosmo
    - brand
  description-meta: The Critical Alloy Research & Discovery Lab (CARD Lab) at the University of Cincinnati develops and designs metallic materials critical for future economic and energy security.
  date: today
  title: About the PI
  categories:
    - Principal Investigator
  date-format: DD MMMM YYYY
  about:
    template: trestles
    image: ../files/site/Payton_Eric_2_crop.jpg
    image-alt: photograph of Prof Eric Payton taken at the University of Cincinnati in August 2022
    image-shape: round
    links:
      - text: '{{< iconify mdi linkedin >}}'
        url: https://www.linkedin.com/in/paytonej
      - text: '{{< iconify simple-icons orcid >}}'
        url: https://orcid.org/0000-0001-7478-9372
      - text: '{{< iconify academicons google-scholar >}}'
        url: https://scholar.google.com/citations?user=abYsKG8AAAAJ&hl=en
      - text: '{{< iconify mdi github >}}'
        url: https://github.com/paytonej
      - text: '![Flag of United States](https://flagcdn.com/us.svg){width=0.25in}'
        url: https://en.wikipedia.org/wiki/United_States_of_America
      - text: '![Flag of Ohio](https://flagcdn.com/us-oh.svg){width=0.25in}'
        url: https://en.wikipedia.org/wiki/Ohio
      - text: '![Flag of New York](https://flagcdn.com/us-ny.svg){width=0.25in}'
        url: https://en.wikipedia.org/wiki/New_York_(state)
      - text: '![Flag of Virginia](https://flagcdn.com/us-va.svg){width=0.25in}'
        url: https://en.wikipedia.org/wiki/Virginia
      - text: '![Flag of Indiana](https://flagcdn.com/us-in.svg){width=0.25in}'
        url: https://en.wikipedia.org/wiki/Indiana
      - text: '![Flag of North Dakota](https://flagcdn.com/us-nd.svg){width=0.25in}'
        url: https://en.wikipedia.org/wiki/North_Dakota
      - text: '![Flag of Texas](https://flagcdn.com/us-tx.svg){width=0.25in}'
        url: https://en.wikipedia.org/wiki/Texas
      - text: '![Flag of Germany](https://flagcdn.com/de.svg){width=0.25in}'
        url: https://en.wikipedia.org/wiki/Germany
  jupyter: card-lab
  
[post-render] Synced 31 asset(s) from files/photos/People to docs/files/photos/People
[post-render] Synced 19 asset(s) from files/photos/Timeline Slideshow Photos to docs/files/photos/Timeline Slideshow Photos
[post-render] Individual file render detected; skipping sitemap generation
[post-render] Individual file render detected; skipping QC checks
[post-render] qc_report.html not found; skipping copy
[post-render] Individual file render detected; skipping qc_report render

Output created: ../docs/people/principal-investigator.html

[pre-render] Timeline slideshow photo source not found; skipping sync: private/Timeline Slideshow Photos
[pre-render] Individual file render detected; skipping people action pre-render


Starting card-lab kernel...[IPKernelApp] WARNING | Kernel is running over TCP without encryption. All communication (including code and outputs) is sent in plain text and is susceptible to eavesdropping. Use IPC transport or launch with kernel manager-provisioned CurveZMQ keys to enable transport encryption.
Done

Executing 'bibliometrics.ipynb'
  Cell 1/16: ''...Done
  Cell 2/16: ''...Done
  Cell 3/16: ''...Done
  Cell 4/16: ''...Done
  Cell 5/16: ''...Done
  Cell 6/16: ''...Done
  Cell 7/16: ''...Done
  Cell 8/16: ''...Done
  Cell 9/16: ''...Done
  Cell 10/16: ''...Done
  Cell 11/16: ''...Done
  Cell 12/16: ''...Done
  Cell 13/16: ''...Done
  Cell 14/16: ''...Done
  Cell 15/16: ''...Done
  Cell 16/16: ''...Done

pandoc 
  to: html
  output-file: bibliometrics.html
  standalone: true
  title-prefix: Critical Alloy Research & Discovery Lab
  section-divs: true
  html-math-method: mathjax
  wrap: none
  default-image-extension: png
  css:
    - ../styles.css
  toc: true
  email-obfuscation: javascript
  variables: {}
  
metadata
  document-css: false
  link-citations: true
  lang: en
  engines:
    - path: /opt/quarto/share/extension-subtrees/julia-engine/_extensions/julia-engine/julia-engine.js
  theme:
    - cosmo
    - brand
  description-meta: The Critical Alloy Research & Discovery Lab (CARD Lab) at the University of Cincinnati develops and designs metallic materials critical for future economic and energy security.
  date: today
  title: Bibliometrics
  date-format: DD MMMM YYYY
  jupyter: card-lab
  
[post-render] Synced 31 asset(s) from files/photos/People to docs/files/photos/People
[post-render] Synced 19 asset(s) from files/photos/Timeline Slideshow Photos to docs/files/photos/Timeline Slideshow Photos
[post-render] Individual file render detected; skipping sitemap generation
[post-render] Individual file render detected; skipping QC checks
[post-render] qc_report.html not found; skipping copy
[post-render] Individual file render detected; skipping qc_report render

Output created: ../docs/research/bibliometrics.html

[pre-render] Timeline slideshow photo source not found; skipping sync: private/Timeline Slideshow Photos
[pre-render] Individual file render detected; skipping people action pre-render


Starting card-lab kernel...[IPKernelApp] WARNING | Kernel is running over TCP without encryption. All communication (including code and outputs) is sent in plain text and is susceptible to eavesdropping. Use IPC transport or launch with kernel manager-provisioned CurveZMQ keys to enable transport encryption.
Done

Executing 'scientometrics.ipynb'
  Cell 1/14: ''...Done
  Cell 2/14: ''...Done
  Cell 3/14: ''...Done
  Cell 4/14: ''...Done
  Cell 5/14: ''...Done
  Cell 6/14: ''...Done
  Cell 7/14: ''...Done
  Cell 8/14: ''...Done
  Cell 9/14: ''...Done
  Cell 10/14: ''...

An error occurred while executing the following cell:
------------------

plt.figure(figsize=(12, 7))
plt.imshow(wordcloud, interpolation="bilinear")
plt.axis("off")
plt.show()
------------------


---------------------------------------------------------------------------
NameError                                 Traceback (most recent call last)
Cell In[10], line 2
      1 plt.figure(figsize=(12, 7))
----> 2 plt.imshow(wordcloud, interpolation="bilinear")
      3 plt.axis("off")
      4 plt.show()

NameError: name 'wordcloud' is not defined

WARN: Error encountered when rendering files
ERROR conda.cli.main_run:execute(148): `conda run quarto render research/scientometrics.ipynb --to html` failed. (See above for error)
Error: Process completed with exit code 1.
```

* Why is there a "null" showing up in the pie charts for demographics?
* Github workflow still running into failures
* Group roles legend still covers up bottom of plots
* Remove which, when, has from the word cloud list
* PI citation map should break down by continent like the others
* "Connect with MMIE" links are broken
* Move site map to a different location. Perhaps as an icon on the left side.
* Cincinnati page is redundant with research @ UC page content
* Pandat and Rolling Mill listings are different from the others in formatting.
* Create front page presentation explaining the group.
* Move teaching to my own separate blog page on my own account.