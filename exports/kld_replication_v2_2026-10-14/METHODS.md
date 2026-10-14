# Research–disease divergence in health economic evaluations (version 2)

Built by `scripts/build_kld_replication_v2.py` on 14 October 2026, revised the same day after a cross-check.

**Numbers updated to the reconciled data** (publication reconciliation, 14 October 2026). The figures and CSVs for that run, which the site uses, are in `exports/publication_reconciliation/kld_followup/`. The CSVs and PNGs in this folder are from the earlier, pre-reconciliation run and differ slightly. This revises version 1 (`exports/kld_replication_2026-10-14/`). The aim is to answer one question: **does research shift with disease burden once high-income studies are removed?** Preliminary, not peer reviewed.

Reference: Schmallenbach L, et al. *Nature Medicine* 31, 3101–3109 (2025). doi:10.1038/s41591-025-03923-0.

## Method

- **Measure (as in the paper).** For each period, KLD(p ‖ q) = Σ p ln(p/q).
  - p is the share of DALYs from each GBD level-2 cause (GBD 2023).
  - q is the share of studies on the same cause; a study naming several causes counts once for each.
  - 0 means research is spread across diseases exactly as burden is.

  The main analysis uses the paper's 16 causes. The sensitivity version uses 20, adding mental disorders and the three injury groups.
- **No smoothing (as in the paper's main analysis).** No cause has zero studies in any 3-year window of the 16-cause analysis. In 1.8% of resampling draws (637 of 36,000), a cause was left with no study; that cause was given 0.5 study.
- **Groups.**
  - **With high-income studies:** all studies against global DALYs. This includes studies naming no country, and it is the same as the paper, whose Fig. 2a and Fig. 3 are global, so geography does not enter.
  - **Without high-income studies:** studies of low- and middle-income countries against LMIC DALYs. This split is our extension; the paper does not split these two figures by income.
  - **High-income studies only** (supplementary): studies of high-income countries against HIC DALYs.

  Income is the World Bank group in force at publication for studies, and in the burden year for DALYs. A study naming countries in both groups counts in both.
- **Why the country studied for the income split.** The paper's regional analyses use first-author country instead.
  - **An economic evaluation is tied to its setting.** Its costs, prices, health-care delivery and value-for-money threshold are those of the country it examines, so it informs decisions there.
  - **That matches our question.** Placing studies by the country studied tests whether the evidence available to each setting matches that setting's burden.
  - **Author country would mix two things.** It would count a high-income team's evaluation of a low-income country as high-income research, confusing who produces evidence with whom it serves. Who produces evidence is covered separately in the map's authorship figures.
  - **Coverage.** Author locations are known for only 85% of studies.
- **Periods.** 3-year rolling windows from 2010–12 to 2021–23, with DALYs summed over the same years.
  - **Main period:** windows within 2010–2019.
  - **Extension:** windows reaching 2020–23 are shown dashed, because COVID-19 affects them.
- **Fig. 3 (as in the paper).** The observed line is compared with two scenarios fixed at 2010–12:
  - **research fixed:** only DALYs change;
  - **DALYs fixed:** only research changes.

  The box reports each line's change from 2010–12 to 2017–19, as % of 2010–12 divergence, with 95% intervals. As in the paper, the two scenarios need not add up to the observed change.
- **Uncertainty.** 95% intervals come from resampling studies within each year (1,000 draws); the 2010–12 base is resampled too.
- **Rare-cause sensitivity (the paper's check).** KLD is recomputed without causes whose research or DALY share is below 1%. We leave out one fixed set per group, covering any cause below 1% in any window, so the line does not jump when a cause crosses 1%.
  - **With high-income studies:** nutritional deficiencies and substance use.
  - **Low- and middle-income countries:** chronic respiratory, skin and substance use.
- **Which diseases moved (Fig. 4 equivalent).** We show research and DALY shares in 2010–12 and 2017–19, not the paper's per-cause KLD terms. Those terms can be negative, so they misread single causes. For example, falling HIV research scored as adding divergence.

## Findings (16 causes, change from 2010–12 to 2017–19, % of 2010–12 divergence, 95% intervals)

| Group | Observed | Only DALYs change (research fixed) | Only research changes (DALYs fixed) |
|---|---|---|---|
| With high-income studies (all vs global DALYs) | −20% (−32 to −6) | −25% (−27 to −22) | +7% (−9 to +25) |
| Without high-income studies (LMIC vs LMIC DALYs) | −5% (−34 to +25) | +10% (+3 to +16) | −9% (−36 to +20) |
| High-income studies only (supplementary) | −21% (−38 to −1) | +10% (+7 to +13) | −30% (−45 to −12) |

**With high-income studies:** divergence fell by a fifth because burden changed; research changes made no detectable contribution. This matches the paper.

**Low- and middle-income countries:** there was no clear change. Burden changes alone would have raised divergence by 10%. Research changes alone lowered it by 9%, but with a wide interval.
- Research did move a lot:
  - **HIV/AIDS:** from 18% to 10% of studies;
  - **cancer:** from 15% to 23%;
  - **maternal and neonatal:** up from 5% to 7%;
  - **cardiovascular:** stayed at about 9% of studies against about 20% of burden.
- Shifts in opposite directions, not inertia, explain the flat line.

**High-income studies only:** research changes explain the fall in divergence. This differs from the paper.

**Rare-cause sensitivity:** the trends hold (−16% with high-income studies, −19% for LMICs with a wide interval), and the sharp LMIC rise in 2016–18 disappears.

**20 causes:**
- With high-income studies, divergence falls 23%, again mostly from burden. Research changes alone: −8% (−20 to +7).
- For LMICs it stays flat (−4%).
- High-income research changes still explain that group's fall (−25%).

## Caveats

1. **Small numbers.**
   - **Study counts:** 440 LMIC studies in 2010–12 and 965 in 2017–19 (all studies: 2,999 and 5,239). The paper had 7.4–8.6 million articles.
   - **What that means:** LMIC intervals are wide, and LMIC changes cannot be told apart from zero.
2. **KLD reacts strongly to causes with few studies.** The LMIC rise in 2016–18 (from 0.205 to 0.276) comes mainly from two causes:
   - **cardiovascular disease:** its research share fell to 9.3% while its burden rose to 20.1%;
   - **chronic respiratory disease:** it fell to 8 studies in that window, 0.9% of studies against 4.7% of burden.

   The rare-cause sensitivity check removes the sharp rise.
3. **Levels are not comparable between panels.** Each panel uses a different burden reference (global, LMIC or HIC DALYs); compare trends within a panel.
4. **Shorter period.** 2010–2023, against the paper's 1999–2019. Windows reaching 2020–23 are affected by COVID-19.
5. **Different body of research.** This is health economic evaluations and reviews of them, not all health research as in the paper. Diseases are coded to GBD 2023 causes from each study's title and abstract (team coding, share v2.1).
6. **No time lag.** Research and burden are compared in the same years.
7. **Double counting by design.** A study naming several causes, or countries in both income groups, counts in each.
8. **20-cause version.** Very few studies are coded to transport injuries:
   - 0–5 per window even across all studies, and none in 2010–12 and 2011–13 overall;
   - none in most windows for LMIC or high-income studies;
   - self-harm and violence has 0–1 LMIC studies in early windows.

   An empty cause is given 0.5 study, so the 20-cause values depend on that choice.

## Files

- **Main figures, 16 causes:** `main_fig2a_16causes.png`, `main_fig3_16causes.png`, `main_fig4_16causes.png`.
- **Rare-cause sensitivity:** `supp_fig2a_rare_causes_excluded_16causes.png`.
- **20-cause versions:** `supp_*_20causes.png`.
- **High-income-only panels:** `supp_*_hic_*.png`.
- **Data:**
  - `kld_windows.csv`: every plotted value, including the rare-cause line and the causes it leaves out.
  - `kld_decomposition.csv`: the table above, both cause sets, as % changes in each line.
  - `kld_cause_contributions.csv`: shares by cause. The per-cause KLD-term columns `research` and `burden` should not be read cause by cause.
