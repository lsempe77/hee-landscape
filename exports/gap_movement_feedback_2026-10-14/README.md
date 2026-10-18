# Standalone disease-gap movement figure

The attached earlier version did not fully implement the feedback. This version:

- Groups communicable/maternal/neonatal/nutritional diseases first, NCDs next, and all injuries in one final row.
- Orders level-2 rows within each group by the sum of LMIC DALYs over all 14 years, 2010–2023. It does not average annual shares.
- Uses a grey dot for 2010–2012 research and an arrowhead for 2021–2023 research, the latest matching complete DALY window.
- Divides both research shares by the same pooled 2021–2023 DALY share; 1 is matched. The reference is fixed so movement reflects changes in research mix, not changes in the burden denominator.
- Uses green Closer or red Farther based on the change in absolute research-minus-burden percentage-point gap. An overshoot can therefore be farther even when it ends above matched.

The main file uses a linear ratio scale, which can include zero-research observations. The `_log` alternative uses the same values, ordering and colours; all current observations are positive. It better separates the small ratios because the observed range is approximately 0.15 to 7.4. No categories are dropped for low counts. Ratios describe relative shares, not whether research is sufficient. The population is studies about LMIC settings, including mixed-income multi-country studies and eligible reviews. Research shares have a unique disease-coded-record denominator within each window; they need not sum to 100% because records can name several causes.

The all-injuries row deduplicates records across injury codes and includes injuries with no specified level-2 cause. Its DALYs sum transport, unintentional and self-harm/interpersonal-violence injuries. Infections with no specified cause cannot be assigned to a displayed level-2 cause. This differs from the old figure's exclusion of unspecified injuries and its minimum-15-record rule.

Income rules are the current map rules: publication-year income for study settings, burden-year income for DALYs, with the existing recorded overrides. Missing burden-year classifications are listed in provenance.json. This is a descriptive movement comparison; the colour does not establish a statistically significant change or a causal response to burden.

figure_data.csv contains exact row counts, shares, ratios, pooled DALYs and closeness calculations. provenance.json records the source hashes and validation settings. No map files were changed.
