# Manuscript figures — 19 October 2026

Seven standalone figures in PNG (300 dpi), PDF and editable-text SVG. No visual-map or site files are changed.

Style follows docs/theme_hee.R: white paper, sans-serif type, fixed income colours, first three categorical colours for regional disease dots, sequential blue map for magnitude, thin marks, recessive one-direction grids and legends. Python/Matplotlib implements the R style because the existing data builders are Python. The source theme is copied into source data; its stale denominator notes are not used.

The supplied figures have different populations: the overview/regional profiles use full evaluations for their analytic panels; intervention circles, outcomes, topics and burden ratios retain their original eligible-study populations, including eligible reviews. These differences are stated in captions.

## 01_evidence_at_a_glance

Eligible studies, 2010–2026; 2026 is incomplete. Map: full economic evaluations only. Countries count each named study once; multi-country studies can appear in several countries. Rates use the source builder’s GBD denominator. Colour limits retain the original log-scale clipping. Grey includes unavailable rates and zero evaluations.

## 02_regional_profiles

Full economic evaluations only; studies naming multiple regions contribute to each. Disease dots show fractional shares across three GBD classes among disease-coded evaluations; one dot is about 1%. Utility bar: QALY or DALY reporting; orange marker: all linked evaluations. Trends: cumulative share of countries with ≥1 evaluation (solid), ≥2 (dashed), all regions ≥1 (grey); 2026 excluded as incomplete.

## 03_intervention_circles

One dot = one study; circle area is proportional to study count. Orange dots fill from the bottom. Base: 27,897 single-country eligible studies with a known publication-year World Bank income group. Includes reviews, matching the supplied figure. Intervention is the primary class assigned from the abstract. L&MICs includes low-, lower-middle- and upper-middle-income settings.

## 04_consequences_by_income

Base: 27,897 single-country eligible studies with a known publication-year World Bank income group (20,236 high income; 7,661 low and middle income). A study can report several outcome families. Panel A omits the residual other-clinical family and families below 5% in both settings. Panel B excludes incomplete 2026. Consequences are extracted from titles and abstracts; reporting does not establish quality.

## 05_topics_by_income

Number of studies in brackets. Dashed line: the corresponding income share across all topic-assigned studies. Topics group similar titles and abstracts; 73 topics with at least 30 classified single-country studies qualify. Income is the World Bank group in force on 1 January of publication year. Includes eligible reviews, matching the supplied figure; 2026 is incomplete.

## 06_research_relative_to_burden

Research: eligible 2010–2026 publications (2026 incomplete), naming a level-2 cause and classified setting. Burden: GBD 2023 DALYs summed over 2010–2023. Research uses publication-year income; burden uses burden-year income. Multi-cause and multi-setting studies can contribute more than once. Groups follow GBD level 1; rows follow global pooled burden. The 1× reference indicates equal shares, not an adequacy target. See source data for denominators and provenance.

Rebuild: python -B scripts/create_manuscript_figures_oct19.py
Natural Earth country boundaries: https://github.com/nvkelso/natural-earth-vector (110m admin-0 countries).


## 07_unequal_weight_country_gaps

Base: all 204 national GBD 2023 locations, including zero-study locations; 31,592 unique study–country pairs. Expected pairs = 31,592 × each country’s share of DALYs across these same 204 locations. Hong Kong, Cayman Islands, French Guiana and Guadeloupe have no row in this national GBD export and are excluded. A multi-country study counts once per named country. Studies span 2010–2026; 2026 is incomplete. Burden: GBD 2023 all-cause DALYs. Income colours use July 2026 classifications, combining the three low- and middle-income groups. Proportionality is a reference point, not an adequacy target. Labels are rounded to whole pairs.

Rebuild: python -B scripts/create_manuscript_unequal_weight_oct19.py

## Sharing through Git

This folder is stored at the repository root and includes all rendered figures, captions and aggregated source tables. After committing and pushing it to the shared repository, collaborators receive it with git pull; no relocation or local path configuration is needed to view the figures.

Rebuilding the figures requires the original data/raw inputs, which are excluded from Git. The exported PNG, PDF and SVG figures can be viewed without those inputs or Python.
