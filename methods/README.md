# Methods

How the studies were coded, and where the code and outputs for each analysis live. Study-level data (the analysis master and the per-study GBD codes) are not in Git; see [Data not in Git](#data-not-in-git).

## GBD 2023 disease coding

[`gbd_coding/GBD_CODING.md`](gbd_coding/GBD_CODING.md) is the team's record of how all 41,657 included studies were coded to GBD 2023 causes: models, prompts, coding rules, team rulings, agreement checks and open questions. It is a copy from the team share (`hee_share_v2_1`, 14 October 2026). Paths in it beginning `projects/hee/`, `R/` or `analysis/` refer to the team's upstream repository, not this one.

Reference tables used by the coding (no study records):

| File | What |
|---|---|
| `gbd_coding/gbd2023_cause_hierarchy_l3_l2_l1.csv` | IHME GBD 2023 causes: 176 level-3, 22 level-2, 3 level-1 |
| `gbd_coding/gbd2023_risk_hierarchy_l3_l2_l1.csv` | IHME GBD 2023 risk factors (53 level-3) |
| `gbd_coding/mesh_gbd_rulings_v1.csv` | Team rulings on disputed headings, with ICD-10 codes and notes |
| `gbd_coding/mesh_gbd_crosswalk_v2.csv` | Final MeSH heading → GBD cause mapping (1,985 headings) |

## Wellcome priority themes

| Step | Where |
|---|---|
| Build the analysis | [`scripts/build_wellcome_analysis_gbd_v5.py`](../scripts/build_wellcome_analysis_gbd_v5.py) (v2.1 master, 41,610 studies; income at publication year) (funder cleaning in `build_wellcome_analysis.py`) |
| Method notes | [`scripts/wellcome_analysis.md`](../scripts/wellcome_analysis.md) |
| Infectious Diseases | Any GBD level-2 infectious cause or "Infections, disease not stated" (coding above) |
| Infectious Diseases: proposed wider scope (under review) | [`scripts/build_infectious_candidates.py`](../scripts/build_infectious_candidates.py) → `exports/infectious_scope_candidates_2026-10-21.xlsx`: viral hepatitis, vaccines and antimicrobial use/resistance studies that GBD codes elsewhere, for Include/Exclude review |
| Mental Health | All mental health: GBD mental disorders or substance use disorders. Wellcome's stated focus, anxiety, depression and psychosis ([source](https://wellcome.org/our-priorities/mental-health)), is reported as a subset (GBD level-3 depressive and anxiety disorders, schizophrenia, bipolar disorder) |
| Climate & Health: keyword screen | [`scripts/build_climate_candidates.py`](../scripts/build_climate_candidates.py) (full keyword and exclusion lists) |
| Climate & Health: hand review | `exports/climate_health_candidates_2026-10-12_reviewed_draft.xlsx` (see its "Method record" sheet) and `exports/climate_health_review_decisions_2026-10-12.csv` (decision, subarea and basis for all 138 candidates; 102 included) |
| Wellcome-funded | Recorded funders name the Wellcome Trust; Burroughs Wellcome Fund excluded |
| Outputs | `docs/figures/wellcome_analysis.html` (full page), `wellcome_analysis.json` (all counts), `wellcome_theme_funders.csv`, `fig_wellcome_priorities.svg` |
| By-year chart | [`scripts/create_wellcome_by_year_oct20.py`](../scripts/create_wellcome_by_year_oct20.py) → `exports/wellcome_by_year_2026-10-20/` |

The Wellcome section is currently hidden on the live map; open `docs/figures/wellcome_analysis.html` directly to read it.

## Data not in Git

`data/raw/` is excluded from Git: source-data redistribution restrictions apply, and the analysis master (145 MB) exceeds GitHub's file limit. To re-run the analyses, get these from the team share:

- `data/raw/hee_analysis_master_v2.csv`: analysis master (one row per record)
- `data/raw/hee_share_v2_1/gbd_disease_long.csv`: GBD group per study (`record_id`, `grp`, `l1`)
- `data/raw/hee_share_v2_1/gbd_by_record.csv`: full per-study GBD coding (levels 1–3, secondary causes, risk factors)

Place them at those paths; the scripts read them from there.
