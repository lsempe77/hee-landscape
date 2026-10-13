# Figure text changes for the upstream build

**For:** whoever runs the upstream figure build for the HEE evidence map.
**Why:** a plain-language review of the website (October 2026) found that text inside the figure images is often too technical for its audience: policymakers, funders and journalists. Captions, titles and summaries on the site have already been fixed. The text inside the images can only change when the figures are redrawn.

The site shows each figure with a plain title and summary first, and a collapsed **Technical details** note underneath. Methods detail belongs in that note, not in the image.

Not covered here:
- The five figures already redrawn in this repository with plain wording and income at publication year: `fig_equity_time`, `fig_metric`, `fig_intervention_mix`, `paper05` and `fig_theme_rank`. Their `*_pubyear` versions show the target style.
- The funder and Wellcome figures (`fig_funder_funders`, `fig_wellcome_priorities`), which wait for the updated funder data.

## Rules for every figure

1. **No internal text in images.** Remove script and file names (`R/lookup-mesh.R`, `R/05-topic-model.py`, `data/crosswalk_mesh_gbd.csv`, `research_burden_ratios.csv`), model names and prompt hashes, "audit finding N", "protocol Appendix K", "Journal version", "Figure 2:"-style journal captions, "reworked at reviewer request", run and access dates, "team export", "metadata harvest", "extraction flag", "screening corpus", "framework v6.8" and indicator codes such as `SP.POP.TOTL`.
2. **Spell out or define jargon in titles, subtitles, axes and legends.**
   - LMIC → "low- and middle-income countries". HIC → "high-income countries". NCD → "non-communicable (long-term) diseases".
   - QALY → "a year of life in full health". DALY → "a year of healthy life lost to illness or early death"; on axes, "Studies per 100,000 healthy years lost (DALYs)".
   - ICER → "cost per health gained". "Model-based" → "estimated with a computer model". "Log scale" → say so in the axis title.
   - Drop "eligible", "full economic evaluation", "single-country" and "extracted geography" from visible text; they belong in Technical details.
3. **Titles state the finding plainly, without wordplay or loaded words.** Avoid "(Un)equal weight", "grabbing… market", "exploit", "seized", "injustice", "inequity", "donors", "scorecard", "opportunity matrix", "where the next pound buys", "real progress", "public good", and "never overlap" (true by construction).
4. **One footnote line at most** (source and years). Denominators, n values, confidence-interval methods, map projections, population cut-offs and MeSH codes move to Technical details.
5. **Consistent terms across figures:**
   - "studies", not a mix of studies, evaluations and evidence
   - "low- and middle-income", not LMIC or low-/middle-income
   - "funders", not donors
   - "100,000", not "100 000"
   - the same disease-group names everywhere ("Signs / symptoms" vs "Complications & symptoms"; "Immune (incl. HIV)" vs "Infectious")
6. **Regions:** the site now uses WHO regions (with the UN M49 fallback for Taiwan and Hong Kong). Figures still on UN sub-regions are `fig_forest`, `fig_map_authorship` and `fig_map_model`. Redraw them by WHO region (`scripts/who_regions.csv`), or say in the image why UN sub-regions are used.
7. **Income groups:** use the group at the time of publication (`scripts/income_pubyear.csv`; World Bank group in force on 1 January of the publication year) for any count of studies. Country-level figures keep the current group.

## Numbers to reconcile, or explain in Technical details

| Item | Values seen | Cause, if known |
|---|---|---|
| Countries | 133, 138, 152, 153, 154, 155, 187, 197 | Different bases (map data, population cut-off, all places named) |
| Study–country counts | 31,471 (ratio figure) vs 31,627 (`fig_deficit`) | Unknown |
| Evaluations | 35,094 (`fig_collab_chord`) vs 41,657 | Chord uses studies with author locations |
| Open access | 71% (`fig_map_openaccess`) vs 66.6% (Overview) | Map counts study–country pairs |
| Model-based | 63.9% (`fig_map_model`) vs 54% (Overview) | Map counts study–country pairs |
| `fig_inequality` | Subtitle "58% of evidence / 43% of burden" vs footnote "48.1% / half" | Unknown |

## Rendering defects

- `fig_funder_opportunity`: the footnote is cut off at the bottom.
- `fig_reach_time`: the 100/100/98/96% end labels overlap.
- `fig_funder_capacity`: the circle-size legend is invisible.
- `fig_injustice`: the title is truncated ("…disease burden? —").
- `fig_inequality`: the annotation dot sits above the curve.
- `fig_map_burden`: grey means "no data", but the middle of the colour scale is also near-grey. Use a hatch or a clearly different grey.
- `fig_intervention_map`: the right-hand labels overlap the lines.

## Per-figure changes

**fig_method_stream**
- Title: "More studies now measure health gains in QALYs or DALYs". The current "exploit" reads as misuse.
- Subtitle: "Between 2010 and 2025, cost-utility studies rose from 43% to 50% of all evaluations." (Drop "seized".)
- Y-axis: "Evaluations published per year".
- Legend: add a one-line plain gloss of the four evaluation types in the footnote.

**fig_disease_circular**
- Subtitle: "Each bar is a disease group; longer bars mean more studies. Colour shows whether research leans towards richer or poorer countries."
- Bar label: "General symptoms & complications (not a disease group)", or leave this bar out.
- Legend: "More in low- and middle-income countries" in place of "Skews LMIC".
- Footnote: keep "A study can cover several diseases, so shares add to more than 100%."; move the rest.

**fig_transition**
- Title: "Research in lower-income countries is shifting towards long-term illnesses". "Mirroring disease burdens" overclaims, since injuries are about 2% of research against 12% of burden.
- Subtitle: "three broad disease types". Note that burden data stop in 2023.
- Y-axis: "Share of research in low- and middle-income countries".

**paper04**
- Title: "In low- and middle-income countries, research is moving from infections towards cancer and long-term disease".
- Subtitle: "Vertical lines show uncertainty"; move the Wilson intervals mention.
- Align the disease-group names with the other figures. Note: its numbers could not be reproduced from the team export, so please check them against the current mapping when redrawing.

**fig_intervention_map**
- Subtitle: "Each dot is a study, placed near studies with similar abstracts. Vaccine and financing research leans most towards low- and middle-income countries." Remove "UMAP-reduced", the run date and the model and prompt details.
- Panel title: "Where the studies are set", not "Who it serves". Labels: "Medicines" and "Screening", not "Pharma" and "Screening/dx".

**paper02**
- Title: "Studies built on computer models usually report QALYs or DALYs; studies of real patients mostly don't."
- Remove "Figure 2:" and move the long caption.

**fig_intervention_decision**
- Title: "Financing and care-model studies report fewer of the details decision-makers look for". "Decision-usefulness lag" overclaims, because the measure is what abstracts mention.
- Column heads: "Reports cost per health gained", "Compares with a value-for-money threshold", "Says whose costs count", "Reports uncertainty", "Uses a computer model".
- Keep "Not reported in the abstract does not mean not done"; remove the prompt hash and file names.

**fig_worldmap**
- Title: "Studies per person, by country".
- Subtitle: "Grey: no studies. Pale grey: studied, but too small to rate per person."

**paper03**
- Remove "Figure 3:", `SP.POP.TOTL` and the access dates.
- Country names: "Serbia" and "Eswatini".

**fig_dotmap**
- Title: "Most economic evaluations are about high-income countries", not "Look north…".

**fig_authorship_pattern** (wait for the affiliation data and redraw with income at publication)
- Panel B: "In 70% of these studies, every other co-author is based in a high-income country."
- Legend: "Other authors all from high-income countries".
- Footnote: keep "'Local' = at least one author based in the country studied."

**fig_forest** (wait for the affiliation data)
- Regions: WHO regions.
- Subtitle: "studies of one country where author locations are known".
- Footnote: "Lines show the 95% uncertainty range". Avoid "NA" for missing (it reads as North America).

**paper06**
- Remove "so the test is unambiguous". Footnote: "Author locations known for 85% of studies".

**fig_collab_chord**
- Subtitle: "How authors from different country income groups work together". Remove "harvest".

**fig_research_burden_ratio**
- Remove the CSV file name; link the download from the page instead.

**paper07**
- Remove "Figure 7:". Axis: "Studies per 100,000 healthy years lost (log scale)".
- Subtitle: "The typical high-income country has 22 times more studies per unit of burden than the typical low-income country."

**fig_burden_disease_companion**
- Title: "Some diseases get far less research than their burden suggests".
- Labels: "Cancers", "Eye and ear", "Other non-communicable". Remove the file names.
- It largely repeats paper08; consider showing one.

**paper08**
- Remove "Figure 8:", "newly separated" and the figure cross-reference.
- Axis: "Research relative to burden (1 = in line with burden)".

**fig_deficit**
- Title: "Where studies fall furthest short of, or exceed, disease burden".
- Move the formula and pair counts. Add a note that Russia is classed as high-income.

**fig_injustice**
- Title: "More disease burden, but not more studies" (fixes the truncation).
- Subtitle: "Most low- and middle-income countries have fewer studies than their disease burden would suggest", not "consistently".

**fig_inequality**
- Title: "Half the disease burden, 17% of the studies". The current title says the opposite of the chart.
- Reconcile the subtitle and footnote numbers. Move the Gini coefficient to Technical details. Axis: "Share of low- and middle-income burden (countries from least to most studied)".

**fig_openaccess**
- Subtitle: "By 2025, about four in five studies were free to read." (Drop "public good".)
- Remove "reference-case audit". Label: "all studies".

**fig_map_burden**
- Title: "Studies relative to disease burden, by country".
- Remove the causal claim about evaluation systems, or soften it. Fix the no-data grey.

**fig_map_openaccess**
- Legend: "% open access (average 71%)". Move the footnote.

**fig_map_growth**
- Title: "Many countries in Africa and Asia have a newer evidence base". "Growing fastest" overclaims.
- Subtitle: "Most countries (about 6 in 7) had more studies in 2018–2026 than in 2010–2017."
- Legend: "% of a country's studies published since 2018".

**fig_map_authorship** (wait for the affiliation data)
- WHO regions. Subtitle: "Share of studies of one country that include at least one author based there." Drop "the gap between regions is the story".

**fig_map_model**
- WHO regions. Define model-based in the subtitle.
- Use a neutral colour pair, since red reads as "bad".

**fig_reach_time**
- Title: "Nearly every country now has at least one economic evaluation".
- Legend: "Countries counted", not "Denominator". Fix the overlapping end labels.

**fig_decision_time**
- Title: "Study summaries increasingly report what decision-makers need".
- Legend gloss: ICER = "cost per health gained"; perspective = "whose costs are counted".

**fig_funder_opportunity**
- Title: "Where research is thinnest compared with disease burden".
- Subtitle: "0.25× = a quarter of the research the burden would suggest". Fix the clipping; remove the file names.

**fig_funder_scorecard**
- Title: "Where evidence is scarcest relative to disease burden", not "Funding priority scorecard".

**fig_funder_capacity**
- Soften "would matter most" to "may benefit most from investment in local researchers". Fix the size legend.

**fig_funder_trajectory**
- Plain period labels (2010–17 vs 2018–26). Replace "most additional"; spell out LMIC in the axis.
