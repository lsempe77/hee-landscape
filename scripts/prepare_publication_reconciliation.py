"""Choose canonical reports using the user's newest-full-article preference."""
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'exports/publication_version_check'
OUT = ROOT / 'exports/publication_reconciliation'
OUT.mkdir(exist_ok=True)
csv.field_size_limit(10**9)
with (ROOT / 'data/raw/hee_analysis_master_v2.csv').open(encoding='utf-8-sig', newline='') as f:
    master = {r['record_id']: r for r in csv.DictReader(f)}
groups = defaultdict(list)
with (ROOT / 'exports/potential_publication_versions_61_records.csv').open(encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        groups[int(r['candidate_group'])].append(r['record_id'])
with (AUDIT / 'group_decisions.csv').open(encoding='utf-8-sig') as f:
    decisions = {int(r['candidate_group']): r for r in csv.DictReader(f)}

# Complete research articles take priority over newer conference or secondary reports.
KEEP = {
    2:'131152149', 4:'131223503', 8:'131261696', 9:'131287453', 11:'131508588',
    13:'131462474', 15:'131493741', 17:'131566085', 18:'131657569', 19:'131658016',
    21:'131756244', 22:'131773498', 23:'131779945', 24:'131785586', 29:'131831214',
    30:'131849063', 31:'131851976', 32:'131875578', 33:'131876003', 34:'131952691',
    36:'131977172', 37:'132018093', 38:'132045926', 39:'132054884', 40:'132057470',
    41:'132100977', 42:'132112608', 43:'132115225', 44:'132122777', 46:'132157565',
    47:'132167172', 48:'132620236', 49:'132823385', 50:'131941353', 51:'131977666',
    52:'132866688', 53:'131121257', 54:'132297933',
}
EXTRA = {50:'131941353', 51:'131977666', 53:'131121257', 54:'132297933', 57:'131377387'}
assert len(KEEP) == 38
plans = []
for group, original_ids in sorted(groups.items()):
    audit = decisions[group]
    members = original_ids + ([EXTRA[group]] if group in EXTRA else [])
    for rid in members:
        row = master[rid]
        assert row['is_eligible'] == 'TRUE', (group, rid, 'stale eligibility')
        action, reason, retained = 'keep', 'distinct_evaluation', ''
        if group in KEEP:
            retained = KEEP[group]
            action = 'keep' if rid == retained else 'exclude'
            reason = 'canonical_report' if action == 'keep' else 'redundant_publication'
            if group == 54 and rid == '132884025':
                reason = 'trial_registration_without_results'
        elif group == 10:
            action = 'exclude' if rid == '131733131' else 'keep'
            reason = 'retracted_publication' if action == 'exclude' else 'retain_nonretracted_report_overlap_unresolved'
        elif group in (16, 27, 57):
            action, reason = 'pending', 'publication_relationship_needs_confirmation'
        elif audit['category'] == 'review_update':
            reason = 'review_or_hta_update_retained'
        elif group == 55:
            reason = 'same_trial_companion_report' if rid in ('132885538', '132928004') else 'distinct_trial_under_generic_heading'
        plans.append(dict(candidate_group=group, record_id=rid, action=action, reason=reason,
            retained_record_id=retained, publication_family_id=f'PV{group:03}' if group != 55 else
                ('MYB' if rid in ('132885538','132928004') else 'DelpHi-MV' if rid=='132885614' else rid),
            title=row['title'], year=row['year'], doi=row['doi'], evidence_strength=audit['evidence_strength'],
            evidence=audit['evidence'], selection_rule='Newest full research article; later conference abstracts, translations and synopses do not displace it; latest complete non-journal report where no full journal article is included.'))
assert len(plans) == len({r['record_id'] for r in plans}) == 123
exclusions = [r for r in plans if r['action']=='exclude']
assert Counter(r['reason'] for r in exclusions) == Counter(redundant_publication=41, trial_registration_without_results=1, retracted_publication=1)

corrections = {
    '131462474': dict(doi='10.1016/j.ajog.2024.04.014', journal='American Journal of Obstetrics and Gynecology',
        publication_type='journal-article', url='https://doi.org/10.1016/j.ajog.2024.04.014',
        note='Conference DOI replaced with the full-article DOI matching the supplied abstract and journal/year. Original DOI retained in metadata_original_doi.',
        source='https://pubmed.ncbi.nlm.nih.gov/38621481/'),
    '132018093': dict(doi='10.6002/ect.mesot2016.P34', journal='Experimental and Clinical Transplantation',
        publication_type='journal-article', url='https://doi.org/10.6002/ect.mesot2016.P34',
        note='2015 conference DOI/journal replaced with the 2017 full-article citation matching the supplied abstract. Geography requires separate verification: recorded Turkey may reflect publisher location.',
        source='https://pubmed.ncbi.nlm.nih.gov/28260458/'),
    '132866626': dict(doi='',
        note='Recorded DOI resolves to an unrelated conscientious-objection paper and has been cleared. Original DOI retained in metadata_original_doi. Preliminary abstract retained; no unverified conference DOI invented. Evaluation linked to canonical full paper 131977666.',
        source='https://api.crossref.org/works/10.3109%2F13625187.2015.1135897'),
}

def write_csv(name, rows):
    with (OUT/name).open('w', encoding='utf-8-sig', newline='') as f:
        writer=csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
write_csv('record_decisions.csv', plans)
write_csv('exclusions.csv', exclusions)
write_csv('retained_canonical_reports.csv', [r for r in plans if r['reason']=='canonical_report'])
(OUT/'metadata_corrections.json').write_text(json.dumps(corrections, ensure_ascii=False, indent=2), encoding='utf-8')
summary = dict(records_examined=123, excluded=len(exclusions), exclusion_reasons=dict(Counter(r['reason'] for r in exclusions)),
    retained=sum(r['action']=='keep' for r in plans), pending_records=sum(r['action']=='pending' for r in plans),
    pending_families=[16,27,57], eligible_before=sum(r['is_eligible']=='TRUE' for r in master.values()),
    eligible_after=sum(r['is_eligible']=='TRUE' for r in master.values())-len(exclusions),
    preference='Newest full research journal article; full research ahead of later conference/translation/synopsis',
    extra_full_reports_reconciled=[50,51,53,54], extra_full_report_pending=[57])
(OUT/'plan_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
notes = ['# Publication reconciliation', '', 'User preference: retain the newest full research journal article. A later conference abstract, translation or journal synopsis does not replace the original full research report.', '',
    '## Counts', '', 'The original audit covered 118 records. Five additional full reports bring this reconciliation to 123 records. There are 43 proposed exclusions: 41 redundant reports, one registration without results, and one retracted paper. Seventy-three records are retained outright and seven records in three families remain included pending confirmation. Eligible master count: 41,657 → 41,614 after applying the clear decisions.', '',
    'This replaces the earlier 39-exclusion estimate against the original title-group baseline: four additional redundant reports are resolved by the separately included full papers. The 61 baseline excess records were not an actual record-level deletion list.', '',
    '## Five reports outside the original groups', '', '| Topic | Retain | Linked records to exclude | Status |', '|---|---|---|---|',
    '| Nurse-midwife abortion evaluation | 131977666; 2016 PLOS article | 132866653, 132866626 | Clear study match; incorrect DOI cleared on excluded preliminary record |',
    '| RxEACH pharmacist cardiovascular care | 131121257; 2019 full article | 132877525, 132877599 | Clear study match |',
    '| CMV monitoring after kidney transplantation | 132297933; 2026 full article | 132884025 registration; 132891161 results abstract | Same registry identifier/results |',
    '| SARAH rheumatoid-arthritis hand exercises | 131941353; 2015 full HTA | 132861889, 132865649 | Same 490-patient trial and authors; final economic analyses retained |',
    '| Physician groups and bundled payments | 131377387; 2022 JAMA article | None yet: 132911981 and 132914275 stay pending | Confirm whether conference samples are preliminary versions or separately intended economic analyses |', '',
    '## Decisions still requiring help', '',
    '1. **Bundled payments (family 57):** a statement from the authors, correspondence, or conference-to-journal version history confirming that the 2021/2022 presentations were preliminary versions of the 2022 article would support consolidation. The journal expands the claims period and changes sample definitions; do not infer exact equivalence solely from the title.',
    '2. **Ginkgo (family 27):** the 2015 German article or an explicit citation to the 2013 analysis is needed to distinguish a secondary reproduction from a separately conducted evaluation. DOI 10.1055/s-0041-101221. Different author attribution is why it remains pending.',
    '3. **Carpal-tunnel closure (family 16):** a registry publication link or confirmation from the authors connecting TCTR20221219005 to DOI 10.5704/MOJ.2407.009 would confirm the probable link.',
    '4. **Valganciclovir geography:** the DOI/journal can be corrected from the matching full article, but the recorded country Turkey should be checked against the study setting. Author affiliations alone are insufficient; supply the explicit site statement or author confirmation before changing geography.', '',
    'Review/HTA updates remain included under the previous recommendation. The MYB and DelpHi-MV companion analyses remain linked but retained; shared clinical participants alone do not prove duplicate economic analyses.', '',
    '## Files', '', '- `record_decisions.csv`: keep/exclude/pending for every record, with reasons.', '- `retained_canonical_reports.csv`: the retained representative of each resolved study family.', '- `exclusions.csv`: the exact 43 records to exclude, with canonical links.', '- `metadata_corrections.json`: the three metadata repairs and source citations.', '',
    'Two families have only conference reports among included candidates (droxidopa) or complete working papers/preprints rather than a full journal article (COVID containment, vertebroplasty, NHS competition). No new external publication is added by this reconciliation; retained exceptions are explicit in the CSV.', '']
(OUT/'README.md').write_text('\n'.join(notes),encoding='utf-8')
print(json.dumps(summary,indent=2))
