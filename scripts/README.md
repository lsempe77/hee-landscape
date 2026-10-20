# Scripts

Every script that builds the HEE map's data and figures and the manuscript figures. Run from the repository root, e.g. `python scripts/build_gbd_figures.py`. Most need the raw inputs in `data/raw/`, which are not in Git; ask the team for a copy.

The scripts stay in one flat folder on purpose: many import one another (`import build_gbd_figures`), which only works when they sit side by side. Older versions an analysis no longer uses are in [archive/](archive/).

## Manuscript figures (October 2026)

Output: [`manuscript figures Oct 19/`](../manuscript%20figures%20Oct%2019/).

| Script | Makes |
|---|---|
| `create_manuscript_figures_oct19.py` | Figures 01–06 (glance, regional profiles, intervention circles, consequences, topics, research vs burden) |
| `create_manuscript_unequal_weight_oct19.py` | 07 unequal weight: country gaps |
| `create_manuscript_study_types_oct19.py` | 08 study types and growth |
| `create_manuscript_evidence_types_oct19.py` | 09 evidence types and growth (Python version) |
| `create_manuscript_evidence_types_oct19.R` | 09 evidence types and growth (R / ggplot version) |
| `create_manuscript_evidence_types_oct19_v2.R` | 09 evidence types and growth (R v2, KPI/track-bar style) |
| `create_manuscript_supp_g4_oct19.py` | Supplementary G4: evaluation types and publications per year |
| `build_country_concentration_figure.py` / `.R` | Country concentration figure (writes to `output/figures/`) |
| `build_overview_figure.py` | Overview figure: one panel per overview paragraph |

## Live map: site data and figures

These write into `docs/`, which is the published site. Pushing their output changes the live map.

| Script | Makes |
|---|---|
| `build_glance_regions_who_v4.py` | "(Un)equal weight" at-a-glance infographic |
| `build_region_disease_themes_who_ee.py` | Top disease themes by WHO region, economic evaluations only (feeds the glance) |
| `build_region_disease_themes_who.py` | Top disease themes by WHO region, all studies |
| `build_who_regions.py` | WHO region for every country (UN M49 fallback) → `who_regions.csv` |
| `build_income_pubyear.py` | World Bank income group at each study's publication year → `income_pubyear.csv` |
| `income_pubyear_figure_data.py` | Data behind the income-stratified gallery figures |
| `build_income_pubyear_figures.py` | Income-stratified gallery figures |
| `build_gbd_figures.py` | Gallery disease figures on GBD 2023 coding |
| `build_disease_gbd_data.py` | Site's GBD disease groups (`docs/data/disease_gbd.json`) |
| `build_authorship_figures.py` | Five author-location figures |
| `recolour_authorship_figures.py` | Recolours pre-rendered authorship figures to the site palette |
| `build_eval_type_figures.py` | Two evaluation-type figures |
| `build_research_burden_ratio.py` | Country research-to-burden ratio figure |
| `build_denominator_audit.py` | Country denominators; inequality and reach figures |
| `build_funder_scorecard.py` | Size-neutral evidence-gap scorecard |
| `build_funder_scorecard_absolute.py` | Absolute evidence-shortfall scorecard |
| `build_wellcome_analysis.py` | Global funder figures; also supplies `funders_of` to the funder filter |
| `build_wellcome_analysis_gbd_v2.py` | Wellcome priority-themes view on GBD 2023 coding |
| `build_funder_filter.py` | Data for the Explorer's funder filter |
| `build_language_filter.py` | Data for the Explorer's language filter |
| `build_dotmap_title.py` | Dot-map layout |
| `build_remaining_figures_reconciled.R` | Remaining static figures from the reconciled CSVs |
| `build_intervention_map_legend.R` | Intervention map with a readable legend |
| `rebuild_reporting_figure.R` | Abstract-reporting heatmap only |
| `create_intervention_mix_v2.py` | Small-multiples intervention mix figure |
| `create_theme_rank_v2.py` | Leaner theme-rank figure |
| `figure_style.py` | Shared colours and styling, imported by many of the above |

## Exploratory and standalone figures

Written to dated folders in `exports/`; they never change the site.

| Script | Makes |
|---|---|
| `build_intervention_redesign.py` | Intervention map redesign options (also used by the manuscript figures) |
| `build_intervention_redesign_v3.py` | Intervention map redesign options, latest |
| `build_kld_replication.py` | Replication of Schmallenbach et al. (2025) Fig. 2a and 3 (also imported by v2) |
| `build_kld_replication_v2.py` | Research–disease divergence, version 2 |
| `create_segmented_kld_panels.py` | 16- and 22-cause KLD contribution panels |
| `create_segmented_mismatch.py` | Disease contributions to research–burden mismatch |
| `create_segmented_mismatch_panels.py` | Global and LMIC mismatch panels |
| `create_grouped_pooled_disease_ratios.py` | GBD level-1 grouped, pooled disease ratios |
| `create_gap_movement_feedback.py` | Reviewer-requested disease gap movement figure |
| `create_standalone_transition.py` | Slide-style transition figure |
| `create_overview_figure_mockups.py` | Overview layout options |
| `build_climate_candidates.py` | Climate & Health candidate list for manual review |

## Data cleaning and classification (one-off steps, kept for the record)

These changed the analysis master in sequence. They are not meant to be re-run.

- **Reviews:** `identify_review_candidates.py`, `screen_reviews_with_abstracts.py`, `resolve_unclear_reviews.py`, `fetch_review_resolution_sources.py`, `resolve_remaining_review_classifications.py`, `migrate_review_categories.py`, `migrate_review_terminology.py`, `crosscheck_review_evidence_basis.py`, `audit_review_evidence_basis_93.py`, `resolve_review_evidence_basis_22.py`, `apply_review_evidence_basis_93.py`, `explain_review_evidence_basis_65.py`, `audit_review_ownership_81.py`, `apply_review_ownership_3.py`, `apply_review_ownership_11.py`, `apply_review_eval_type.py`
- **Duplicate publications:** `build_publication_version_check.py`, `check_publication_version_sources.py`, `prepare_publication_reconciliation.py`, `apply_publication_reconciliation.py`, `apply_publication_followup.py`, `rebuild_publication_followup.py`, `apply_publication_links.py`, `reconcile_publication_methods.py`, `finalize_methods_decisions.py`, `update_selection_presentation.py`
- **Housekeeping:** `archive_superseded_raw_files.py`, `install_reconciled_figures.py`, `export_country_audit_sources.R`

## Checks

- `check_site_figures.py`: every figure the site shows exists and opens
- `verify_all_figure_refresh.py`: integrity and denominator check for the gallery
- `verify_publication_reconciliation.py`: exclusions, links and website indices after reconciliation

## Lookup tables and notes in this folder

`who_regions.csv`, `who_gho_country_regions.csv`, `wb_regions.csv`, `wb_income_history.csv`, `income_pubyear.csv`, `topic_disease_map.csv`, `region_disease_themes_who*.json` are read by the scripts above; leave them here. Notes: `wellcome_analysis.md`, `denominator_audit.md`, `publication_language_recovery.md`, `publication_links.md`.
