"""Apply verified publication decisions, preserving original records and provenance.

Run after prepare_publication_reconciliation.py. Pending relationships stay included.
"""
import csv
import hashlib
import json
import os
import re
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw'
PLAN=ROOT/'exports/publication_reconciliation'
TARGETS=[RAW/n for n in ('hee_analysis_master_v2.csv','hee_analysis_master_v2_1.csv',
    'hee_analysis_master_v2_who.csv','hee_analysis_master_with_review_explanations.csv')]
TARGETS.append(RAW/'hee_share_v2_1/hee_analysis_master.csv')
FIELDS=['publication_family_id','retained_record_id','publication_linkage_status',
    'publication_linkage_reason','publication_status','is_retracted','metadata_original_doi',
    'metadata_original_journal','metadata_correction_note','metadata_correction_source']
RETRACTION='https://pubmed.ncbi.nlm.nih.gov/30740297/'

def read_csv(path):
    with path.open(encoding='utf-8-sig',newline='') as f:
        rd=csv.DictReader(f); return rd.fieldnames,list(rd)

def read_json(path):return json.loads(path.read_text(encoding='utf-8'))
def write_json(path,value):
    stage=path.with_suffix(path.suffix+'.reconcile.tmp')
    stage.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    os.replace(stage,path)
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def update_row(row, decision, corrections):
    original=dict(row)
    row.update({k:row.get(k,'') for k in FIELDS})
    if not decision:return row
    row.update(publication_family_id=decision['publication_family_id'],
        retained_record_id=decision['retained_record_id'],
        publication_linkage_status=decision['action'], publication_linkage_reason=decision['reason'])
    rid=row['record_id']
    if decision['action']=='exclude':
        row['is_eligible']='FALSE'
        labels={'redundant_publication':'Excluded: linked publication',
            'trial_registration_without_results':'Excluded: trial registration without results',
            'retracted_publication':'Excluded: retracted publication'}
        row['eligibility']=labels[decision['reason']]
        if decision['reason']=='redundant_publication':row['is_duplicate']='TRUE'
    if rid=='131733131':
        row['publication_status']='Retracted';row['is_retracted']='TRUE'
        row['metadata_correction_source']=RETRACTION
    elif rid=='132530207':row['publication_status']='Withdrawn'
    if rid in corrections:
        fix=corrections[rid]
        if not row['metadata_original_doi']:row['metadata_original_doi']=original['doi']
        if not row['metadata_original_journal']:row['metadata_original_journal']=original.get('journal','')
        for k,v in fix.items():
            if k in original:row[k]=v
        row['metadata_correction_note']=fix['note'];row['metadata_correction_source']=fix['source']
        if 'doi_source' in row:row['doi_source']='Publication reconciliation: verified report citation' if row['doi'] else 'Publication reconciliation: incorrect DOI cleared'
        if 'url' in fix and 'url_source' in row:row['url_source']='Publication reconciliation: verified full article DOI'
    return row

def update_site(site, master, exclusions):
    data=site/'data'; studies=read_json(data/'studies.json'); dictionary=read_json(data/'dict.json')
    n=len(studies['id']); old_ids=list(studies['record_id'])
    keep=[i for i,rid in enumerate(old_ids) if rid not in exclusions]
    mapping={old:new for new,old in enumerate(keep)}
    assert len(keep)==n-len(set(old_ids)&exclusions)
    for k,v in studies.items():
        assert isinstance(v,list) and len(v)==n,(site,k,'unexpected study-column shape')
    studies={k:[v[i] for i in keep] for k,v in studies.items()}
    studies['id']=list(range(len(keep)))
    for k in ('doi','journal','url','doi_source','url_source',*FIELDS):
        if k=='journal':continue # journal is not a coded study column in this bundle
        if k in studies or k in FIELDS:
            studies[k]=['' if master[rid].get(k,'') in ('NA','na') else master[rid].get(k,'') for rid in studies['record_id']]
    assert set(studies['record_id'])=={rid for rid,r in master.items() if r['is_eligible']=='TRUE'}, site
    write_json(data/'studies.json',studies)
    for name in ('geo','disease','disease_gbd','funders'):
        path=data/(name+'.json')
        if not path.exists():continue
        obj=read_json(path)
        count=len(obj['s']); selected=[i for i,s in enumerate(obj['s']) if s in mapping]
        pair_fields={'geo':('s','c','y'),'disease':('s','g'),'disease_gbd':('s','g'),'funders':('s','f')}[name]
        for k in pair_fields:
            assert len(obj[k])==count,(name,k)
            obj[k]=[mapping[obj[k][i]] if k=='s' else obj[k][i] for i in selected]
        if name=='funders':
            obj['any']=[mapping[s] for s in obj['any'] if s in mapping]
            counts=Counter(obj['f']);obj['n']=[counts[i] for i in range(len(obj['names']))]
        write_json(path,obj)
    path=data/'languages.json'
    if path.exists():
        obj=read_json(path);assert len(obj['code'])==n
        obj['code']=[obj['code'][i] for i in keep]
        counts=Counter(obj['code']);obj['n']=[counts[i] for i in range(len(obj['levels']))]
        write_json(path,obj)
    for path in (data/'drill').glob('*.json'):
        obj=read_json(path);count=len(obj['s'])
        selected=[i for i,s in enumerate(obj['s']) if s in mapping]
        for k,v in obj.items():
            assert isinstance(v,list) and len(v)==count,(path,k)
            obj[k]=[mapping[v[i]] if k=='s' else v[i] for i in selected]
        write_json(path,obj)
    geo=read_json(data/'geo.json');countries=read_json(data/'countries.json')
    counts=Counter(c for _,c in set(zip(geo['s'],geo['c'])))
    for i,c in enumerate(countries):
        c['studies']=counts[i]
        for metric,denom,scale in [('per100k_dalys','dalys',1e5),('per_bn_usd','total_spend_bn',1),('per_million','pop',1e6)]:
            if metric in c:c[metric]=c['studies']/c[denom]*scale if c.get(denom) else None
    write_json(data/'countries.json',countries)
    meta=dictionary['meta'];meta['n_studies']=len(keep);meta['built']='2026-10-14'
    def count_level(field,level):
        return sum(dictionary['levels'][field][i]==level for i in studies[field])
    for key,field,level in [('pct_single','geo_scope','Single country'),('pct_qaly','qaly_label','Uses QALY'),
                          ('pct_model','model_label','Model-based'),('pct_oa','oa_label','Open access')]:
        meta[key]=100*count_level(field,level)/len(keep)
    active=[master[rid] for rid in studies['record_id']]
    reviews=[r for r in active if r.get('review_type') in ('Systematic review','Review (non-systematic)')]
    meta['n_reviews']=len(reviews)
    review_ids={r['record_id'] for r in reviews}
    meta['pct_rev_nocountry']=100*sum(rid in review_ids and dictionary['levels']['geo_scope'][code]=='No country stated'
        for rid,code in zip(studies['record_id'],studies['geo_scope']))/len(reviews) if reviews else 0
    if 'review_only' in meta:meta['review_only']=sum(r['review_type']!='Not identified as a review' and r['review_has_original_evaluation']!='Yes' for r in active)
    meta['n_journals']=len({r['journal'] for r in active if r['journal'] not in ('','NA')})
    access=meta.get('publication_access',{})
    access.update(n_studies=len(keep),n_mapped=len(keep),n_doi=sum(bool(v and v!='NA') for v in studies['doi']),
        n_url=sum(bool(v and v!='NA') for v in studies['url']),
        n_doi_or_url=sum(bool(d and d!='NA' or u and u!='NA') for d,u in zip(studies['doi'],studies['url'])))
    # Match against the original RIS update IDs, including records whose DOI was corrected later.
    _,ris=read_csv(RAW/'url_lookup/EPPI_updated_studies.csv')
    ris_ids={r['record_id'] for r in ris};access['n_ris_updates_matched']=sum(rid in ris_ids for rid in studies['record_id'])
    meta['publication_access']=access
    meta['publication_reconciliation']={'excluded':43,'redundant_reports':41,'registrations':1,'retracted':1,'pending_families':3}
    write_json(data/'dict.json',dictionary)
    return {'site':str(site.relative_to(ROOT)),'before':n,'after':len(keep),'reindexed_drill_files':len(list((data/'drill').glob('*.json')))}

def main():
    csv.field_size_limit(10**9)
    _,decisions=read_csv(PLAN/'record_decisions.csv');by_id={r['record_id']:r for r in decisions}
    exclusions={r['record_id'] for r in decisions if r['action']=='exclude'}
    assert len(exclusions)==43
    corrections=read_json(PLAN/'metadata_corrections.json')
    timestamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup_dir=RAW/'publication_reconciliation/backups';backup_dir.mkdir(parents=True,exist_ok=True)
    backup=backup_dir/('before_publication_reconciliation_'+timestamp+'.zip')
    site_roots=[ROOT/'docs',ROOT/'docs/v2',ROOT/'docs/v3']
    before={str(p.relative_to(ROOT)):digest(p) for p in TARGETS}
    with zipfile.ZipFile(backup,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
        for p in TARGETS:z.write(p,str(p.relative_to(ROOT)))
        for site in site_roots:
            for p in (site/'data').rglob('*.json'):z.write(p,str(p.relative_to(ROOT)))
    results=[]
    # Stage and compare every original field before replacing any master.
    stages=[]
    for path in TARGETS:
        stage=path.with_suffix('.publication_reconciliation.tmp')
        with path.open(encoding='utf-8-sig',newline='') as src,stage.open('w',encoding='utf-8',newline='') as dst:
            reader=csv.DictReader(src);fields=reader.fieldnames
            writer=csv.DictWriter(dst,fieldnames=fields+[k for k in FIELDS if k not in fields]);writer.writeheader()
            seen=set();n=eligible=excluded=0
            for original in reader:
                rid=original['record_id'];decision=by_id.get(rid)
                if decision:seen.add(rid)
                n+=1;eligible+=original['is_eligible']=='TRUE'
                excluded+=rid in exclusions and original['is_eligible']=='TRUE'
                row=update_row(dict(original),decision,corrections)
                writer.writerow(row)
            assert seen==set(by_id),(path,'missing reviewed IDs')
            assert excluded==43,(path,'stale exclusions',excluded)
        with path.open(encoding='utf-8-sig',newline='') as src,stage.open(encoding='utf-8',newline='') as dst:
            old,new=csv.DictReader(src),csv.DictReader(dst)
            for original in old:
                updated=next(new);expected=update_row(dict(original),by_id.get(original['record_id']),corrections)
                assert updated==expected,(path,original['record_id'])
            assert next(new,None) is None
        assert digest(path)==before[str(path.relative_to(ROOT))], 'Master changed during staging'
        results.append(dict(path=str(path.relative_to(ROOT)),rows=n,eligible_before=eligible,eligible_after=eligible-excluded,
            before_sha256=before[str(path.relative_to(ROOT))],after_sha256=digest(stage)))
        stages.append((path,stage))
    for path,stage in stages:os.replace(stage,path)
    _,master_rows=read_csv(TARGETS[0]);master={r['record_id']:r for r in master_rows}
    sites=[update_site(site,master,exclusions) for site in site_roots]
    excluded_public=[{k:master[r['record_id']].get(k,'') for k in ('record_id','title','doi','eligibility',
        'publication_status','is_retracted','retained_record_id','publication_family_id','publication_linkage_reason',
        'metadata_correction_note','metadata_correction_source')} for r in decisions if r['action']=='exclude']
    write_json(ROOT/'docs/data/excluded_publications.json',excluded_public)
    # Replace outcome constants using eligible IDs, rather than subtracting guessed deltas.
    ids={rid for rid,r in master.items() if r['is_eligible']=='TRUE'}
    daly=set();other=set()
    with (RAW/'hee_outcomes_long.csv').open(encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f):
            if r['record_id'] not in ids:continue
            if r['family']=='DALYs':daly.add(r['record_id'])
            elif r['family']!='QALYs':other.add(r['record_id'])
    app=ROOT/'docs/app.js';text=app.read_text(encoding='utf-8')
    for constant,value in [('OUTCOME_STUDIES',len(ids)),('DALY_STUDIES',len(daly)),('OTHER_OUTCOME_STUDIES',len(other))]:
        text,n=re.subn(r'(const '+constant+r' = )\d+(;)',lambda m:m[1]+str(value)+m[2],text);assert n==1,constant
    app.write_text(text,encoding='utf-8')
    result=dict(applied_at_utc=timestamp,backup=str(backup.relative_to(ROOT)),masters=results,sites=sites,
        excluded=43,exclusion_reasons=dict(Counter(r['reason'] for r in decisions if r['action']=='exclude')),
        metadata_corrected=list(corrections),all_other_original_fields_verified_unchanged=True,
        pending_families=3,pending_records=7,eligible_after=len(ids))
    (PLAN/'application.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
