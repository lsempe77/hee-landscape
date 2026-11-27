# Wellcome priority themes dashboard v3: implementation report

## Start here: current state (v3.10, 27 Nov 2026)

This section is the up-to-date summary. The sections after it are the version history: why each change was made. **Where the history disagrees with this section, this section is correct.** For example, v3's "all infectious causes" scope and v3.1's "three areas" were both superseded.

### Current page and how to rebuild it

- **Current page:** `wellcome_priority_themes-v3.10.html`.
- **Rebuild:**
  ```
  python scripts/build_wellcome_analysis_gbd_v15.py
  python scripts/export_wellcome_standalone_v3.py --build exports/wellcome_themes_v15_build --out <new file>
  ```
- **To change it:** copy v15 to `_v16.py`, edit the copy and export to a new file name. Never edit the HTML by hand. The export refuses to overwrite an existing file.

### Earlier pages (all kept unchanged, in `Archive/`)

The main folder holds only the current page, the spec, this report and the evidence files. Every earlier HTML version is in `Archive/`, inside this folder.

| Page | Builder | What it was |
|---|---|---|
| v2 | v6 | Superseded design |
| v3 | v7, before it was edited for v3.1 (cannot be rebuilt exactly) | All infectious causes |
| v3.1 | v7 | TB + diarrhoeal only |
| v3.2 | v8 | Four focus areas |
| v3.3 | v9 | Added WHO evidence |
| v3.4 | v10 | Layout fixes; same counts as v3.2 and v3.3 |
| v3.5 | v11 | New colours, publication CSV, DOI links, shorter technical note; same counts |
| v3.6 | v12 | Grouped list of uncaptured Wellcome-funded publications removed; same counts |
| v3.7 | v13 (draft) | Intermediate draft of the v3.8 wording; not for use |
| v3.8 | v13 | Tone review of the technical note, crosswalk and theme criteria; same counts |
| v3.9 | v14 | Visual refresh (cards, gradient header, tinted tiles, cool greys); same counts and wording |
| v3.10 | v15 | Current: "About the thematic mapping" link removed from the top banner |

### How to make the next version (checklist)

1. **Pull first.** Run `git pull`, then read this "Start here" section and README "Read first".
2. **Copy the latest builder** to the next number (`scripts/build_wellcome_analysis_gbd_v15.py` → `_v16.py`). Make the changes in the copy. Never edit an exported HTML file by hand.
3. **Build.** Run `python scripts/build_wellcome_analysis_gbd_v16.py`. It must print all checks `True`; if it stops, fix the cause, and do not weaken a check.
4. **Export to a new file name.** Run `python scripts/export_wellcome_standalone_v3.py --build exports/wellcome_themes_v16_build --out exports/wellcome_themes_standalone_2026-11-25_v3/wellcome_priority_themes-v3.11.html`. Use the next free number; the export refuses to overwrite.
5. **Check the page in a browser.** Look at desktop and phone width, both theme tabs, the trend toggle, the technical note and the downloads.
6. **Archive the previous page.** Move it into `Archive/`, so the main folder keeps only the current page.
7. **Update the docs:**
   - this "Start here" section: current page, rebuild commands, table of earlier pages, and any new rule;
   - add a short history entry at the end of this report;
   - update README "Read first", and the version and builder named in `CLAUDE.md` and `AGENTS.md`;
   - add the new build folder to `.gitignore`.
8. **Run the secrets check.** `python scripts/check_secrets.py` must print OK. Commit and push only when the owner agrees: pushing to `main` deploys the live site, although this export folder is not part of it.

### Scope: settled decisions (user, 27 Nov 2026)

| Theme | Wellcome's area (source) | GBD 2023 code(s) | Status |
|---|---|---|---|
| Infectious Diseases | Tuberculosis (ID page PDF, p.3) | Tuberculosis | Exact |
| Infectious Diseases | Cholera (ID page PDF, p.3) | Diarrheal diseases | **Kept on purpose** as a broad proxy (GBD has no cholera cause); flagged on page |
| Infectious Diseases | Vector-borne diseases "such as schistosomiasis, leishmaniasis and dengue" (ID page PDF, p.3) | Malaria, Dengue, Leishmaniasis, Schistosomiasis, Chagas disease, Lymphatic filariasis, Onchocerciasis, Zika virus, Yellow fever, African trypanosomiasis | Whole category, chosen for consistency with "all forms of psychotic disorders". All ten are in the WHO fact sheet table (PDF) |
| Infectious Diseases | Drug-resistant infections (ID page PDF, p.3) | none | Not representable |
| Mental Health | Anxiety, incl. OCD and PTSD (MH page PDF p.1; Award call) | Anxiety disorders | Fits; PTSD/OCD coding inconsistency noted (see below) |
| Mental Health | Depression, incl. post-natal (same sources) | Depressive disorders | Exact |
| Mental Health | Psychosis, incl. schizophrenia, postpartum psychosis, bipolar (Award call) | Schizophrenia; Bipolar disorder | Fits; postpartum psychosis has no GBD code (0 publications in the map) |
| Mental Health | Early intervention (MH page) | none | Not representable. All ages included: do not add "young people" wording |

### Rules not to break

1. **GBD codes only, the same for every funder.** No title or abstract screening adds publications.
   - The 17 v2 "added on review" studies stay excluded: only Wellcome-funded studies were screened, which is not comparable with other funders.
   - Title searches in this report were checks only.
2. **Mixed GBD codes are excluded**, even when they contain eligible diseases:
   - encephalitis (Japanese and tick-borne encephalitis, West Nile);
   - other neglected tropical diseases (chikungunya, Rift Valley fever, Crimean-Congo haemorrhagic fever, plague, scrub typhus);
   - other unspecified infectious diseases (Lyme disease);
   - "Mental disorders" with no specific condition;
   - broad infection groups.

   This affects about 35 vector-borne publications, 1 Wellcome-funded (Japanese encephalitis, Bangladesh), and is stated on the page.
3. **"Other mental disorders" is not added** (user decision, 27 Nov 2026), even though it holds 17 PTSD and 11 OCD studies (1 Wellcome-funded). Fix this only in the shared GBD coding, for all funders, with team approval, because the manuscript uses the same coding.
4. **Climate & Health stays out** of every displayed figure.
5. **Spec wording and terms:**
   - Keep the spec's introductory text and interpretive note.
   - Use neutral terms ("captured / not captured by the thematic mapping").
   - Say "studies" or "publications", not "economic evaluations".
6. **Trend charts:** line charts only. The annual view has a fixed 0–100 axis with ticks at 0/30/60/90; the cumulative view has its own axis; 2026 is drawn as a partial year.
7. **The builder stops** if any count check fails, if the crosswalk table's codes differ from the codes used for counting, or if "Climate", "◆" or "added on review" appears outside the technical note. Do not weaken these checks.
8. **Colours are validated** (Wellcome #5530C8, other funders #B9A6F2, not identified #E3E4EC; income #0B7FA3 / #E5793A / #CDD3DD). The v3.9 look (white cards on a cool background, gradient header, tinted headline tiles, violet heading accents) is the agreed design. Re-run the palette validator if you change them.
9. **Keep the technical note short.** It is based on the user's draft (27 Nov 2026), checked against the final codes. Add detail to this report, not to the page.
10. **No grouped list of uncaptured Wellcome-funded publications** (user decision, 27 Nov 2026). Topic groups made them look like coding misses and hid why they are not mapped. This departs on purpose from the v3 spec, which asked for an "Other Wellcome-funded HEE publications" list. The count stays in the coverage bar; the CSV lists them ungrouped with GBD codes.
11. **Tone.** Present the mapping as the closest match possible with GBD codes, with limitations stated openly (user decision, 27 Nov 2026). Avoid wording that implies the team mapped wrongly; v3.8 removed "overly broad proxy", "partial fit", "flagged for a coding fix", "not reviewed publication by publication", "may miss relevant publications" and "has not been assessed". Facts are unchanged. Internal issues, such as the PTSD/OCD coding and title-search counts, belong in this report, not on the page.

### Current numbers (dataset: master v2.1, 41,610 publications)

| Set | Publications | Funder identified | Wellcome-funded | Wellcome rank |
|---|---|---|---|---|
| Both themes (unique) | 2,368 | 768 (32.4%) | 43 (5.6% of funder identified) | — |
| Infectious Diseases | 1,277 | 413 | 36 | 2nd of 457 |
| Mental Health | 1,092 | 355 | 7 | joint 6th of 310 |

- Full map: 174 Wellcome-funded publications, 43 captured and 131 not captured.
- 1 publication is in both themes.

### Evidence: sources for Wellcome's and WHO's priorities

| Source | Live URL | Local copy (not in git) |
|---|---|---|
| Wellcome, Infectious Disease priority page ("Our focus includes", p.3) | https://wellcome.org/our-priorities/infectious-disease | `Infectious Disease _ Our priorities _ Wellcome.pdf`, saved 27 Nov 2026 20:05 |
| Wellcome, Mental Health priority page (mission, p.1) | https://wellcome.org/our-priorities/mental-health | `Mental Health _ Our priorities _ Wellcome.pdf`, saved 27 Nov 2026 20:06 |
| Wellcome, Mental Health Award call (scope: anxiety incl. OCD and PTSD; depression incl. post-natal; psychotic disorders incl. schizophrenia, postpartum psychosis and bipolar) | https://wellcome.org/research-funding/schemes/mental-health-award-transforming-early-intervention | `Mental Health Award call - scope text (copied 27 Nov 2026).txt` (in git) |
| WHO, "Vector-borne diseases" fact sheet (26 Sep 2024; table of diseases by vector) | https://www.who.int/news-room/fact-sheets/detail/vector-borne-diseases | `Vector-borne diseases.pdf`, saved 27 Nov 2026 20:21 |

The PDFs are copies of other organisations' web pages, so they are git-ignored. They are kept on the preparer's machine only. Anyone checking the sources should open the live URLs; the wording quoted on the page was checked against the saved copies on 27 Nov 2026. Pages can change over time.

**Lesson learned:** an early version said Wellcome names three Infectious Disease areas. That came from web-search summaries, and the saved page shows four. **Check any new claim about Wellcome's priorities against a saved page, not a search summary.**

### Still open

1. **Optional:** save a local copy of the Mental Health Award call page; it is not for git. Its scope text is already saved as a .txt file, and the URL is in the evidence table.
2. **PTSD/OCD coding fix** in the shared GBD coding (rule 3).
3. **Untested:** the PNG and CSV download clicks (the CSV contents were checked: 174 rows, 43 captured, all with DOI links), print preview, embedding in the live site and screen readers. Desktop (1280px) and mobile (390px) layouts, tabs, the trend toggle, keyboard tooltips and the methodology link were checked in headless Chrome.

---

# Version history

## 1. Files and data

| | |
|---|---|
| Output | `wellcome_priority_themes-v3.html` (1.1 MB, self-contained except Google Fonts, as in v2) |
| Preserved unchanged | `wellcome_priority_themes-v2.html`, all files in `data/raw/`, `scripts/build_wellcome_analysis_gbd_v6.py`, `scripts/export_wellcome_standalone_v2.py` |
| New scripts | `scripts/build_wellcome_analysis_gbd_v7.py` (analysis and page) → `exports/wellcome_themes_v7_build/` (git-ignored); `scripts/export_wellcome_standalone_v3.py` (packs the page, embeds CSV, JSON and html2canvas; refuses to overwrite) |
| Rebuild | `python scripts/build_wellcome_analysis_gbd_v7.py` then `python scripts/export_wellcome_standalone_v3.py` |
| Dataset | `data/raw/hee_analysis_master_v2_1.csv` (41,610 eligible publications, SHA-256 `fb0bc6dfb116…`); GBD 2023 team coding, share v2.1 (received 14 October 2026); publications 2010 to 3 August 2026 |
| Funding rules | Unchanged: v7 imports v6's input validation and funder normalisation (Crossref funders; Wellcome Trust named, Burroughs Wellcome excluded) |

No source data changed. The full-map Wellcome count (174) and the publication-year trend are the same as in v2.

## 2. Crosswalk and exclusions

Eligibility was set from the documented specifications (`methods/README.md`, v5/v6 builder constants) before any revised funding result was calculated. The same rule applies to every publication, whatever its funder.

| Theme | Priority area | Eligible GBD code(s) | Status |
|---|---|---|---|
| Infectious Diseases | Infectious disease (previously agreed definition) | 5 GBD level-2 infectious groups | Confirmed, but broad |
| Infectious Diseases | Infection, disease not stated | Team group "Infections, disease not stated" | **Flagged.** Retained as previously agreed. 676 publications are in the theme only through this group (1 Wellcome-funded). |
| Infectious Diseases | Cross-cutting (vaccines, drug resistance, epidemic preparedness) | none | Not representable by GBD codes |
| Mental Health | Depression / Anxiety | Depressive disorders / Anxiety disorders (L3) | Confirmed |
| Mental Health | Psychosis | Schizophrenia; Bipolar disorder (L3) | Previously agreed judgement (bipolar disorder: Wellcome call lists it among psychotic disorders) |
| Mental Health | Early intervention | none | Not representable |

Excluded from all displayed analyses:

- Climate & Health.
- The 17 v6 "added on review" publications.
- Other mental disorders and substance use disorders, which were in the broad v5/v6 Mental Health theme.
- 200 publications coded only to "Mental disorders" with no level-3 condition (1 Wellcome-funded). **Flagged**, because they cannot be assigned to the focus conditions.

**Needs a decision:**

1. **Infectious Diseases scope.** The spec asks for Wellcome's *specified* priority areas, not the whole theme. The only agreed definition found covers all infectious causes. The proposed wider scope (`exports/infectious_scope_candidates_2026-10-21.xlsx`) was never approved. No replacement was inferred.
2. **"Infections, disease not stated": keep or drop.**
3. **Bipolar disorder in the psychosis category.** Confirm.

## 3. Recalculated totals (unit: unique publication)

| Set | n | Funder identified (% of n) | Wellcome-funded (% of funder identified) | Other funders only | Funder not identified |
|---|---|---|---|---|---|
| All mapped (I ∪ M) | 7,416 (17.8% of 41,610) | 2,329 (31.4%) | 99 (4.3%; 1.3% of n) | 2,230 | 5,087 |
| Infectious Diseases | 6,333 | 1,976 (31.2%) | 92 (4.7%) | 1,884 | 4,357 |
| Mental Health | 1,092 | 355 (32.5%) | 7 (2.0%) | 348 | 737 |

- I ∩ M = 9 publications, none of them Wellcome-funded.
- Wellcome rank: Infectious Diseases 4th of 1,665 identified funders; Mental Health joint 6th of 310.
- Full map: W = 174, of which 99 are captured by the mapping (56.9%) and 75 are not (43.1%).

Change from v2:

| Theme | v2 n | v2 Wellcome-funded | v3 n | v3 Wellcome-funded | Reason |
|---|---|---|---|---|---|
| Infectious Diseases | 6,346 | 105 | 6,333 | 92 | 13 review additions removed |
| Mental Health | 1,913 | 17 | 1,092 | 7 | Restricted to focus conditions; 1 review addition removed |
| Climate & Health | 105 | 7 | removed | removed | Excluded from v3 |

**Reconciliation checks:** all pass, and the build stops if any fails.

- W ⊆ F.
- Funding segments sum to n for each theme and for the union.
- Captured plus not captured = W.
- |I ∪ M| = |I| + |M| − |I ∩ M|.
- The trend sums to W.
- The unmatched lists sum to 75.
- Record IDs are unique.

## 4. Charts

| | Annual | Cumulative |
|---|---|---|
| Axis | Fixed 0–100, ticks at 0/30/60/90 | Zero-based, own rounded axis: 0–200, ticks every 50 |
| Notes | Annual maximum is 24 (2021), so the axis ceiling was not raised | — |

Both views:

- Line charts with straight segments.
- 2026 is shown with a dashed final segment and a hollow point, plus an explanatory note.
- Exact counts appear on hover, or with the arrow keys when the chart has keyboard focus.

Proportions:

- Desktop plot area is 870 × 290 (3.0:1).
- Below 640px the plot is about 1.8:1, with fewer year labels.

## 5. Tests performed (headless Chrome)

**Verified:**

- Rendered at 1280px and at 390px (in an iframe), with no horizontal overflow after fixes.
- Explore theme activates the Mental Health tab and scrolls to it.
- Tabs switch, including with the arrow keys.
- Annual/cumulative toggle and its axis ticks, tooltip text and keyboard navigation.
- The "About the thematic mapping" link opens the methodology.
- html2canvas is embedded.
- No "Climate", "◆" or "added on review" text appears outside the methodology. The build also checks this.

**Not tested:**

- The actual PNG download file.
- Print preview. The CSS shows both theme panels and hides controls, and the methodology opens on `beforeprint`.
- Embedding in the live site iframe.
- Screen readers.
- Offline use: fonts still come from Google Fonts.

## 6. Design notes

- Income-group colours changed. High income is now slate blue rather than purple, so it is not confused with the purple used for Wellcome funding.
- In the Mental Health theme Wellcome's segment is very small (7 of 1,092). It is identified by tooltip and figures, not by a widened bar.

## v3.1 update (27 Nov 2026): Infectious Diseases narrowed to Wellcome's named areas

Output: `wellcome_priority_themes-v3.1.html`. The v3 file is kept unchanged.

Wellcome's Infectious Disease priority page (https://wellcome.org/our-priorities/infectious-disease, checked 27 Nov 2026) names three areas: tuberculosis, cholera and drug-resistant infections. The scope below was chosen by the user.

| Priority area | GBD 2023 code | Status |
|---|---|---|
| Tuberculosis | Tuberculosis (level 3) | Confirmed |
| Cholera | Diarrheal diseases (level 3) | Flagged: overly broad proxy (includes rotavirus etc.); GBD has no cholera cause |
| Drug-resistant infections | none | Not representable by GBD codes |

This replaces question 1 in section 2. Question 2 ("Infections, disease not stated") no longer applies, because that group is now excluded. Mental Health is unchanged.

Revised totals:

| Set | n | Funder identified (% of n) | Wellcome-funded (% of funder identified) | Wellcome rank |
|---|---|---|---|---|
| All mapped | 1,944 (4.7% of 41,610) | 621 (31.9%) | 23 (3.7%) | — |
| Infectious Diseases | 852 (TB 522, diarrhoeal 333, 3 in both) | 266 (31.2%) | 16 (6.0%) | Joint 5th of 307 |
| Mental Health | 1,092 | 355 (32.5%) | 7 (2.0%) | Joint 6th of 310 |

Other figures:

- The two themes do not overlap.
- Full map: 174 Wellcome-funded publications, of which 23 are captured (13.2%) and 151 are not (86.8%).
- Not eligible: 5,481 publications with other infectious causes (76 Wellcome-funded), shown as the first group under "Other Wellcome-funded HEE publications". 662 of these are coded only to a broad infection group.

All reconciliation checks pass. Headless Chrome render at 1280px checked.

## v3.2 update (27 Nov 2026): four Infectious Disease focus areas, sourced from saved Wellcome pages

Output: `wellcome_priority_themes-v3.2.html`. Built by `scripts/build_wellcome_analysis_gbd_v8.py`, then `export_wellcome_standalone_v3.py --build exports/wellcome_themes_v8_build`. v3 and v3.1 are kept unchanged.

**Correction to v3.1.** v3.1 said Wellcome names three Infectious Disease areas. The saved page (`Infectious Disease _ Our priorities _ Wellcome.pdf`, p.3, captured 27 Nov 2026 20:05) lists four under "Our focus includes":

- tuberculosis;
- cholera;
- vector-borne diseases "such as schistosomiasis, leishmaniasis and dengue";
- drug-resistant infections.

The three-area claim came from web-search summaries.

### Evidence for each Wellcome claim

| Claim | Evidence |
|---|---|
| Infectious Disease focus areas | Infectious Disease PDF, p.3 |
| Mental Health: "step change in early interventions for anxiety, depression and psychosis" | Mental Health PDF, p.1 |
| Anxiety includes OCD and PTSD; depression includes post-natal depression; psychotic disorders include schizophrenia, postpartum psychosis and bipolar disorder | Mental Health Award call text, supplied by the user. **Save this page as a PDF.** |
| Which diseases count as vector-borne | **To be evidenced:** save a PDF of a standard list, e.g. the WHO vector-borne diseases fact sheet |

### Scope decisions (user, 27 Nov 2026)

- **Vector-borne diseases are mapped as a category.** Wellcome's "such as" gives examples, so this is read the same way as "all forms of psychotic disorders". GBD causes included: malaria, dengue, leishmaniasis, schistosomiasis, Chagas disease, lymphatic filariasis, onchocerciasis, Zika, yellow fever, African trypanosomiasis.
- **Encephalitis is excluded,** because its GBD cause mixes vector-borne and other infections.
- **Diarrhoeal diseases stays as the cholera proxy.**
- **No supplementary screening is used.** Eligibility rests on GBD codes alone, applied to every funder.

### Totals

| Set | n | Funder identified (% of n) | Wellcome-funded (% of funder identified) | Wellcome rank |
|---|---|---|---|---|
| All mapped | 2,368 (5.7% of 41,610) | 768 (32.4%) | 43 (5.6%) | — |
| Infectious Diseases | 1,277 | 413 (32.3%) | 36 (8.7%) | 2nd of 457 |
| Mental Health | 1,092 | 355 (32.5%) | 7 (2.0%) | Joint 6th of 310 |

- 1 publication is in both themes.
- Full map: 174 Wellcome-funded, 43 captured (24.7%) and 131 not captured (75.3%).
- All reconciliation checks pass.

### PTSD and OCD: noted, not recoded

Wellcome counts OCD and PTSD as anxiety. The team's MeSH crosswalk maps both to anxiety disorders: the OCD ruling was confirmed on 14 Oct 2026, and PTSD is a "models agree" mapping.

In the coded data, though, some of these publications are coded to "Other mental disorders" instead. A title check found:

| Condition | Titles | Coded to anxiety disorders | Coded to "Other mental disorders" |
|---|---|---|---|
| PTSD | 37 | 20 | 17 (1 Wellcome-funded) |
| OCD | 23 | 12 | 11 |

The proposed fix is to recode them in the shared GBD coding for all funders. The selection should use a set rule, such as MeSH headings, not the title search. That needs team approval, because it also changes the coding the manuscript uses.

## v3.3 update (27 Nov 2026): vector-borne list evidenced by WHO (text only)

Output: `wellcome_priority_themes-v3.3.html`. Built by `scripts/build_wellcome_analysis_gbd_v9.py`, then `export_wellcome_standalone_v3.py --build exports/wellcome_themes_v9_build`. v3.2 is kept. **Counts are identical to v3.2.**

**Source.** The WHO fact sheet "Vector-borne diseases" (26 Sep 2024; `Vector-borne diseases.pdf`, saved 27 Nov 2026 20:21) lists all ten included GBD causes in its table: malaria, dengue, leishmaniasis, schistosomiasis, Chagas disease, lymphatic filariasis, onchocerciasis, Zika, yellow fever and African trypanosomiasis. WHO describes its table as non-exhaustive. The "to be evidenced" item in v3.2 is resolved.

**New limitation.** Some WHO-listed vector-borne diseases have no GBD cause of their own and sit in mixed codes:

| Mixed GBD code | WHO-listed diseases in it |
|---|---|
| Encephalitis | Japanese encephalitis, tick-borne encephalitis, West Nile |
| Other neglected tropical diseases | chikungunya, Rift Valley fever, Crimean-Congo haemorrhagic fever, plague, scrub typhus |
| Other unspecified infectious diseases | Lyme disease |

- These codes also cover diseases that are not vector-borne, so they stay excluded. That keeps the rule "include only GBD causes made up entirely of eligible diseases", with no title screening.
- About 35 publications are affected (title search). 1 is Wellcome-funded: the Japanese encephalitis study in Bangladesh.
- This limitation is stated on the page.

**Evidence still to save.** The Mental Health Award call page (OCD and PTSD as anxiety; post-natal depression; schizophrenia, postpartum psychosis and bipolar disorder as psychosis). The call text is quoted on the page from the user's copy.

## v3.4 update (27 Nov 2026): layout and wording tidy-up (counts unchanged)

Output: `wellcome_priority_themes-v3.4.html`. Built by `scripts/build_wellcome_analysis_gbd_v10.py`. v3.3 is kept.

Changes:

- **Crosswalk table:** cites short source names, with the full quotes printed once under "Sources for Wellcome's priorities". Column widths are fixed, so the first columns no longer collapse letter by letter.
- **Overview headers:** column headers are shortened to two lines and aligned to the bottom. The headline labels are shorter.
- **Status wording:** repeated text removed ("Confirmed · Confirmed match." now reads "Confirmed · Exact match."). The anxiety row no longer says both "flagged" and "confirmed".
- **Grammar:** "1 is in both" and "1 publication".
- **Breakdown rows:** tighter spacing.

Checked in headless Chrome at desktop width (1280px) and in both theme tabs at mobile width (390px), with the methodology open.

## v3.5 update (27 Nov 2026): colours, publication CSV, DOI links, shorter technical note (counts unchanged)

Output: `wellcome_priority_themes-v3.5.html`. Built by `scripts/build_wellcome_analysis_gbd_v11.py`. v3.4 is kept.

### Colours

Refreshed and checked with the dataviz palette validator: all checks pass. The contrast warnings for the light colours are covered by printed labels and legends.

| Element | Colour |
|---|---|
| Wellcome-funded | #5530C8 |
| Other reported funders only | #B9A6F2 |
| Funder not identified | #E2DFE8 |
| High-income setting | #0B7FA3 |
| Low- & middle-income setting | #E5793A |
| Multi-country, regional or income unavailable | #D8D2C6 |
| Captured / not captured | #5530C8 / #DCD5F5 |

Also:
- 2px gaps between stacked segments.
- The active tab is violet.
- Downloads are shown as buttons.

### Downloads

- **New:** `wellcome_funded_publications.csv`: all 174 Wellcome-funded publications. Columns: year, title, DOI link, captured by the mapping (43 yes), themes, GBD causes, other funders identified.
- **Existing:** funder counts by theme (CSV), all figures (JSON) and the page as an image (PNG). The export embeds every file.

### Links

Publication titles now link to their DOI. The master's `url` field is empty for these records, so in v3–v3.4 the titles had no links.

### Technical note (formerly "Methodology and limitations")

Rewritten from the user's draft and checked against the final codes and Wellcome's wording. It has four parts:

1. How publications were matched.
2. The codes used: the crosswalk table, which the build now checks against the codes actually counted.
3. What the mapping does not capture.
4. Counting and funding, then sources.

**Changes to the draft wording, so it stays accurate:**
- The four Infectious Disease areas are named.
- Cholera → diarrhoeal diseases is stated.
- Psychosis is "no single GBD category", represented by schizophrenia and bipolar disorder.

## v3.6 update (27 Nov 2026): uncaptured-publications list removed (counts unchanged)

Output: `wellcome_priority_themes-v3.6.html`. Built by `scripts/build_wellcome_analysis_gbd_v12.py`. v3.5 is kept.

**What was removed.** The "Other Wellcome-funded HEE publications (131)" drawer is gone from the page, and the keyword groups are gone from the JSON. The user's reason: grouping those publications by topic (cardiometabolic, food systems and so on) made them look relevant to the themes and as if the coding were wrong. It also did not explain the comparability reasons for not mapping them.

**This departs on purpose from the v3 spec** (section 4C), which asked for that list.

**What stays:**
- the coverage bar (43 captured, 131 not captured);
- the interpretive note;
- the technical note's "What the mapping does not capture";
- the CSV of all 174 Wellcome-funded publications: ungrouped, with GBD code and a captured yes/no column.

The builder still computes the groups for its own count check, but does not publish them.

## v3.8 update (27 Nov 2026): tone review (counts unchanged)

Output: `wellcome_priority_themes-v3.8.html`. Built by `scripts/build_wellcome_analysis_gbd_v13.py`. `wellcome_priority_themes-v3.7.html` is an intermediate draft of the same changes; it can be deleted if no longer wanted. v3.6 is kept.

**The user's direction:** present the mapping as the closest match possible with GBD codes, with limitations the team is aware of and transparent about, not as mistakes. The facts are unchanged; the wording changed in three places.

### Technical note

- **"How were publications matched"** now explains that most priorities have a direct GBD code, and that the nearest category was used where none exists (cholera, psychosis). It also says drug-resistant infections and early intervention are covered through the underlying conditions.
- **"What the mapping does not capture"** became **"Scope of the mapping".** Codes that combine conditions are described as left out "to keep the mapping specific".
- Removed:
  - "may… miss relevant publications";
  - "has not been assessed";
  - "full texts were not screened";
  - the mention of the 17 earlier review additions. The rule that every funder's publications are identified the same way stays.

### Crosswalk

- Badge labels: Direct match / Closest code / Full category / Not a GBD category. They are neutral colours, not warning orange.
- Each row's text no longer repeats its badge.
- Drug-resistant infections now notes that drug-resistant TB is included under tuberculosis. Checked: MDR-TB titles are coded to tuberculosis.

### Theme criteria panels

- "Limitations" became "Points to note".
- Removed "they were not reviewed publication by publication" and "flagged for a coding fix".

### Stays in this report only (not on the page)

- The PTSD/OCD split in the coding (rule 3).
- The title-search count of vector-borne publications in mixed codes (about 35, 1 Wellcome-funded).

## Housekeeping (27 Nov 2026): older pages archived

Moved, not deleted: v2, v3 and v3.1–v3.7 are now in `Archive/`. The main folder holds the current page (v3.8), the spec, this report and the evidence files. File names in the history sections above refer to `Archive/` copies.

## v3.9 update (27 Nov 2026): visual refresh (counts and wording unchanged)

Output: `wellcome_priority_themes-v3.9.html`. Built by `scripts/build_wellcome_analysis_gbd_v14.py`. v3.8 has been moved to `Archive/`.

**Why v3.8 looked flat.** Most of the overview bars are "funder not identified" grey (about 68%) and pale lavender; Wellcome is a 2% sliver. Colour appeared only in thin marks on an off-white page. The warm cream background and beige grey also muddied the cool violets.

**What changed (the spec's colour roles are kept):**

- **Page and sections:** a cool background (#f5f5fa), with each section on a white card with a soft shadow.
- **Header:** a violet gradient band with an "HEE evidence map" label.
- **Headline figures:** shown as tinted tiles; the Wellcome tile is the most saturated.
- **Section headings:** a violet accent bar.
- **Bars:** thicker and rounder, with 2px gaps between segments.
- **Greys:** cool instead of beige. Funder not identified #E3E4EC; multi-country, regional or unavailable #CDD3DD.
- **Trend line:** a light violet fill underneath. Still straight segments on the same fixed axes.
- **Theme tabs:** open with a two-line summary. The detail that was only in the old long descriptions moved into "Definition and matching criteria": drug-resistant TB is counted under tuberculosis, and all stages and ages are included.

Checked in headless Chrome at desktop and phone width: the chart draws, both tabs work and all three downloads are embedded.

## v3.10 update (27 Nov 2026): banner link removed

Output: `wellcome_priority_themes-v3.10.html`. Built by `scripts/build_wellcome_analysis_gbd_v15.py`. v3.9 has been moved to `Archive/`.

**Change:** the "About the thematic mapping" link is removed from the top banner, at the owner's request. The introductory text itself is unchanged.

**The technical note is still reachable** from:
- the overview footnote's "About the thematic mapping" link;
- each theme's "Definition and matching criteria".

Counts, wording and design are otherwise unchanged.
