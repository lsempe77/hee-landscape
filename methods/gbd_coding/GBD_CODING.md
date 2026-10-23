# HEE: GBD 2023 disease coding of the included studies

Record of how the 41,657 included HEE studies were coded to GBD 2023 causes, the team rulings, and
where every output lives. Built 2026-10-12/14. Total model spend about $307 (OpenRouter).

## What was coded

Two independent codings, compared with each other:

| | GBD (abstract) | GBD (MeSH) |
|---|---|---|
| Unit | each included study (41,657) | each MeSH disease heading carried by included studies (1,985) |
| Input | title + abstract | heading name, tree numbers, NLM scope note |
| Prompt | `projects/hee/prompts/prompt-gbd-disease-classifier-v1.5.md` | `projects/hee/prompts/prompt-gbd-mesh-term-reference-v1.2.md` |
| Models | deepseek-v4.1-flash = **main coding**; GLM-5.2 (Baidu) = second coder on a random 47% (19,587 studies; stopped when Baidu's price rose 13-fold, L. Sempe 2026-10-13) | Claude Opus 5.5 + GPT-5.6-sol, both on every heading; final mapping = rulings + rules below |
| Levels | level 3 (rolled up to level 2 and level 1 by the GBD hierarchy) and level 2 classified directly | level 3 and level 2 |
| Cost | $166.53 + $0.16 hepatitis re-check | $120.58 |
| Runner | `R/gbd_classify.py`, `R/gbd_hepatitis_recode.py` | `R/gbd_classify.py` |

Reference lists: `projects/hee/data/reference/gbd2023_cause_hierarchy_l3_l2_l1.csv` (176 level-3
causes, 22 level-2, 3 level-1) and `gbd2023_risk_hierarchy_l3_l2_l1.csv` (53 level-3 risks), from
IHME's GBD 2023 hierarchies (Y2025M10D23). Scope notes: `mesh_scope_notes.csv` (NLM MeSH SPARQL,
`R/fetch_mesh_scope_notes.py`).

## Coding rules (B. Hutchinson and team, 2026-10-13/14)

1. **Code the condition the evaluated intervention targets**; conditions measured as outcomes go in
   a separate secondary field; background mentions are not coded.
2. **Never infer a disease from a risk factor.** Risk factors are recorded in their own column
   (level 3, rolled up to level 2); a cause is coded only when the text names it (e.g. renal
   hypertension = Chronic kidney disease + risk High systolic blood pressure).
3. **Injuries named by their nature** (hip fracture, head trauma) without the external cause:
   level 1 *Injuries*; no guessing of the external cause.
4. **Adverse effects of medical treatment** (GBD's own definition) covers surgical and
   perioperative complications and complications of devices; GBD has no separate surgical cause.
   Infections are coded to the infectious disease, not to adverse effects, unless caused by human
   error. Postprocedural pain is the exception: its ICD-10 codes are garbage codes (5).
5. **General headings are coded at the level the text supports** (revised 2026-10-14): Neoplasm
   Metastasis, Neoplasm Recurrence, Lymphatic Metastasis, Precancerous Conditions → level 2
   *Neoplasms*; Ischemia → level 2 *Cardiovascular diseases*; enough to place them at level 1/2, not
   level 3/4, because no specific disease is named. **Disease unattributable**: the condition is a
   **GBD garbage code** in IHME's ICD-10 → GBD mapping (GBD 2019 supplement, p. 1476,
   https://pmc.ncbi.nlm.nih.gov/articles/instance/7567026/bin/mmc1.pdf), e.g. heart failure (I50),
   infertility, carpal tunnel syndrome, sepsis, postprocedural pain (G89.18 acute, G89.28 chronic).
   No cause is assigned and nothing is redistributed.
6. **Method for disputed headings (B. Hutchinson, following Tamara's suggestion of ICD-10):** give
   the heading its ICD-10 code and take the GBD cause IHME's ICD-10 table assigns to it. Brian's
   look-ups: `projects/hee/analysis/Classification GBD to ICD.xlsx`.
7. **Pathogen headings** (pneumococcal, staphylococcal, bacterial infections…): level 1
   *Communicable*, unless the pathogen names one disease (Helicobacter → Upper digestive system
   diseases; Chlamydia → STIs excluding HIV; Meningococcal → Meningitis).
8. **Viral hepatitis (PROVISIONAL, 2026-10-14, to confirm).** In IHME's ICD-10 mapping, *Acute
   hepatitis* is acute infection only (B15–B17); chronic viral hepatitis (B18) is counted under
   *Cirrhosis and other chronic liver diseases* (and liver cancer when it progresses). Studies first
   coded Acute hepatitis (807) were re-checked one by one (`R/gbd_hepatitis_recode.py`,
   deepseek-v4.1-flash, $0.16): **chronic** infection care (screening, treatment, monitoring; 611) →
   Cirrhosis and other chronic liver diseases; **prevention** of new infection (vaccination,
   mother-to-child transmission, harm reduction, blood safety; 148) → Acute hepatitis + Cirrhosis;
   **acute** (hepatitis A/E, outbreaks; 46) and 2 unresolved → Acute hepatitis unchanged. The MeSH
   side already followed this split (Hepatitis C, Chronic → Cirrhosis; Hepatitis C → both).

All rulings, one row per MeSH heading with the question they answer and the ICD-10 code:
`projects/hee/data/reference/mesh_gbd_rulings_v1.csv` (58 rows). Revisions are recorded in each
row's `note`:
- 2026-10-14, B. Hutchinson: Q1 headings to level 2; postoperative pain → disease unattributable;
  Opiate Overdose → Drug use disorders (opioid use disorders, as GBD treats accidental opioid
  poisoning, supplement pp. 33-35); Peritoneal Neoplasms → Other malignant neoplasms (all 12
  included studies are peritoneal cancer); Hemophilia B = D67 → Endocrine, metabolic, blood, and
  immune disorders, confirmed.
- 2026-10-14, **provisional** (`question = round2-provisional`, L. Sempe by Brian's method, sent for
  confirmation): the 15 headings the models could not agree on and the earlier rules did not settle,
  e.g. Leiomyoma → Gynecological diseases (D25), Endometritis → Maternal disorders (all studies
  postpartum), Foreign-Body Migration and Cerebrospinal Fluid Leak → Adverse effects of medical
  treatment, general headings (Colonic Diseases, Child Behavior Disorders, Fetal Diseases, Serous
  Cystadenocarcinoma) at level 2. Five are flagged low/medium confidence for an ICD check:
  Keratoconus, Retinal Perforations, Short Bowel Syndrome (possible garbage codes), Pelvic
  Inflammatory Disease, Obsessive-Compulsive Disorder. Two more applied by analogy with Brian's
  rulings: Carotid Artery Diseases → Stroke; Sleep Apnea Syndromes → Other chronic respiratory.

## Final MeSH crosswalk

`projects/hee/data/reference/mesh_gbd_crosswalk_v2.csv` (`R/gbd_crosswalk_v2.py`, no model calls).
Order of decision: a ruling > both models agree > automatic rules for the rest (drop "Other
neoplasms" next to a specific cancer; take the named cause where one model gave none; same cause,
union of risk factors; one model's causes contain the other's: union, five at most) > headings in
five or fewer studies: left without a cause in the check (`minor_no_cause`). No heading is left
unresolved.

| Status | Headings |
|---|---:|
| cause (incl. general headings at level 2) | 1,642 |
| not a condition (e.g. Disease Progression) | 164 |
| minor, no cause (models differ, ≤5 studies) | 96 |
| disease unattributable | 53 |
| risk factor only | 30 |

## Results (abstract coding, main model)

- 41,651 of 41,657 studies coded (6 failed calls). A GBD cause: 36,480 (87.6%); no specific
  disease: 2,510; risk factor only: 1,517; **disease unattributable: 1,072** (mostly heart failure);
  nothing coded: 72. Risk factor recorded for 3,603 studies.
- Level 1 (multi-valued): non-communicable 26,856; communicable, maternal, neonatal and nutritional
  7,560; injuries 2,558 studies. Largest level-2 causes: neoplasms 7,863; cardiovascular 4,092;
  diabetes and kidney 2,635; digestive 2,602.
- Level-3 roll-up and directly classified level 2 agree on 90.2% of studies; the roll-up is the main
  coding. flash vs GLM on 19,587 studies: 87.4% exact at level 3, 91.1% at level 2 (before the
  hepatitis re-check).
- **Against GBD (MeSH)**, on all 22,794 studies with MeSH disease headings: same level-2 causes for
  72.5%, at least one shared for 89.0%; the abstract coding is a subset of the MeSH coding for 83.7%
  (MeSH tags every condition a study mentions, so it codes more causes per study). When the
  abstract coding names a cause, MeSH agrees for most groups at 85-98%. The weak spot is
  unintentional injuries / adverse effects of medical treatment (about 0.45 both ways): the abstract
  coding records complications as secondary causes, MeSH tags them as topics.
- Scoring detail: `R/gbd_analyse_v2.py` → `gbd/gbd_check_v2.json`; a level-1 code on one side
  matches the other side's level-2 causes under it.

## In the analysis

- **Join file**: `data/gbd_by_record.csv` (`R/make_gbd_by_record.py`), one row per included study
  (41,657): `gbd_status`, `gbd_l3`, `gbd_l2`, `gbd_l1`, `gbd_secondary_l3`, `gbd_risk_l3`,
  `gbd_risk_l2`, `gbd_disease_unattributable`, `gbd_hepatitis_recode`. `gbd_l2` uses GBD's own 22
  level-2 names, so it joins the GBD burden export directly, with no crosswalk. Shipped in the team
  share folder (`hee_share_v2_1/`).
- **Research vs burden by GBD cause**: `R/fig-burden-by-gbd-cause.R` →
  `figures/fig_burden_gbd_l2.png` and `data/burden_gbd_l2_ratios.csv` (research share ÷ DALY share,
  HIC vs LMIC settings; 17,945 HIC and 7,093 LMIC study-settings). Lowest ratios in both settings:
  transport injuries (0.01-0.02), self-harm and interpersonal violence (0.07-0.11), unintentional
  injuries (0.4-0.5), mental, neurological and musculoskeletal disorders. Highest: HIV/STIs (3.5
  LMIC, 6.6 HIC), other infectious diseases (2.2 LMIC, 15.4 HIC), neoplasms, digestive diseases
  (2.4 LMIC after the hepatitis re-check). Maternal and neonatal disorders split by setting (0.54
  LMIC, 2.1 HIC). The HIC "other infectious diseases" ratio stays high after the hepatitis fix:
  meningitis, varicella, pertussis, measles and unspecified infections (fungal, hospital-acquired)
  are heavily evaluated against a small 2023 burden. The MeSH-based figure
  (`fig-burden-by-disease.R`, 14 groups) is unchanged and no longer used.
- **Disease groups of the map (2026-10-14, team decision, L. Sempe)**: `data/gbd_disease_long.csv`
  (one row per study × group: the 22 level-2 causes + "Injuries, cause not stated" and "Infections,
  disease not stated") replaces the 14 MeSH groups in every figure, the paper and the web app. Single
  source in R: `R/lookup-gbd-groups.R`. GBD versions of the figures: `R/fig-companion-disease_gbd.R`,
  `fig-companion-transition_gbd.R`, `fig-companion-burden-disease_gbd.R`, `fig-funder-opportunity_gbd.R`,
  `fig-funder-trajectory_gbd.R` (gallery), `fig-map-disease_gbd.R`, `fig-companion-disease-method_gbd.R`
  (unregistered, like their MeSH originals); paper Figures 4, 5, 8 (`hee-paper_v2_gbd.html`,
  `figures/paper04_gbd.png`, `paper05_gbd.png`, `paper08_gbd.png`, `R/export-paper-figures_gbd.py`).

## Files

| File | Tracked | What |
|---|---|---|
| `analysis/data/gbd_by_record.csv` | no (record level) | the join file above |
| `analysis/gbd/hee_gbd_study_coding_v2.csv` | no | full study coding incl. quote, confidence, classified level 2, GLM coding |
| `analysis/gbd/hepatitis_recode.jsonl` | no | the hepatitis re-check |
| `analysis/gbd/abstract_vs_mesh_by_study_v2.csv`, `gbd_check_v2.json` | no | comparison with MeSH |
| `data/reference/mesh_gbd_crosswalk_v2.csv`, `mesh_gbd_rulings_v1.csv` | yes | final MeSH mapping and the rulings |
| `analysis/Classification GBD to ICD.xlsx`, `… - round 2.xlsx` | yes | Brian's ICD look-ups; the round-2 list sent for confirmation |
| `analysis/gbd_pilot/raw_*.jsonl` | no | raw model answers |

The v1 outputs (`*_v1.*`, before the rulings) are kept beside the v2 ones.

## Still open

- **Confirmation of the provisional rulings** (round-2 list): the hepatitis rule (8), the 15
  round-2 headings (5 of them flagged for an ICD check) and the 2 by-analogy rulings.
- **Abstract coding and the garbage-code rule**: prompt v1.5 records postoperative complications as
  adverse effects of medical treatment (secondary cause); postprocedural pain as such is disease
  unattributable on the MeSH side. A small residual disagreement, not re-run.
- **Risk factors**: B. Hutchinson notes there may be a similar IHME table mapping exposures to GBD
  risk factors; search for it if the risk-factor coding raises questions.
- **Full ICD-10 route** (deferred, no UMLS key): MeSH → ICD-10 (UMLS) → GBD for all 1,985 headings.
- **Done 2026-10-14: in the paper and the web app** (team decision, L. Sempe): every disease figure,
  the paper's Figures 4, 5 and 8 and the web app's disease filter and panels use the GBD coding
  (`data/gbd_disease_long.csv`, `R/lookup-gbd-groups.R`). Still not in the master dataset (the
  `disease_groups` column of `hee_analysis_master.csv` is the MeSH crosswalk); the coding ships as a
  separate join file. The risk-factor analysis needs risk-attributable DALYs from the GBD Results tool.
