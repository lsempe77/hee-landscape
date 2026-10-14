# Research–disease divergence in health economic evaluations: replication of Schmallenbach et al. (2025)

Built by `scripts/build_kld_replication.py` on 14 October 2026.

Reference: Schmallenbach L, et al. Global distribution of research efforts, disease burden, and impact of US public funding withdrawal. *Nature Medicine* 31, 3101–3109 (2025). doi:10.1038/s41591-025-03923-0. We replicate their Fig. 2a (divergence over time) and Fig. 3 (research versus burden as drivers of the change).

## Measure (as in the paper)

For each year, KLD(p ‖ q) = Σ p(x) ln(p(x)/q(x)).
- **p(x)** is the share of DALYs from each GBD level-2 cause. This is the reference distribution.
- **q(x)** is the share of research on the same cause.

0 means research matches burden exactly; higher values mean greater divergence. A study naming several causes counts once for each cause, as the paper's articles do.

**Causes.** The main analysis uses the paper's 16 level-2 causes. They leave out other infectious diseases, other non-communicable diseases, mental disorders and the three injury groups. A sensitivity version adds mental disorders and the three injury groups (20 causes).

**Fig. 3 counterfactuals.** Two simulated lines are compared with the observed one:
- **research fixed at its 2010 mix:** only DALYs change;
- **DALYs fixed at their 2010 mix:** only research changes.

If the observed line follows the first, changing burden explains the trend. If it follows the second, changing research does.

## Data

- **Research:** the 41,657 eligible studies, published 2010–2023. Each study's GBD level-2 causes come from the team's GBD 2023 coding of titles and abstracts (share v2.1).
- **Burden:** GBD 2023 DALYs (number, all ages, both sexes) for 204 locations, for every year 2010–2023, from the GBD Results tool.

## Differences from the paper

1. **Geography.** The paper's Fig. 2a and Fig. 3 are global (all research vs global DALYs), so geography does not enter; our "all studies" group does the same. The income groups are our extension, and for them research is placed by the country studied. The paper's regional analyses use first-author country instead. Country studied suits our question, which is whether evaluations of a setting track that setting's burden.
2. **Groups.** There are three groups, each compared with the matching burden:
   - **All studies against global DALYs.** This includes studies naming no country.
   - **Studies naming a low- or middle-income country against LMIC DALYs.**
   - **Studies naming a high-income country against HIC DALYs.**

   Income is the World Bank group in force on 1 January of the publication year for studies, and of the burden year for DALYs. A study naming countries in both groups counts in both.
3. **Burden-year income gaps.** A few country-years have no World Bank group:
   - South Sudan 2011–12 takes Sudan's group.
   - Venezuela 2022–23 takes its last group (FY21).
   - Microstates without a group (Cook Islands, Niue, Tokelau and others) count in the global totals only.
4. **Smoothing.** Research shares use add-one (Laplace) smoothing in every year and group. The paper ran this as a sensitivity check. We need it because the yearly LMIC and HIC counts are small (121 LMIC studies in 2010), and a cause with no studies would make KLD infinite.
5. **Uncertainty.** The 95% intervals come from resampling studies within each year, with 1,000 draws. In Fig. 3, the 2010 base mix is resampled too. The paper instead simulated DALY uncertainty; our uncertainty is dominated by small study counts.
6. **Period.** 2010–2023, set by the DALY data. 2020–21 are marked as COVID-19 years. The paper's Fig. 3 stops at 2019, and our changes are reported both to 2019 and to 2023.

## Files

- `fig2a_kld_trend_16causes.png`, `fig2a_kld_trend_20causes.png`: divergence over time for the three groups.
- `fig3_decomposition_16causes.png`, `fig3_decomposition_20causes.png`: observed against the two counterfactuals, one panel per group.
- `kld_results.csv`: every value plotted, with study and study–cause link counts.
