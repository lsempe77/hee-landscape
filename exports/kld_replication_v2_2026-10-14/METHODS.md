# Research–disease divergence in health economic evaluations (version 2)

Built by `scripts/build_kld_replication_v2.py` on 14 October 2026. This revises version 1 (`exports/kld_replication_2026-10-14/`, which has the full list of differences from the paper). The aim is to answer one question: **does research shift with disease burden once high-income studies are removed?**

Reference: Schmallenbach L, et al. *Nature Medicine* 31, 3101–3109 (2025). doi:10.1038/s41591-025-03923-0.

## Design

- **Measure.** For each period, KLD(p ‖ q) = Σ p ln(p/q).
  - p is the share of DALYs from each GBD level-2 cause.
  - q is the share of research on the same cause, counting study–cause links, with add-one smoothing.

  The main analysis uses the paper's 16 causes. The supplementary version uses 20, adding mental disorders and the three injury groups.
- **Groups.** The main comparison has two:
  - **with high-income studies:** all studies against global DALYs;
  - **without:** studies of low- and middle-income countries against LMIC DALYs.

  Studies of high-income countries against HIC DALYs are supplementary. Studies are placed by the country studied, and income is the World Bank group in force at publication.
- **Periods.** 3-year rolling windows, labelled 2010–12 to 2021–23.
  - **Main period:** windows within 2010–2019, as the paper stops its Fig. 3 at 2019.
  - **Extension:** windows reaching 2020–23 are shown dashed, because COVID-19 affects them.
  - **DALYs:** summed over the same three years.
- **Decomposition (Fig. 3 box and `kld_decomposition.csv`).** The change in KLD from 2010–12 to 2017–19 is split into two parts:
  - a **research part**, from research shares changing;
  - a **burden part**, from DALY shares changing.

  Each part is the average of the two possible orderings: fixing research first, or fixing burden first. The two parts therefore add up exactly to the observed change. Results are expressed as % of the 2010–12 divergence.
- **Uncertainty.** 95% intervals come from resampling studies within each year, with 1,000 draws.
- **Diseases (Fig. 4).** The paper's Fig. 4 splits KLD into per-cause terms. Those terms can be negative, so a cause whose research moves towards its burden can still score as adding divergence. In our LMIC data:
  - **HIV research** fell from 17.7% to 9.5% of studies, against 3–4% of DALYs, yet it scored as adding divergence;
  - **cancer research** rose from 14% to 23%, against about 10% of DALYs, yet it scored as reducing it.

  We therefore show the shares themselves: each cause's research share and DALY share in 2010–12 and in 2017–19, and whether the gap between them narrowed or widened. The per-cause KLD terms remain in `kld_cause_contributions.csv` (columns `research`, `burden`) but should not be read cause by cause.

## Findings (16 causes, 2010–12 → 2017–19, % of 2010–12 divergence, 95% intervals)

| Group | Observed change | From research shifting | From burden shifting |
|---|---|---|---|
| With high-income studies (all vs global DALYs) | −20% (−32 to −7) | +6% (−8 to +21) | −26% (−29 to −23) |
| Without high-income studies (LMIC vs LMIC DALYs) | −1% (−30 to +36) | −7% (−35 to +28) | +7% (+2 to +10) |
| High-income studies only (supplementary) | −21% (−37 to −1) | −30% (−45 to −11) | +9% (+7 to +11) |

**With high-income studies:** divergence fell by about a fifth, and the fall is explained by burden shifting. Research made no detectable contribution. This matches the paper's finding for health research overall.

**Without high-income studies:** there was no net change in divergence.
- Burden shifting alone would have widened it by about 7%, as LMIC burden moved towards non-communicable diseases.
- Research offset that, but its part cannot be told apart from zero.
- Fig. 4 shows that LMIC research did move a lot:
  - **HIV/AIDS:** from 17.7% to 9.5% of studies;
  - **respiratory infections and TB:** from 13.5% to 10.0%;
  - **maternal and neonatal:** up from 5.2% to 6.9%;
  - **cancer:** from 14% to 23%, well past its roughly 10% share of burden;
  - **cardiovascular:** stayed at about 9% of studies against about 20% of burden.

  Large shifts that cancel out, not inertia, explain the flat line.

**High-income studies only:** divergence fell by about a fifth, and research shifting explains it. Burden barely moved.

**20 causes (adding mental disorders and injuries):**
- High-income research shifting still explains the fall: −25% (−39 to −11).
- The global fall is again mostly burden.
- LMIC divergence stays flat: −1% (−26 to +23).

## Caveats

- **Small LMIC counts.** There are 442 LMIC studies in 2010–12, against millions of articles in the paper. The LMIC research part has a wide interval.
- **Not the paper's geography.** Research is placed by the country studied, while the paper uses first-author country.
- **COVID-affected extension.** The windows reaching 2020–23 are affected by COVID-19 and shown separately.

## Files

- **Main figures, 16 causes:** `main_fig2a_16causes.png`, `main_fig3_16causes.png`, `main_fig4_16causes.png`.
- **20-cause versions:** `supp_*_20causes.png`.
- **High-income-only panels:** `supp_*_hic_*.png`.
- **Data:** `kld_windows.csv` (every plotted value), `kld_decomposition.csv` (the table above, both cause sets), `kld_cause_contributions.csv` (shares and per-cause terms).
