"""Apply the user's four follow-up decisions, preserving evidence and backups."""
import csv
import json
import os
import re
import zipfile
from collections import Counter
from datetime import datetime, timezone
import apply_publication_reconciliation as base

csv.field_size_limit(10**9)
ROOT, PLAN = base.ROOT, base.PLAN
RID = '132018093'

def write_csv(path, fields, rows):
    stage = path.with_suffix('.followup.tmp')
    with stage.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
    os.replace(stage, path)

def main():
    fields, decisions = base.read_csv(PLAN/'record_decisions.csv')
    assert sum(d['action']=='pending' for d in decisions)==7, 'Already applied or unexpected state'
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    sites = [ROOT/p for p in ('docs','docs/v2','docs/v3')]
    geo_paths = list((ROOT/'data/raw').glob('hee_geo_long*.csv'))
    backup = ROOT/'data/raw/publication_reconciliation/backups'/('before_followup_'+timestamp+'.zip')
    with zipfile.ZipFile(backup,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
        for p in [*base.TARGETS,*geo_paths,*PLAN.glob('*.csv'),*PLAN.glob('*.json')]:
            z.write(p,str(p.relative_to(ROOT)))
        for site in sites:
            for p in (site/'data').rglob('*.json'): z.write(p,str(p.relative_to(ROOT)))
    groups = {
        '16': ('131512107', 'User directed linkage of TCTR20221219005 to the 2024 results article. Distinctive title, interventions and outcomes match; no explicit registry-to-publication citation verified. Treat as user-adjudicated linkage, not newly source-confirmed.'),
        '27': ('131808468', 'Publisher footnote explicitly identifies the 2015 German report as a shortened translation of Rainer, Mucke and Schlaefke (2013). User directed retention of the 2013 original.'),
        '57': ('131377387', 'User directed consolidation with the full JAMA article based on matching topic, episode categories, overlapping author and conference comparison sample. Claims periods and estimates differ; preliminary-to-final relationship is user-adjudicated, not explicitly source-confirmed.')}
    for d in decisions:
        if d['candidate_group'] not in groups: continue
        canonical, evidence = groups[d['candidate_group']]
        d['action'] = 'keep' if d['record_id']==canonical else 'exclude'
        d['reason'] = 'canonical_report' if d['action']=='keep' else ('trial_registration_without_results' if d['candidate_group']=='16' else 'redundant_publication')
        d['retained_record_id']=canonical; d['evidence']=evidence
        d['evidence_strength']='confirmed_translation' if d['candidate_group']=='27' else 'user_adjudicated'
    by_id={d['record_id']:d for d in decisions}
    exclusions={d['record_id'] for d in decisions if d['action']=='exclude'}
    assert len(exclusions)==47
    corrections=base.read_json(PLAN/'metadata_corrections.json')
    note='Sample location not reported in title/abstract. "Printed in Turkey" is a publisher notice, not a recruitment or treatment location. Turkey and derived geography/income classifications cleared under the user-directed title/abstract rule.'
    corrections[RID]['note']='2015 conference DOI/journal replaced with the 2017 full-article citation matching the supplied abstract. '+note
    originals={}
    for path in base.TARGETS:
        cols, rows=base.read_csv(path)
        before=sum(r['is_eligible']=='TRUE' for r in rows)
        for r in rows:
            rid=r['record_id']
            if rid in by_id: base.update_row(r,by_id[rid],{})
            if rid==RID:
                originals[str(path.relative_to(ROOT))]={k:r[k] for k in cols if any(x in k for x in ('country','income','continent','region','geo_'))}
                for k in ('country_iso3','country_name','income_group','income_broad','income_group_pubyear','income_broad_pubyear','continent','un_region','who_region','who_region_source','country_pop','country_dalys'):
                    if k in r:r[k]='NA'
                r['n_countries_extracted']='0';r['geo_scope']='none';r['income_reason']='no place stated'
                r['metadata_correction_note']=corrections[RID]['note']
        assert before==41614 and sum(r['is_eligible']=='TRUE' for r in rows)==41610
        write_csv(path,cols,rows)
    for path in geo_paths:
        cols,rows=base.read_csv(path)
        write_csv(path,cols,[r for r in rows if r['record_id']!=RID])
    _,rows=base.read_csv(base.TARGETS[0]);master={r['record_id']:r for r in rows}
    for site in sites:
        data=site/'data';st=base.read_json(data/'studies.json');i=st['record_id'].index(RID)
        dictionary=base.read_json(data/'dict.json')
        st['geo_scope'][i]=dictionary['levels']['geo_scope'].index('No country stated')
        base.write_json(data/'studies.json',st)
        geo=base.read_json(data/'geo.json');keep=[j for j,s in enumerate(geo['s']) if s!=i]
        for k in ('s','c','y'):geo[k]=[geo[k][j] for j in keep]
        base.write_json(data/'geo.json',geo)
        # Remove the unsupported country assignment from country drill-downs too.
        for p in (data/'drill').glob('*.json'):
            obj=base.read_json(p)
            if p.stem in ('TUR','Turkey','country_TUR'):
                keep=[j for j,s in enumerate(obj['s']) if s!=i]
                base.write_json(p,{k:[v[j] for j in keep] for k,v in obj.items()})
        base.update_site(site,master,exclusions)
        dictionary=base.read_json(data/'dict.json')
        dictionary['meta']['publication_reconciliation']={'excluded':47,'redundant_reports':44,'registrations':2,'retracted':1,'pending_families':0}
        base.write_json(data/'dict.json',dictionary)
    write_csv(PLAN/'record_decisions.csv',fields,decisions)
    write_csv(PLAN/'exclusions.csv',fields,[d for d in decisions if d['action']=='exclude'])
    write_csv(PLAN/'retained_canonical_reports.csv',fields,[dict(d,doi=master[d['record_id']]['doi']) for d in decisions if d['reason']=='canonical_report'])
    (PLAN/'metadata_corrections.json').write_text(json.dumps(corrections,indent=2)+'\n',encoding='utf-8')
    summary=base.read_json(PLAN/'plan_summary.json')
    summary.update(excluded=47,exclusion_reasons=dict(Counter(d['reason'] for d in decisions if d['action']=='exclude')),retained=76,pending_records=0,pending_families=[],eligible_after=41610,extra_full_reports_reconciled=[50,51,53,54,57],extra_full_report_pending=[])
    (PLAN/'plan_summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    public=[{k:master[d['record_id']].get(k,'') for k in ('record_id','title','doi','eligibility','publication_status','is_retracted','retained_record_id','publication_family_id','publication_linkage_reason','metadata_correction_note','metadata_correction_source')} for d in decisions if d['action']=='exclude']
    base.write_json(ROOT/'docs/data/excluded_publications.json',public)
    eligible={rid for rid,r in master.items() if r['is_eligible']=='TRUE'}
    daly=set();other=set()
    _,outcomes=base.read_csv(ROOT/'data/raw/hee_outcomes_long.csv')
    for r in outcomes:
        if r['record_id'] not in eligible:continue
        if r['family']=='DALYs':daly.add(r['record_id'])
        elif r['family']!='QALYs':other.add(r['record_id'])
    p=ROOT/'docs/app.js';text=p.read_text(encoding='utf-8')
    for key,n in [('OUTCOME_STUDIES',len(eligible)),('DALY_STUDIES',len(daly)),('OTHER_OUTCOME_STUDIES',len(other))]:
        text=re.sub(r'(const '+key+r' = )\d+(;)',lambda m:m[1]+str(n)+m[2],text)
    p.write_text(text,encoding='utf-8')
    write_csv(PLAN/'eligibility_counts_after.csv',['eligibility','n'],[{'eligibility':k,'n':v} for k,v in Counter(r['eligibility'] for r in rows).items()])
    report={'applied_at_utc':timestamp,'backup':str(backup.relative_to(ROOT)),'additional_exclusions':4,'excluded_total':47,'eligible_after':41610,'geography_original':originals,'geography_note':note,'linkage_authority':groups}
    (PLAN/'followup_application.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
