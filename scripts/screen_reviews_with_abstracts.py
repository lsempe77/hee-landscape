"""Join full abstracts and run an auditable, preliminary review-type screen.

Default: prepare JSON screening results without changing the master.
Use --apply to update the CSV master after validation, staging and a backup.
No eligibility decisions are changed. Labels require human verification.
"""

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import unicodedata
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data' / 'raw'
VERSION = 'title-abstract-rules-v3'
NS = {'x': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def rx(pattern):
    return re.compile(pattern, re.I)


SR = rx(r'\bsystematic(?:[ -]+(?:literature|evidence))?[ -]+reviews?\b')
META = rx(r'\b(?:network[ -]+)?meta[ -]?analys(?:is|es)\b')
NARRATIVE = rx(r'\b(?:narrative|non[ -]?systematic|unsystematic|traditional)[ -]+(?:literature[ -]+)?reviews?\b')
OTHER = rx(r'\b(?:scoping|umbrella|rapid|integrative|critical|realist|literature|evidence|mapping|state[ -]of[ -]the[ -]art)[ -]+reviews?\b|\breview of (?:the )?literature\b|\boverview of (?:systematic )?reviews\b')
REVIEW = rx(r'\breviews?\b|\bmeta[ -]?analys(?:is|es)\b|\bevidence synthesis\b')
SELF_REVIEW = rx(r'\b(?:we|this (?:study|paper|article|review))\b.{0,100}\b(?:conduct(?:ed|s)?|perform(?:ed|s)?|undert(?:ook|aken)|present(?:ed|s)?|provid(?:e|es|ed)|report(?:ed|s)?|aim(?:ed|s)?|is|was)\b.{0,90}\b(?:review|meta[ -]?analysis)\b|\b(?:systematic|narrative|scoping|literature|rapid|umbrella) review.{0,60}\b(?:was|were)\s+(?:conducted|performed|undertaken)\b')
SEARCH = rx(r'\b(?:search(?:ed|es|ing)?|retriev(?:ed|al)|screen(?:ed|ing))\b')
DATABASE = rx(r'\b(?:pubmed|medline|embase|cochrane|scopus|web of science|cinahl|econlit|electronic databases?|bibliographic databases?)\b')
SELECTION = rx(r'\b(?:inclusion criteria|eligibility criteria|eligible (?:studies|articles)|stud(?:y|ies) selection|stud(?:y|ies) were (?:included|selected)|(?:studies|articles|papers) (?:were )?(?:included|identified|selected)|included (?:studies|articles)|studies met (?:the )?(?:inclusion|eligibility) criteria)\b')
RIGOUR = rx(r'\b(?:prisma|prospero|risk of bias|quality assess(?:ed|ment)|two (?:independent )?reviewers|independently (?:screened|assessed|reviewed))\b')
INPUT_REVIEW = rx(r'\b(?:derived|obtained|sourced|taken|extracted|informed|based|using|from|through)\b.{0,75}\b(?:systematic|literature|published|previous|existing|cochrane) reviews?\b|\b(?:systematic|literature) review.{0,70}\b(?:inform|parameter|input|populate)\w*\b')
PRIMARY = rx(r'\bwe\s+(?:developed|constructed|built|adapted|used|conducted|performed)\b.{0,100}\b(?:markov|microsimulation|decision[ -]analytic|decision[ -]tree|simulation|cost[ -]effectiveness|cost[ -]utility)\b|\b(?:markov|decision[ -]analytic|decision[ -]tree|microsimulation|simulation)\s+model\b.{0,90}\b(?:was|is)\s+(?:developed|constructed|built|used|adapted)\b|\b(?:we|this study)\b.{0,70}\b(?:randomized|randomised|recruited|enrolled)\b|\b(?:trial[ -]based economic evaluation|economic evaluation alongside|economic evaluation (?:was )?conducted alongside)\b')
PRIMARY_TITLE = rx(r'\b(?:model[ -]based|trial[ -]based|markov|microsimulation|decision[ -]analytic|decision[ -]tree|randomi[sz]ed (?:controlled )?trial|retrospective cohort|prospective cohort)\b')
CHART_REVIEW = rx(r'\b(?:chart|medical records?|patient records?|case notes?|retrospective (?:chart|record))[ -]+reviews?\b|\breview(?:ed|ing)? (?:of )?(?:medical|patient|hospital) records\b')
PROTOCOL = rx(r'\b(?:protocol for (?:a |an |the )?(?:systematic|scoping|umbrella|rapid|literature|evidence) review|(?:systematic|scoping|umbrella|rapid|literature|evidence) review\s*(?::|[-])?\s*(?:study )?protocol)\b')
FUTURE = rx(r'\bwe will (?:conduct|perform|undertake).{0,30}\b(?:systematic|scoping|rapid|literature) review\b')
OWN_SR = rx(r'\b(?:this|our|present) systematic(?: literature)? review\b|\bwe systematically reviewed\b|\b(?:methods?|design):\s*(?:a )?systematic(?: literature)? review\b')
STRONG_PRIMARY = rx(r'\bwe\s+(?:developed|constructed|built|adapted)\b.{0,90}\b(?:model|simulation)\b|\b(?:markov|decision[ -]analytic|decision[ -]tree|microsimulation|simulation)\s+model\b.{0,90}\b(?:was|is)\s+(?:developed|constructed|built|used|adapted)\b|\bwe\s+(?:randomi[sz]ed|recruited|enrolled)\b|\b(?:trial[ -]based economic evaluation|economic evaluation alongside|economic evaluation (?:was )?conducted alongside)\b')
OWN_COHORT = rx(r'\bwe (?:conducted|performed|undertook).{0,25}\b(?:retrospective|prospective|cross[ -]sectional|cohort|case[ -]control)\b.{0,30}\b(?:study|analysis)\b|\bin this (?:cross[ -]sectional|cohort|case[ -]control|retrospective|prospective) study\b')
APPRAISAL = rx(r'\bevidence review group\b|\bsingle technology appraisal\b')


def clean(text):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', text).replace('–', '-').replace('—', '-')).strip()


def sentences(text):
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+|\b(?:BACKGROUND|OBJECTIVES?|AIMS?|METHODS?|RESULTS?|CONCLUSIONS?|PURPOSE|DESIGN):\s*', clean(text)) if s.strip()]


def result(kind, subtype, confidence, reason, evidence, component='', mixed=False):
    return {
        'review_type': kind,
        'review_subtype': subtype,
        'review_screen_confidence': confidence,
        'review_screen_reason': reason,
        'review_screen_evidence': evidence[:1800],
        'review_component': component,
        'review_mixed_primary_analysis': 'TRUE' if mixed else 'FALSE',
        'review_verification_status': 'Provisional - title/abstract screen; not human verified',
        'review_screen_method': VERSION,
    }


def classify(title, abstract):
    title, abstract = clean(title), clean(abstract)
    parts = sentences(abstract)
    own = [s for s in parts if SELF_REVIEW.search(s)]
    primary = [s for s in parts if STRONG_PRIMARY.search(s) or OWN_COHORT.search(s) or (PRIMARY.search(s) and not REVIEW.search(s) and not rx(r'\b(?:randomi[sz]ed|controlled) (?:trials?|studies)\b').search(s))]
    systematic = [s for s in parts if (s in own and SR.search(s)) or OWN_SR.search(s)]
    narrative = [s for s in own if NARRATIVE.search(s)]
    other = [s for s in own if OTHER.search(s)]
    search = [s for s in parts if SEARCH.search(s) and DATABASE.search(s)]
    selected = [s for s in parts if SELECTION.search(s)]
    has_methods = bool(search and selected)
    title_review = bool(SR.search(title) or NARRATIVE.search(title) or OTHER.search(title) or META.search(title))
    primary_signal = bool(primary or (PRIMARY_TITLE.search(title) and not title_review) or
                          (title_review and rx(r'\b(?:and|plus|with) (?:a |an )?(?:model[ -]based|trial[ -]based|economic evaluation|cost[ -]effectiveness analysis|original (?:analysis|evaluation))\b').search(title)))
    excerpt = lambda ss: ' | '.join(ss[:3])
    if (PROTOCOL.search(title) and title_review) or (FUTURE.search(abstract) and (title_review or systematic) and not selected):
        return result('Review protocol', 'Systematic review protocol' if SR.search(title + ' ' + abstract) else 'Other review protocol',
                      'High' if PROTOCOL.search(title) else 'Moderate', 'A planned review, not a completed evidence synthesis.', title + ' | ' + excerpt(own))
    if title_review and primary_signal:
        return result('Mixed review and original evaluation', 'Systematic review component' if SR.search(title) or systematic else 'Other review component',
                      'Moderate', 'Review label and original model/trial methods both present; check the paper before excluding it as secondary evidence.',
                      title + ' | ' + excerpt(primary), 'Review plus original analysis', True)
    if SR.search(title):
        return result('Systematic review', 'Systematic review with meta-analysis' if META.search(title + ' ' + abstract) else 'Systematic review',
                      'High', 'The title explicitly identifies this paper as a systematic review.', title + ' | ' + excerpt(systematic or search))
    if NARRATIVE.search(title):
        return result('Non-systematic review', NARRATIVE.search(title).group(), 'High',
                      'The title explicitly identifies a narrative/non-systematic review.', title)
    if APPRAISAL.search(title):
        return result('Unclear - manual check needed', 'Technology appraisal / evidence review group', 'Low',
                      'Review refers to technology appraisal; check whether this report includes a completed research synthesis or an original evaluation.', title)
    if OTHER.search(title):
        subtype = OTHER.search(title).group()
        return result('Other review - methods need checking', subtype, 'High',
                      'A review subtype is named, but it should not automatically be called non-systematic.', title + ' | ' + excerpt(search))
    if systematic and primary_signal:
        if INPUT_REVIEW.search(abstract) and not title_review:
            return result('No review identified', 'Original evaluation using a review', 'Moderate',
                          'Original evaluation methods are reported; the review appears to supply model inputs rather than define the paper.',
                          excerpt(primary + systematic), 'Systematic review used as input')
        return result('Mixed review and original evaluation', 'Systematic review component', 'Moderate',
                      'The abstract reports both conducting a systematic review and an original evaluation; verify their roles.',
                      excerpt(systematic + primary), 'Review plus original analysis', True)
    if systematic:
        return result('Systematic review', 'Systematic review with meta-analysis' if META.search(abstract) else 'Systematic review',
                      'High' if has_methods else 'Moderate', 'The abstract describes this paper conducting or presenting a systematic review.', excerpt(systematic + search))
    if narrative and not primary_signal:
        return result('Non-systematic review', NARRATIVE.search(excerpt(narrative)).group(), 'Moderate',
                      'The abstract describes this paper as a narrative/non-systematic review.', excerpt(narrative))
    if other and not primary_signal:
        return result('Other review - methods need checking', OTHER.search(excerpt(other)).group(), 'Moderate',
                      'The abstract identifies a review subtype; systematic status is not established.', excerpt(other + search))
    if has_methods and (RIGOUR.search(abstract) or rx(r'\bsystematic (?:literature )?(?:search|review)').search(abstract)) and not primary_signal and not CHART_REVIEW.search(title):
        return result('Systematic review', 'Inferred from review methods', 'Moderate',
                      'Database searching, study selection and a review-method signal are present; full-text verification is needed.', excerpt(search + selected))
    if META.search(title) or (has_methods and META.search(abstract) and not primary_signal):
        return result('Other review - methods need checking', 'Meta-analysis; systematic status unclear', 'Moderate',
                      'Meta-analysis is identified, but this alone does not establish systematic review methods.', title + ' | ' + excerpt(search + selected))
    if primary_signal and (SR.search(abstract) or OTHER.search(abstract)):
        return result('No review identified', 'Original evaluation mentioning/using a review', 'Moderate',
                      'Original evaluation methods are present; mentioning a review does not make this paper a review.', excerpt(primary), 'Review mentioned or used as input')
    if CHART_REVIEW.search(title):
        return result('No review identified', 'Original chart/record review', 'Moderate',
                      'Review refers to patient/chart records rather than a synthesis of research studies.', title)
    if REVIEW.search(title) or own or has_methods or SR.search(abstract) or NARRATIVE.search(abstract) or OTHER.search(abstract):
        return result('Unclear - manual check needed', 'Possible review or review mentioned', 'Low',
                      'Review-related wording is present, but this paper\'s role or review methods are unclear.', title + ' | ' + excerpt(own or search or [s for s in parts if REVIEW.search(s)]))
    return result('No review identified', '', 'Low',
                  'No qualifying review signal found in the title/abstract. This is not proof that the paper is primary research.', '')


def read_upload(path):
    records = []
    with zipfile.ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read('xl/workbook.xml'))
        sheets = workbook.find('x:sheets', NS)
        if len(sheets) != 1:
            raise ValueError('Expected exactly one uploaded worksheet.')
        relations = ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
        rid = sheets[0].attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']
        target = next(r.attrib['Target'] for r in relations if r.attrib['Id'] == rid)
        sheetpath = target.lstrip('/') if target.startswith('/') else 'xl/' + target
        strings = []
        if 'xl/sharedStrings.xml' in archive.namelist():
            with archive.open('xl/sharedStrings.xml') as handle:
                for _, element in ET.iterparse(handle, events=('end',)):
                    if element.tag == '{' + NS['x'] + '}si':
                        strings.append(''.join(t.text or '' for t in element.findall('.//x:t', NS)))
                        element.clear()
        with archive.open(sheetpath) as handle:
            headers = None
            for _, row in ET.iterparse(handle, events=('end',)):
                if row.tag != '{' + NS['x'] + '}row':
                    continue
                values = {}
                for cell in row.findall('x:c', NS):
                    column = re.sub(r'\d', '', cell.attrib['r'])
                    if cell.find('x:f', NS) is not None:
                        raise ValueError('Formula cells are not accepted as screening input.')
                    value = cell.findtext('x:v', default='', namespaces=NS)
                    if cell.attrib.get('t') == 'inlineStr':
                        value = ''.join(t.text or '' for t in cell.findall('.//x:t', NS))
                    elif cell.attrib.get('t') == 's':
                        value = strings[int(value)]
                    values[column] = value
                if headers is None:
                    headers = values
                    if not {'record_id', 'title', 'abstract'} <= set(headers.values()):
                        raise ValueError('Uploaded workbook needs record_id, title and abstract.')
                elif any(values.values()):
                    records.append({name: values.get(column, '') for column, name in headers.items()})
                row.clear()
    return records


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--master', type=Path, default=RAW / 'hee_analysis_master.csv')
    parser.add_argument('--upload', type=Path, default=RAW / 'hee_included_titles_abstracts_for_review_screening.xlsx')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--reuse-prepared', action='store_true', help='Use the audited JSON screen only when input hashes and method version still match.')
    args = parser.parse_args()
    csv.field_size_limit(10_000_000)
    source_hash, upload_hash = sha(args.master), sha(args.upload)
    with args.master.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        fields, master = list(reader.fieldnames), list(reader)
    if len(set(fields)) != len(fields) or not {'record_id', 'title', 'is_eligible'} <= set(fields) or any(None in r or any(v is None for v in r.values()) for r in master):
        raise ValueError('Missing/duplicate master columns or malformed CSV rows.')
    by_id = {r['record_id']: r for r in master}
    if len(by_id) != len(master):
        raise ValueError('Duplicate master IDs; refusing to join.')
    upload = read_upload(args.upload)
    included = {r['record_id'] for r in master if r['is_eligible'] == 'TRUE'}
    if len({r['record_id'] for r in upload}) != len(upload) or {r['record_id'] for r in upload} != included:
        raise ValueError('Uploaded IDs must match the complete eligible master exactly, without duplicates.')
    screened = {}
    out = args.master.parent / 'review_screening'
    if args.reuse_prepared:
        prior = json.loads((out / 'review_screen_summary.json').read_text(encoding='utf-8'))
        if prior['master_sha256_before'] != source_hash or prior['upload_sha256'] != upload_hash or prior['method'] != VERSION:
            raise ValueError('Prepared results are stale; rerun the screening.')
        screened = json.loads((out / 'review_screen_results.json').read_text(encoding='utf-8'))
        if set(screened) != included:
            raise ValueError('Prepared result IDs do not match the eligible master.')
    for r in upload:
        old = by_id[r['record_id']]
        if clean(r['title']) != clean(old['title']) or not r['abstract'].strip():
            raise ValueError(f"Title mismatch or empty abstract: {r['record_id']}")
        if not args.reuse_prepared:
            screened[r['record_id']] = classify(r['title'], r['abstract'])
    new_fields = ['abstract', 'abstract_source'] + list(next(iter(screened.values())))
    new_fields += ['review_type_human_verified', 'review_screened_at']
    timestamp = datetime.now(timezone.utc).isoformat(timespec='seconds')
    out.mkdir(exist_ok=True)
    (out / 'review_screen_results.json').write_text(json.dumps(screened, ensure_ascii=False, indent=2), encoding='utf-8')
    summary = {'method': VERSION, 'screened_at': timestamp, 'master_sha256_before': source_hash,
               'upload_sha256': upload_hash, 'master_rows': len(master), 'matched_included_records': len(upload),
               'not_screened_records': len(master)-len(upload), 'review_type_counts': dict(Counter(r['review_type'] for r in screened.values())),
               'confidence_counts': dict(Counter(r['review_screen_confidence'] for r in screened.values())),
               'all_labels_provisional': True, 'master_updated': False}
    if args.apply:
        if sha(args.master) != source_hash or sha(args.upload) != upload_hash:
            raise ValueError('An input changed during screening; refusing to overwrite.')
        final_fields = fields + [f for f in new_fields if f not in fields]
        upload_by_id = {r['record_id']: r for r in upload}
        with tempfile.NamedTemporaryFile(mode='w', newline='', encoding='utf-8', dir=args.master.parent, delete=False, suffix='.csv.tmp') as handle:
            staging = Path(handle.name)
            writer = csv.DictWriter(handle, fieldnames=final_fields)
            writer.writeheader()
            for old in master:
                row = dict(old)
                for f in new_fields:
                    row.setdefault(f, '')
                rid = old['record_id']
                if rid in screened:
                    row['abstract'] = upload_by_id[rid]['abstract']
                    row['abstract_source'] = args.upload.name
                    row.update(screened[rid])
                    row['review_screened_at'] = timestamp
                elif not row['review_type']:
                    row['review_type'] = 'Not screened - abstract not supplied'
                    row['review_verification_status'] = 'Not screened'
                writer.writerow(row)
        try:
            with staging.open(encoding='utf-8', newline='') as handle:
                output_rows = list(csv.DictReader(handle))
            if len(output_rows) != len(master):
                raise ValueError('Output row count changed.')
            for old, new in zip(master, output_rows):
                if any(old[f] != new[f] for f in fields if f not in new_fields):
                    raise ValueError('An existing analysis value changed.')
                if old['record_id'] in upload_by_id and new['abstract'] != upload_by_id[old['record_id']]['abstract']:
                    raise ValueError('A full abstract was not preserved exactly.')
            backups = out / 'backups'
            backups.mkdir(exist_ok=True)
            backup = backups / f"{args.master.stem}_before_abstract_review_screen_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}.csv"
            shutil.copy2(args.master, backup)
            if sha(backup) != source_hash or sha(args.master) != source_hash:
                raise ValueError('Backup or input verification failed.')
            os.replace(staging, args.master)
            summary.update(master_updated=True, backup=str(backup), master_sha256_after=sha(args.master))
        finally:
            staging.unlink(missing_ok=True)
    (out / 'review_screen_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    priority = {'Unclear - manual check needed': 1, 'Mixed review and original evaluation': 2,
                'Other review - methods need checking': 3, 'Review protocol': 4,
                'Systematic review': 5, 'Non-systematic review': 6}
    queue_fields = ['manual_check_priority', 'record_id', 'year', 'title', 'abstract', 'doi', 'url'] + new_fields[2:] + ['reviewer_notes']
    records = {r['record_id']: r for r in upload}
    queue = sorted((rid for rid, label in screened.items() if label['review_type'] in priority),
                   key=lambda rid: (priority[screened[rid]['review_type']], rid))
    with (out / 'review_screening_queue.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=queue_fields)
        writer.writeheader()
        for rid in queue:
            row = {key: records[rid].get(key, by_id[rid].get(key, '')) for key in queue_fields}
            row.update(screened[rid], manual_check_priority=priority[screened[rid]['review_type']], review_screened_at=timestamp)
            writer.writerow(row)
    notes = [
        '# Full abstracts and preliminary review screening', '',
        f"Matched {len(upload):,} included records by record_id and title. The master retains all {len(master):,} original rows.",
        f"Input: {args.upload.name}. Full uploaded abstract text is preserved exactly; no abstract text was inferred or shortened.",
        f"Method: {VERSION}. Screen run: {timestamp}.", '',
        '## Interpretation', '',
        'All review_type labels are provisional automated title/abstract screens, not verified study designs or eligibility decisions.',
        'Systematic review: explicit title/self-description, or review-method signals (database search, study selection and systematic/rigour wording).',
        'Non-systematic review: explicit narrative/non-systematic label. Missing methods alone is not grounds to call a review non-systematic.',
        'Other review: scoping, umbrella, rapid, literature or meta-analysis labels whose systematic status needs checking.',
        'Mixed review and original evaluation: review plus new model/trial/cohort signals. Do not automatically exclude these as secondary evidence.',
        'Unclear: possible review, technology appraisal, or ambiguous use of previously published reviews.',
        'No review identified: no qualifying signal, or an original evaluation that mentions/uses review inputs. This is not proof of primary-study status.',
        'Review protocol: planned review, not a completed synthesis. Treatment protocols and registered protocols in completed reviews are different.',
        'Not screened: the uploaded file contains included records only; other master rows have no supplied abstract and were not screened.', '',
        'Confidence describes the strength of rule-based text signals, not a calibrated probability. Every classification still needs human verification.',
        'Known limitations: indirect phrasing, incomplete reporting, translation and mixed studies can cause false positives/negatives. Check full text where needed.',
        'No manual independent double screening was performed. Economic-evaluation type, eligibility, funding and all other pre-existing analysis fields are unchanged.', '',
        '## Added columns', '',
        '`abstract`: full text from uploaded workbook; blank for records without supplied abstracts.',
        '`abstract_source`: uploaded workbook filename.',
        '`review_type`, `review_subtype`: proposed paper type and detailed subtype.',
        '`review_screen_confidence`, `review_screen_reason`, `review_screen_evidence`: strength, rationale and supporting title/abstract extracts.',
        '`review_component`, `review_mixed_primary_analysis`: distinguishes reviews used as inputs and hybrid papers.',
        '`review_verification_status`, `review_screen_method`, `review_screened_at`: screening provenance.',
        '`review_type_human_verified`: left blank for reviewer-confirmed final labels; preserved if already populated.', '',
        '## Counts among included records', '',
    ]
    notes += [f"- {label}: {count:,}" for label, count in summary['review_type_counts'].items()]
    notes += ['', '## Files and safeguards', '',
              'The master is written to a temporary file, read back, compared row-by-row, backed up, then atomically replaced.',
              'All pre-existing analysis fields, IDs, row order and eligibility values must match the original. All matched abstracts must match the upload exactly.',
              'review_screening_queue.csv includes flagged records, full abstracts, proposed labels and a blank final-label column for manual checking.',
              'review_screen_results.json and review_screen_summary.json retain the screen and input hashes.',
              f"Backup: {summary.get('backup', 'Not applied; master unchanged')}", '',
              '## Methodological references', '',
              'Cochrane Handbook, Chapter 1: https://training.cochrane.org/handbook/current/chapter-01',
              'JBI scoping review guidance: https://jbi-global.atlassian.net/wiki/spaces/MANUAL/pages/355862573/10.1.2+Scoping+reviews+compared+to+other+types+of+review',
              '', 'These references inform the distinctions; the automated screen is not a validated Cochrane/JBI screening tool.', '']
    (out / 'README.md').write_text('\n'.join(notes), encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
