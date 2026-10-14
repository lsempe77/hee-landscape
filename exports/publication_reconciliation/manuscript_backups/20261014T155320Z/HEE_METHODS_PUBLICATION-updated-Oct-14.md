# Methods

*Publication version of the HEE methods (health economic evaluations arm). The full record of
decisions, provenance and data checks is `HEE_METHODS.md`; final descriptive counts use the reconciled v2
analysis dataset (14 October 2026); screening and validation results describe their original
reference samples, and topic-model stability describes the original clustering run. Items in [square brackets] need confirming before submission.*

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

A subsequent publication-family audit investigated 61 potential excess reports across 57
normalised-title groups containing 118 records, and traced five additional full articles.
Titles, author teams, abstracts, sample sizes, interventions, study periods, results, DOIs,
trial registrations and publisher version statements were compared. We retained the newest
full research article for each duplicated evaluation; later abstracts, translations and
synopses did not displace a full article. Distinct evaluations, substantive companion analyses
and review/HTA updates were retained. The audit excluded 44 redundant reports, two registrations
without results and one retracted paper. Bundled-payments and carpal-tunnel relationships were
adjudicated by the study team from matching study details without an explicit publication link;
the Ginkgo translation was explicitly confirmed by the publisher. Original records were
preserved with exclusion reasons and retained-report links. This was a targeted audit, not a
whole-corpus search for all linked publications.

Review status was subsequently reconciled using titles and abstracts, distinguishing systematic
reviews, non-systematic reviews and records not identified as reviews. Labels were based on
explicit descriptions and reconciled against documented exceptions; targeted published-methods
checks resolved selected ambiguous cases. A separate field recorded whether a review also
contained an original evaluation, so review status did not by itself determine exclusion.
These classifications were not independently validated across the whole corpus.

Extraction accuracy was assessed against a human-coded sample: of studies the model accepted as
full economic evaluations, 9–12% were judged not to be.

## Coding and external data

Study geography was based on the country or setting named in the title and abstract;
author affiliations and publisher locations were not used to infer the patient setting.
Where the title and abstract did not state a sample location, it was recorded as not reported.
For income comparisons over time, countries were mapped to World Bank historical classifications
in force on 1 January of each study's publication year. Missing country-year classifications
were excluded from these comparisons, except for recorded 2026 exceptions: Ethiopia used its
FY2025 low-income classification and Venezuela its last available FY2021 upper-middle-income
classification. Taiwan was coded as high income in every year by recorded override.
Country-level maps and cross-sectional summaries used the July 2026 classification. Populations
were retrieved from the World Bank API [access date]. Studies naming more than 15 countries
were classed as multi-country. Disease areas were coded to Global
Burden of Disease (GBD) 2023 causes from each study's title and abstract by a language model
(DeepSeek-V4.1-Flash), recording the condition targeted by the evaluated intervention at level 3
of the GBD cause hierarchy and rolling it up to level 2 and level 1; risk factors were recorded
separately and never used to infer a disease. Conditions that IHME's ICD-10 to GBD mapping treats
as garbage codes (for example, heart failure) were recorded as disease unattributable, and
injuries or infections named without a specific cause were coded at level 1. Coding rules for
disputed conditions were set by a subject-matter expert using the ICD-10 mapping. A GBD analysis group was
assigned to 36,446 of 41,610 included records (87.6%), and analyses use 24 groups: the 22 GBD level-2 causes plus injuries
and infections without a stated cause. In the original coding-validation samples, a second model (GLM-5.2) coded a random 47% of
studies (agreement 91.1% at level 2), and an independent coding derived from the National Library
of Medicine's Medical Subject Headings (MeSH) shared at least one level-2 cause with the abstract
coding for 89.0% of the 22,794 studies with MeSH disease headings. Disease burden was measured in disability-adjusted life-years (DALYs) from GBD 2023,
and health spending from the IHME health-spending series. Outcomes reported by each study were
grouped into families by ordered keyword rules; a study was counted as using a generic outcome
measure if it reported quality-adjusted or disability-adjusted life-years.

## Topic mapping

To describe the thematic structure of the evidence beyond disease codes, titles and abstracts
were embedded with a sentence-transformer model (all-MiniLM-L6-v2), reduced to two dimensions
with UMAP and clustered with HDBSCAN (minimum cluster size 200), giving 73 clusters labelled by
their most distinctive terms (class-based TF-IDF); 13.7% of studies were not assigned to a
cluster. The model was fitted to 41,661 records eligible at the time of the October 2026
run and was not refitted after subsequent eligibility changes, preserving cluster identities.
Of the final 41,610 included records, 41,583 had topic coordinates; 27 were unmapped.
Clustering was stable across five additional random seeds (mean adjusted Rand index 0.89
among clustered studies; 71 of 73 clusters recovered in every run).

## Analysis

Analyses are descriptive. We report counts and proportions with Wilson 95% confidence
intervals where used; research density per country relative to population, disease burden and
health spending; and, by disease area, the ratio of each area's share of research to its share
of disease burden, separately for high-income and for low-income and middle-income countries.
A ratio of one indicates research proportional to burden; it is a reference point, not a target.
Single-country studies with a known publication-year income group were used for study-level
income comparisons; multi-country studies could contribute once to each named country's
country-level counts and to each relevant income stratum in disease-share analyses.

Country denominator sets were matched to the comparison: national burden analyses used the
204 national GBD 2023 locations, including locations with no studies; website country-density
analyses used the available country list and metric-specific non-missing denominators. Study
locations absent from the national burden export were excluded from that comparison, not
assigned zero burden. Annual reach analyses used each year's income classification and
excluded unclassified country-years; the broader country-universe sensitivity used Natural
Earth country entities without a population floor. Analyses extending through 2026 treated
that final year as partial.

As an exploratory extension of Schmallenbach et al. (Nature Medicine, 2025;
doi:10.1038/s41591-025-03923-0), we measured divergence between disease-burden shares (p) and
research shares (q) using Kullback–Leibler divergence, KLD(p||q) = sum p ln(p/q), with natural
logarithms. Research shares counted study–cause links; a study naming several causes could
contribute to each. DALYs and research were pooled within matching three-year windows from
2010–2012 to 2021–2023. The main comparison used 16 GBD level-2 causes matching the published
analysis. All studies were compared with global DALYs; studies of low- and middle-income
settings were compared with DALYs in those settings, with high-income settings supplementary.
Research setting used publication-year income classification; burden used the classification
in the burden year. Records without a reported country contributed to the global analysis
but not the setting-specific panels. Scores across panels therefore had different burden
references and were interpreted within panels.

To distinguish changes in research from changes in burden, we compared the observed trend with
two scenarios fixed at the 2010–2012 baseline: unchanged research shares with changing burden,
and unchanged burden shares with changing research. Their relative changes through 2017–2019
were descriptive scenarios, not causal effects or additive components. Uncertainty intervals
were based on 1,000 bootstrap resamples of studies within publication year, including the
baseline; DALY uncertainty was not propagated. Main 16-cause point estimates used no smoothing;
if a bootstrap draw left a cause without studies, that cause received 0.5 study. Sensitivities
used 20 causes including mental disorders and additional injury groups, and excluded causes
whose research or burden share was below 1% in any window, using a fixed retained cause set
within each panel. Empty causes in the sparse 20-cause point estimates also received 0.5 study.
Windows reaching 2020–2023 were shown separately as a COVID-affected extension. These analyses
were exploratory. Analyses were done in R (version 4.4.1) and Python.

## Deviations from the protocol

Screening and extraction were done by language models with human-labelled validation rather than
by two independent human reviewers, and no systematic full-text eligibility stage was conducted. Selected publisher pages,
full texts and registrations were consulted during subsequent review-classification and
publication-linkage checks; these did not constitute a full-text stage for the entire corpus. As a result, records
the screening model flagged as uncertain were assessed at extraction from the abstract instead
of at full text, and records without an abstract were excluded. Cost-minimisation analyses were
excluded as partial evaluations in all cases, and studies with non-clinical consequences were
excluded.

## Results at a glance

Of 1,154,050 records identified, 34,239 had no abstract and could not be screened. Of the
1,119,811 screened, 98,065 were advanced to data extraction (45,792 included and 52,273 flagged
as uncertain), of which 25,220 had no abstract to extract from. Of the 72,845 records extracted,
31,235 were excluded (13,573 partial evaluations, 11,975 not classifiable as full evaluations,
4,965 with non-clinical consequences, 675 duplicates identified by DOI or title/year,
44 additional redundant publications, two trial registrations without results and one
retracted paper), leaving **41,610 included records**. The reconciled review classification
identified 1,856 systematic and 796 non-systematic reviews (2,652 total); the other 38,958 records
were not identified as reviews. This classification does not independently establish that
every remaining record is a primary study. Of included records, 19,515 (46.9%) reported a
generic outcome measure (QALYs or DALYs). The study selection flow is shown in figure 1.

## Limitations

Screening sensitivity on the independent sample (0.86) was below the 0.95 target, so some
eligible evaluations are missing. Extraction over-includes by an estimated 9–12%, and studies
whose only consequence is service use or a diagnostic result could not all be removed. Of the 32,853 records with an interpretable publication-language code,
32,792 (99.8%) were coded as English; language was missing for 8,754 records and three had an
uninterpretable code. A country, region or global scope was recorded for 71.8% of records;
29,104 (69.9%) had a named country, and 87.6% had a GBD analysis group. Methodological quality
was not assessed through a systematic full-text audit; decision-analytic reporting indicators
record what abstracts reported, not necessarily what was done. The publication-family audit
resolved the flagged groups but does not establish that all linked publications in the corpus
have been found. Companion analyses and review updates remain included, so the analysis unit
is an included report rather than necessarily a unique underlying clinical study. Review
classifications remain limited by title/abstract reporting and selective follow-up checks.
There are 806 included records coded as posted content (1.9%); this is a metadata category
that commonly includes preprints and working papers, not a verified preprint count.
[Team decision required: retain standalone preprints and other non-article reports, exclude
them, or present a sensitivity analysis.] Screening and extraction validation describe their
original samples and were not repeated following this reconciliation. Topic assignments were
filtered to the final dataset without refitting the clustering model. The KLD results depend
on the selected cause set and sparse-category treatment and do not measure research quality,
funding amounts or causal responsiveness to burden.
