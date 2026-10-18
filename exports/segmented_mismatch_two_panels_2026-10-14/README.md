# Global and L&MICs segmented mismatch panels

L&MICs means low- and middle-income countries: all three World Bank low-, lower-middle- and upper-middle-income groups. It does not mean lower-middle-income countries alone. Internal `lmic` data keys and existing output filenames are retained for stable file references.

Panel A: all eligible disease-coded records, including HIC and L&MICs settings and records without a stated country, compared with global DALYs across 204 national GBD locations. Panel B: records naming an L&MICs study setting, compared with L&MICs DALYs. Mixed-income multi-country records can enter Panel B. Panel B is a subset of Panel A, not an independent complementary population.

Both panels use 2010–2012 and 2021–2023 research, with their corresponding pooled 2021–2023 DALY distribution fixed for both research windows. Both use all 22 level-2 causes and identical row order: level-1 groups, then global DALYs summed across 2010–2023. This common global ordering differs from the earlier L&MICs-only figure's L&MICs ordering but permits direct row alignment. Global burden is summed directly from the deduplicated 14 × 204 × 22 number/all-ages/both-sexes rows; it does not exclude countries with missing income classification. L&MICs burden retains the existing burden-year income rules.

The metric remains total variation distance, ½ Σ |q_i−p_i|, with q normalised study–cause links and p DALY shares. Contributions are nonnegative; their changes can be positive or negative. Every level-1 subtotal sums its level-2 causes, and all causes/groups sum to the overall total at each period and for change. The level-1 subtotals retain within-group mismatch; they are not a separate distance computed after collapsing causes. Do not sum across the three display sections.

Confidence intervals for change use 1,000 study bootstrap draws within publication year. Subtotal and overall intervals come from per-draw sums, not summed marginal interval bounds. These are descriptive comparisons and do not propagate DALY/coding uncertainty. The different global/L&MICs references mean panel differences are not a causal or mechanical HIC-removal effect. This is the TV metric, not the earlier KLD score. Exact contributions and shares are in contributions_both_panels.csv; provenance and bootstrap matrices are saved alongside the figure.

No map files were changed.
