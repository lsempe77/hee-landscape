# HEE evidence map — interactive

Static site for the health economic evaluation (HEE) evidence map, published at
<https://3ieimpact.pages.dev/hee/>. Plain HTML/JS served from `docs/`: no server, no build step.
**Anything pushed to `main` goes live.**

## Before you push

Several people push here, so it is easy to undo someone's recent design work (for example the
Overview cards' links) by editing an old copy of `docs/app.js`. To guard against that:

- **Once per clone**, turn on the shared git hook: `git config core.hooksPath .githooks`.
  Every push to `main` then runs `scripts/check_site_features.py` on what you are pushing and
  stops the push if a protected feature has gone missing, or if it would force-push over
  commits already on GitHub. A GitHub Action runs the same check after each push.
- `git pull` before you edit and before you push; edit `docs/app.js` and `docs/index.html` in
  place rather than pasting in a copy.
- Shipping a design feature others should keep? Add it to `FEATURES` in
  `scripts/check_site_features.py`. Removing one on purpose? Edit its entry in the same commit.
- **No keys in the repo.** Everything here is public, history included. Keep API keys (e.g.
  OpenRouter) in environment variables or a local `.env` (gitignored). The same hook runs
  `scripts/check_secrets.py` on every push, to any branch or remote, and stops it if something
  looks like a key, token, password or private key. `python scripts/check_secrets.py --history`
  scans every version ever committed (clean as of 3 Nov 2026). If a real key ever gets pushed,
  revoke it with the provider first; removing it from the repo does not undo the exposure.
- AI agents (Claude Code, Kilo, etc.) follow [CLAUDE.md](CLAUDE.md) / [AGENTS.md](AGENTS.md).

## Read first: Wellcome priority themes page (standalone export)

The current version is `exports/wellcome_themes_standalone_2026-11-25_v3/wellcome_priority_themes.html`.
These visual and wording choices were made on purpose (Nov 2026). **Keep them; do not undo or redo them.**

- **Build it from the scripts, never by hand.** Run `python scripts/build_wellcome_analysis_gbd_v6.py`, then
  `python scripts/export_wellcome_standalone_v2.py`. v6 writes only to `exports/wellcome_themes_v6_build/`
  (git-ignored), and the export goes to a new dated folder; neither touches `docs/`. Do not rebuild the
  standalone with v5 or `export_wellcome_standalone.py`: that brings back the old wording and drops the
  additions below.
- **17 studies added on review are counted in the themes.** These are Wellcome-funded publications that GBD
  codes to another condition, judged from title and abstract to fit a theme: 13 Infectious Diseases
  (antimicrobial stewardship, 4 HPV vaccine, 5 hepatitis C, 2 Group B strep vaccine, AIMS antibiotic
  prophylaxis), 1 Mental Health (MENISCUS), and 3 Climate & Health (palm-oil tax, red-meat tax, walking to
  work; sub-area "Mitigation with health co-benefits"). They are listed by record ID, with a reason for
  each, in `REVIEW_ADDED` in the v6 script. Totals: Infectious 6,346, Mental Health 1,913, Climate 105.
  129 Wellcome-funded publications are in the themes and 45 are beyond them (previously 112 and 62).
- **One integrated view, no toggle.** The ◆ marker appears only beside those 17 titles in each theme's
  "What the N publications cover" lists, with a hover note giving their GBD code and the reason. In
  Infectious Diseases and Mental Health they form an "Added on review (GBD codes another condition)" group.
  There is no ◆ note on the theme cards. A toggle version exists (`--toggle`) but was not chosen.
- **Technical details and sources** uses the wording agreed on 25 Nov 2026:
  - the funding share sentence ("Funding is recorded for X% of the current evidence base");
  - a shorter World Bank income sentence;
  - "Theme mapping." as its own heading, then one paragraph each for Infectious Diseases, Mental Health,
    HPV/hepatitis C classification and Climate & Health;
  - one ◆ "Added on review" line, which notes that other funders' publications were not reviewed this way.

  The old "Source: …" paragraph and the paragraph on how themes were defined were removed on purpose.
- Only Wellcome-funded publications were reviewed for additions, so Wellcome's theme counts are not
  directly comparable with other funders'. Keep that caveat if the page changes.
- **The live map is unchanged.** `docs/figures/wellcome_analysis.html` is still the v5, GBD-only page, which
  matches the manuscript. Changing the live page is a separate decision.

## Latest updates

Newest first; add a line here when you push something colleagues should know about.

- **25 Nov 2026: Wellcome standalone page, v6.** The 17 studies added on review are now counted in their
  themes and marked ◆ in the theme lists, and the Technical details have been rewritten. See "Read first"
  above. New scripts: `build_wellcome_analysis_gbd_v6.py` and `export_wellcome_standalone_v2.py`. The
  2026-10-21 standalone export was removed, and the live map is unchanged.

- **23 Oct 2026: Explorer HALY filter opens on All again.** Since 21 Oct the HALY type filter had no "All"
  option, so the Explorer opened (and reset) on No HALY: 22,095 studies, 0% using a QALY, and the CSV
  download held only those. "All" is back as the default (41,610 studies, 44% QALY).
- **23 Oct 2026: DOIs in the Countries study lists.** Clicking a cell in a country profile lists its studies;
  each now shows "DOI: …" linked to doi.org, or "Publication link: …" when there is no DOI (39,173 DOIs and
  2,270 web links; 99.6% of studies). Helper: `studyReference` in `docs/app.js`.
- **23 Oct 2026: Progress bar for "Download filtered studies (CSV)".** Shows MB loaded and percent while the
  titles and abstracts load (about 90 MB for all studies), then "Building the CSV file…".
  `docs/data/text/index.json` now lists each chunk's size; `scripts/build_study_text.py` writes them.
- **23 Oct 2026: Overview cards on Thematic analysis pages.** Authorship & access, Geography, Methods & metrics
  and Research funding open with their Overview card(s) above the figures. One map (`TILE_THEME` in
  `docs/app.js`) drives both the Overview card links and these cards.
- **23 Oct 2026: Overall QALY and DALY shares in "How health benefits are measured differs by country
  income".** Footer and caption now say 43.6% of all 41,610 studies report a QALY and 3.4% a DALY (income rows:
  27,897 single-country studies). Same all-records base as the manuscript (46.9% QALY or DALY), reviews
  included; keep the two in step if the manuscript changes. Figure: `fig_metric_pubyear_v2.webp`.
- **23 Oct 2026: Methods folder and Wellcome review files added to Git.** `methods/README.md` (where each
  analysis's code and outputs live; GBD coding record and reference tables), `scripts/export_wellcome_audit.py`
  and `scripts/export_wellcome_standalone.py`, and their outputs in `exports/` (Wellcome audit workbook,
  standalone Wellcome page, Infectious Diseases scope candidates for review).

- **22 Oct 2026: Income and region groupings made consistent.** Country-level views and figures (one dot or bar
  per country, all years pooled) now give each country the World Bank group most of its studies were published
  under, matching the publication-year rule used for studies (zero-study countries: the group held in most years
  2010–2026). Built by `scripts/build_country_income_pubyear.py` (`income_pub` in `countries.json`). "Model use
  across regions" now uses WHO regions. Figure captions corrected; the equity-trend burden line is now computed
  (85%, World Bank groups at the 2023 burden year) instead of a hardcoded 83%. New versioned scripts:
  `build_remaining_figures_reconciled_v2.R`, `build_funder_scorecard_v3.py`, `build_funder_scorecard_absolute_v2.py`,
  `build_research_burden_ratio_v2.py`, `build_denominator_audit_v2.py`, `build_income_pubyear_figures_v2.py`.

- **22 Oct 2026: Explorer download now has every title, plus abstracts.** "Download filtered studies" used
  to leave titles blank for the ~11,000 studies naming no country (titles came from the per-country files).
  It now reads the title and abstract of all 41,610 studies from `docs/data/text/` and adds an `abstract`
  column. Code: `scripts/build_study_text.py` (rerun when the master or `studies.json` changes).
- **22 Oct 2026: HALY type filter.** Bubbles are No HALY, Any HALY, QALY only, DALY only, and Both QALY
  and DALY; "only" now excludes studies reporting the other measure.

- **21 Oct 2026: Wellcome page, version 5.** Opens with "The three themes at a glance" (publications matching
  the themes → funder identified → Wellcome-funded, with each step's split by theme), then all 174
  Wellcome-funded publications (112 in the themes, 62 outside). Mental Health covers all mental health, with
  Wellcome's stated focus (anxiety, depression, psychosis) shown as a sourced subset; details sit behind "?"
  marks and collapsible sections. Code: `scripts/build_wellcome_analysis_gbd_v5.py`.
- **21 Oct 2026: "No funder identified" wording across the map.** Funders come from Crossref metadata, so a
  publication without one may still report funding in its full text; the site now says so (Explorer filter,
  Overview card, glance infographic, funder figures). The general top-funders chart is redrawn on the 41,610.

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
