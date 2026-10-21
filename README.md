# HEE evidence map — interactive

Static site for the health economic evaluation (HEE) evidence map, published at
<https://3ieimpact.pages.dev/hee/>. Plain HTML/JS served from `docs/`: no server, no build step.
**Anything pushed to `main` goes live.**

## Latest updates

Newest first; add a line here when you push something colleagues should know about.

- **21 Oct 2026: Wellcome priority themes page redesigned.** View it at
  <https://3ieimpact.pages.dev/hee/figures/wellcome_analysis.html> (the section is still hidden in the
  map's menus). Built on the v2.1 master (41,610) with publication-year income; shows funding
  reporting explicitly, and Wellcome's share uses publications that report a funder. Code:
  `scripts/build_wellcome_analysis_gbd_v4.py` (v3 has the same data in the old layout; v2 archived).
- **21 Oct 2026: Infectious Diseases scope candidates.** `scripts/build_infectious_candidates.py` lists
  hepatitis, vaccine and antimicrobial-resistance publications that GBD codes outside the infectious
  theme. The scope decision is pending; theme counts are unchanged.
- **21 Oct 2026: Old site builds unpublished.** `docs/v1`–`v3` moved to `archive/site_builds/`.
- **20 Oct 2026: Wellcome-funded publications by year** figure in `exports/wellcome_by_year_2026-10-20/`.
- **20 Oct 2026: Repository tidied.** Every script is indexed by purpose in
  [scripts/README.md](scripts/README.md); superseded scripts are in `scripts/archive/`, older exports
  in `archive/exports/`.

**Current data: the HEE v2.1 master, 41,610 included full economic evaluations** (2010–2026). That
is the dataset team's v2 (41,657) without 44 linked publications, 2 trial registrations without
results and 1 retracted paper (`docs/data/dict.json`, `meta.publication_reconciliation`). Diseases
are coded to GBD 2023 causes (`docs/data/disease_gbd.json`). The interim manuscript uses the same
41,610.

| Folder | What it holds | Published? |
|---|---|---|
| `docs/` | the website: `index.html`, `app.js`, `styles.css`, `data/*.json`, `figures/` | yes |
| `scripts/` | the scripts that build `docs/data`, `docs/figures` and the manuscript figures; index in [scripts/README.md](scripts/README.md) | no |
| `manuscript figures Oct 19/` | figures for the interim manuscript | no |
| `exports/` | dated exploratory outputs and review records (e.g. the Climate & Health decisions the Wellcome view cites) | no |
| `output/` | figures written by the country concentration scripts | no |
| `archive/` | superseded outputs and the earlier site builds `site_builds/v1`–`v3`; see [archive/README.md](archive/README.md) | no |
| `tests/` | tests for the denominator audit, review screening and Wellcome analysis | no |
| `data/raw/` | raw inputs (master dataset and lookups); git-ignored, ask the team for a copy | no |

After changing `docs/app.js` or any file in `docs/data/`, update `BUILD` at the top of `app.js` and
the matching `?v=` in `docs/index.html`, so browsers fetch the new files instead of cached copies.

Runtime dependencies are pinned jsdelivr CDNs (plotly.js-dist-min 2.35.2, tom-select 2.3.1,
noUiSlider 15.8.1) and Google Fonts (Newsreader, Inter); html2canvas 1.4.1 is bundled in
`docs/vendor/`.

The sister map for health financing functions is
[suvarnapande/hff-landscape](https://github.com/suvarnapande/hff-landscape)
(<https://3ieimpact.pages.dev/hff/>). Studies in both maps (about 1,870) are counted in each map
on its own; never add the two totals.
