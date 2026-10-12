"""Audit review labels against evidence basis; do not change the master."""
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEWS = {'Systematic review', 'Review (non-systematic)'}
SYNTHESIS = 'Literature/registry synthesis'


def main():
    csv.field_size_limit(10_000_000)
    source = ROOT / 'data/raw/hee_analysis_master_v2.csv'
    out = source.parent / 'review_screening'
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    basis_counts, type_counts, status_counts = Counter(), Counter(), Counter()
    audit = []
    eligible = 0
    fields = ['record_id', 'title', 'year', 'review_type', 'design_basis',
              'review_has_original_evaluation', 'basis_matches_synthesis',
              'crosscheck_priority', 'crosscheck_result', 'crosscheck_note',
              'econ_eval_type', 'model_based', 'review_subtype',
              'review_screen_reason', 'review_screen_evidence', 'doi', 'url']
    with source.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        assert {'record_id', 'review_type', 'design_basis', 'review_has_original_evaluation', 'is_eligible'} <= set(reader.fieldnames)
        for row in reader:
            if row['is_eligible'] != 'TRUE':
                continue
            eligible += 1
            type_counts[row['review_type']] += 1
            if row['review_type'] not in REVIEWS:
                continue
            matches = row['design_basis'] == SYNTHESIS
            if matches:
                priority, status = '3', 'Synthesis basis recorded'
                note = 'Review classification and recorded synthesis basis agree. This does not independently validate the review methods.'
            elif row['review_has_original_evaluation'] == 'Yes':
                priority, status = '2', 'Different basis; original evaluation identified'
                note = 'A different evidence basis can describe the original evaluation in a paper that also conducts a review. Check which component design_basis is intended to represent.'
            else:
                priority, status = '1', 'Different basis; review/evaluation components need checking'
                note = 'Check the abstract/methods to distinguish a secondary synthesis of trials or observational studies from an own original evaluation. Either design_basis, the original-evaluation flag, or the review label may need correction; no change is inferred from this cross-check alone.'
            record = {key: row.get(key, '') for key in fields}
            record.update(basis_matches_synthesis='Yes' if matches else 'No',
                          crosscheck_priority=priority, crosscheck_result=status, crosscheck_note=note)
            audit.append(record)
            basis_counts[row['review_type'], row['design_basis']] += 1
            status_counts[status] += 1
    assert len({row['record_id'] for row in audit}) == len(audit)
    assert len(audit) == sum(type_counts[k] for k in REVIEWS) == sum(status_counts.values())
    audit.sort(key=lambda row: (row['crosscheck_priority'], row['review_type'], row['record_id']))
    for filename, records in [('review_evidence_basis_crosscheck.csv', audit),
                              ('review_evidence_basis_differences.csv', [r for r in audit if r['basis_matches_synthesis'] == 'No'])]:
        with (out / filename).open('w', encoding='utf-8-sig', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(records)
        with (out / filename).open(encoding='utf-8-sig', newline='') as handle:
            assert list(csv.DictReader(handle)) == records
    summary = {'source': source.name, 'source_sha256': source_hash,
               'checked_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
               'eligible_records': eligible, 'review_records': len(audit),
               'review_type_counts': dict(type_counts), 'crosscheck_counts': dict(status_counts),
               'basis_counts': [{'review_type': kind, 'design_basis': basis, 'count': count}
                                for (kind, basis), count in sorted(basis_counts.items())],
               'interpretation': 'Field consistency audit, not a new review-methods assessment. Original evaluation and review components may legitimately have different evidence bases.',
               'master_changed': False}
    assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
    (out / 'review_evidence_basis_crosscheck_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
