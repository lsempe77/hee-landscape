"""Align selection text and Figure 1 in current and versioned site bundles."""
import json
import shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
caption=json.loads((ROOT/'docs/data/figure_updates.json').read_text(encoding='utf-8'))['paper01.webp']['caption']
summary='The map includes 41,610 records. The current classification identifies 1,856 systematic reviews and 796 non-systematic reviews; 38,958 records are not identified as reviews. The diagram shows screening, extraction and subsequent publication reconciliation.'
for site in ('docs','docs/v2','docs/v3'):
    root=ROOT/site
    p=root/'data/content.json';content=json.loads(p.read_text(encoding='utf-8'))
    funnel=content['funnel'];cut=next(i for i,r in enumerate(funnel) if r['label']=='Analysis population')
    content['funnel']=funnel[:cut]+[
        {'label':'Excluded — additional redundant publications','records':'−44','strong':False},
        {'label':'Excluded — registrations without results','records':'−2','strong':False},
        {'label':'Excluded — retracted paper','records':'−1','strong':False},
        {'label':'Analysis population','records':'41,610','strong':True},
        {'label':'of which systematic reviews','records':'1,856','strong':False},
        {'label':'of which non-systematic reviews','records':'796','strong':False}]
    content['paper01_caption']=caption
    for section in content['gallery']:
        for f in section.get('figs',[]):
            if f['file']=='paper01.webp':
                f.update(title='Study selection: 41,610 included records',caption=caption,summary=summary)
                if site!='docs':f['file']='fig_selection_reconciled.svg'
    p.write_text(json.dumps(content,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    p=root/'data/figure_copy.json'
    if p.exists():
        copy=json.loads(p.read_text(encoding='utf-8'))
        copy['paper01.webp']={'title':'Study selection: 41,610 included records','summary':summary,'caption':caption}
        if site!='docs':copy['fig_selection_reconciled.svg']=copy['paper01.webp']
        p.write_text(json.dumps(copy,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if site!='docs':shutil.copy2(ROOT/'docs/figures/fig_selection_reconciled.svg',root/'figures/fig_selection_reconciled.svg')
    for name in ('app.js','index.html'):
        p=root/name;text=p.read_text(encoding='utf-8')
        text=text.replace('Some reviews also include the authors\' own evaluation. The selection diagram uses an older, stricter " +\n      "title-only flag and counts 1,706 reviews.',
                          'Some reviews also include the authors\' own evaluation. The selection diagram uses the same " +\n      "current classification: 1,856 systematic and 796 non-systematic reviews.')
        text=text.replace('2026-10-14-publication-followup','2026-10-14-methods-reconciled')
        p.write_text(text,encoding='utf-8')
verification=ROOT/'exports/publication_reconciliation/verification.json'
v=json.loads(verification.read_text(encoding='utf-8'));v['manuscript_updated']=True
v['manuscript_reconciliation']='manuscript_reconciliation.json; references/dates and preprint policy remain open'
verification.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
print('Selection figure, funnel counts and review explanations updated in current/v2/v3 bundles.')
