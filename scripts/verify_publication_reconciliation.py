"""Check exclusions, canonical links, metadata repairs and all website indices."""
import csv
import json
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PLAN=ROOT/'exports/publication_reconciliation'
csv.field_size_limit(10**9)
def read_csv(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def read_json(path):return json.loads(path.read_text(encoding='utf-8'))

def main():
    decisions=read_csv(PLAN/'record_decisions.csv')
    excluded={r['record_id'] for r in decisions if r['action']=='exclude'}
    pending={r['record_id'] for r in decisions if r['action']=='pending'}
    corrections=read_json(PLAN/'metadata_corrections.json')
    master={r['record_id']:r for r in read_csv(ROOT/'data/raw/hee_analysis_master_v2.csv')}
    eligible={rid for rid,r in master.items() if r['is_eligible']=='TRUE'}
    assert len(master)==72845 and len(eligible)==41610
    assert len(excluded)==47 and len(pending)==0
    assert master['132018093']['geo_scope']=='none'
    assert master['132018093']['country_iso3']=='NA'
    assert not eligible&excluded
    assert master['131733131']['publication_status']=='Retracted'
    assert master['131733131']['is_retracted']=='TRUE'
    assert master['131733131']['eligibility']=='Excluded: retracted publication'
    for d in decisions:
        r=master[d['record_id']]
        if d['reason']=='redundant_publication':
            assert r['is_duplicate']=='TRUE'
            assert r['retained_record_id'] in eligible
            assert r['retained_record_id']!=r['record_id']
        if d['action']=='keep':assert r['is_eligible']=='TRUE'
    for rid,fix in corrections.items():
        assert master[rid]['doi']==fix['doi']
        assert master[rid]['metadata_original_doi']
    assert master['132866626']['metadata_original_doi']=='10.3109/13625187.2015.1135897'
    # docs/v2 and docs/v3 moved to archive/site_builds/ on 2026-10-21 and are no longer published.
    for site in ('docs',):
        data=ROOT/site/'data';st=read_json(data/'studies.json');n=len(st['id'])
        assert n==41610 and set(st['record_id'])==eligible
        assert st['id']==list(range(n))
        assert all(len(v)==n for v in st.values())
        assert read_json(data/'dict.json')['meta']['n_studies']==n
        for rid in ('131462474','132018093'):
            i=st['record_id'].index(rid);assert st['doi'][i]==corrections[rid]['doi']
        for name in ('geo','disease','disease_gbd','funders'):
            p=data/(name+'.json')
            if p.exists():
                obj=read_json(p);assert all(0<=s<n for s in obj['s'])
                fields={'geo':['s','c','y'],'disease':['s','g'],'disease_gbd':['s','g'],'funders':['s','f']}[name]
                assert len({len(obj[k]) for k in fields})==1
        geo=read_json(data/'geo.json');countries=read_json(data/'countries.json')
        assert st['record_id'].index('132018093') not in geo['s']
        assert '132018093' not in [st['record_id'][i] for i in read_json(data/'drill/TUR.json')['s']]
        counts=Counter(c for _,c in set(zip(geo['s'],geo['c'])))
        assert all(c['studies']==counts[i] for i,c in enumerate(countries))
        for p in (data/'drill').glob('*.json'):
            obj=read_json(p);assert all(0<=s<n for s in obj['s'])
            assert len({len(v) for v in obj.values()})==1
            for s,title in zip(obj['s'],obj['t']):
                assert not title or ' '.join(title.split()).casefold()==' '.join(master[st['record_id'][s]]['title'].split()).casefold(),(p,s)
        p=data/'languages.json'
        if p.exists():
            languages=read_json(p);assert len(languages['code'])==n and sum(languages['n'])==n
        print(site+': eligible IDs, lengths, indices, country counts and publication links verified.')
    for name in ('hee_analysis_master_v2_1.csv','hee_analysis_master_v2_who.csv',
                 'hee_analysis_master_with_review_explanations.csv','hee_share_v2_1/hee_analysis_master.csv'):
        rows=read_csv(ROOT/'data/raw'/name)
        assert len(rows)==72845
        assert {r['record_id'] for r in rows if r['is_eligible']=='TRUE'}==eligible
        target={r['record_id']:r for r in rows if r['record_id'] in excluded|set(corrections)}
        assert all(target[rid]['publication_status']==master[rid]['publication_status'] for rid in excluded)
        assert all(target[rid]['doi']==fix['doi'] for rid,fix in corrections.items())
        location=target['132018093']
        for k in ('country_iso3','country_name','income_group','income_broad','income_group_pubyear','income_broad_pubyear','who_region','continent','un_region'):
            if k in location:assert location[k]=='NA',(name,k)
    print('Five masters agree: 41,610 included; 47 exclusions; no pending family decisions; citation repairs preserved and unsupported sample geography cleared.')

if __name__=='__main__':main()
