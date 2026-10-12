"""Apply the approved 93-record audit while preserving every other master value."""
import csv
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/raw/review_screening'
FIELDS = {
    'review_type': 'recommended_review_type',
    'review_has_original_evaluation': 'recommended_original_evaluation',
    'design_basis': 'recommended_design_basis',
}

def main():
    csv.field_size_limit(10_000_000)
    master = ROOT / 'data/raw/hee_analysis_master_v2.csv'
    audit_path = OUT / 'review_evidence_basis_93_assessments.csv'
    summary_path = OUT / 'review_evidence_basis_93_summary.json'
    summary = json.loads(summary_path.read_text(encoding='utf-8'))
    before_hash = hashlib.sha256(master.read_bytes()).hexdigest()
    assert before_hash == summary['source_sha256'], 'Master changed since audit; reconcile before applying.'
    with audit_path.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        audit_fields = reader.fieldnames
        audits = list(reader)
    decisions = {row['record_id']: row for row in audits}
    assert len(audits) == len(decisions) == 93
    assert all(row['review_decision_resolved'] == 'Yes' for row in audits)
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backups = OUT / 'backups'
    backups.mkdir(exist_ok=True)
    backup = backups / f'hee_analysis_master_v2_before_93_record_audit_{timestamp}.csv'
    shutil.copy2(master, backup)
    assert hashlib.sha256(backup.read_bytes()).hexdigest() == before_hash
    staging = master.with_suffix('.audit93.tmp')
    counts = dict.fromkeys(FIELDS, 0)
    seen = set()
    changed_records = set()
    row_count = 0
    with master.open(encoding='utf-8', newline='') as src, staging.open('w', encoding='utf-8', newline='') as dst:
        reader = csv.DictReader(src)
        master_fields = reader.fieldnames
        writer = csv.DictWriter(dst, fieldnames=master_fields)
        writer.writeheader()
        for row in reader:
            row_count += 1
            rid = row['record_id']
            if rid in decisions:
                assert rid not in seen
                seen.add(rid)
                decision = decisions[rid]
                assert row['title'] == decision['title'], rid
                for field, recommended in FIELDS.items():
                    assert row[field] == decision[field], f'Stale audit: {rid} {field}'
                    if row[field] != decision[recommended]:
                        counts[field] += 1
                        changed_records.add(rid)
                    row[field] = decision[recommended]
            writer.writerow(row)
    assert seen == set(decisions)
    # Compare every field and row against the backup, including unaffected records.
    with backup.open(encoding='utf-8', newline='') as src, staging.open(encoding='utf-8', newline='') as dst:
        before, after = csv.DictReader(src), csv.DictReader(dst)
        assert before.fieldnames == after.fieldnames == master_fields
        checked = 0
        for original in before:
            updated = next(after)
            rid = original['record_id']
            expected = dict(original)
            if rid in decisions:
                expected.update({field: decisions[rid][recommended] for field, recommended in FIELDS.items()})
            assert updated == expected, rid
            checked += 1
        assert next(after, None) is None and checked == row_count
    assert hashlib.sha256(master.read_bytes()).hexdigest() == before_hash
    after_hash = hashlib.sha256(staging.read_bytes()).hexdigest()
    os.replace(staging, master)
    assert hashlib.sha256(master.read_bytes()).hexdigest() == after_hash
    for row in audits:
        row['applied_to_master'] = 'Yes'
    with audit_path.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=audit_fields)
        writer.writeheader()
        writer.writerows(audits)
    result = {'records_audited': 93, 'records_changed': len(changed_records),
              'field_changes': counts, 'total_master_records': row_count,
              'backup': str(backup), 'applied_at_utc': timestamp,
              'before_sha256': before_hash, 'after_sha256': after_hash,
              'all_other_fields_verified_unchanged': True}
    summary.update(master_changed=True, application=result,
                   note='All 93 approved audit recommendations applied. Counts overlap. All other fields, row order and record count verified unchanged against the saved backup.')
    summary_path.write_text(json.dumps(summary, indent=2), encoding='utf-8')
    (OUT / 'review_evidence_basis_93_application.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
