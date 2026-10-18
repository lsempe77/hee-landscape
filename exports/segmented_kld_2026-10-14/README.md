# Segmented KLD: two standalone cause sets

- `16_causes/KLD_segmented_16_causes_global_and_LandMICs.png`: reference-paper 16-cause set.
- `22_causes/KLD_segmented_22_causes_global_and_LandMICs.png`: extended 22-cause set.

Each version also has PDF and SVG exports, contribution CSVs, bootstrap draws and provenance. Both show all-studies/global and L&MICs-focused panels. L&MICs means low-, lower-middle- and upper-middle-income countries.

Both compare 2010–2012 with 2021–2023, using contemporaneous DALY distributions and KLD(p||q). This follows the existing Fig. 2a method at those endpoints; it is not the earlier 2010–2012 versus 2017–2019 comparison. The latest endpoint includes the COVID period. Disease contributions use the explicitly stated nonnegative allocation p ln(p/q) − p + q, whose sum equals overall KLD. These allocations differ from signed p ln(p/q) cause terms. Level-1 rows sum descendant contributions rather than recomputing KLD on collapsed categories.

Important sensitivity distinction: the 16-cause point estimates require no smoothing. In the 22-cause set, transport injuries have zero early-window research in both panels; the existing Fig. 2a implementation's zero-only 0.5 correction is therefore necessary for finite point estimates. The 22-cause version is an extended analysis with that correction, not an unsmoothed exact replication. Zero-containing bootstrap windows receive the same correction; frequencies are in each provenance file. Interpret the expanded-set results with this sensitivity in mind.

Shares are re-normalised separately over the selected causes, so 16- and 22-cause absolute totals are not directly interchangeable. The 16-cause figure marks injuries outside the analysis. Green indicates a negative estimated change in KLD contribution; red a positive change. Intervals come from 1,000 study bootstrap draws within year and omit DALY and coding uncertainty. A falling contribution does not identify whether research or burden caused the change.

No map files were changed. Builder: `scripts/create_segmented_kld_panels.py --causes 16` (or `22`).
