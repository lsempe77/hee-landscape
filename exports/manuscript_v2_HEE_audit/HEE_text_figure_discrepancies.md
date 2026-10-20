# HEE text–figure audit — manuscript v2.0

Reviewed: `C:/Users/Sawa/Downloads/HSF_Interim_Manuscript_Draft_v2.0.docx` (file modified 19 October 2026). The manuscript was not edited.

Scope: HEE Results text, the actual embedded Figures 10–15 and their captions, and HEE claims in the Discussion. Embedded figures were extracted and visually inspected directly; document page layout was not rendered. Paragraph numbers below refer to `manuscript_paragraphs.txt`, not Word page numbers. Supplementary figures are referenced by placeholders and are not embedded in the reviewed file, so their visual agreement could not be checked. Numerical checks use the repository's current eligible master, deduplicated study–country pairs, outcome-family records, topic assignments and exported figure data.

## Main finding

The principal issue is mixing the 39,625 original full evaluations with the 41,610 eligible HEE publications, which also include 1,985 reviews without an identified original evaluation. Figures 10 (map) and 11 use full evaluations; Figures 12–15 retain broader eligible-publication populations, subject to each figure's additional filters. These analyses can legitimately coexist, but their populations must be named explicitly.

## Confirmed discrepancies and required clarifications

| Location | Manuscript statement | Figure/source finding | Assessment |
|---|---|---|---|
| Figure 12 caption, paragraph 0252 | Base 27,417 economic evaluations | Embedded figure footer: 27,897 single-country eligible studies, including reviews; the nine circle counts sum to 27,897 | Direct contradiction, difference 480. Either change caption to the figure's population or replace the figure with the full-evaluation version. |
| Figure 12 caption, paragraph 0252 | Darker versus lighter dots distinguish income | Embedded figure uses blue versus orange, explicitly labelled HIC versus L&MIC | Caption belongs to an earlier figure. Replace with the actual colour mapping. |
| Figure 12 caption, paragraph 0252 | World Bank classification (2026), with no publication-year qualification | Figure footer and source use income at publication year | Specify publication-year income, as the adjacent Results text already does. |
| Outcomes paragraph 0255 / Figure 13 | Adverse events 28%; survival 28%; symptoms 21%; quality of life 17%, cited to Figure 13 | These reproduce the all-publication population, n=41,610. Figure 13 uses 27,897 single-country studies; weighted across its two settings the corresponding shares are 24.5%, 30.0%, 17.3%, 15.9%. The plotted setting-specific percentages are different again. | Denominator mismatch rather than an arithmetic error. Label the all-publication percentages as such and explain the figure's smaller base, or report its setting-specific percentages. |
| Outcomes paragraph 0255 / Figure 11 | 46.9% of evaluations report QALYs or DALYs | 46.9% = 19,515 / 41,610 eligible publications. Among original full evaluations the value is 18,774 / 39,625 = 47.4%. Figure 11 uses full evaluations and displays 47% after rounding. | At one decimal place, use 47.4% if describing full evaluations, or retain 46.9% with the broader population named. The integer figure label alone masks this distinction. |
| Disease paragraph 0245 | 36,446 evaluations (87.6%) have a GBD cause | These values use all 41,610 publications. Among full evaluations, 34,812 have a GBD cause. The stated cancer count 7,856 is also all-publication; the full-evaluation count is 7,531. | Same population/terminology issue: identify eligible publications, or recompute this paragraph consistently for full evaluations. |
| Disease paragraph 0245 | The remaining publications are 2,500 no specific disease, 1,516 risk-factor only, 1,070 unattributable | 36,446 + 2,500 + 1,516 + 1,070 = 41,532, leaving 78 of the 41,610 unexplained. Source contains 72 `none_coded` and 6 `not_coded`. | Add the 78 uncoded records to make the classification exhaustive. |
| Geography paragraph 0243 / Figure 10 | 187 of the world's 204 countries or territories | Figure 10's 187 study-geography locations include Hong Kong, Cayman Islands, French Guiana and Guadeloupe, which are outside the 204-location national GBD export. Only 183 of the 204 GBD locations have studies. | The 187 count is correct; “187 of 204” combines two country universes. Say 187 countries and territories, then discuss GBD overlap separately if necessary. |
| Geography paragraph 0243 | Top three/five/ten account for 49.7%, 57.7%, 70.7% of studies naming a country | Distinct full evaluations naming any top-three/five/ten country: 49.1%, 57.1%, 70.1%, denominator 28,505. For all eligible country-naming publications: 49.5%, 57.4%, 70.4%, denominator 29,104. | The quoted percentages do not reproduce under either current population. Specify population and count each study once in each top-country union. Do not substitute shares of study–country pairs. |
| Figure 15 caption, paragraph 0274 | “The shaded area” identifies ratios below one | Embedded figure has a dashed 1× reference line and no shaded area | Stale caption. Say “Values to the left of 1× indicate a smaller research share than burden share.” |
| Figure 15 caption and Methods | Burden pooling period not stated | Embedded figure footer and source use absolute DALYs pooled over 2010–2023; research spans 2010–2026 | State the pooling period and distinguish GBD 2023 release/round from a single burden year. |
| Discussion paragraph 0277 | 41,610 full economic evaluations | Figure 10 and Results: 41,610 eligible publications, including 39,625 original full evaluations | Definite numerical category error. Replace with “41,610 HEE publications, including 39,625 original full evaluations.” |
| Discussion paragraph 0282 versus Results 0243 | Median HIC evaluations per 10 million: 73.4 in Discussion, 84.1 in Results | 84.1 reproduces the current website country-reference median for all eligible publications. A full-evaluation-only median on that same reference is 80.7, not 73.4. | Reconcile population and reference country set; the two manuscript values contradict each other. |
| Discussion paragraph 0298 versus Results 0243 | 157 of 160 countries over one million population, versus 98.7% coverage | 157 / 160 = 98.1%, not 98.7%. The current website country reference has 155 locations, of which 153 have studies: 98.7%, with Eritrea and Mauritius unreached. | These are different reference universes. Do not mix them; validate the intended full population reference before choosing a single global coverage statement. |
| Discussion paragraph 0298 versus Figure 12 | L&MIC vaccine share 41%, financing/payment share 32% | Embedded Figure 12: 42% vaccines and 33% financing/payment. Exact broader-publication shares: 42.47% and 33.21%. Full-evaluation-only shares: 42.61% and 33.37%, rounding to 43% and 33%. | Discussion values are stale under both current versions. Match the chosen figure population. |

## Additional data-source checks, not direct text–figure contradictions

- Funding paragraph 0266 says 30,508 studies lack funding information. The current web funding registry identifies a funder for 11,149 / 41,610 publications, leaving 30,461 without a registered funder. The headline 27% still rounds correctly. Reconcile the funding-data version and definition before changing exact text; a raw nonempty funder string and a harmonised named funder are different measures.
- The geographical Gini of 0.84 is not reproducible from the distribution of evaluation counts across the 187 observed countries: full-evaluation counts give 0.86265 (0.86), broader eligible-publication counts 0.86340 (0.86). Including zero-study countries changes the result again. The manuscript needs the Gini's country universe and definition before this can be treated as the same statistic.
- The country burden paragraph 0270 uses 154 countries and 31,437 study–country pairs, which matches the existing website burden-reference audit. It should name the broader eligible-publication population, since full-evaluation-only counts differ. The reported income-group burden multipliers are referenced to an absent supplementary figure and were not visually verified here.
- Figure 11's embedded image predates the newly added burden-coverage explanation in the repository's current regional-profile image. Its regional numeric values remain the same. Insert the latest image if the manuscript is intended to include that clarification.

## Checks that pass

- 41,610 total eligible HEE publications; 39,625 original full evaluations; 1,985 reviews without identified original evaluation.
- 38,958 non-review evaluations + 667 reviews reporting their own original evaluation = 39,625.
- Full-evaluation type shares: CUA 48.2% (19,097); CEA 25.6% (10,150); CCA 22.8% (9,020); CBA 3.4% (1,358).
- 95.2% full evaluations and 4.8% reviews-only are correctly rounded.
- 51% published since 2020 is consistent after rounding (50.79% of all eligible publications; 50.52% of full evaluations).
- 71.9% of original full evaluations name a country: 28,505 / 39,625.
- All 187 countries and territories have at least one original full evaluation in the current complete geography data. Figure 10's map is now counts, not DALY-adjusted rates, and its caption describes that correctly.
- Figure 11's African communicable share 78%, other regions 15–40%, and HIV 25% match the text.
- The 36% pharmaceutical share rounds correctly for both Figure 12's existing broad population and the alternative full-evaluation population.
- Figure 14: 73 qualifying topic clusters and 24,225 topic-assigned single-country studies with known publication-year income are correct. The base should be described as *topic-assigned*, not simply all single-country studies with known income (which would be 27,897). Topic labels and the high-versus-lower-income pattern agree with the prose.
- Figure 15 research denominators HIC 17,692 and L&MIC 7,331 match the source data.
- Open access: 24,216 / 36,332 known-status publications = 66.65%, correctly rounded to 66.7% in the text and 67% in Figure 10. This is a known-status denominator, not all 41,610.

## Suggested priority

First decide whether Figures 12–15 are intended to include reviews. Then align their captions, text and denominators. Correct the definite Figure 12 base mismatch, the omitted 78 disease records, the Discussion's 41,610-full-evaluations wording and the stale Discussion percentages. Preserve the independently verified 39,625 full-evaluation total.

Recalculated values are recorded in `computed_checks.json`. No manuscript text or figures were changed during this audit.
