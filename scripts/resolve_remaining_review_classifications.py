"""Apply the user's not-identified policy to the final 117 ambiguous screens."""
import csv
import hashlib
import json
import os
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/raw/review_screening'
NO = 'Not identified as a review'
NOT_ORIGINAL = 'Original evaluation not identified'
SR = {
    '131182763': 'The report explicitly registers its systematic review as PROSPERO CRD42018112908, alongside the BiCARB trial.',
    '131377316': 'The authors explicitly state that they extracted effectiveness and safety evidence through a systematic review for their decision-tree evaluation.',
    '131491543': 'The plain-language abstract explicitly says we estimated effectiveness by doing a systematic literature review; the report also conducts network meta-analysis and decision modelling.',
    '131531806': 'The plain-language abstract explicitly says we estimated effectiveness by doing a systematic literature review; the report also conducts network meta-analysis and decision modelling.',
    '131698524': 'The programme design explicitly includes a systematic review in Phase 1, reports its findings, and describes subsequent original cohort and economic evaluations.',
    '131732454': 'The authors explicitly identify interventions through a systematic review and then meta-analyse the results and conduct an incremental economic evaluation.',
    '131745341': 'The report specifies an own systematic review, databases searched and updated searches, alongside a newly developed decision tree.',
    '131747332': 'The methods specify a systematic literature review of non-biologic therapies with a MEDLINE search of randomised trials from 1990 to 2007, alongside original risk-benefit modelling.',
    '131781315': 'The abstract reports a systematic literature review identifying trials, a meta-analysis of nine trials and a new Italian cost comparison within this study.',
    '131820584': 'The stated purpose of the current study is to provide a systematic review and meta-analysis; its searches, included studies and synthesis findings are reported.',
    '131831634': 'This study presents a systematic literature review of economic evaluations, summarising included studies and their heterogeneity rather than developing a new evaluation.',
    '131923210': 'The abstract explicitly labels the study design Systematic review and reports database searches, eligibility screening and synthesis of five included studies.',
    '131980396': 'The analysis describes its systematic literature review, search period, four included trials and original cost-per-responder calculations.',
    '132022604': 'The HTA methods identify a rigorous systematic review, report findings from that review, and conduct direct costing and incremental economic analysis.',
    '132028423': 'This overview reports a dated systematic literature review, extraction and synthesis of 24 economic publications; no separate new economic evaluation is established.',
    '132857276': 'The methods specify a systematic literature review with a dated MEDLINE search and report findings from it alongside a new Markov evaluation.',
}
NON_SR = {
    '131718006': 'The authors select and synthesise two economic studies from a prior WHO-submission review. This own focused synthesis is identified, but is not itself explicitly labelled systematic; included original models belong to the reviewed studies.',
    '131994610': 'The authors conduct their own network meta-analysis using studies from a systematic review, alongside a new Markov model. Systematic describes the source review, not an explicitly systematic label for their own synthesis.',
}
ORIGINAL_YES = set(SR) - {'131820584', '131831634', '131923210', '132028423'}
ORIGINAL_YES.add('131994610')
FLAG_CORRECTIONS = {'131792270', '132852324'}
METHOD = 'remaining-review-resolution-v2-user-not-identified-policy'


def sync_current_results():
    """Preserve approved classifications in the screening caches for future runs."""
    csv.field_size_limit(10_000_000)
    snapshots = [OUT / 'unclear_117_snapshot.json', OUT / 'evidence_basis_81_records.json']
    ids = {r['record_id'] for path in snapshots
           for r in json.loads(path.read_text(encoding='utf-8'))}
    current = {}
    with (ROOT / 'data/raw/hee_analysis_master_v2.csv').open(encoding='utf-8', newline='') as f:
        for row in csv.DictReader(f):
            if row['record_id'] in ids:
                current[row['record_id']] = row
    assert set(current) == ids
    persistent_path = OUT / 'review_resolution_applied.json'
    persistent = json.loads(persistent_path.read_text(encoding='utf-8'))
    results_path = OUT / 'review_screen_results.json'
    results = json.loads(results_path.read_text(encoding='utf-8'))
    for rid, row in current.items():
        values = {k: v for k, v in row.items() if k.startswith('review_')}
        persistent[rid] = dict(
            title_abstract_sha256=hashlib.sha256((row['title'] + '\n' + row['abstract']).encode()).hexdigest(),
            classification=values, source='Supplied abstract and approved record-specific ownership audit',
            rule=METHOD)
        results.setdefault(rid, {}).update(values)
    persistent_path.write_text(json.dumps(persistent, ensure_ascii=False, indent=2), encoding='utf-8')
    results_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    queue = OUT / 'review_screening_queue.csv'
    with queue.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        fields, rows = reader.fieldnames, list(reader)
    for row in rows:
        if row['record_id'] in current:
            row.update({k: v for k, v in current[row['record_id']].items()
                        if k.startswith('review_') and k in fields})
            row['manual_check_priority'] = {
                'Systematic review': '5', 'Review (non-systematic)': '6', NO: '7'}[row['review_type']]
    with queue.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    (OUT / 'unclear_resolution_remaining.json').write_text('[]', encoding='utf-8')
    remaining = OUT / 'remaining_review_checks.csv'
    with remaining.open(encoding='utf-8-sig', newline='') as f:
        remaining_fields = next(csv.reader(f))
    with remaining.open('w', encoding='utf-8-sig', newline='') as f:
        csv.writer(f).writerow(remaining_fields)


def main():
    csv.field_size_limit(10_000_000)
    master = ROOT / 'data/raw/hee_analysis_master_v2.csv'
    before_hash = hashlib.sha256(master.read_bytes()).hexdigest()
    timestamp = datetime.now(timezone.utc).isoformat(timespec='seconds')
    backup = OUT / 'backups' / ('hee_analysis_master_v2_before_final_review_resolution_' +
                              datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.csv')
    shutil.copy2(master, backup)
    assert hashlib.sha256(backup.read_bytes()).hexdigest() == before_hash
    staging = master.with_suffix('.finalreviews.tmp')
    changes = {}
    audit = []
    count = 0
    with master.open(encoding='utf-8', newline='') as src, staging.open('w', encoding='utf-8', newline='') as dst:
        reader = csv.DictReader(src)
        fields = reader.fieldnames
        writer = csv.DictWriter(dst, fieldnames=fields)
        writer.writeheader()
        for row in reader:
            count += 1
            rid = row['record_id']
            update = {}
            if row['review_type'] == 'Unclear - manual check needed':
                kind = 'Systematic review' if rid in SR else 'Review (non-systematic)' if rid in NON_SR else NO
                reason = SR.get(rid) or NON_SR.get(rid) or (
                    "Review-related wording describes evidence sources, background or a review whose ownership is not established. "
                    "The supplied title/abstract does not explicitly identify a literature review conducted by these authors. "
                    "Under the agreed policy, code Not identified as a review; this does not assert that no literature was consulted.")
                evidence = ' | '.join(s for s in re.split(r'(?<=[.!?])\s+', row['abstract'])
                                      if re.search(r'review|search|meta.analys', s, re.I))[:2500]
                original = 'Yes' if rid in ORIGINAL_YES else row['review_has_original_evaluation']
                update = dict(review_type=kind, review_subtype=(
                    'Own explicitly identified systematic review' if rid in SR else
                    'Own synthesis without an explicit systematic label' if rid in NON_SR else
                    'Own literature review not identified in supplied material'),
                    review_screen_reason=reason, review_screen_evidence=evidence,
                    review_screen_method=METHOD, review_screened_at=timestamp,
                    review_has_original_evaluation=original,
                    review_mixed_primary_analysis='TRUE' if kind != NO and original == 'Yes' else 'FALSE')
                audit.append(dict(record_id=rid, title=row['title'], previous_review_type=row['review_type'],
                                  review_type=kind, reason=reason, evidence=evidence,
                                  review_has_original_evaluation=original))
            elif rid in FLAG_CORRECTIONS:
                assert row['review_type'] == 'Review (non-systematic)' and row['review_has_original_evaluation'] == 'Yes'
                update = dict(review_has_original_evaluation=NOT_ORIGINAL, review_mixed_primary_analysis='FALSE')
            if update:
                assert rid not in changes
                changes[rid] = {k: v for k, v in update.items() if k in fields}
                row.update(changes[rid])
            writer.writerow(row)
    assert len(audit) == 117 and len(changes) == 119
    assert set(SR) | set(NON_SR) <= {r['record_id'] for r in audit}
    with backup.open(encoding='utf-8', newline='') as src, staging.open(encoding='utf-8', newline='') as dst:
        before, after = csv.DictReader(src), csv.DictReader(dst)
        assert before.fieldnames == after.fieldnames == fields
        checked = 0
        for original in before:
            expected = dict(original)
            expected.update(changes.get(original['record_id'], {}))
            assert next(after) == expected
            checked += 1
        assert next(after, None) is None and checked == count
    assert hashlib.sha256(master.read_bytes()).hexdigest() == before_hash
    after_hash = hashlib.sha256(staging.read_bytes()).hexdigest()
    os.replace(staging, master)
    with (OUT / 'final_117_review_resolution.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(audit[0]))
        writer.writeheader()
        writer.writerows(audit)
    # Mark the separate two-record audit recommendations as applied.
    path = OUT / 'review_ownership_81_assessments.csv'
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        audit_fields, ownership = reader.fieldnames, list(reader)
    for row in ownership:
        if row['record_id'] in FLAG_CORRECTIONS:
            row['applied_to_master'] = 'Yes'
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=audit_fields)
        writer.writeheader()
        writer.writerows(ownership)
    result = dict(records_resolved=117, categories=dict(Counter(r['review_type'] for r in audit)),
                  original_evaluation_flag_corrections=2, remaining_unclear=0,
                  evidence_basis_changed=False, total_master_records=count,
                  backup=str(backup), before_sha256=before_hash, after_sha256=after_hash,
                  all_other_fields_verified_unchanged=True, timestamp=timestamp)
    (OUT / 'final_117_review_resolution_application.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    summary_path = OUT / 'review_ownership_81_summary.json'
    summary = json.loads(summary_path.read_text(encoding='utf-8'))
    summary.update(all_proposed_classification_changes_applied=True, evidence_basis_verification_pending=False,
                   evidence_basis_note='User confirmed evidence-basis labels were previously verified; retain existing labels.',
                   final_application=result)
    summary_path.write_text(json.dumps(summary, indent=2), encoding='utf-8')
    sync_current_results()
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
