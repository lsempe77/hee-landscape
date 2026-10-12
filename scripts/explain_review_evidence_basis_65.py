"""Append the approved evidence-basis explanation to 65 hybrid review records."""
import csv
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/raw/review_screening'
MARKER = 'Review classification and evidence basis describe different aspects of this paper.'


def main():
    csv.field_size_limit(10_000_000)
    master = ROOT / 'data/raw/hee_analysis_master_v2.csv'
    with (OUT / 'review_ownership_81_assessments.csv').open(encoding='utf-8-sig', newline='') as f:
        decisions = {r['record_id']: r for r in csv.DictReader(f)
                     if r['finding'] == 'Own review and original evaluation supported'}
    assert len(decisions) == 65
    before_hash = hashlib.sha256(master.read_bytes()).hexdigest()
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup = OUT / 'backups' / f'hee_analysis_master_v2_before_65_explanations_{timestamp}.csv'
    backup.parent.mkdir(exist_ok=True)
    shutil.copy2(master, backup)
    assert hashlib.sha256(backup.read_bytes()).hexdigest() == before_hash
    staging = master.with_suffix('.explanations65.tmp')
    changes = {}
    count = 0
    with master.open(encoding='utf-8', newline='') as src, staging.open('w', encoding='utf-8', newline='') as dst:
        reader = csv.DictReader(src)
        fields = reader.fieldnames
        writer = csv.DictWriter(dst, fieldnames=fields)
        writer.writeheader()
        for row in reader:
            count += 1
            rid = row['record_id']
            if rid in decisions:
                assert rid not in changes
                decision = decisions[rid]
                assert row['title'] == decision['title']
                assert row['review_type'] == decision['recommended_review_type']
                assert row['review_has_original_evaluation'] == 'Yes'
                assert MARKER not in row['review_screen_reason'], 'Explanation already applied'
                note = (f"{MARKER} The ownership audit identifies both an authors' own literature review "
                        f"and an original evaluation. The current evidence-basis label is '{row['design_basis']}'. "
                        "A trial or observational basis can describe the original evaluation even when the paper also "
                        "conducts a review; a new model based on literature synthesis may instead warrant "
                        "'Literature/registry synthesis'. The presence of an original evaluation alone does not "
                        "validate the evidence-basis label. This audit checked review ownership, not the correctness "
                        "of that label; interpretation requires checking which component supplies the evaluation's evidence.")
                original = row['review_screen_reason']
                row['review_screen_reason'] = original.rstrip() + '\n\n' + note
                changes[rid] = dict(before=original, after=row['review_screen_reason'])
            writer.writerow(row)
    assert set(changes) == set(decisions)
    with backup.open(encoding='utf-8', newline='') as src, staging.open(encoding='utf-8', newline='') as dst:
        before, after = csv.DictReader(src), csv.DictReader(dst)
        assert before.fieldnames == after.fieldnames == fields
        checked = 0
        for original in before:
            expected = dict(original)
            if original['record_id'] in changes:
                expected['review_screen_reason'] = changes[original['record_id']]['after']
            assert next(after) == expected
            checked += 1
        assert next(after, None) is None and checked == count
    assert hashlib.sha256(master.read_bytes()).hexdigest() == before_hash
    after_hash = hashlib.sha256(staging.read_bytes()).hexdigest()
    os.replace(staging, master)
    result = dict(records_updated=len(changes), column='review_screen_reason', total_master_records=count,
                  all_other_fields_verified_unchanged=True, backup=str(backup),
                  before_sha256=before_hash, after_sha256=after_hash, applied_at_utc=timestamp)
    (OUT / 'review_evidence_basis_65_explanations_application.json').write_text(
        json.dumps(dict(result, changes=changes), indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
