"""Audit own-review ownership in the original 81 different-basis hybrid records.

Read-only for the master. This cohort is preserved from the original cross-check,
not recalculated after application of the separate 93-record audit.
"""
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/raw/review_screening'
NO_REVIEW = 'Not identified as a review'
NOT_ORIGINAL = 'Original evaluation not identified'

NO_OWN_REVIEW = {
    '131184555': 'Practice review refers to retrospective review of 305 children’s hospital files and original infection/cost analyses, not a research-literature review.',
    '131296984': 'Review describes a checklist used to produce and revise clinical care pathways. The reported HTA evaluates that checklist; no own literature synthesis is identified in the available abstract. Full article is access-restricted.',
    '131374209': 'Review of outcomes means a 10-year retrospective cohort of 39 own fracture patients, with original cost and functional-outcome comparisons.',
    '131936649': 'Review refers to evaluation of the hospital’s two-year MRSA screening programme. Full methods describe a retrospective case-control study and economic analysis, without own literature-synthesis methods.',
    '131952691': 'Pharmacist review of medication is the clinical intervention evaluated economically alongside a cluster RCT, not a literature review.',
    '131991410': 'Prospective Review of Early Cataract Outcomes and Grading (PRECOG) is the name of a prospective patient cohort; no own literature synthesis is identified.',
    '132026445': 'Post-arthroplasty review clinics are a patient follow-up service. This is a prospective observational evaluation of implementation at ten sites.',
    '132030309': 'Telephonic review is the clinical follow-up intervention in an original randomised trial, not a literature synthesis.',
    '132866509': 'Hospital pharmacist review describes a medication-review intervention; this record reports trial-based cost-effectiveness rather than a literature review.',
    '132866570': 'Structured pharmacist review describes the medication-review intervention in the cluster RCT, not a research-literature synthesis.',
    '132822593': 'The full methods report a prospective/cross-sectional study of 103 own NSCLC patients and a new decision-tree analysis. No own literature synthesis is reported; SEER Cancer Statistics Review is a cited model input.',
    '131155314': 'The accepted manuscript attributes the evidence search to Roche and describes ERG appraisal of submitted evidence plus independent clinical/economic base-case analyses. It does not identify an own new literature synthesis by the ERG.',
    '131348332': 'Full-text sections explicitly attribute the systematic review and network meta-analysis to the company. The ERG critiques these and produces independent economic scenarios; the organisation name Kleijnen Systematic Reviews does not establish an own review.',
    '131861415': 'Published methods and the full first-line pemetrexed ERG report describe assessment of company searches and the submitted trial, rather than an own literature synthesis. The ERG produces its own exploratory cost/survival analysis.',
}
REVIEW_ONLY = {
    '131792270': 'The article explicitly reviews clinical trial evidence and summarises results of a published UK cost-utility analysis. It is a genuine non-systematic review, but a new original evaluation is not identified.',
    '132852324': 'The pharmacoeconomic review summarises existing cost-utility and cost studies from several countries. A new model or original evaluation conducted for this review is not identified.',
}
OWN_SR = '131122503 131137979 131222245 131227499 131361077 131381259 131413032 131475942 131514847 131567423 131604379 131604513 131638496 131724374 131724483 131805674 131815780 131848576 131878937 131911639 131934062 131934226 131956585 131956738 131988370 132019001 132019493 132047903 132085798 132103002 132104439 132105996 132530205 132530266 132530358 132808271'.split()
OWN_NON_SR = '130604704 131239726 131295548 131334881 131337910 131349773 131352550 131356182 131402421 131409002 131547387 131556370 131565589 131594801 131666995 131708850 131717407 131738079 131810037 131812687 131861725 131902115 131948776 132034863 132045630 132530639 132530674 132856119 132904539'.split()
DETAILS = {
    '131122503': 'The full discussion explicitly identifies the SLR as conducted in this analysis, and the methods provide its eligibility criteria and supplementary appendix. It is an own SR, not just an external SR used as input.',
    '131638496': 'The full methods explicitly call this our systematic review and link it to development of the new model. Separate publication of the review does not make it an unrelated external review.',
    '132104439': 'The full methods explicitly report conducting a systematic review of resource-utilisation evidence for this model. Some utility inputs come from a separately published review, but that does not negate the own resource-use SR.',
    '131594801': 'Full methods document an own PubMed search and study eligibility assessment, plus standardised economic re-analysis of eight trials conducted by the research group. They decline to pool heterogeneous economic estimates and instead compare trial-specific results. Retain non-systematic synthesis; do not infer a completed pooled economic meta-analysis.',
    '132045630': 'The accepted manuscript reports the ERG’s own random-effects network meta-analysis (section 3.1) and new economic dominance/scenario conclusions (sections 3.2.2 and 4.1). This is an own synthesis despite the initial studies coming from the company search.',
    '131861725': 'Published methods explicitly report rerunning and extending searches; this establishes an own evidence review. The company’s systematic review remains distinct from the ERG’s non-systematic synthesis.',
    '131848576': 'Own searches and clinical synthesis are explicit. The original budget-impact analysis is also explicit even though the main simulation model was submitted by the manufacturer.',
    '131666995': 'The abstract explicitly describes own systematic literature searches and a global evidence review alongside the Peruvian cohort. A systematic search alone is not treated as an explicit systematic-review label under the agreed rule.',
}
SOURCES = {
    '131155314': 'https://discovery.ucl.ac.uk/id/eprint/10092153/3/Ciccarelli_Ocrelizumab%20manuscript%20revised_clean%20R2.pdf',
    '131861415': 'https://njl-admin.nihr.ac.uk/document/download/2035646 | https://njl-admin.nihr.ac.uk/document/download/2022569',
    '131861725': 'https://njl-admin.nihr.ac.uk/document/download/2035641',
    '132045630': 'https://wrap.warwick.ac.uk/100477/1/WRAP-Ixazomib-relapsed-refractory-multiple-myeloma-Armoiry-2018.pdf',
    '131296984': 'https://www.recentiprogressi.it/archivio/3761/articoli/37483/',
}

def main():
    rows = json.loads((OUT/'evidence_basis_81_records.json').read_text(encoding='utf-8'))
    groups = [set(NO_OWN_REVIEW),set(REVIEW_ONLY),set(OWN_SR),set(OWN_NON_SR)]
    assert sum(map(len,groups)) == len(set.union(*groups)) == len(rows) == 81
    assert set.union(*groups) == {r['record_id'] for r in rows}
    assert not set.union(*groups) & {r['record_id'] for r in json.loads((OUT/'evidence_basis_93_records.json').read_text(encoding='utf-8'))}
    master = ROOT/'data/raw/hee_analysis_master_v2.csv'
    before_hash = hashlib.sha256(master.read_bytes()).hexdigest()
    output=[]
    for row in rows:
        rid=row['record_id']
        cache=OUT/'public_fulltext_cache'/f'{rid}.json'
        fetched=json.loads(cache.read_text(encoding='utf-8')) if cache.exists() else {}
        source=SOURCES.get(rid) or fetched.get('source') or (f"https://doi.org/{row['doi']}" if row['doi'] not in ('NA','') else row['url'])
        full=bool(fetched.get('paragraphs')) or rid in {'131155314','131861415','131861725','132045630'}
        parts=re.split(r'(?<=[.!?])\s+',row['abstract'])
        signals=[p for p in parts if re.search(r'review|systematic|meta.analys|method|design|search|conduct',p,re.I)]
        evidence=' | '.join(signals)[:2500]
        kind=row['review_type']; original=row['review_has_original_evaluation']
        if rid in NO_OWN_REVIEW:
            kind=NO_REVIEW; finding='Own literature review not identified'; reason=NO_OWN_REVIEW[rid]
        elif rid in REVIEW_ONLY:
            original=NOT_ORIGINAL; finding='Own review supported; original evaluation not identified'; reason=REVIEW_ONLY[rid]
        else:
            finding='Own review and original evaluation supported'
            reason=DETAILS.get(rid) or ('This record explicitly identifies its own systematic review alongside original modelling, patient-data analysis or trial evaluation.' if rid in OWN_SR else 'The title/methods explicitly identify an own literature review or meta-analysis alongside a separate original evaluation. No explicit own systematic-review label is established under the agreed classification rule.')
        output.append(dict(record_id=rid,title=row['title'],review_type=row['review_type'],
            review_has_original_evaluation=row['review_has_original_evaluation'],design_basis=row['design_basis'],
            finding=finding,recommended_review_type=kind,recommended_original_evaluation=original,
            review_label_change='Yes' if kind!=row['review_type'] else 'No',
            original_flag_change='Yes' if original!=row['review_has_original_evaluation'] else 'No',
            assessment_reason=reason,assessment_evidence=evidence,
            assessment_source=source,assessment_basis='Full published methods/report' if full else 'Supplied abstract/title',
            applied_to_master='No'))
    output.sort(key=lambda r:(r['finding'],r['record_id']))
    target=OUT/'review_ownership_81_assessments.csv'
    with target.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(output[0])); writer.writeheader(); writer.writerows(output)
    with target.open(encoding='utf-8-sig',newline='') as f: assert list(csv.DictReader(f))==output
    assert hashlib.sha256(master.read_bytes()).hexdigest()==before_hash
    summary=dict(assessed=81,cohort='Original cross-check: different evidence basis and original evaluation Yes; disjoint from the previous 93-record audit',
        findings=dict(Counter(r['finding'] for r in output)),
        recommended_review_counts=dict(Counter(r['recommended_review_type'] for r in output)),
        proposed_review_label_changes=sum(r['review_label_change']=='Yes' for r in output),
        proposed_original_flag_changes=sum(r['original_flag_change']=='Yes' for r in output),
        master_changed=False,source_sha256=before_hash,
        interpretation='Not identified as a review records absence of an established own research-literature synthesis in the assessed material, not proof that no literature was consulted. A clinical record/medication/service review and a critique of a company submission do not by themselves establish an own literature review. All changes are proposals; no master update is applied.')
    (OUT/'review_ownership_81_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))

if __name__=='__main__': main()
