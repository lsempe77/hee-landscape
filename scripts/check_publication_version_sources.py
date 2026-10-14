"""Cache Crossref evidence for the title-match publication audit; no master edits."""
import concurrent.futures
import csv
import json
import time
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen, Request

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'exports/publication_version_check'
OUT.mkdir(exist_ok=True)
rows = list(csv.DictReader((ROOT / 'exports/potential_publication_versions_61_records.csv').open(encoding='utf-8-sig')))

def fetch(row):
    path = OUT / (row['record_id'] + '_crossref.json')
    if path.exists():
        return row['record_id'], 'cached'
    doi = row['doi']
    if doi in ('', 'NA'):
        return row['record_id'], 'no DOI'
    try:
        time.sleep(0.8)
        request = Request('https://api.crossref.org/works/' + quote(doi, safe=''), headers={'User-Agent': 'HEE-publication-audit/1.0'})
        with urlopen(request, timeout=25) as response:
            data = json.load(response)['message']
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        return row['record_id'], 'ok'
    except Exception as exc:
        return row['record_id'], str(exc)

if __name__ == '__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(fetch, rows))
    (OUT / 'fetch_status.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    from collections import Counter
    print(dict(Counter(status for _, status in results)))
