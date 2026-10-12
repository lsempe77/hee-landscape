"""Evidence-based second pass over unresolved review screens; prepare before apply."""
import argparse
import csv
import hashlib
import json
import os
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import screen_reviews_with_abstracts as screen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/raw/review_screening'
METHOD = 'unclear-review-resolution-v1-user-explicit-label-policy'


def match(pattern, text):
    return re.search(pattern, text, re.I)


def propose(row):
    title = screen.clean(row['title'])
    abstract = screen.clean(row['abstract'])
    parts = screen.sentences(abstract)
    methods = [s for s in parts if match(r'method|design|model|cohort|retrospective|randomi[sz]|patients|participants|cost.utility|cost.effectiveness', s)]
    review_parts = [s for s in parts if screen.REVIEW.search(s) or screen.SEARCH.search(s)]
    # Identify syntheses, not clinical/administrative reviews or another group's work.
    third_party = r'\b(?:company|manufacturer|sponsor|previous|prior|earlier|published study|published review|recent review|existing review)\b'
    service = r'\b(?:medications?|medicines?|prescriptions?|drug utili[sz]ation|life|inhaler|peer)[ -]reviews?\b|\breview.*\b(?:charts|medical records|electronic medical records|patient records|case notes)\b|\b(?:retrospective|database|chart|medical record|single.institution|single.centre|single.center)[ -]reviews?\b'
    synthesis = r'\b(?:systematic(?:\s+(?:literature|evidence|economic))?\s+reviews?|(?:narrative|scoping|rapid|umbrella|comprehensive|structured|critical|comparative|integrated|pharmacoeconomic)(?:\s+literature)?\s+reviews?|literature reviews?|review of (?:the )?(?:current )?(?:literature|published|studies|evidence)|meta[ -]?analys(?:is|es))\b'
    action = r'\b(?:conduct(?:ed|ing)?|perform(?:ed|ing)?|undert(?:ook|aken|ake)|carried out|reviewed|searched|updated|synthesi[sz]ed)\b'
    systematic = r'\bsystematic(?:\s+(?:literature|evidence|economic))?\s+reviews?\b'
    own = []
    for sentence in parts:
        if not match(synthesis, sentence) or match(service, sentence):
            continue
        if match(third_party, sentence) and not match(r'\b(?:we|our|authors|researchers|EAC)\b.*' + action, sentence):
            continue
        if match(r'\b(?:retrieve|retrieved|retrieving|included|collect|collected|search for|searched for)\b.{0,80}' + systematic, sentence) and not match(systematic + r'.{0,60}\b(?:was|were|has been)\s+(?:conducted|performed|undertaken)', sentence):
            continue
        if match(action + r'\s+(?:(?:a|an|the|two|three|four|five|seven|our|own|extensive|comprehensive|detailed|structured|updated|rapid|systematic|literature|evidence|economic|network)\s+){0,6}' + synthesis, sentence) or match(synthesis + r'.{0,220}\b(?:was|were|has been|have been|is)\s+(?:conducted|performed|undertaken|chosen|carried out)', sentence) or match(r'^(?:methods|design)\s*:?\s*(?:this is |a |we used |we undertook )?' + synthesis, sentence) or match(r'\b(?:design|methods)\b.{0,90}\b(?:programme|work packages|study designs|qualitative studies|secondary analyses|quantitative studies|cohort|objective)\b.*' + systematic, sentence) or match(r'\b(?:this|our|present)\s+(?:systematic|narrative|scoping|literature|rapid|umbrella)?\s*review\b', sentence) or match(r'\b(?:as part of this analysis|investigative method|systematic review methodology|first was a systematic review|aim.*systematically review|level of evidence.*systematic review)\b', sentence):
            own.append(sentence)
    primary = [s for s in methods if match(
        r'\b(?:markov|decision.analytic|decision.analysis|decision.tree|microsimulation|partitioned.survival|cost.effectiveness|cost.utility)\b.{0,100}\b(?:model|analysis|developed|constructed|built|designed|performed|conducted|simulat|used)\w*\b'
        r'|\b(?:model|simulation)\b.{0,100}\b(?:developed|constructed|built|designed|created|simulat|populated)\w*\b'
        r'|\b(?:retrospective|prospective|cross.sectional|trial.based|within.trial|randomi[sz]ed controlled trial)\b.{0,80}\b(?:study|analysis|evaluation|review|patients|participants)\b'
        r'|\b(?:we|authors|researchers)\b.{0,70}\b(?:enrolled|recruited|randomi[sz]ed)\b'
        r'|\b(?:decision[ -]tree|economic|financial|mathematical|diabetes|population|cost.avoidance)\s*(?:model)?\b.{0,90}\b(?:created|formulated|developed|designed|used|estimated|compared)\b'
        r'|\b(?:model|modelling|modeling|microsimulation|simulation|within.trial|trial.based)\b.{0,100}\b(?:cost|economic|QALY|cost.effectiveness)\b', s)
        and not match(r'\b(?:included studies|studies included|studies were|studies that|published studies|previous studies|company|manufacturer|sponsor)\b', s)]
    original = 'Yes' if primary else 'Original evaluation not identified'

    def decision(kind, subtype, reason, evidence, rule, confidence='Moderate'):
        result = screen.result(kind, subtype, confidence, reason, ' | '.join(evidence)[:1800])
        result.update(review_has_original_evaluation=original,
                      review_mixed_primary_analysis='TRUE' if original == 'Yes' and kind in ('Systematic review', 'Review (non-systematic)') else 'FALSE',
                      review_component='Own review plus original evaluation' if original == 'Yes' and kind in ('Systematic review', 'Review (non-systematic)') else '',
                      resolution_source='Uploaded full abstract',
                      review_screen_method=METHOD, resolution_rule=rule)
        return result

    if 'cochrane database of systematic reviews' in row.get('journal', '').lower() and match(r'\b(?:main results|data collection and analysis)\b', abstract):
        return decision('Systematic review', 'Completed Cochrane systematic review', 'The record is a completed Cochrane review with reported study selection, synthesis and results; Cochrane identifies these as systematic reviews.', review_parts[:3], 'completed-cochrane-review')

    if not match(systematic, abstract) and match(r'\b(?:in this review|this is a narrative review|purpose of review|study design:? review|design:? narrative review|review article|a literature review is presented|literature review.*has been deployed|literature was also reviewed|review of the current literature|areas covered in this review)\b', abstract):
        return decision('Review (non-systematic)', 'Narrative/literature review', 'The abstract identifies this work as a review of research literature without an explicit systematic-review label.', review_parts[:3], 'self-described-other-review')

    own_sr = [s for s in own if match(systematic, re.sub(r'Cochrane Database of Systematic Reviews', '', s, flags=re.I)) and not match(r'\b(?:recent|published study|published systematic|derived from|using data from|reviews were used|review were used)\b', s)]
    if match(systematic, title) and not screen.TITLE_INPUT.search(title):
        return decision('Systematic review', 'Explicit systematic-review title', 'The title identifies this paper as a systematic review.', [title] + primary[:1], 'own-sr-title')
    own_sr = [s for s in own_sr if not match(r'\b(?:informed by|incorporating data|combining cost)\b', s) or match(r'\b(?:we|authors|researchers|EAC)\b.*' + action, s)]
    if match(r'\bscoping review of systematic reviews\b', abstract):
        return decision('Review (non-systematic)', 'Scoping review of existing systematic reviews', 'The own synthesis is a scoping review; systematic describes the included reviews, not the own review.', review_parts[:2], 'scoping-of-reviews')
    if own_sr:
        return decision('Systematic review', 'Own systematic review - explicit methods', 'The abstract explicitly describes a systematic review conducted within this work.', own_sr[:2] + primary[:1], 'own-sr-methods')
    own_non = [s for s in own if not match(systematic, s)]
    if own_non:
        return decision('Review (non-systematic)', 'Own synthesis without explicit systematic label', 'The abstract describes conducting a literature review or meta-analysis without an explicit systematic-review self-description.', own_non[:2] + primary[:1], 'own-other-methods')
    if screen.APPRAISAL.search(title) or match(r'pharmacoeconomic review report|reimbursement review', title):
        own_search = [s for s in parts if match(r'\b(?:ERG|EAC|review group|assessment group|CADTH|CDA.AMC)\b.{0,100}\b(?:independently searched|conducted.*search|searched for relevant|performed.*search|additional literature search)\b', s)]
        own_economic = [s for s in parts if match(r'\b(?:ERG|EAC|review group|assessment group|CADTH|CDA.AMC)\b.{0,120}\b(?:adjusted|modified|recalculated|revised|revisions|undertook.*analys|conducted.*analys|scenario analyses|sensitivity analys|base.case|developed.*model|changes.*model|re.analysis|reanalys)\w*\b', s) and not match(r'\b(?:requested|could not|unable to|could not be|at the ERG.s request)\b', s)]
        original = 'Yes' if own_economic else 'Original evaluation not identified'
        if own_search:
            return decision('Review (non-systematic)', 'Own supplementary evidence search in technology appraisal', 'The independent assessment group conducted its own supplementary evidence search; this own synthesis is not explicitly described as a systematic review.', own_search[:2] + own_economic[:1], 'appraisal-own-search')
        appraisal = [s for s in parts if match(r'\b(?:submission|manufacturer|sponsor|ERG|review group|CDA.AMC|CADTH)\b', s)]
        return decision('Not identified as a review', 'Technology appraisal of submitted evidence; own synthesis not identified', 'This report appraises submitted evidence. The abstract does not establish a literature synthesis conducted by the report authors; company reviews and organisation names are not counted as an own review.', appraisal[:2] + own_economic[:1], 'appraisal-submission-review')
    search = [s for s in parts if screen.SEARCH.search(s) and screen.DATABASE.search(s) and not match(third_party, s)]
    selection = [s for s in parts if screen.SELECTION.search(s)]
    if match(r'rapid health technology assessment', title) and match(r'\b(?:databases?|websites?)\b.{0,150}\bsearched\b|\bsearched\b.{0,150}\b(?:databases?|websites?)\b', abstract) and match(r'\bincluded\b', abstract):
        original = 'Original evaluation not identified'
        return decision('Review (non-systematic)', 'Rapid evidence synthesis without own systematic label', 'This rapid HTA searches and synthesises existing reviews/economic studies. Included systematic reviews are inputs, not an explicit systematic label for this own synthesis.', review_parts[:3], 'rapid-hta-synthesis')
    if search and selection:
        return decision('Review (non-systematic)', 'Literature synthesis - no explicit systematic label', 'This work reports searching and selecting studies; systematic searching alone does not meet the agreed explicit systematic-review label.', search[:1] + selection[:2], 'search-selection')
    if match(service, title) or any(match(service, s) for s in parts):
        # A simultaneous genuine synthesis must already have passed the own-review tests.
        if not any(match(systematic, s) for s in parts):
            evidence = [s for s in parts if match(service, s)]
            return decision('Not identified as a review', 'Clinical service or patient-record review', 'Review refers to a clinical service, patient records or an administrative process, not a synthesis of research studies.', [title] + evidence[:2], 'clinical-record-review')
    if match(r'\breview\b|\bmeta.analys', title) and not match(service, title) and not screen.APPRAISAL.search(title):
        if match(r'pharmacoeconomic review report|reimbursement review', title):
            return None
        return decision('Review (non-systematic)', 'Review - no explicit systematic label', 'The title identifies a review and the abstract does not explicitly identify an own systematic review.', [title] + review_parts[:2], 'other-review-title')
    if any(match(systematic, s) for s in parts):
        # Passive "derived from a systematic review" alone cannot establish who did it.
        external = [s for s in parts if match(systematic, s) and match(r'\b(?:previous|prior|earlier|published|existing|recent|cochrane)\b|guideline|company|manufacturer|sponsor', s)]
        if external and len(external) == len([s for s in parts if match(systematic, s)]):
            return decision('Not identified as a review', 'Existing review cited or used as input', 'The systematic review is explicitly attributed to earlier/published work or an external submission rather than conducted by this paper.', external[:2] + primary[:1], 'external-review')
        return None
    if primary and not screen.APPRAISAL.search(title):
        return decision('Not identified as a review', 'Original evaluation; no own synthesis established', 'The abstract reports original evaluation methods but does not describe conducting a literature synthesis; review-related wording concerns inputs or background.', primary[:2] + review_parts[:1], 'primary-no-own-review')
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    master = ROOT / 'data/raw/hee_analysis_master_v2.csv'
    csv.field_size_limit(10_000_000)
    before_hash = hashlib.sha256(master.read_bytes()).hexdigest()
    with master.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        fields, rows = list(reader.fieldnames), list(reader)
    unclear = [r for r in rows if r['review_type'] == 'Unclear - manual check needed']
    overrides_path = OUT / 'unclear_resolution_overrides.json'
    overrides = json.loads(overrides_path.read_text(encoding='utf-8')) if overrides_path.exists() else {}
    decisions = {}
    unresolved = []
    for row in unclear:
        result = propose(row)
        if row['record_id'] in overrides:
            override = overrides[row['record_id']]
            result = screen.result(override['review_type'], override['review_subtype'], 'Moderate', override['reason'], override['evidence'])
            result.update(review_has_original_evaluation=override['original_evaluation'],
                          review_mixed_primary_analysis='TRUE' if override['original_evaluation'] == 'Yes' and override['review_type'] in ('Systematic review', 'Review (non-systematic)') else 'FALSE',
                          review_component=override.get('component', ''), review_screen_method=METHOD,
                          resolution_rule='record-specific-assessment', resolution_source=override.get('source', 'Uploaded full abstract'))
        if result:
            decisions[row['record_id']] = result
        else:
            unresolved.append(row)
    (OUT / 'unclear_resolution_proposals.json').write_text(json.dumps(decisions, ensure_ascii=False, indent=2), encoding='utf-8')
    (OUT / 'unclear_resolution_remaining.json').write_text(json.dumps(unresolved, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'assessed': len(unclear), 'proposed': len(decisions), 'remaining': len(unresolved),
                      'categories': dict(Counter(r['review_type'] for r in decisions.values())),
                      'rules': dict(Counter(r['resolution_rule'] for r in decisions.values()))}, indent=2))
    if not args.apply:
        return
    if not decisions:
        print('No new decisions to apply.')
        return
    timestamp = datetime.now(timezone.utc).isoformat(timespec='seconds')
    originals = [dict(r) for r in rows]
    allowed = set(next(iter(decisions.values()))) & set(fields)
    allowed.add('review_screened_at')
    changes = []
    for row in rows:
        result = decisions.get(row['record_id'])
        if result:
            changes.append({'record_id': row['record_id'], 'title': row['title'], 'previous_review_type': row['review_type'], **result})
            row.update({k: v for k, v in result.items() if k in fields})
            row['review_screened_at'] = timestamp
    staging = master.with_suffix('.resolution.tmp')
    with staging.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    with staging.open(encoding='utf-8', newline='') as handle:
        checked = list(csv.DictReader(handle))
    assert len(checked) == len(originals)
    for before, after in zip(originals, checked):
        assert all(before[k] == after[k] for k in fields if k not in allowed)
        if before['record_id'] not in decisions:
            assert before == after
    assert hashlib.sha256(master.read_bytes()).hexdigest() == before_hash
    backup = OUT / 'backups' / ('hee_analysis_master_v2_before_unclear_resolution_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.csv')
    shutil.copy2(master, backup)
    assert hashlib.sha256(backup.read_bytes()).hexdigest() == before_hash
    os.replace(staging, master)
    persistent_path = OUT / 'review_resolution_applied.json'
    persistent = json.loads(persistent_path.read_text(encoding='utf-8')) if persistent_path.exists() else {}
    for row in unclear:
        rid = row['record_id']
        if rid in decisions:
            persistent[rid] = {'title_abstract_sha256': hashlib.sha256((row['title'] + '\n' + row['abstract']).encode()).hexdigest(),
                               'classification': {k: v for k, v in decisions[rid].items() if k in fields},
                               'source': decisions[rid].get('resolution_source', 'Uploaded full abstract'), 'rule': decisions[rid]['resolution_rule']}
    persistent_path.write_text(json.dumps(persistent, ensure_ascii=False, indent=2), encoding='utf-8')
    remaining_fields = ['record_id', 'title', 'doi', 'url', 'abstract', 'review_type', 'review_subtype', 'evidence_needed', 'public_source_status']
    with (OUT / 'remaining_review_checks.csv').open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=remaining_fields)
        writer.writeheader()
        for row in unresolved:
            cache_path = OUT / 'public_fulltext_cache' / (row['record_id'] + '.json')
            cached = json.loads(cache_path.read_text(encoding='utf-8')) if cache_path.exists() else {}
            writer.writerow({**{k: row.get(k, '') for k in remaining_fields},
                             'evidence_needed': 'Methods/full text establishing whether this record conducts a new review or only uses an existing review; if own, its explicit design label.',
                             'public_source_status': cached.get('status', 'No public full text retrieved')})
    audit_fields = list(dict.fromkeys(k for change in changes for k in change))
    with (OUT / 'unclear_resolution_decisions.csv').open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=audit_fields)
        writer.writeheader()
        writer.writerows(changes)
    results_path = OUT / 'review_screen_results.json'
    results = json.loads(results_path.read_text(encoding='utf-8'))
    for rid, result in decisions.items():
        results[rid].update({k: v for k, v in result.items() if k in fields})
    results_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    queue = OUT / 'review_screening_queue.csv'
    with queue.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        qfields, queued = list(reader.fieldnames), list(reader)
    for row in queued:
        if row['record_id'] in decisions:
            row.update({k: v for k, v in decisions[row['record_id']].items() if k in qfields})
            row['review_screened_at'] = timestamp
            row['manual_check_priority'] = {'Systematic review': '5', 'Review (non-systematic)': '6', 'Not identified as a review': '7', 'Review protocol': '4'}[row['review_type']]
    with queue.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=qfields)
        writer.writeheader()
        writer.writerows(queued)
    summary_path = OUT / 'review_screen_summary.json'
    summary = json.loads(summary_path.read_text(encoding='utf-8'))
    summary.update(review_type_counts=dict(Counter(r['review_type'] for r in rows if r['is_eligible'] == 'TRUE')),
                   confidence_counts=dict(Counter(r['review_screen_confidence'] for r in rows if r['is_eligible'] == 'TRUE')),
                   master_sha256_after=hashlib.sha256(master.read_bytes()).hexdigest(),
                   unclear_resolution={'assessed': len(unclear), 'resolved': len(decisions), 'remaining': len(unresolved), 'backup': str(backup), 'timestamp': timestamp, 'method': METHOD})
    summary_path.write_text(json.dumps(summary, indent=2), encoding='utf-8')
    notes = ['# Resolution of ambiguous review classifications', '',
             f'Assessed {len(unclear):,} previously unclear included records; resolved {len(decisions):,}; {len(unresolved):,} remain awaiting methods evidence.', '',
             'Classification uses the agreed own-review rule. Existing reviews used as inputs are not counted as an own SR. Scoping/rapid/umbrella and other syntheses without explicit systematic self-description are Review (non-systematic). Indexing publication-type labels alone do not establish own-review authorship.', '',
             'These are agent evidence assessments, not independent human verification. Not identified as a review means an own synthesis was not established, not proof of absence. Original evaluation not identified in the original-evaluation column does not establish absence.', '',
             'unclear_resolution_decisions.csv contains decisions, reasons, evidence and source URLs. remaining_review_checks.csv provides the outstanding records and evidence needed. review_resolution_applied.json preserves decisions with title/abstract hashes for future screening runs.', '',
             f'Backup: {backup.name}. All IDs, row order, full abstracts, eligibility and other analysis fields were checked unchanged.', '',
             '## Resolved classifications', '']
    notes += [f'- {kind}: {count:,}' for kind, count in Counter(r['review_type'] for r in decisions.values()).items()]
    (OUT / 'unclear_resolution_report.md').write_text('\n'.join(notes) + '\n', encoding='utf-8')
    print('Applied and validated; backup: ' + str(backup))


if __name__ == '__main__':
    main()
