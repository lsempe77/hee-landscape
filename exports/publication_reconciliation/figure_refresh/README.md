# Current gallery figure reconciliation

The current local map uses 41,610 included records. All 43 unique main-gallery figures have current-dataset build provenance. Fifteen residual static figures were rebuilt and installed; the remaining figures had already been rebuilt after publication reconciliation. The region infographic, KLD extension and funder alternative view are recorded separately. Published Schmallenbach comparison figures are reference images, not analyses of this dataset.

## Residual figures rebuilt

Growth, intervention topic map, generic outcomes by model-use flag, intervention reporting heatmap, open-access trend, population density, country burden intensity, burden/evidence scatter, local-capacity scatter, regional model use, country population map, country dot map, country burden map, country open-access map and country recent-publication share map.

Sources are the current master, eligible study-country pairs, extracted primary intervention labels, frozen topic coordinates, outcomes, known affiliations, website country metadata and the national GBD burden export. No model extraction or topic-clustering run was repeated. Topic coordinates are filtered to eligible IDs. Charts use their declared subsets and denominators; they do not all have the full 41,610-record denominator.

The reporting heatmap uses the full included denominator within each row, including unavailable flags; model-based counts records positively identified as model-based. The generic-outcome comparison instead restricts to records with a known model-use flag. Open-access time-series use the same eligible single-country, publication-year-income-known and OA-known base for all three lines (22,954 records through 2025). Country recent-publication shares describe age composition, not estimated growth rates.

## Evidence

- all_figure_audit.json / .csv: every gallery key, shown asset, builder, caption and SHA256; independent denominator check.
- remaining_figure_manifest.json: 15 new assets and exact captions.
- remaining_figure_counts.json: current input bases.
- visual_review.png: rendered previews of the 15 rebuilt figures (the reporting heatmap was subsequently corrected and separately reviewed).
- file_checks.log: all referenced figure files exist and open.
- data_checks.log: five master datasets and current/v2/v3 study indices agree.
- presentation_backups: prior presentation JSON and application files.

Old assets remain available for traceability. The current site routes gallery keys to the new assets; versioned local bundles also carry refreshed gallery presentations. Browser interaction and deployment were not performed in this check.
