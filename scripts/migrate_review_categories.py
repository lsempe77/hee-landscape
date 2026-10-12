"""Separate existing mixed-review labels without re-screening other records."""
import csv
import hashlib
import json
import os
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from screen_reviews_with_abstracts import separate_original_evaluation


def main():
    root = Path(__file__).resolve().parents[1]
    master = root / 'data/raw/hee_analysis_master_v2.csv'
    out = master.parent / 'review_screening'
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    csv.field_size_limit(10_000_000)
    with master.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        fields, rows = list(reader.fieldnames), list(reader)
    original = [dict(row) for row in rows]
    column = 'review_has_original_evaluation'
    if column in fields:
        fields.remove(column)
    fields.insert(fields.index('review_type') + 1, column)
    changes = []
    for row in rows:
        previous = row['review_type']
        separate_original_evaluation(row)
        if previous.startswith('Not screened'):
            row[column] = 'Not screened'
        if previous != row['review_type']:
            changes.append(dict(record_id=row['record_id'], previous_review_type=previous,
                                review_type=row['review_type'], review_has_original_evaluation=row[column]))
    assert not any(row['review_type'] == 'Mixed review and original evaluation' for row in rows)
    staging = master.with_suffix('.categories.tmp')
    with staging.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    with staging.open(encoding='utf-8', newline='') as handle:
        verified = list(csv.DictReader(handle))
    assert len(verified) == len(original)
    allowed = {column, 'review_type', 'review_type_explanation'}
    for before, after in zip(original, verified):
        assert all(before[key] == after[key] for key in before if key not in allowed)
    backup = out / 'backups' / f'hee_analysis_master_before_review_category_split_{timestamp}.csv'
    backup.parent.mkdir(exist_ok=True)
    shutil.copy2(master, backup)
    assert hashlib.sha256(backup.read_bytes()).digest() == hashlib.sha256(master.read_bytes()).digest()
    os.replace(staging, master)
    results_path = out / 'review_screen_results.json'
    results = json.loads(results_path.read_text(encoding='utf-8'))
    for result in results.values():
        separate_original_evaluation(result)
    results_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    queue = out / 'review_screening_queue.csv'
    with queue.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        queue_fields, queued = list(reader.fieldnames), list(reader)
    if column in queue_fields:
        queue_fields.remove(column)
    queue_fields.insert(queue_fields.index('review_type') + 1, column)
    for row in queued:
        separate_original_evaluation(row)
    with queue.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=queue_fields)
        writer.writeheader()
        writer.writerows(queued)
    summary_path = out / 'review_screen_summary.json'
    summary = json.loads(summary_path.read_text(encoding='utf-8'))
    summary['review_type_counts'] = dict(Counter(row['review_type'] for row in rows if row['is_eligible'] == 'TRUE'))
    summary['master_sha256_after'] = hashlib.sha256(master.read_bytes()).hexdigest()
    summary['category_split'] = {'backup': str(backup), 'changed_records': len(changes),
                               'counts': dict(Counter(row['review_type'] for row in changes))}
    summary_path.write_text(json.dumps(summary, indent=2), encoding='utf-8')
    (out / f'review_category_split_{timestamp}.json').write_text(json.dumps(changes, indent=2), encoding='utf-8')
    (out / 'review_category_policy.md').write_text(
        '# Review category policy\n\n'
        'review_type separates Systematic review from Review (non-systematic). '
        'Scoping, rapid and umbrella reviews without an explicit systematic self-description '
        'are Review (non-systematic). Authors conducting their own systematic review remain '
        'Systematic review even when they also conduct an original evaluation. '
        'Using an existing review as input does not establish an own review.\n\n'
        'review_has_original_evaluation is adjacent to review_type: Yes means an original '
        'evaluation/analysis was identified; Not identified is not a confirmed absence; '
        'Not screened means no abstract was supplied. Existing mixed records are split '
        'using their recorded review subtype, retaining their evidence and provenance.\n', encoding='utf-8')
    print(json.dumps(summary['category_split'], indent=2))


if __name__ == '__main__':
    main()
