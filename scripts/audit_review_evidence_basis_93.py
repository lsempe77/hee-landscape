"""Record evidence assessments of the 93 priority mismatches, without editing v2."""
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/raw/review_screening'
SYNTHESIS = 'Literature/registry synthesis'
NO_REVIEW = 'Not identified as a review'
NON_SR = 'Review (non-systematic)'
NOT_ORIGINAL = 'Original evaluation not identified'


def assessments(rows):
    by_id = {r['record_id']: r for r in rows}
    decisions = {}

    def add(ids, reason, review=None, original='Yes', basis=None, issue='Original evaluation flag missing', status='Supported by supplied abstract', source=None):
        for rid in ids.split():
            assert rid in by_id and rid not in decisions, rid
            row = by_id[rid]
            decisions[rid] = {'recommended_review_type': review or row['review_type'],
                              'recommended_original_evaluation': original,
                              'recommended_design_basis': basis or row['design_basis'],
                              'finding': issue, 'assessment_status': status,
                              'assessment_reason': reason, 'assessment_source': source or 'Full supplied abstract'}

    add('130737891 131122133 131171899 131173945 131180458 131195806 131210328 131249182 131265928 131299866 131301518 131352785 131362797 131415987 131431839 131436505 131440467 131455603 131513690 131563043 131743312 131786338 131873773 131902804 131911979 131975996 132018951 132033319 132078383 132306620 132351797 132530160 132530585',
        'This work describes both an own review/synthesis and an original trial, cohort/data analysis or economic evaluation. Keep the review label; set the separate original-evaluation flag to Yes. The non-synthesis basis can legitimately describe its original study component.')
    add('131355174 131467815 131504534 131627071 131698575 131878093 131998670 132523867 132529568 132530866 132837028',
        'An own synthesis feeds a new economic model or analysis. The RCT/trial describes published input studies rather than a clinical trial newly conducted by this record. Record original evaluation Yes and use the synthesis basis.',
        basis=SYNTHESIS, issue='Original evaluation flag and evidence basis need correction')
    add('131116377 132053434',
        'The authors conduct an IPD synthesis and a new cost-effectiveness analysis of existing trials, rather than a new randomised trial. The original economic analysis is identified separately from the synthesis.',
        basis=SYNTHESIS, issue='Original evaluation flag and evidence basis need correction')
    add('131295788',
        'The paper is explicitly a systematic review and individual-participant-data meta-analysis of existing trials. The RCT basis refers to included studies; a separate original evaluation beyond the synthesis is not established.',
        original=NOT_ORIGINAL, basis=SYNTHESIS, issue='Included RCTs mistaken for own trial')
    add('132039824',
        'Own SR/IPD synthesis of existing RCTs, original NHS cohort data, and new economic modelling. The RCT describes input studies; Observational describes the own patient-data component.',
        basis='Observational', issue='Original evaluation flag and evidence basis need correction')
    add('131182408 131223970 131384795 131452912 131771873 131924087 132015428 132084595 132087766 132110506 132420156 132841185 132877328 132910116',
        'The abstract reports an original patient/database/intervention evaluation. Review wording refers to patient records, a clinical service, an administrative organisation/policy, or a general study review; no own research-literature synthesis is established.',
        review=NO_REVIEW, issue='False review signal; original evaluation flag missing')
    add('131132326',
        'The own synthesis is an evidence-based background review; the systematic review is one of its included evidence sources. The authors also conduct a 22-year centre cost comparison. Systematic describes an input, not this own review.',
        review=NON_SR, issue='Existing SR mistaken for own SR; original evaluation flag missing')
    add('131208140',
        'The full-text scenario analysis uses a separately cited published systematic review (reference 17) for protection estimates. The authors conduct the original cluster trial and economic model, but an own new synthesis is not identified.',
        review=NO_REVIEW, issue='Published SR mistaken for own SR; original evaluation flag missing',
        source='https://pmc.ncbi.nlm.nih.gov/articles/PMC6251210/')
    add('131988355',
        'The authors populate a new Markov model with a recent published patient-level meta-analysis. The supplied abstract does not describe conducting a new own meta-analysis.',
        review=NO_REVIEW, basis=SYNTHESIS, issue='Existing meta-analysis mistaken for own synthesis; economic model missing')
    add('132049564',
        'This narrative article reviews SMILE trial findings. Its economic analysis section reports the separately cited cost-effectiveness study (reference 18); a new original economic evaluation in this review is not established.',
        original=NOT_ORIGINAL, basis=SYNTHESIS, issue='Reviewed trial mistaken for own RCT',
        source='https://pmc.ncbi.nlm.nih.gov/articles/PMC5960496/')
    add('132107511',
        'This Evidence-Based Reviews in Surgery article is an expert review of the Roulin et al. 2016 randomised trial. The abstract describes that reviewed trial, rather than a new trial conducted by these reviewers.',
        original=NOT_ORIGINAL, basis=SYNTHESIS, issue='Reviewed trial mistaken for own RCT',
        source='https://ebrs.online/courses/early-cholecystectomy-cholecystitis/')
    add('132845895',
        'The article states that it provides an overview and reviews officially reported outcomes of two Medicare Health Support cohorts. The randomisation describes the reported programme, not a new trial conducted for this overview. Ownership of any additional economic analysis needs methods confirmation.',
        original=NOT_ORIGINAL, basis=SYNTHESIS, issue='Programme overview and trial ownership need distinction',
        status='Evidence basis proposed; additional-analysis ownership not established')
    add('131429691',
        'The EAG appraises the submitted trial and generates independent economic scenarios; the full text does not establish an own literature synthesis. Trial describes the company evidence input. The own economic re-analysis is identified.',
        review=NO_REVIEW, basis=SYNTHESIS, issue='Submission appraisal mistaken for literature review; economic re-analysis missing',
        source='https://pmc.ncbi.nlm.nih.gov/articles/PMC10721753/')
    add('131791448 131861701',
        'The ERG independently searches/reruns the literature search and conducts its own economic sensitivity/model analyses. Its own synthesis is not explicitly labelled systematic in the supplied abstract; the cited RCT is an input.',
        basis=SYNTHESIS, issue='Original ERG economic analysis missing; input RCT mistaken for own trial')
    add('131908440',
        'The ERG searches for additional literature, supporting an own synthesis without an explicit systematic label. The new model/revised ICER is attributed to the company, while independent new ERG economic results are not established.',
        original=NOT_ORIGINAL, basis=SYNTHESIS, issue='Included RCT mistaken for own trial')
    add('131861071 131861153 131861307 131861421 131861606 131861607 131861630 131861637 131861664 131861719 131861723 131861764 131861768 131967253',
        'The abstract explicitly identifies independent ERG economic scenarios, corrections or re-analysis, so original evaluation should be Yes. It describes appraisal of company-submitted evidence rather than establishing an own new literature synthesis. The input RCT is not an own trial.',
        review=NO_REVIEW, basis=SYNTHESIS, issue='Own ERG economic analysis missing; own literature-review status needs methods',
        status='Economic/basis correction supported; own literature-review methods need checking')
    add('131823666 131860926 131860928 131861508 131861705 131861732 131861751',
        'This is an appraisal of submitted company evidence, with published or submitted trials/models as inputs. The abstract does not establish an own literature synthesis or independently produced ERG economic evaluation. Full report methods are needed to confirm those components.',
        review=NO_REVIEW, original=NOT_ORIGINAL, basis=SYNTHESIS,
        issue='Submission appraisal and input trial; own components not established',
        status='Synthesis basis supported; own review/evaluation methods need checking')
    assert set(decisions) == set(by_id), sorted(set(by_id) - set(decisions))

    # Record-specific explanations supersede broad group descriptions.
    detail = {
        '130737891': 'Own critical literature review plus new trial-based cost-utility analysis of U-PGx PREPARE patients; keep RCT basis and set original evaluation Yes.',
        '131122133': 'Own SR identifies PROMs, followed by original patient-dataset analyses and Markov cost-utility modelling; keep Observational and set original evaluation Yes.',
        '131249182': 'MiQuit3 conducts a new RCT and economic analysis, then synthesises that trial with two previous trials. No explicit own SR label; keep Review (non-systematic), RCT, and set original Yes.',
        '131299866': 'Own SR and prospective aneurysm cohort with original costs/QoL data; formal comparative economic analysis was infeasible. Original Yes denotes the own cohort/cost analysis, not successful completion of a formal cost-effectiveness model.',
        '131415987': 'ARCHIE explicitly reports its own systematic review under PRISMA and its own clinical trial, within-trial costs and outcomes. Set original Yes. Trial basis remains defensible; randomisation status would need a separate design audit.',
        '131467815': 'Health Technology Wales conducts its own systematic searches/evidence review and develops a cost-utility model using published OPERA trial results. No own systematic-review label or own RCT is established; use synthesis basis and original Yes.',
        '131563043': 'Own literature review informs a protocol evaluated in a pre/post quasi-experiment, with QALY and cost-saving estimates; keep Quasi-experimental and set original Yes.',
        '131823666': 'The de novo model is explicitly attributed to Novartis. The abstract establishes appraisal of submitted evidence, not an own literature synthesis or independent ERG economic evaluation; the recorded RCT is an input.',
        '131860926': 'Model revisions are described passively as based on ERG concerns; authorship of the revised calculation is not explicit. Do not turn the original-evaluation flag to Yes solely from that sentence.',
        '131861508': 'The revised indirect comparison is explicitly submitted by the manufacturer in response to ERG clarification; this is not evidence of an own ERG analysis.',
        '131861701': 'The ERG reruns modified search strategies and repairs/runs the revised model in probabilistic sensitivity analyses. Retain Review (non-systematic), set original Yes, and use synthesis basis.',
        '131908440': 'Own ERG search for additional evidence is explicit. Company authorship is explicit for the new model and its revision; model validation alone does not establish a new ERG economic evaluation.',
        '132039824': 'Own SR/IPD synthesis of RCTs, an original NHS usual-care cohort, and a new economic model. The RCTs are included evidence. Recommend Observational for the original patient-data component and original Yes.',
        '132530585': 'Updated literature reviews accompany new analyses of previously collected patient-level rehabilitation datasets (8070 admissions), staffing, costs and outcomes; keep Observational and set original Yes.',
        '132877328': 'The abstract describes 34 own consecutive RVOT-intervention patients and original clinical/cost comparisons. It has no qualifying literature-review methods; propose Not identified as a review and original Yes.',
        '132910116': 'Prospective review and feedback describes an antibiotic-prescribing intervention in an original cluster-randomised crossover trial; it is not a literature synthesis. Propose Not identified as a review and original Yes.',
    }
    for rid, reason in detail.items():
        decisions[rid]['assessment_reason'] = reason
    decisions['132039824']['recommended_design_basis'] = 'Observational'
    # Insufficient reporting is not evidence that a review was absent.
    for rid, decision in decisions.items():
        decision['review_decision_resolved'] = 'No' if 'methods need checking' in decision['assessment_status'] else 'Yes'
        if decision['review_decision_resolved'] == 'No':
            decision['recommended_review_type'] = by_id[rid]['review_type']
    decisions['131860928'].update(
        recommended_review_type=NON_SR,
        review_decision_resolved='Yes',
        assessment_status='Own review and synthesis basis supported; independent economic analysis needs checking',
        assessment_reason='The full ERG report documents independent searches of Cochrane, MEDLINE and EMBASE in Appendix 1. This establishes an own evidence review, without an explicit own systematic-review label. The input trials were not conducted by the ERG; independent economic-analysis ownership remains to be confirmed.',
        assessment_source='https://www.nice.org.uk/guidance/ta211/documents/constipation-women-prucalopride-evidence-review-group-report2')
    followup = OUT / 'review_evidence_basis_22_resolutions.json'
    if followup.exists():
        resolutions = json.loads(followup.read_text(encoding='utf-8'))
        assert len(resolutions) == 22 and set(resolutions) <= set(decisions)
        for rid, resolution in resolutions.items():
            decisions[rid].update(resolution)
    return decisions


def main():
    rows = json.loads((OUT / 'evidence_basis_93_records.json').read_text(encoding='utf-8'))
    assert len(rows) == 93 and len({r['record_id'] for r in rows}) == 93
    master = ROOT / 'data/raw/hee_analysis_master_v2.csv'
    source_hash = hashlib.sha256(master.read_bytes()).hexdigest()
    decisions = assessments(rows)
    output = []
    for row in rows:
        decision = decisions[row['record_id']]
        parts = re.split(r'(?<=[.!?])\s+|\s*\|\s*', row['abstract'])
        signals = [p for p in parts if re.search(r'review|systematic|meta.analys|methods|design|\bERG\b|\bEAG\b|model|trial|retrospective|cost', p, re.I)]
        evidence = ' | '.join(signals)[:3000]
        record = {k: row.get(k, '') for k in ['record_id', 'title', 'doi', 'url', 'review_type', 'design_basis', 'review_has_original_evaluation']}
        record.update(decision, abstract_evidence=evidence,
                      review_label_change='Yes' if decision['recommended_review_type'] != row['review_type'] else 'No',
                      original_flag_change='Yes' if decision['recommended_original_evaluation'] != row['review_has_original_evaluation'] else 'No',
                      evidence_basis_change='Yes' if decision['recommended_design_basis'] != row['design_basis'] else 'No',
                      applied_to_master='No')
        output.append(record)
    csv.field_size_limit(10_000_000)
    target = OUT / 'review_evidence_basis_93_assessments.csv'
    with target.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output[0]))
        writer.writeheader()
        writer.writerows(output)
    with target.open(encoding='utf-8-sig', newline='') as handle:
        assert list(csv.DictReader(handle)) == output
    assert hashlib.sha256(master.read_bytes()).hexdigest() == source_hash
    summary = {'assessed': len(rows), 'source_sha256': source_hash, 'master_changed': False,
               'recommended_review_counts': dict(Counter(r['recommended_review_type'] for r in output)),
               'review_label_changes': sum(r['review_label_change'] == 'Yes' for r in output),
               'original_flag_changes': sum(r['original_flag_change'] == 'Yes' for r in output),
               'evidence_basis_changes': sum(r['evidence_basis_change'] == 'Yes' for r in output),
               'assessment_status_counts': dict(Counter(r['assessment_status'] for r in output)),
               'unresolved_review_decisions': sum(r['review_decision_resolved'] == 'No' for r in output),
               'note': 'Change counts overlap. Unresolved own-review decisions retain the current review label. Recommended changes are an audit for discussion; master classifications remain unchanged.'}
    (OUT / 'review_evidence_basis_93_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
