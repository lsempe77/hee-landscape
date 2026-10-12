"""Retrieve public Europe PMC metadata/full text for ambiguous review ownership."""
import concurrent.futures
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / 'data/raw/review_screening'
CACHE = OUT / 'public_fulltext_cache'


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'HEE-review-classification/1.0'}), timeout=35) as response:
        return response.read()


def fetch(row):
    path = CACHE / (row['record_id'] + '.json')
    if path.exists():
        return json.loads(path.read_text(encoding='utf-8'))
    doi = row['doi'].replace('https://doi.org/', '').strip()
    if doi.lower() in ('na', 'nan', 'none', ''):
        doi = ''
    query = 'DOI:"' + doi + '"' if doi else 'TITLE:"' + re.sub(r'[^\w\s-]', ' ', row['title']) + '"'
    url = 'https://www.ebi.ac.uk/europepmc/webservices/rest/search?' + urllib.parse.urlencode({'query': query, 'format': 'json', 'resultType': 'core', 'pageSize': 2})
    result = {'record_id': row['record_id'], 'title': row['title'], 'query_url': url}
    try:
        data = json.loads(get(url))
        matches = data.get('resultList', {}).get('result', [])
        if not matches:
            result['status'] = 'No indexed match'
        else:
            paper = matches[0]
            if doi and paper.get('doi', '').lower() != doi.lower():
                result['status'] = 'DOI mismatch'
            else:
                result['metadata'] = paper
                pmcid = paper.get('pmcid')
                if pmcid:
                    full_url = 'https://www.ebi.ac.uk/europepmc/webservices/rest/' + pmcid + '/fullTextXML'
                    result['source'] = 'https://pmc.ncbi.nlm.nih.gov/articles/' + pmcid + '/'
                    try:
                        xml = get(full_url)
                        document = ET.fromstring(xml)
                        body = document.find('body')
                        if body is not None:
                            # Paragraphs retain their containing section titles for ownership checks.
                            snippets = []
                            for section in body.findall('.//sec'):
                                heading = section.find('title')
                                heading_text = ''.join(heading.itertext()) if heading is not None else ''
                                for paragraph in section.findall('p'):
                                    snippets.append({'section': heading_text, 'text': ''.join(paragraph.itertext())})
                            result['paragraphs'] = snippets
                            result['status'] = 'Full text available'
                        else:
                            result['status'] = 'XML has no article body'
                    except Exception as error:
                        result['status'] = 'Full text unavailable: ' + str(error)
                else:
                    result['status'] = 'Metadata only'
    except Exception as error:
        result['status'] = 'Retrieval failed: ' + str(error)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


def main():
    CACHE.mkdir(exist_ok=True)
    rows = json.loads((OUT / 'unclear_resolution_remaining.json').read_text(encoding='utf-8'))
    selected = [r for r in rows if re.search(r'systematic.{0,25}review', r['abstract'], re.I)]
    counts = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for i, result in enumerate(pool.map(fetch, selected), 1):
            counts[result['status']] = counts.get(result['status'], 0) + 1
            if i % 25 == 0:
                print(f'{i}/{len(selected)} retrieved: {counts}', flush=True)
    print(counts, flush=True)


if __name__ == '__main__':
    main()
