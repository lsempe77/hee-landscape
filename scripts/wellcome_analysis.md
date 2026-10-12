# General funder analysis and the Wellcome-specific view

Run from the repository root:

```powershell
python scripts/build_wellcome_analysis.py
python -m unittest discover -s tests -p "test_wellcome_analysis.py"
```

The builder requires matplotlib, `data/raw/hee_analysis_master_v2.csv`,
`docs/data/dict.json` and `docs/data/content.json`. It validates required columns,
unique IDs, publication years, income values and the eligible-study total against
the web build. All figures, report and metadata are staged before replacement.
An incomplete or incompatible input dataset cannot replace the published outputs.

## Separation of audiences

The global `fig_funder_funders.svg` ranks the top 15 recorded funders by unique
eligible studies. Every funder has identical styling. Colours encode study setting,
including a grey category for other scope or unknown income. The rank uses all
eligible studies; the original image displayed only the income-known subset.
Counts are acknowledgements, not funding amounts or a donor-impact measure.

The Overview contains a separately labelled Wellcome card linking to the
`Wellcome-specific analysis` thematic section. Only this section highlights Wellcome.
It contains `fig_wellcome_priorities.svg` and `wellcome_analysis.html`, with donor
rankings disaggregated by theme, Wellcome counts, geographic focus and annual
publication counts. The original highlighted WebP remains archived but is no longer
referenced by the current app.

## Definitions and denominators

- Include only `is_eligible == TRUE`; count each record once per funder and theme.
- Normalise obvious NIHR, HTA, NIH, Gates, MRC and common name variants. Agency
  subunits are not comprehensively merged. Repeated names within a study count once.
- Exclude missing, no-funding and self-funded entries. The newly validated base
  is 11,149 named-funder studies, one below the earlier 11,150 overview
  classification snapshot because `Self-funded part-time doctoral student` is excluded.
- Keep Burroughs Wellcome Fund distinct from Wellcome Trust. Explicitly named
  Royal Society, MRC and NIHR cofunders in joint Wellcome strings are retained.
- The Wellcome cohort is studies whose **funder field** names Wellcome, not author
  affiliation, project relevance, exclusive support or confirmed programme membership.
- Infectious Diseases uses the existing harmonised `Infectious` disease group.
- Mental Health uses `Mental & substance use`, a broad proxy that includes substance
  use. Wellcome's Mental Health programme focuses on early intervention in anxiety,
  depression and psychosis. An additional title screen for these conditions (including
  schizophrenia) is reported separately; it does not establish early intervention.
- Climate & Health has no dedicated classification in the dataset. A **provisional
  title screen** uses the versioned regular expression in the builder, including health
  hazards and health-sector emissions. Climate Schools and the tropical/subtropical
  influenza climate-setting title are excluded as false matches. Primary-topic climate
  labels alone are not used: several label unrelated microsimulation studies. All title
  matches are shown for review. Full-text validation and a broader search remain outstanding.
- Themes can overlap. Disease-tag coverage is shown; missing tags are not negative
  classifications. No theme burden or priority-programme funding allocation is inferred.
- Show both the observed Wellcome share of all identified theme studies and its share
  among theme studies naming any funder, with explicit denominators.
- HIC/LMIC categories use `single_country` studies with known `income_broad`. Other
  scope and missing income remain in the third category, including in donor totals.

The report exports aggregate donor counts as CSV and analysis as JSON. The JSON
records the source-master SHA-256, web-build vintage, publication period and scope
definitions. Raw master data is not published by this builder.

Programme scope was checked against official sources on 12 October 2026:

- [Infectious Disease](https://wellcome.org/our-priorities/infectious-disease)
- [Mental Health](https://wellcome.org/our-priorities/mental-health)
- [Climate and Health](https://wellcome.org/our-priorities/climate-and-health)

These analyses describe the economic evaluations captured in the map, not Wellcome's
complete grants portfolio. Publication years 2010–2026 span changing strategies, and
2026 is partial. Funder attribution and theme coding have incomplete coverage.
