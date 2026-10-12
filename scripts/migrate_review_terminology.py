"""Apply agreed display labels, preserving classifications and archived versions."""
import csv
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABELS = {'Non-systematic review': 'Review (non-systematic)',
          'No review identified': 'Not identified as a review',
          'Not identified': 'Original evaluation not identified'}


def rename(value):
    if isinstance(value, dict):
        return {LABELS.get(k, k): rename(v) for k, v in value.items()}
    if isinstance(value, list):
        return [rename(v) for v in value]
    if isinstance(value, str):
        return LABELS.get(value, value)
    return value


def main():
    csv.field_size_limit(10_000_000)
    out = ROOT / 'data/raw/review_screening'
    master = ROOT / 'data/raw/hee_analysis_master_v2.csv'
    backup = out / 'backups' / ('hee_analysis_master_v2_before_label_rename_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.csv')
    shutil.copy2(master, backup)
    for path in [master] + list(out.glob('*.csv')):
        staging = path.with_suffix('.labels.tmp')
        expected = hashlib.sha256()
        count = 0
        with path.open(encoding='utf-8-sig', newline='') as source, staging.open('w', encoding='utf-8', newline='') as target:
            reader = csv.DictReader(source)
            writer = csv.DictWriter(target, fieldnames=reader.fieldnames)
            writer.writeheader()
            for old in reader:
                row = {k: LABELS.get(v, v) if k in ('review_type', 'previous_review_type', 'review_has_original_evaluation') else v for k, v in old.items()}
                writer.writerow(row)
                expected.update(json.dumps(row, ensure_ascii=False).encode('utf-8'))
                count += 1
        actual = hashlib.sha256()
        checked = 0
        with staging.open(encoding='utf-8', newline='') as target:
            for row in csv.DictReader(target):
                actual.update(json.dumps(row, ensure_ascii=False).encode('utf-8'))
                checked += 1
        assert count == checked and actual.digest() == expected.digest()
        os.replace(staging, path)
        print(f'{path.name}: {count:,} rows validated', flush=True)
    for path in out.glob('*.json'):
        text = path.read_text(encoding='utf-8')
        if any('"' + old + '"' in text for old in LABELS):
            path.write_text(json.dumps(rename(json.loads(text)), ensure_ascii=False, indent=2), encoding='utf-8')
    for path in out.glob('*.md'):
        text = path.read_text(encoding='utf-8')
        for old, new in list(LABELS.items())[:2]:
            text = text.replace(old, new)
        path.write_text(text, encoding='utf-8')
    summary_path = out / 'review_screen_summary.json'
    summary = json.loads(summary_path.read_text(encoding='utf-8'))
    summary.update(master_sha256_after=hashlib.sha256(master.read_bytes()).hexdigest(),
                   terminology_migration={'labels': LABELS, 'backup': str(backup)})
    summary_path.write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print('Label changes complete; classifications and other values preserved.', flush=True)


if __name__ == '__main__':
    main()
