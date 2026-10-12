"""Persist full-report assessments for the 22 outstanding audit records; no master edits."""
import csv
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/raw/review_screening'
NON_SR = 'Review (non-systematic)'
NO_REVIEW = 'Not identified as a review'
NOT_ORIGINAL = 'Original evaluation not identified'

# Record ID, public report document, own synthesis, independently produced evaluation, rationale.
DECISIONS = [
    ('131823666',2035701,False,True,'Methods describe appraisal of the submitted clinical evidence and independent changes to the economic model. No own literature synthesis is identified in the published methods.'),
    ('131860926',2035706,True,True,'Methods explicitly report rerunning and extending searches and rerunning the economic model to correct problems. The systematic review being appraised is the manufacturer’s review.'),
    ('131860928',2035704,True,True,'Methods report own clinical/economic searches and additional economic analyses; results describe rerunning the model with lower utility gains and daily treatment.'),
    ('131861071',2035702,True,True,'Methods explicitly identify independent searches and further clinical and economic sensitivity analyses by the ERG.'),
    ('131861153',2035703,False,True,'Methods describe appraisal of the company’s searches and narrative synthesis, followed by the ERG’s revised base case and sensitivity analyses. An own literature synthesis is not identified.'),
    ('131861307',2035709,True,True,'Methods report an own search for ongoing trials, with independent trial appraisal and economic analyses using the York model.'),
    ('131861421',2035643,True,True,'The ERG reran and screened PubMed searches and corrected/reran the economic model. Systematic review refers to the manufacturer’s work.'),
    ('131861508',2035647,True,True,'Methods report replication of the amended search strategy and ERG model revisions; the results distinguish the company’s indirect comparison from independently revised model results.'),
    ('131861606',2035644,False,True,'Methods describe assessing the completeness of company searches and recalculating the economic base case. No own literature synthesis is identified in those methods.'),
    ('131861607',2035672,True,True,'Methods report rerunning modified RCT searches and independently running additional economic sensitivity analyses.'),
    ('131861630',2035679,False,True,'Methods describe assessing the company’s searches, systematic review and mixed treatment comparison; the ERG corrects and adjusts the economic model. No own literature synthesis is identified.'),
    ('131861637',2035642,True,True,'Methods explicitly report an independent broader search, own eligibility criteria and economic model re-analysis.'),
    ('131861664',2035645,True,True,'Methods explicitly report own searches and independent modifications of the manufacturer’s economic model.'),
    ('131861705',2035640,True,True,'Methods explicitly report rerunning/extending searches, identifying additional economic papers and rerunning the model with a shorter horizon and alternative assumptions.'),
    ('131861719',2035700,True,True,'Methods report an own search for ongoing trials. Results and Table 2 distinguish independent ERG economic scenarios and an alternative model from company results.'),
    ('131861723',2035674,True,True,'The full ERG report (document 2022544, section 4.1.1) explicitly states that the ERG undertook its own searches. The published summary reports corrected base-case results, survival re-analysis and own probabilistic sensitivity analysis.'),
    ('131861732',2035676,True,True,'Methods explicitly report repeated literature searches, a narrative critique and independently conducted economic sensitivity analyses.'),
    ('131861751',2035673,True,False,'Methods report own rerun searches with a trials filter. The economic model was rerun to check wiring/parameterisation errors; independently produced new economic estimates are not identified in this publication. Validation alone does not establish original evaluation.'),
    ('131861764',2035648,True,True,'Methods report repeated literature searches and correction of model errors by the ERG for the base case.'),
    ('131861768',2035670,True,True,'The ERG independently pools trial control-arm outcomes and analyses heterogeneity, providing an own synthesis even without a new search. Independent economic re-analysis is identified in the abstract and methods.'),
]

def main():
    records = {r['record_id']: r for r in json.loads((OUT/'evidence_basis_93_records.json').read_text(encoding='utf-8'))}
    decisions = {}
    for rid, doc, own_review, original, reason in DECISIONS:
        text = (OUT/f'report22_cache/{doc}.txt').read_text(encoding='utf-8')
        match = re.search(r'10\.3310/hta\d+suppl\d[/\-]\d+', text)
        assert match and match.group().replace('-','/') == records[rid]['doi'].replace('-','/'), rid
        decisions[rid] = dict(recommended_review_type=NON_SR if own_review else NO_REVIEW,
            recommended_original_evaluation='Yes' if original else NOT_ORIGINAL,
            recommended_design_basis='Literature/registry synthesis',
            review_decision_resolved='Yes', assessment_status='Resolved from full published methods/report',
            assessment_reason=reason, assessment_source=f'https://njl-admin.nihr.ac.uk/document/download/{doc}',
            finding='Full-report follow-up of previously unresolved appraisal components')
    decisions['131861723']['assessment_source'] += ' | https://njl-admin.nihr.ac.uk/document/download/2022544'
    decisions['131967253'] = dict(recommended_review_type=NO_REVIEW,
        recommended_original_evaluation='Yes', recommended_design_basis='Literature/registry synthesis',
        review_decision_resolved='Yes', assessment_status='Resolved from full published methods/report',
        assessment_reason='The accepted manuscript and full TA386 report attribute the clinical and economic systematic reviews to the company. The ERG appraises those reviews and independently produces alternative economic base-case/scenario estimates. An own new literature synthesis is not identified.',
        assessment_source='https://eprints.whiterose.ac.uk/104728/ | https://www.nice.org.uk/guidance/TA386/documents/committee-papers-2',
        finding='Company SR distinguished from independent ERG economic re-analysis')
    decisions['132845895'] = dict(recommended_review_type=NON_SR,
        recommended_original_evaluation=NOT_ORIGINAL, recommended_design_basis='Literature/registry synthesis',
        review_decision_resolved='Yes', assessment_status='Resolved from full published methods/report',
        assessment_reason='This article summarises final contractual results reported by CMS evaluation contractors. Its additional post-hoc and end-of-life economic studies are separately cited publications (references 20 and 21). No new original economic evaluation is identified in this overview; reviewing these reported results is non-systematic synthesis.',
        assessment_source='https://journals.sagepub.com/doi/10.1089/pop.2010.0069 | https://www.researchgate.net/publication/50194309_Learning_From_Our_Mistakes',
        finding='Programme-result synthesis distinguished from separately published economic analyses')
    assert len(decisions)==22
    (OUT/'review_evidence_basis_22_resolutions.json').write_text(json.dumps(decisions,indent=2,ensure_ascii=False),encoding='utf-8')
    rows=[dict(record_id=rid,title=records[rid]['title'],**decision) for rid,decision in decisions.items()]
    with (OUT/'review_evidence_basis_22_resolutions.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    print(json.dumps({'resolved':len(rows),'review_types':dict(Counter(r['recommended_review_type'] for r in rows)),
        'original_evaluation':dict(Counter(r['recommended_original_evaluation'] for r in rows)),
        'master_changed':False},indent=2))

if __name__=='__main__': main()
