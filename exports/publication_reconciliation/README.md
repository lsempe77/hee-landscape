# Publication reconciliation

## Current state after user adjudication, 14 October 2026

The final figure pass now covers all 43 unique main-gallery figures: 15 residual static figures were rebuilt, stale caption overrides corrected, and the remaining figures verified against their current-dataset rebuilds. See figure_refresh/README.md and all_figure_audit.json. Published reference figures remain comparison images. This is a local-workspace update; deployment has not been performed.

The first-application account below is historical. Current totals: **47 exclusions (44 redundant reports, two registrations without results, one retracted paper); 41,610 included records; 76 of the 123 audited records retained; no pending family decisions.** All 72,845 original master rows are preserved.

- Bundled payments: retain full JAMA article 131377387; exclude and link abstracts 132911981 and 132914275. User-adjudicated relationship; explicit preliminary-to-final statement not verified.
- Ginkgo: retain original 131808468 (2013); exclude German report 131918773 (2015). Publisher confirms shortened translation.
- Carpal-tunnel closure: retain article 131512107; exclude and link registration 132884066 (TCTR20221219005). User-adjudicated relationship; explicit registry-to-paper citation not verified.
- Valganciclovir 132018093: retained; sample location not reported in title/abstract. Turkey is in the publisher notice, not a patient-site statement. Country, regional and income assignments cleared, including active long-form geography entries. This does not claim location is absent from every possible source.

Current decision CSVs and plan_summary.json reflect these decisions. followup_application.json preserves original geography, decision authority and the follow-up backup path. Follow-up build logs and kld_followup contain refreshed outputs. application.json and the original audit REPORT.md remain historical. The updated October 14 methods manuscript and Figure 1 have now been reconciled; manuscript_reconciliation.json records checked totals and remaining references/dates/policy placeholders.

User preference: retain the newest full research journal article. A later conference abstract, translation or journal synopsis does not replace the original full research report.

## Counts

The original audit covered 118 records. Five additional full reports bring this reconciliation to 123 records. Applied 43 exclusions: 41 redundant reports, one registration without results, and one retracted paper. Seventy-three records are retained outright and seven records in three families remain included pending confirmation. Eligible master count: 41,657 → 41,614 after applying the clear decisions. Original records and metadata are preserved for traceability; no rows were physically deleted.

This replaces the earlier 39-exclusion estimate against the original title-group baseline: four additional redundant reports are resolved by the separately included full papers. The 61 baseline excess records were not an actual record-level deletion list.

## Five reports outside the original groups

| Topic | Retain | Excluded linked records | Status |
|---|---|---|---|
| Nurse-midwife abortion evaluation | 131977666; 2016 PLOS article | 132866653, 132866626 | Clear study match; incorrect DOI cleared on excluded preliminary record |
| RxEACH pharmacist cardiovascular care | 131121257; 2019 full article | 132877525, 132877599 | Clear study match |
| CMV monitoring after kidney transplantation | 132297933; 2026 full article | 132884025 registration; 132891161 results abstract | Same registry identifier/results |
| SARAH rheumatoid-arthritis hand exercises | 131941353; 2015 full HTA | 132861889, 132865649 | Same 490-patient trial and authors; final economic analyses retained |
| Physician groups and bundled payments | 131377387; 2022 JAMA article | None yet: 132911981 and 132914275 stay pending | Confirm whether conference samples are preliminary versions or separately intended economic analyses |

## Decisions still requiring help

1. **Bundled payments (family 57):** a statement from the authors, correspondence, or conference-to-journal version history confirming that the 2021/2022 presentations were preliminary versions of the 2022 article would support consolidation. The journal expands the claims period and changes sample definitions; do not infer exact equivalence solely from the title.
2. **Ginkgo (family 27):** the 2015 German article or an explicit citation to the 2013 analysis is needed to distinguish a secondary reproduction from a separately conducted evaluation. DOI 10.1055/s-0041-101221. Different author attribution is why it remains pending.
3. **Carpal-tunnel closure (family 16):** a registry publication link or confirmation from the authors connecting TCTR20221219005 to DOI 10.5704/MOJ.2407.009 would confirm the probable link.
4. **Valganciclovir geography:** the DOI/journal can be corrected from the matching full article, but the recorded country Turkey should be checked against the study setting. Author affiliations alone are insufficient; supply the explicit site statement or author confirmation before changing geography.

Review/HTA updates remain included under the previous recommendation. The MYB and DelpHi-MV companion analyses remain linked but retained; shared clinical participants alone do not prove duplicate economic analyses.

## Files

- `record_decisions.csv`: keep/exclude/pending for every record, with reasons.
- `retained_canonical_reports.csv`: the retained representative of each resolved study family.
- `exclusions.csv`: the exact 43 records to exclude, with canonical links.
- `metadata_corrections.json`: the three metadata repairs and source citations.

Some families have only conference reports among included candidates (droxidopa) or complete working papers/preprints rather than a full journal article (COVID containment, vertebroplasty, NHS competition). No new external publication is added by this reconciliation; retained exceptions are explicit in the CSV.

## Application and verification

The clear decisions were applied to five master CSVs and the current, v2 and v3 web study bundles. All masters retain 72,845 rows; 41,614 are included. Backups and before/after hashes are recorded in application.json. Every original field outside the selected eligibility/duplicate/citation repairs was verified unchanged. Pending records remain included. The v1 historical website and earlier dated exports were preserved.

The record/index checks pass for all three updated website bundles. Existing local build scripts rebuilt disease, income, evaluation-type, authorship, regional, country-denominator and Wellcome outputs. Current KLD figures were rebuilt with the existing 1,000-draw setting in a fresh output folder. The browser runtime failed to start, so interactive visual verification was unavailable.

The publication methods manuscript was not edited and still contains the earlier 41,657 total and the unverified 61-second-version wording. Use the new flow counts below and describe this post hoc linkage/retraction audit when revising it.
