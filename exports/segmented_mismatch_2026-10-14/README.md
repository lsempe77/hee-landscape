# Segmented contribution figure

Three sections show the same mismatch change at increasing detail: overall, summed level-1 contributions and individual level-2 contributions. The setting remains LMIC research; “overall” means all 22 disease and injury causes, not all-country research. All three injury causes are retained individually at level 2 and summed at level 1.

## Exact decomposition

Research shares q are normalised unique study–cause links. Burden shares p are pooled LMIC DALYs in 2021–2023, normalised across the same 22 causes. Both research windows use that fixed p.

This differs from the preceding arrow figure, whose disease shares divide by the number of disease-coded records and therefore need not sum to 100%. A proper distribution distance requires both sets of shares to sum to 100%; contribution directions can consequently differ between the two figures. This figure also keeps the three injury causes separate at level 2 and excludes unspecified injury codes, whereas the preceding collapsed-injury row includes them.

TV(p,q) = ½ Σ_i |q_i − p_i|. Disease contribution c_i = ½ |q_i − p_i|. Level-1 contribution C_g = Σ_(i in g) c_i. The overall value is Σ_g C_g = Σ_i c_i. Changes obey the same identity. The computations and graph use percentage-point units.

Level-1 bars are grouped contributions to the fine-grained overall mismatch, not total variation recomputed after collapsing the cause categories. Collapsing first can hide opposing gaps within a group and give a different result. These sections should never be added together.

TV avoids negative per-cause KLD terms and is finite when a cause has zero observed research. No artificial 0.5-study smoothing is required. This is a new metric, not a re-expression of the earlier KLD score, and its values must not be compared numerically with those KLD figures. It measures share-distribution mismatch, not study quality, funding need or a causal response to disease burden.

Research windows are 2010–2012 and 2021–2023. Rows are ordered within level-1 groups by summed LMIC DALYs over 2010–2023. The substantive dataset and geography/income rules are unchanged: eligible reports, country studied, publication-year income for research and burden-year income for DALYs, with the existing recorded overrides. Multi-disease studies count once per named level-2 cause. A mixed-income study may enter the LMIC set. Unspecified injury/infection records are not assigned to a level-2 cause here; unlike the preceding collapsed-injury arrow plot, this figure restricts both sides to the same 22 level-2 causes.

Confidence intervals are percentile intervals for change, from 1,000 study resamples within publication year. Each resampled study carries all its cause codes; shares are renormalised in every draw. Level-1 and total intervals are computed from sums in each draw, not by summing marginal interval endpoints. DALY uncertainty and extraction/coding uncertainty are not propagated. All point and per-draw additivity checks pass.

contributions.csv has exact values and intervals. bootstrap_changes.npz contains the 1,000 contribution-change vectors; provenance.json records sources and checks. No map files were changed.
