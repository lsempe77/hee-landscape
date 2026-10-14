# HEE analysis — methods and decisions

## Reconciliation addendum — 14 October 2026

This dated addendum supersedes the earlier headline counts below. Five masters preserve 72,845 rows, with 41,610 included after 47 additional exclusions: 44 redundant reports, two registrations without results and one retracted paper. The targeted publication audit covered 118 records in 57 title groups (61 potential excess reports) plus five separately included full articles. Retain the newest full research article; newer abstracts, translations and synopses do not replace it. Distinct evaluations, substantive companion analyses and review/HTA updates remain included. Bundled-payments and carpal-tunnel links were user-adjudicated; the Ginkgo translation is publisher-confirmed. Exact decisions, evidence, backups and verification are in exports/publication_reconciliation.

Current review coding identifies 1,856 systematic and 796 non-systematic reviews; 38,958 records are not identified as reviews. The old strict-title split of 39,951/1,706 is historical. The updated publication draft explains the title/abstract classification and selective published-methods follow-up. Review status does not establish absence/presence of an original economic evaluation, which has its own field.

Valganciclovir record 132018093 has no sample location in its title/abstract; Turkey was a publisher notice. Its country and derived geography/income fields and active long-form geography entries were cleared, with original values retained in the follow-up backup and report. Citation repairs and retraction flags are preserved.

Study-level time comparisons use publication-year World Bank groups; country views use July 2026 groups. Country denominators and setting-specific KLD benchmarks follow the documented local build scripts. The updated publication draft now describes exploratory KLD scenarios, 1,000 within-year bootstrap draws, rare-cause and 20-cause sensitivities, and the COVID extension. Topic clusters were filtered to eligible records, not refitted; 41,583 final records have coordinates.

HEE_METHODS_PUBLICATION-updated-Oct-14.md and the reconciled selection figure are updated. Protocol reference, search dates, World Bank access date and standalone preprint/non-article policy remain open. Other older open-work items below should not be interpreted as automatically required for this manuscript reconciliation.

**Purpose.** A single, citable record of *what the HEE analysis does and why* — every
consequential methodological decision, its rationale, and where it is encoded — so the paper's
Methods section and any reviewer can reconstruct and defend it. This document **consolidates and
points to** the detailed working documents; it does not replace them:

| detail lives in | for |
|---|---|
| `PIPELINE_FLOW.md` | the full record-level funnel and its reconciliation |
| `V2_DATASET_README.md` | the v2 dataset for the project team: files, flow, definitions, limitations |
| `../audit/PHASE_F_DECISIONS.md` | the Phase F rulings applied by the v2 rebuild |
| `DATA_QUALITY_AUDIT.md` | the 22 data-integrity findings, each with severity and v2 status |
| `CODEBOOK.md` | descriptives for every variable (regenerate with `R/98-codebook.R`) |
| `GAP_FRAMEWORK.md` | the paper's argument (the decision-usefulness cascade) |
| `VISUALIZATION_PLAN.md`, `COMPANION_CATALOGUE.md` | the figure catalogues, two registers |
| `datahsf/HEE_ARM_FINAL.md`, `hee/DEX/EXTRACTION_RUN_FINAL.md` | the screening and extraction stages |

Last reconciled 2026-09-07; **updated for the v2 (Phase F) dataset on 2026-10-07 and to its final
numbers on 2026-10-11** — the
current analysis population is **41,657 full economic evaluations** (was 38,199 in the v1 build
published 2026-09-08). Numbers in this file describe v2 unless marked *(v1, history)*. Where a
decision was made by the study team it is dated and tagged **(team)**; where it is an analyst
implementation choice it is tagged **(analyst)**. A plain-language overview of the v2 dataset for
the project team is in `V2_DATASET_README.md`.

---

## v2 rebuild (Phase F), 2026-10-07

The Phase F rebuild applied every pending data ruling in one pass and was promoted on
2026-10-07: `data/` now holds the v2 build; the v1 build published 2026-09-08 is preserved,
untouched, in `data_v1_published_20260908/`. Rulings are recorded in full in
`../audit/PHASE_F_DECISIONS.md` (team answers 2026-10-05 by S. Lee and B. Hutchinson, ruling-level
answers confirmed by L. Sempe; later rulings by L. Sempe). Every data change is applied by
`R/make_v2_build.py`, which writes versioned `*_v2` copies of the build scripts with asserted
substitutions (a drifted original fails loudly).

**Headline:** 41,657 eligible full economic evaluations (39,951 articles + 1,706 reviews by the
strict title flag). Per team ruling 2026-10-07 (L. Sempe), **the included studies are the
41,657**; the number of records that reached data extraction (72,845) is a pipeline stage and is
reported only in the selection flow (PRISMA), never as a headline count.

| ruling | decision and rationale | by, when | encoded in |
|---|---|---|---|
| **Unsure bucket (option D)** | All 52,273 records the screening model voted INCLUDE but flagged unsure advance to data extraction, whose eligibility check is the next assessment. Rationale: Appendix F2 sends "unclear at title and abstract" to the next stage; recall on records with an abstract rose 0.73 → 0.87 (blinded audit) and 0.76 → 0.93 (gt_700), precision paid at extraction. **Deviation:** the next stage reads the abstract, not the full text. Supersedes the 2026-09-16 hold-out decision | L. Sempe, 2026-10-06 | `PHASE_F_DECISIONS.md`; commit `a5a3355`; round-2 input `34a04fc`, extraction `fb31200` |
| **No-abstract records excluded** | Records with no abstract are not screenable at title/abstract and the project has no full-text stage: 34,239 never screened (own PRISMA line) and 25,220 includes with no abstract (24,573 unsure + 647 confident) excluded before extraction | L. Sempe, 2026-10-06 | `DEX/build_extraction_input_round2.py`; `R/prisma_v2.R` |
| **F-a: "Consequences not clinical" excluded** | The codebook's full evaluation requires clinical consequences (`hee_extraction_v6.8.yaml:442-445, 485-486`), so a CnC study fails the map's own definition. Supersedes ruling (a) of 2026-09-04 (kept and flagged). 4,965 excluded in v2 | team, 2026-10-05 | `00-build-analysis-data_v2.R` via `make_v2_build.py` (`c825506`) |
| **F-b: repaired screening basis** | Rebuild on the repaired 45,792 confident includes (the 2026-09-16 repair restored 1,816 mandatory second-opinion union flips); the 204 net new includes were extracted in round 2 | L. Sempe, 2026-10-05 | round-2 input `34a04fc` |
| **F-c: current inputs absorbed** | Use the corrected crosswalk (2026-09-15) and GBD 2023 re-pull (2026-09-17) rather than the inputs frozen in the v1 master | L. Sempe, 2026-10-05 | `make_v2_build.py` |
| **F-d: v6.9 re-extraction not run** | v6.9 (design_facts only) removed 1–2 over-includes on the 160-record gold against a same-prompt noise of 17 cells, so the ~$170 corpus re-run failed its own gate. v6.8 labels kept; measured over-inclusion (~9–12%) disclosed | L. Sempe, 2026-10-05 | `DEX/v69_validation.json` |
| **Q1: no consequence → unclear** | A would-be full evaluation whose consequences cell names nothing (missing, empty, "none", "not reported") is "Excluded: unclear at extraction". Applied by rule: moved exactly 1,431 of the old eligible set (the count the ruling quoted) and 2,020 of the v2 set at the time (43,681 → 41,661, before the final Q2 keep rule took it to 41,657). The **service-use-only** and **diagnostic-only** branches were **not** applied by rule: a regex on the free text matched mostly clinical outcomes ("survival to discharge", "stage at diagnosis"); disclosed as a limitation, as part of the measured over-inclusion | team, 2026-10-05 (apply by rule); applied 2026-10-07 | `make_v2_build.py`; commit `39a7fc5` |
| **Q2: title de-duplication** | After DOI de-duplication, records are also de-duplicated on normalised title + year (different years stay). 135 further copies flagged, **73** of them otherwise eligible (duplicates in total: 602 DOI + 73 title = 675). Keep rule **as ruled** (aligned 2026-10-07): the copy with a DOI, else the journal article (OpenAlex `publication_type`), else the longer abstract; lowest record ID breaks remaining ties. The first v2 build used eligible-copy-first; aligning it moved eligible 41,661 → 41,657 | team (option A), 2026-10-05; aligned 2026-10-07 | `make_v2_build.py`; commit `7b50722` |
| **Q3: income and geography** | (i) **Taiwan = High income**, a recorded override because the World Bank API has no TWN entry (344 eligible single-country studies); (ii) a reason code (`income_reason`) on every row: classified / multi-country / region or global only / country not classified / no place stated; (iii) multi-country studies count each named country (3ie EGM convention), but a study naming **more than 15 countries** is "multi-country" and leaves the country map (5 studies) | team 2026-10-05; Taiwan L. Sempe 2026-10-05 | `00-build-analysis-data_v2.R`, `03-build-master_v2.R` (via `make_v2_build.py`); `R/country-universe.R` |
| **Q4: crosswalk extension (option A)** | MeSH C11 + C09 → Sense organ; C07, C15 and non-kidney C12 → Other NCD; kidney-named C12 headings (kidney, renal, nephr-, glomerul-, uraemia, proteinuria, albuminuria) → code `C12.KID` → Metabolic & nutritional (GBD "Diabetes and kidney diseases" covers CKD of any cause). C23, C22, C24, C25 stay unmapped. **14 disease groups** (was 12). No model calls | team (B) 2026-10-05; option A L. Sempe 2026-10-06 | `make_v2_build.py`, `data/crosswalk_mesh_gbd.csv`, `R/lookup-mesh_v2.R` (= `R/lookup-mesh.R` since promotion); commit `f12bb34` |
| **Crosswalk fix (i): maternal = pregnancy branch only** | MeSH C12.050 is "Female Urogenital Diseases and Pregnancy Complications"; only C12.050.703 is pregnancy. The 2026-09-15 remap took all of C12.050, misclassing ~2,400 studies of female urogenital disease as maternal. The published v1 statement that maternal health "no longer appears as a gap" was this artefact; corrected: maternal research is 0.7× its burden share in LMIC (a gap) and 5.0× in HIC | analyst, 2026-10-07 | commit `19c44aa` |
| **Crosswalk fix (ii): residual branches per heading** | C07, C15 and non-pregnancy C12 are decided per MeSH heading: a heading counts only if it is in no mapped disease branch, so HIV/STI, cervical-cancer and pregnancy headings are no longer double-counted as Other NCD (3,719 → 849 eligible studies) | analyst, 2026-10-07 | commit `0e1cd8e` (`01-build-metadata-maps_v2.py`) |
| **Outcome-family rule extension** | "Other clinical" held 24.6% of eligible outcome mentions (build self-check threshold 15%). Extended by rules only (no model classification), appended before the catch-all so nothing previously classified moves; new family **"Reproductive & birth outcomes"**. Other clinical → 13.7% | L. Sempe, 2026-10-07 | `R/outcome_rules_ext_v2.py`; commit `b05fa88` |
| **Generic-measure share on the right base** | 46.9% of the 41,657 report a QALY or DALY. The v1 "57.2% are full evaluations" became a pipeline yield in v2 (41,657 of the records extracted, inflated by the unsure bucket) and is reported only at selection | analyst, 2026-10-07 | `make_paper_v2.py`; commit `e8ef369` |
| **Paper v2 recommendations** | Other NCD left out of the research-vs-burden figure (residual on both sides); both screening sensitivities reported; stale 2026-09-04 callout cut; Limitations section added | L. Sempe accepted, 2026-10-07 | `make_paper_v2.py`; commit `d20a48c` |
| **Screening prompt v0.5 validated, corpus not re-screened** | v0.5 realigns v0.3 with Appendix F2 (narrative reviews that synthesise, before-after comparators, fiscal examples, second-hand CE claims, excluded publication types) plus the 2026-10-06 rulings on clinical practice guidelines and hospital charges. Fresh runs of both prompts on 1,498 labelled records: no net recall change (+2 / −3 studies), so the ~$700 re-screen was dropped | L. Sempe, 2026-10-06 | `audit/v05_validation.json`; commit `d04c602` |
| **Topic model re-run on v2** | Same Appendix K method on the 41,661 documents eligible on 2026-10-07 (§6.8): 73 clusters, 13.7% noise; 5-seed stability check passes. Deliberately **not** re-run after the final Q2 keep rule, so cluster numbers and the theme worksheet stay stable; 41,630 of the 41,657 included studies have coordinates. A draft 15-theme grouping is **pending team sign-off** and not wired into figures | analyst, 2026-10-07 | `R/05-topic-model_v2.py`, `R/05b-topic-stability_v2.py`, `R/make_themes_v2.py`; commit `566b637` |
| **Q6: evaluation-type confidence** | New column `econ_eval_type_conf`: the extractor's own confidence in `econ_eval_type` (the production `--no-reconcile` path had set a constant "high"). Included studies: high 26,819 (64.4%), moderate 12,797 (30.7%), low 2,041 (4.9%); supports a robustness check dropping low-confidence types | team (A), 2026-10-05; built 2026-10-07 | `make_v2_build.py` (01 v2 writes `data/econ_eval_type_confidence.csv`); commit `7b50722` |
| **Q7: trial, randomisation not stated** | New `design_basis` level, never folded into RCT: a design coded "Other" whose extraction quotes or notes name a trial but never randomisation. 1,277 extracted records flagged (`data/design_trial_no_rand.csv`); 1,057 included (2.5%); "Other" falls to 794 (1.9%) | team (A), 2026-10-05; built 2026-10-07 | `make_v2_build.py`; commit `7b50722` |
| **Q5: unspecified care setting as its own bar** | No current figure shows care setting, so there is nothing to build; the rule applies if such a figure is added | team (A), 2026-10-05 | — |
| **Intervention class completed** | The 7,137 newly eligible studies (+3 for the final keep rule) were labelled with the same frozen prompt and model (`deepseek/deepseek-v4.1-flash`, reasoning off), about $4. All 41,657 included studies are labelled (1 parse failure); the three intervention figures are restored on the /v2/ preview. A claims check corrected one caption: "care models lag" was false even in v1, now "financing and care models lag" | analyst, 2026-10-07/08 | `R/make_intervention_records_v2.py` → `reviews/intervention-extraction-records.csv` (v1 kept as `_v1_20260908.csv`); commits `7b50722`, `6aa112a` |
| **Included studies = 41,657** | The headline count everywhere is the analysis population; 72,845 extracted appears only in the selection flow | L. Sempe, 2026-10-07 | this file, `V2_DATASET_README.md`, paper and web app |

**Not applied, or dropped:** Q8 (no blanket contradiction rule) needs nothing. Q9
(re-extract ~920 cells with a failed supporting quote) was dropped on 2026-10-06: it moves no
figure. The human gate-100 coding and a second reader on the eligibility check were dropped in
favour of disclosing the measured over-inclusion.

*(History: the first v2 build of 2026-10-07 kept the eligible copy first; on 2026-10-07 the keep
rule was aligned with the Q2 ruling, see the table.)*

**Screening accuracy reported with v2.** 0.959 on the human-labelled development reference
(93/97; Wilson 95% CI 0.899–0.984); **0.86 on the independent blinded 1,000-record audit**
(32 of the 37 eligible studies with an abstract, counting records sent forward as unsure; 95% CI
0.72–0.94), below the 0.95 protocol target.

---

## 1. Scope and unit of analysis

The HEE arm maps **full economic evaluations** of health-care delivery published from 1 January
2010 onward (protocol Appendix F, code list F2): studies that compare two or more ways of
delivering care on **both costs and consequences**. The unit of analysis is the **study**
(one row per extracted record). The analysis is descriptive and, where it compares research
against disease burden, **ecological** — it characterises the evidence base, not causal effects.

---

## 2. Data pipeline and provenance

Every analysis number traces to the corpus through this funnel (full version and reconciliation
arithmetic in `PIPELINE_FLOW.md`):

| stage (v2, 2026-10-07) | records | source |
|---|---:|---|
| Identified (ML-classifier candidate pool) | 1,154,050 | `HEE_ARM_FINAL.md` |
| Unscreenable (no abstract in any source) | −34,239 | by rule, never seen by a model |
| Screened at title/abstract | 1,119,811 | |
| Excluded at screening | −1,021,746 | topic / design / year (repaired basis) |
| **Advanced to data extraction** | 98,065 | 45,792 confident includes + 52,273 unsure (option D, §v2) |
| Includes with no abstract to extract from | −25,220 | no-abstract ruling 2026-10-06 |
| Data extracted (round 1 44,941 + round 2 27,904) | 72,845 | `EXTRACTION_RUN_FINAL.md`, `PHASE_F_DECISIONS.md` step 4 |
| Excluded — partial evaluation | −13,573 | §3 |
| Excluded — unclear at extraction (incl. Q1) | −11,975 | §3 |
| Excluded — consequences not clinical | −4,965 | §3 (F-a) |
| Excluded — duplicate DOI or title | −675 | §3 (602 DOI + 73 title) |
| **Analysis population** | **41,657** | `hee-paper_v2.qmd` (Figure 1, `R/prisma_v2.R`) |
| *of which reviews synthesising published evaluations* | *1,706* | strict title flag; retained by extraction design (§3) |

*(v1, history: 1,023,562 excluded, 50,661 unsure held out, 45,588 confident includes, 647 no
abstract, 44,941 extracted, −3,388 partial, −2,819 unclear, −535 duplicate DOI = 38,199, of which
1,602 reviews.)*

**Screening** used GLM-5.2 self-hosted (4-bit W4AFP8, 4×H200), k=3, temperature 0.5, prompt
v0.3, no critic, with a DeepSeek-V4-Pro **union second opinion** on split votes; measured
sensitivity **0.959** against the current corrected human reference vintage (93/97; Wilson 95% CI
0.899–0.984; the pre-registered 2026-08-19 vintage measured 0.962, 100/104 — full evaluation in
`reviews/unsure-sample-results.md` §10; the 0.95 floor is supported by the point estimate but not
demonstrated at 95% confidence). On the **independent blinded 1,000-record audit**, never used for
development, sensitivity is **0.86** (32 of 37 eligible studies with an abstract, unsure records
counted in; 95% CI 0.72–0.94), below the 0.95 target. **Extraction** used the validated framework
(v6.8), GLM-5.2 pinned to a single OpenRouter endpoint (provider routing, not the prompt,
governs JSON reliability — see `EXTRACTION_RUN_FINAL.md`). The **metadata harvest** (CrossRef +
OpenAlex + PubMed + NLM MeSH; DOIs, authors, affiliations, funders, journals, MeSH, open-access)
was run for the extracted set and completed for 2010–2019 on 2026-09-04, with a **DOI-supplement
harvest** (2026-09-07) and a **round-2 harvest** for the v2 extractions
(`projects/datahsf/chain_harvest_round2.sh`); in v2, 87% of eligible studies have a journal and an
OpenAlex topic, 55% a MeSH disease code. Extraction ran in two rounds with the same framework
(v6.8) and endpoint: round 1 on the 44,941 confident includes with an abstract, round 2 on 27,904
records (27,700 unsure with an abstract + 204 repair includes; 4 records refused by the provider
with HTTP 403 are not extractable).

The analysis project holds only the extracted rows (72,845 in v2); the upstream counts enter the
PRISMA as sourced constants cited on the figure.

---

## 3. Eligibility — the analysis population (41,657)

Encoded in `R/00-build-analysis-data_v2.R` (generated by `R/make_v2_build.py`; `eligibility` /
`is_eligible`), which prints the breakdown. A record is eligible only if, in this order, it is not
unclear (status or type missing, or status "Unclear"), its type is not partial or None, its
status is not "Consequences not clinical" or another non-full status, its consequences cell names
a consequence (Q1), and it is not a duplicate copy (DOI, then title + year).

- **Partial evaluations are out of scope** *(team, 2026-09-04)*. The map is a map of *full*
  economic evaluations, so cost-minimisation, budget-impact, cost-of-illness, and any study
  comparing only one arm or only costs are **excluded**, not reported as a sub-type.
- **"Consequences not clinical" studies are EXCLUDED** *(team, 2026-10-05, superseding ruling
  (a) of 2026-09-04)*. The codebook defines a full evaluation as requiring CLINICAL
  consequences (`hee_extraction_v6.8.yaml:442-445, 485-486`), so a CnC study fails the map's
  own definition. **Applied in v2: 4,965 excluded.** *(v1, history: the frozen 2026-09-08 master
  kept them, flagged `consequence_clinical = FALSE`, 2,158 of the 38,199; the column is now
  vestigial, TRUE for every eligible study.)* The gold sample found 12 of 113 gate rows where
  production said "Full evaluation" and the adjudicated human answer excludes — the measured
  over-inclusion disclosed in §11. Ruling record: `audit/phase_d_adjudications.json`; evidence:
  `audit/phase_d_human_gold_results.md`.
- **No consequence named → unclear (Q1)** *(team, 2026-10-05; applied 2026-10-07)*. See the v2
  section: 2,020 v2 studies moved to "unclear at extraction"; the service-use-only and
  diagnostic-only branches are not applied by rule.
- **A partial/none `econ_eval_type` disqualifies regardless of `full_eval_status`** *(team,
  2026-09-08)*. Budget-impact, cost-minimisation, cost-of-illness and "no evaluation" are
  ineligible for a map of *full* evaluations even when the status field reads "Consequences not
  clinical" — so the type check runs before the rescue above. *(v1, history: this moved **117**
  such studies from eligible to excluded-partial, population 38,316 → 38,199.)* No eligible study
  carries one of those types (checked in v2 by `R/99-data-quality-audit.R` section J).
- **"Unclear at extraction" is excluded** *(team)*. Inability to confirm a full evaluation fails
  the bar (11,975 in v2, incl. Q1). Note the two different "unsure" stages: unsure at
  title/abstract now ADVANCES to extraction (option D, 2026-10-06); unclear at extraction is
  EXCLUDED, because extraction is the last assessment the project performs.
- **Conservative disqualification** *(analyst)*: `full_eval_status` and `econ_eval_type` come
  from the same `design_facts` call in v6.8 (corrected 2026-10-01; this previously said
  different model calls); a study is excluded if **either** field disqualifies it.
- **Duplicate DOIs removed** *(analyst, audit finding 11)*. The same paper appears under more
  than one record ID (Appendix F code 6 excludes exact duplicates). Keep rule within a DOI group:
  prefer an eligible copy, then the lowest record ID for determinism. **v2 adds a second pass on
  normalised title + year (Q2, team 2026-10-05)**, which reaches records with no DOI. In v2, 961
  copies are flagged in total and 675 otherwise-eligible copies excluded (602 DOI + 73 title).
  5,272 eligible records (12.7%) still have no DOI, so the duplicate count remains a floor.
  *(v1, history: 524 DOI groups, 1,084 records, 535 eligible copies excluded.)*
- **Reviews of published evaluations are retained, and disclosed** *(analyst, 2026-09-15;
  reviewer request, `reviews/brian-investigations.md` item 1)*. Extraction framework v6.8 codes a
  systematic, scoping or narrative review of published economic evaluations as a synthesis
  ("Literature/registry synthesis") and extracts it in full, so reviews sit **inside** the
  analysis population by design, not by accident. A strict title flag (the title names a
  systematic review, meta-analysis, literature review, scoping review or umbrella review)
  identifies **1,706** of the 41,657 (4.1%), so the population is 39,951 articles + 1,706
  reviews; 72% of the reviews name no single country, so the country-level panels draw mostly on
  articles. Figure 1 (PRISMA) draws the analysis population as these two components and the app
  funnel carries the same disclosure sub-line. This is a disclosure, not an exclusion.
  *(v1, history: 1,602 of 38,199, 65% naming no single country.)*

> **Population items, resolved by the v2 rebuild (2026-10-07).** *(History: on 2026-10-05 the
> unsure-at-TA records were held out by the 2026-09-16 decision, and the CnC exclusion and the
> repaired screening basis were deferred to one rebuild, leaving the published population at
> 38,199.)* All three are now applied: the unsure records advanced to extraction (option D), CnC
> is excluded, and the build runs on the repaired basis. Population: 41,657.

---

## 4. Variables

Six fields are model-written at extraction (`econ_eval_type`, `full_eval_status`,
`design_basis`, `model_based`, `hee.geo`, `hee.consequences`); everything else is derived from
them or joined from an external source. Full descriptives for all variables are in `CODEBOOK.md`.

Four harmonisation disciplines, each a way to publish a wrong number if ignored (encoded in
`00-build-analysis-data_v2.R`):

1. **`None` the string is a finding, not missing.** `econ_eval_type == "None"` means the
   extractor determined no economic evaluation was performed; `NA` means it could not tell.
   Collapsing them would move 12,517 extracted records (v2; 3,128 in v1) from a result into
   missingness.
2. **Geography is multi-valued.** 1,207 eligible studies name more than one country (or more than
   15, which count as "multi-country" off the map), so a country-level count exceeds the study
   count. Every figure declares whether its denominator is *studies* or *study–country pairs*,
   and every income figure shows `income_reason` (v2, Q3) for studies without an income group.
3. **Outcomes are free text** (47,924 distinct strings across the 116,458 outcome mentions of
   eligible studies). Mapped to **15 outcome families** by an **ordered, first-match-wins** regex
   list (§7); the order is a modelling choice (QALY tested before "quality of life",
   progression-free survival before survival). v2 appends the rule extension of 2026-10-07
   (`R/outcome_rules_ext_v2.py`) before the catch-all and adds **"Reproductive & birth
   outcomes"**; the unmatched ("Other clinical") share fell from 24.6% to **13.7%** of eligible
   mentions, under the 15% self-check threshold *(v1, history: 23.3% with 14 families)*.
4. **Cost-utility vs cost-effectiveness follows the outcome, applied consistently** *(analyst,
   2026-09-08)*. The extraction rule (`hee_extraction_v3.yaml`) is that a preference-weighted
   outcome — QALY, DALY, utility — makes a study **cost-utility**, not cost-effectiveness ("the
   QALY is the discriminator; if two apply, cost-utility"). The model applied this inconsistently,
   so `00-build-analysis-data_v2.R` reclassifies any `econ_eval_type == "Cost-effectiveness"` study
   that reports a QALY or DALY outcome to **Cost-utility** (560 extracted records moved in v2; of
   the 41,657 eligible, cost-utility is 47.7%, cost-effectiveness 26.2%, cost-consequence 22.7%,
   cost-benefit 3.4%; *v1, history: 488 moved, CUA 50.4%, CEA 27.5% of 38,199*). Both are eligible
   full evaluations, so this step does not change the analysis population, `eval_family` or
   `is_full_eval` — it only moves studies between two eligible types.

---

## 5. External reference data — sources and access

No bibliometric or denominator variable uses a bundled snapshot; each is fetched from a dated
source. This is itself a correction (audit findings 1–2: Natural Earth's income and population
snapshots were wrong for 30% and understated population by a median 7.3%, and changed a
published sub-claim).

| reference | source | script / file | notes |
|---|---|---|---|
| **Income group** (4- and 2-level) | World Bank API classification | `R/fetch-wb-income.py` → `data/wb_income_classification.csv` (access date in header) | Taiwan has no WB entry → **High income by recorded override** (Q3, L. Sempe 2026-10-05; footnoted); before v2 it was `NA` |
| **Population** | World Bank `SP.POP.TOTL` | `R/fetch-wb-population.py` → `data/wb_population.csv` (access date in header) | denominator for per-capita density |
| **Disease burden (DALYs)** | IHME **GBD 2023** (country totals + 22 Level-2 causes) | `data/gbd2023_dalys_country_total.csv`, `..._cause_l2.csv`; `R/lookup-gbd.R` | Number, All ages, Both sexes, 2023; 4 corpus countries have no national GBD row and are dropped, never zero-filled |
| **Health spending** | IHME **Health Spending 1995–2022** | `data/ihme_health_spending_1995_2022.csv`; `R/lookup-spending.R` | total health expenditure per capita (PPP), 2022; country level only; national THE = per-capita × World Bank 2023 population |
| **Disease / intervention / arrangement** | NLM **MeSH** C-/E-/N-trees (harvest) | `mesh_disease_anytopic.csv`, `mesh_intervention_anytopic.csv` | **any-topic**, see §6 |
| **Research topic** | **OpenAlex** primary-topic taxonomy (harvest) | `openalex_cluster_by_record.csv` | a *pre-assigned* classification (distinct from the emergent topic model, §6) |
| **Author affiliations** | OpenAlex (harvest) | `affiliation_by_record.csv` | used for authorship and the (excluded) geography proxy |

> **Pre-submission:** confirm the World Bank access date is current before the paper is
> submitted (`fetch-wb-*.py` headers).

---

## 6. Key analytical decisions

The consequential choices that shape figures and headline numbers, each with its rationale and
where it is enforced.

**6.1 Geography is extracted-only; the affiliation proxy is excluded from income figures**
*(analyst, 2026-09-06; audit finding 17; the figures in this paragraph are the v1 measurement —
the v2 build prints the same numbers as typed constants, so they have not been re-measured on
v2).* Geography is missing for ~33% of v1 studies (v2: 28.2% of eligible studies name no place). A proxy —
placing a study by its single author-affiliation country — is **accurate** (94.2% agreement, no
income bias *in agreement*) but its **availability is income-biased**: 83.8% of the studies it
can place are high-income (vs 71.7% of extracted), because rich countries produce many
single-affiliation domestic evaluations that never name their setting. Merged, it would inflate
the headline burden gap from **17.8× to 25.8×** — a measurement artefact. **Decision:** `geo_long`
stays extracted-only (every income figure unchanged); the proxy is saved separately
(`hee_geo_affiliation_proxy.rds`) with a `geo_source` flag for opt-in uses where the skew is
harmless. Authorship figures additionally filter `geo_source == "extracted"` — placing a study
by its affiliation and then asking whether it has a local author is circular. *General lesson: a
proxy can be accurate where it applies and still bias a comparison if whether it applies
correlates with the axis being compared.*

**6.2 Income at study level is single-country only; "Mixed" is its own class** *(analyst).* A
study naming countries in more than one income group is coded `Mixed`, not forced into one.
Income comparisons use single-country studies; the 4-level split is used for any within-LMIC
question (2-level cannot separate China from Malawi).

**6.3 MeSH uses any-topic headings, never major-topic** *(analyst, 2026-09-05; audit finding
16).* Major-topic (`*`) marking is a real NLM indexing property that jumps from ~2–4% (2010–19)
to ~14–49% (2020–26) at the harvest boundary. Building the epidemiological-transition series on
major-topic would manufacture a spurious disease-coding explosion at 2020. Any-topic C-tree
coverage is smooth across all 17 years and is used throughout; the denominator is declared.

**6.4 Disease burden is a reference point, not a target** *(analyst wording, 2026-09-07).* The
burden figures divide a disease's (or country's) **share of research** by its **share of
disease burden**; proportionality-to-burden is one reference against which to read the evidence,
**not** a normative target — research allocation also reflects tractability, intervention cost
and the stock of existing evidence. Figures describe the disproportion in neutral terms ("a
smaller share of research than of burden"), not as a verdict ("over-/under-studied").

**6.5 MeSH↔GBD crosswalk** *(analyst; revised 2026-09-15, reviewer request — `reviews/crosswalk-change-note.md`; extended in v2, 2026-10-06/07).* **Fourteen** disease groups map between the MeSH
C-tree and GBD Level-2 causes (`data/crosswalk_mesh_gbd.csv`; single source `R/lookup-mesh.R`, which since the v2 promotion carries the content of `R/lookup-mesh_v2.R`; the v1 file is kept as `R/lookup-mesh_v1_20260908.R`). Eligible studies per group (multi-valued; 21,648 of 41,661 carry at least one): Infectious 6,441; Neoplasms 5,213; Cardiovascular 3,767; Metabolic & nutritional 3,168; Digestive 3,058; Chronic respiratory 2,466; Neurological 2,347; Skin 1,618; Musculoskeletal 1,349; Mental & substance use 1,318; Maternal & neonatal 1,174; Injuries 1,149; Other NCD 849; Sense organ 722.

How it got here: (1) 2026-09-15 — Neurological (MeSH **C10**) was split from Mental & substance use (MeSH **F03**, newly emitted), and a maternal code was added for MeSH-2026's move of Pregnancy Complications from the retired C13 into C12.050. (2) v2, Q4 option A (2026-10-06) — C11 + C09 → Sense organ; C07, C15 and non-kidney C12 → Other NCD; kidney-named C12 headings → `C12.KID` → Metabolic & nutritional. (3) v2 fixes (2026-10-07) — the maternal code is emitted only for the **pregnancy branch C12.050.703** (the 2026-09-15 remap took all of C12.050, which includes female urogenital disease, misclassing ~2,400 studies; the v1 claim that maternal health "no longer appears as a gap" was that artefact, and maternal research is in fact 0.7× its burden share in LMIC, a gap, and 5.0× in HIC); and the residual branches C07/C15/C12 are decided **per MeSH heading**, so a heading counts only if it sits in no mapped disease branch (Other NCD 3,719 → 849). MeSH signs and symptoms (C23), animal (C22), occupational (C24) and chemically induced (C25) disorders have no clean GBD counterpart and are excluded from
**both** sides of any research-vs-burden comparison; Other NCD is shown in the disease figures but
left out of the research-vs-burden ratio figure, because it is a residual group on both sides. The transition figure additionally groups
GBD (exact) and MeSH (approximate — C18 mixes nutritional and metabolic) into the three classic
epidemiological-transition classes; the MeSH approximation is disclosed.

**6.6 Intervention class and care setting are model-derived (tier-2)** *(analyst, 2026-09-17;
`reviews/intervention-extraction.md`).* Two variables the harvest cannot supply — the type of
intervention a study evaluates (eight named classes plus a residual `other`, with an optional
secondary class) and its care setting — were extracted for every one of the v1 38,199 eligible
evaluations; the studies newly eligible in v2 were labelled with the same frozen prompt and
model on 2026-10-07/08, so all 41,657 included studies now carry a label (1 parse failure) by a single-pass language model (`deepseek/deepseek-v4.1-flash` via OpenRouter,
temperature 0, reasoning disabled, frozen prompt sha256 `5b847afc…`; one call per record, 0 parse
failures). With no human gold standard, reliability is a three-way consistency check rather than
accuracy: agreement with a deterministic keyword lexicon (82.7% of full-pass records), purity
against the frozen emergent-topic clusters (the expected class dominant or co-dominant in 60 of
68, 88.2%), and 96.0% primary-class / 76.5% care-setting agreement with a different model lineage
on a 149-record subsample. The taxonomy is corroborated by independent bibliographic structure
where the lexicon is blind (MeSH E07 → devices ×6.3, E04 → surgery ×3.5; OpenAlex Biomedical
Engineering → devices ×7.45, Economics → financing ×5.49). Limits: no human validation exists, the
lexicon is a lower bound flagging many studies per record (it reports financing for 29.6% against
the extraction's 2.7%, the most derivation-sensitive class), and one forced primary class
understates genuinely dual-intervention studies — so the field is declared tier-2 and the gallery
figures state that lexical rules were not used.

**6.7 Decision-analytic signals are read from the abstract, and report ≠ conduct** *(analyst,
2026-09-07).* The reference-case audit the protocol envisages needs the article PDFs, which are
not retrieved. As an honest substitute, four decision-analytic elements (an incremental ratio,
a cost-effectiveness threshold, an uncertainty analysis, an analytic perspective) are detected
by conservative keyword matching on the **abstract text** (from the screening corpus, 100% of
eligible; `R/04-emit-abstract-signals.py`). Every figure using these states plainly that it
measures **what the abstract reports, not what the study did** — "not reported" is not
"not done".

**6.8 Emergent topic model** *(analyst, protocol Appendix K).* In addition to the OpenAlex
pre-assigned topic taxonomy, an emergent thematic map is produced faithfully to Appendix K:
sentence embeddings of title+abstract → UMAP to two dimensions → HDBSCAN clustering in that
reduced space → distinctive-term (c-TF-IDF) cluster labels (`R/05-topic-model.py`, local, no
API). UMAP positions are for visualisation, not metric distance; HDBSCAN leaves some documents
unclustered ("noise"). Stated on the figure.

**v2 run (2026-10-07):** all-MiniLM-L6-v2 embeddings of the 41,661 studies eligible on that date (deliberately not re-run for the final 41,657, so cluster numbers stay stable; 27 included studies have no coordinates), UMAP to 2D
(seed 42), HDBSCAN minimum cluster size 200 → **73 clusters, 13.7% noise** (`R/05-topic-model_v2.py`
→ `data/topic_map.csv`, `data/topic_labels.csv`). **Seed stability** (`R/05b-topic-stability_v2.py`
→ `data/topic_stability.json`; seeds 1, 7, 13, 101, 2026): 71–79 clusters per run; mean adjusted
Rand index 0.89 among documents clustered in both runs (0.56 counting noise); **71 of 73 clusters
recovered (Jaccard ≥ 0.5) in every re-run**, 54 at ≥ 0.7. The v1 15-theme grouping
(`R/lookup-themes.R`) is invalid after any re-run because HDBSCAN renumbers clusters; a **draft**
15-theme grouping of the 73 v2 clusters (`R/make_themes_v2.py` → `reviews/theme-curation-worksheet_v2.csv`,
`R/lookup-themes_v2.R`) is **pending team sign-off** and is not wired into any figure.

The model reads **title and abstract only** — deliberately. It is the *unsupervised* complement
to the two controlled-vocabulary lenses the map also carries: expert-assigned **MeSH** subject
headings (the disease figures, §6) and the **OpenAlex** pre-assigned topic taxonomy (the topic
landscape). Keywords are not folded into the embedding, for three reasons: genuine author
keywords are essentially absent from this corpus (CrossRef keyword coverage ≈ 0%); the available
OpenAlex *concept* tags are noisy (e.g. "Value (mathematics)", "Medicine"); and mixing a
half-covered controlled vocabulary into the emergent map would collapse it into the supervised
views it exists to complement. The three lenses are reported separately by design.

**6.9 Analysis master table** *(analyst).* `R/03-build-master.R` assembles one wide, one-row-per-
study `data/hee_analysis_master.csv` (all attributes pre-joined) that every figure reads, so
joins are not re-derived per figure; the two grains that cannot fold in (study×country,
study×outcome) stay as long tables, also emitted as CSV.

---

## 7. Statistical and derivation methods

- **Outcome families** — ordered regex, first match wins, 14 families (`00-build-analysis-data.R`).
- **Density** — studies per unit population (World Bank), per unit DALY (GBD) or per unit
  health expenditure (IHME); reported as group medians with the within- vs between-group
  spread stated. The spending figure is read against the absolute evidence base: low-income
  countries register more studies per dollar because their budgets are small, while their
  absolute study count remains far below the high-income one.
- **Associations** — where the paper models predictors (e.g. use of a comparable metric, local
  authorship), **logistic regression** reported as adjusted **odds ratios with 95% CIs**,
  described as associations, not causes (observational/ecological).
- **Proportions** — figures reaching the paper should carry uncertainty intervals (Wilson for
  proportions); this is a pre-submission checklist item.
- **Concentration** — within-income evidence inequality is summarised with a Lorenz curve and a
  Gini coefficient, weighted by disease burden so it is an equity statement, not a country-size
  artefact.

---

## 8. Data quality and integrity

The governing discipline: **reconcile counts against the corpus total as the last step of any
stage.** Three silent screening gaps (10,313 screened-not-retrieved, 19,865 double-counted, 147
never screened) were found this way, none by an error message (`HEE_ARM_FINAL.md`).

Twenty-two findings (five added in v2) are logged with severity and status in `DATA_QUALITY_AUDIT.md`; reproduce
with `R/99-data-quality-audit.R`. The load-bearing ones for the analysis:

- **Income/population snapshots were wrong** (findings 1–2) — fixed by fetching from the World
  Bank API; one published sub-claim ("low- and lower-middle-income indistinguishable") was an
  artefact and was withdrawn.
- **Extraction is not reproducible run-to-run** (finding 8) — two temperature-0 runs of a
  byte-identical framework differ on 36 of 100 `consequences` cells. Any version comparison must
  clear an aggregate several times that floor; which records flipped means nothing.
- **Fields contradict each other for 11.8% of extracted records in v2** (8.3% in v1; the rise
  comes from the round-2 unsure records) (finding 4): `full_eval_status` and `econ_eval_type`
  come from the same `design_facts` call in v6.8, so their disagreement is within-call
  inconsistency, a disclosed floor on extraction noise, handled by conservative disqualification
  (§3): no contradictory record is eligible. (Corrected 2026-10-01; this previously said different
  model calls.)
- **The eligibility check over-includes by about 9–12%** (finding 20): on the human-coded gold
  sample, 12 of 113 gate rows and 4 of 43 in the random band (9.3%, CI 3.7–21.6) accepted as full
  evaluations were not. Disclosed, not corrected (the v6.9 fix failed its gate).
- **Two crosswalk defects found and fixed in v2** (findings 18–19; §6.5).
- **Publication year disagrees with CrossRef for 14.1%** (finding 12, mostly online-first vs
  issue date) — every time series is shifted a year for ~1 study in 7; the date choice is
  currently implicit and should be stated.

---

## 9. Visualisation

Two registers, tagged per figure:

- **Lancet core** (`R/theme_hee.R`) — journal figures: descriptive titles, greyscale-safe,
  uncertainty shown; the deliverable is `hee-paper_v2.qmd` (generated from `hee-paper.qmd` by
  `R/make_paper_v2.py`; v1 was `hee-paper.qmd`).
- **Companion** (`R/theme_companion.R`) — the public-facing / poster set: editorial typography
  (Franklin Gothic, off-white ground), bolder colour, annotation; catalogued in
  `COMPANION_CATALOGUE.md`.

All figures render through `ragg::agg_png` (system fonts). **Wording is measured throughout**
(2026-09-07 pass): the figures describe a *disproportion between research share and burden
share*, never a verdict; value-laden framing ("over-studied", "neglected", "injustice") was
removed from every companion figure and the paper's Figure 8. Figures that would mislead were
**dropped rather than shipped**: intervention treemap (the MeSH E-tree methods tag swamps it),
language (99.8% English — a one-line limitation, not a figure).

---

## 10. Software and reproducibility

- **R 4.4.1**; key packages: `dplyr`, `tidyr`, `ggplot2`, `sf`, `rnaturalearth`, `countrycode`,
  `ggtext`, `ggrepel`, `circlize`, `ragg`.
- **Python** (analysis helpers): `pandas`/`csv`, and for the topic model
  `sentence-transformers` (all-MiniLM-L6-v2), `umap-learn`, `hdbscan`, `scikit-learn`.
- **Run order (v2):** `python R/make_v2_build.py` (regenerates the `*_v2` scripts), then from
  `projects/hee/analysis`: `python R/01-build-metadata-maps_v2.py` ; `python R/02-emit-harvest-fields_v2.py` ;
  `Rscript R/00-build-analysis-data_v2.R` (from the repo root) ; `Rscript R/03-build-master_v2.R` ;
  `python R/04-emit-abstract-signals_v2.py` ; `Rscript R/03-build-master_v2.R` ;
  `python R/06-emit-study-texts_v2.py` ; `python R/05-topic-model_v2.py` (then optionally
  `R/05b-topic-stability_v2.py`, `R/make_themes_v2.py`). The chain writes to `data_v2/`;
  promotion copies `data_v2/` to `data/` (done 2026-10-07; the two are byte-identical). Then
  `R/98-codebook.R`, `R/99-data-quality-audit.R`, figure scripts and `hee-paper_v2.qmd`
  (`R/prisma_v2.R`). Reference fetchers (`fetch-wb-*.py`, GBD export) are run when the dated
  sources need refreshing. *(v1 order: `00` → `02` + `04` → `03` → figures → `hee-paper.qmd`.)*
- Derived data (`data/*.csv`, `*.rds`) and figures are regenerable and git-ignored; the scripts
  are the source of truth.
- **Web app**: the public interactive site (pure HTML/JS, no server runtime) — build,
  test, publish and decision log in `WEBAPP.md`.

---

## 11. Limitations (for the paper)

1. **Per-study methodological quality is not audited.** The reference-case audit needs PDFs,
   which are not retrieved; the abstract-signal panel (§6.7) is an honest but partial substitute.
2. **The corpus is effectively English-only** (99.8%; audit finding 14). Non-English economic
   evaluations are absent, and their absence concentrates in exactly the under-served regions the
   map reports — a property of the search, stated plainly.
3. **Geography is missing for 28.2% of eligible studies** (no place stated) and cannot be filled
   without income bias (§6.1); country-level figures are of the placeable subset (67.0%
   single-country), declared, with `income_reason` shown.
4. **MeSH / topic / bibliometric coverage is partial** (~52–87% of eligible depending on field);
   every figure using them declares its base.
5. **Comparisons of research to burden are ecological** and describe disproportion, not cause,
   against a reference that is not a target (§6.4).
6. **Extraction carries irreducible run-to-run noise** (§8); its two design fields disagree for
   11.8% of extracted records (none eligible).
7. **Screening sensitivity on the independent blinded audit is 0.86** (95% CI 0.72–0.94), below
   the protocol's 0.95; some eligible evaluations are missing.
8. **The eligibility check over-includes by ~9–12%** (§8); studies whose only consequence is
   service use or a diagnostic result could not be removed by rule (Q1).
9. **Screening and extraction were done by language models** (one model with a second opinion on
   split votes at screening; one model at extraction), not by two independent human reviewers.
10. **Protocol deviations, stated:** unsure-at-TA records advanced to an abstract-based extraction
    stage, not to full-text review; records with no abstract were excluded (no full-text stage);
    cost-minimisation analyses were excluded whether or not they established equivalent outcomes
    (F2 3B excludes only those that do not); studies with non-clinical consequences were
    excluded.
11. Preprint eligibility (audit finding 15) is an open team decision.
12. *(v1, history: the 50,661 unsure-at-TA records were held out with no handling policy; resolved
    by option D, 2026-10-06.)*

---

## 12. Decisions log

| date | decision | by | where |
|---|---|---|---|
| 2026-08-26 | Unsure-at-TA is its own PRISMA line, not an exclude | team | `HEE_ARM_FINAL.md`, §2 |
| 2026-09-04 | Partial evaluations excluded; consequences-not-clinical kept & flagged; unclear excluded | team | §3, build script |
| 2026-09-04 | Income/population fetched from World Bank API, not bundled snapshots | analyst | §5, audit 1–2 |
| 2026-09-04 | Duplicate-DOI de-duplication (keep eligible, then lowest id) | analyst | §3, audit 11 |
| 2026-09-05 | MeSH any-topic, not major-topic, for the time series | analyst | §6.3, audit 16 |
| 2026-09-05 | GBD Level-2 as the burden denominator; 11-group MeSH↔GBD crosswalk | analyst | §5–6.5 |
| 2026-09-06 | Affiliation geography proxy excluded from income figures (income-biased availability) | analyst | §6.1, audit 17 |
| 2026-09-07 | Rebuild the single analysis master; C14 signals from corpus abstracts (100%) | analyst | §6.7, §6.9 |
| 2026-09-07 | Measured, non-verdict wording across all figures + paper Fig 8 | analyst | §9 |
| 2026-09-07 | Emergent topic model per protocol Appendix K (embed → UMAP → HDBSCAN) | analyst | §6.8 |
| 2026-09-09 | GBD round updated 2021 → 2023 (both exports re-pulled at year 2023; cause list unchanged, 22 Level-2) | analyst | §5, §6.5 |
| 2026-09-09 | Health spending added as a second denominator (studies per US$1bn of health expenditure) | analyst | §5, §7 |
| 2026-09-16 | Unsure-bucket workstream stopped at sampling: hold out, disclose, no full re-score | L. Sempe | `reviews/unsure-bucket-decision.md` |
| 2026-10-05 | "Consequences not clinical" EXCLUDED, superseding ruling (a) of 2026-09-04; applied in v2 (4,965 excluded) | L. Sempe | §3, `audit/phase_d_adjudications.json` |
| 2026-10-05 | Phase F rulings F-b (repaired basis), F-c (current inputs), F-d (v6.9 gated; failed, v6.8 kept), Q1–Q9 | team / L. Sempe | §v2, `../audit/PHASE_F_DECISIONS.md` |
| 2026-10-06 | Unsure bucket advances to extraction (option D), superseding 2026-09-16; no-abstract records excluded | L. Sempe | §v2, §2 |
| 2026-10-06 | Clinical practice guidelines treated like reviews; hospital charges count as costs when compared with clinical consequences (prompt v0.5; corpus not re-screened, no recall change) | L. Sempe | §v2 |
| 2026-10-06 | Q4 crosswalk option A (Sense organ, Other NCD, C12.KID) | L. Sempe | §6.5, `f12bb34` |
| 2026-10-07 | Q1 applied by rule (2,020 v2 studies → unclear); v2 promoted to `data/` (41,661) | analyst | §3, `39a7fc5`, `83fa7a5` |
| 2026-10-07 | Outcome-family rule extension; new Reproductive & birth family | L. Sempe | §4, `b05fa88` |
| 2026-10-07 | Maternal = C12.050.703 only; residual branches per heading | analyst | §6.5, `19c44aa`, `0e1cd8e` |
| 2026-10-07 | Generic-measure share on full evaluations (46.9%); 57.2% is a pipeline yield, reported at selection | analyst | §v2, `e8ef369` |
| 2026-10-07 | Included studies are the analysis population (now 41,657); 72,845 extracted only in the selection flow | L. Sempe | §v2 |
| 2026-10-07 | Q2 keep rule aligned with the ruling (41,661 → 41,657); Q6 confidence column; Q7 design level; intervention labels for all included | analyst | §v2, `7b50722` |

---

## 13. Still open (needs a team decision or external input)

- **Theme grouping sign-off**: the draft 15-theme grouping of the 73 v2 topic clusters
  (`reviews/theme-curation-worksheet_v2.csv`, `reviewer_group` column) needs team review before
  any theme figure returns.
- *(Resolved 2026-10-08: intervention class for all included studies; the three intervention
  figures are restored. Resolved 2026-10-07: Q6 and Q7 built; Q5 has no figure to apply to.)*
- **Affiliation-proxy numbers** (§6.1) need re-measuring on v2 before they are quoted.
- *(Resolved: unsure-at-TA records — held out 2026-09-16, then advanced to extraction by option
  D, 2026-10-06. The equivalent HFF question is handled by HFF Decision 6.)*
- **Reference-case extraction** (7 fields on ~4,000 LMIC studies) — the only path to a true
  rung-5 quality audit; needs a team go-ahead, a paid run, and probably PDF retrieval.
- **Preprint / non-article eligibility** (audit finding 15) and the **publication-year source**
  choice (audit finding 12).
- **World Bank access date** refresh before submission.
