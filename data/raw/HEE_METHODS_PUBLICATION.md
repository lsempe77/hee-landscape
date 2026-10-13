# Methods

*Publication version of the HEE methods (health economic evaluations arm). The full record of
decisions, provenance and data checks is `HEE_METHODS.md`; every number here is taken from the v2
analysis dataset (October 2026). Items in [square brackets] need confirming before submission.*

## Study design

We conducted a systematic evidence map of full economic evaluations of health-care delivery
published from 1 January 2010 onward, as one arm of a protocol-registered map of health-system
financing research [protocol reference]. A full economic evaluation was defined as a study that
compares two or more ways of delivering care on both their costs and their clinical consequences.
The map is descriptive: it characterises the evidence base, and comparisons of research volume
with disease burden are ecological.

## Search and study identification

We searched Scopus, the Cochrane Library, and MEDLINE, EconLit and Global Health (Ovid) [search
dates], combining terms for health, for financing and for specified topics (search strategies in
the protocol, appendix E). After de-duplication in EPPI-Reviewer, 1,154,050 unique records were
identified. Every record was screened; machine-learning prioritisation was not used to truncate
screening.

## Eligibility criteria

Records were assessed against a hierarchical code list (protocol appendix F, list F2), in which
the first failing criterion determines the exclusion: publication before 2010; a topic that is
not the delivery of health care through health-system or private platforms (fiscal policy, such
as taxes and subsidies, was in scope); and a design that is not a full economic evaluation. Partial
evaluations, including cost-of-illness studies, budget-impact analyses, cost-minimisation
analyses and studies comparing costs only, were excluded, as were studies whose consequences were
not clinical (for example, service use alone). Systematic and narrative reviews that synthesised
published economic evaluations were eligible.

## Screening

Titles and abstracts were screened by a large language model (GLM-5.2) using a structured prompt
that encodes the code list. Each record was assessed three times (temperature 0.5) and the votes
were aggregated; where the three assessments disagreed, a second model (DeepSeek-V4-Pro) assessed
the record and either model's inclusion was sufficient. The prompt was developed against
human-labelled reference sets until it met prespecified thresholds (sensitivity of at least 0.95,
Cohen's κ of at least 0.70, expected calibration error of at most 0.10); sensitivity on the
development reference was 0.959 (93 of 97 eligible records; 95% CI 0.899–0.984). Sensitivity was
then measured on an independent, blinded random sample of 1,000 records that was never used in
development: 0.86 (32 of 37 eligible records with an abstract; 95% CI 0.72–0.94). Records that the
model included but flagged as uncertain were advanced to data extraction, where the eligibility
assessment was repeated on the abstract. Records without an abstract in any source could not be
screened or extracted and were excluded.

## Data extraction

Data were extracted from titles and abstracts by GLM-5.2 using a structured extraction framework
that asks for a verbatim supporting quotation for each field. Extracted fields were the type of
economic evaluation, whether it met the definition of a full evaluation, the evidence base (for
example trial, observational or modelled), whether a decision-analytic model was used, the
countries studied and the consequences measured. A study was eligible for analysis only if both
type and status fields identified a full economic evaluation with a clinical consequence; studies
the model could not classify were excluded. Duplicate publications were removed by DOI and then
by normalised title and year. The type of intervention evaluated and the care setting were coded
by a second language model (DeepSeek-V4.1-Flash, temperature 0), with a single frozen prompt.

Extraction accuracy was assessed against a human-coded sample: of studies the model accepted as
full economic evaluations, 9–12% were judged not to be.

## Coding and external data

For publication-year income analyses, countries were mapped to World Bank historical income
classifications in force on 1 January of each study's publication year (the World Bank fiscal
year ending in that calendar year). Countries changing classification therefore contribute to
different income groups in different publication years. This uses publication year as a proxy
for the timing of the research, rather than the year of data collection. Countries without a
classification in that year were excluded from income-group comparisons, except Ethiopia:
for 2026 publications, its missing FY2026 classification was replaced by its FY2025 low-income
classification. For Venezuela's 2026 publications, its missing FY2026 classification was
replaced by its last available classification, FY2021 upper-middle income, because FY2025 was
also unavailable. These are analysis exceptions rather than official FY2026 classifications;
Venezuela's missing classifications for 2022–2025 were not filled. Taiwan, which has no
World Bank entry, was coded as high income in every year by recorded override. Populations were
retrieved from the World Bank API [access date]. Studies
naming more than 15 countries were classed as multi-country. Disease areas were assigned from
the National Library of Medicine's Medical Subject Headings (MeSH), mapped to 14 groups aligned
with Global Burden of Disease (GBD) 2023 level-2 causes; maternal and neonatal conditions were
taken from the MeSH pregnancy-complications branch, and residual urogenital, blood and oral
conditions were grouped as other non-communicable diseases only when the heading belonged to no
other group. Disease burden was measured in disability-adjusted life-years (DALYs) from GBD 2023,
and health spending from the IHME health-spending series. Outcomes reported by each study were
grouped into families by ordered keyword rules; a study was counted as using a generic outcome
measure if it reported quality-adjusted or disability-adjusted life-years.

## Topic mapping

To describe the thematic structure of the evidence beyond disease codes, titles and abstracts
were embedded with a sentence-transformer model (all-MiniLM-L6-v2), reduced to two dimensions
with UMAP and clustered with HDBSCAN (minimum cluster size 200), giving 73 clusters labelled by
their most distinctive terms (class-based TF-IDF); 13.7% of studies were not assigned to a
cluster. Clustering was stable across five additional random seeds (mean adjusted Rand index 0.89
among clustered studies; 71 of 73 clusters recovered in every run).

## Analysis

Analyses are descriptive. We report counts and proportions with Wilson 95% confidence
intervals; research density per country relative to population, disease burden and health
spending; and, by disease area, the ratio of each area's share of research to its share of
disease burden, separately for high-income and for low-income and middle-income countries. A
ratio of one indicates research proportional to burden; it is a reference point, not a target.
Study-level income comparisons use studies of a single country. The web Explorer's income
filter and income trends use publication-year classifications; the filter also applies to
study counts displayed on its country maps and tables. Country-level colours, income labels
and profile peer comparisons use the July 2026 classification, allowing each country to have
one income group in these summaries. Country landscapes and profiles include all publication
years and do not inherit Explorer filters. These distinctions are stated alongside the views.
Country counts vary with geography coverage, available denominators and minimum-study rules.
The website contains 155 countries, 153 with studies; its burden analysis includes 154 with
positive DALYs (152 with studies), contributing 31,471 unique study–country pairs. The deficit
figure instead uses all 204 locations in the national GBD export and 31,627 pairs across that
same location set. The full eligible geography contains 187 countries/territories and 31,775
pairs. Each multi-country study contributes once per named country. The country-reach figure
uses each year's income classification for its denominator and reports cumulative coverage
within that year's groups; unavailable country-year classifications are excluded.
Analyses were done in R (version 4.4.1) and
Python.

## Deviations from the protocol

Screening and extraction were done by language models with human-labelled validation rather than
by two independent human reviewers, and no full-text stage was conducted. As a result, records
the screening model flagged as uncertain were assessed at extraction from the abstract instead
of at full text, and records without an abstract were excluded. Cost-minimisation analyses were
excluded as partial evaluations in all cases, and studies with non-clinical consequences were
excluded.

## Results at a glance

Of 1,154,050 records identified, 34,239 had no abstract and could not be screened. Of the
1,119,811 screened, 98,065 were advanced to data extraction (45,792 included and 52,273 flagged
as uncertain), of which 25,220 had no abstract to extract from. Of the 72,845 records extracted,
31,188 were excluded (13,573 partial evaluations, 11,975 not classifiable as full evaluations,
4,965 with non-clinical consequences and 675 duplicates), leaving **41,657 full economic
evaluations**: 39,951 primary studies and 1,706 reviews. Of these, 46.9% reported a generic
outcome measure (QALYs or DALYs). The study selection flow is shown in figure 1.

## Limitations

Screening sensitivity on the independent sample (0.86) was below the 0.95 target, so some
eligible evaluations are missing. Extraction over-includes by an estimated 9–12%, and studies
whose only consequence is service use or a diagnostic result could not all be removed. The
evidence base is almost entirely in English (99.8%). Geography could be assigned for 72% of
studies, and MeSH disease codes for about half. Methodological quality was not assessed, because
full texts were not retrieved; indicators of decision-analytic reporting are taken from abstracts
and record what was reported, not what was done.
