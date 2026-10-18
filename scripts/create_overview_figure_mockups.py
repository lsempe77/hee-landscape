"""Standalone overview layout options; reuse current map images without editing them."""
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'exports/overview_figure_mockups_2026-10-14'
BG='#faf8f4'; INK='#17354a'; MUTED='#66737a'; BLUE='#49779b'; TEAL='#72a5ab'; GOLD='#d0aa67'

def read(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def image_panel(fig,rect,file):
    ax=fig.add_axes(rect);ax.imshow(Image.open(ROOT/'docs/figures'/file));ax.axis('off')

def heading(fig,x,y,letter,title):
    fig.text(x,y,letter,fontsize=16,fontweight='bold',color=TEAL,va='top')
    fig.text(x+.026,y,title,fontsize=15,fontweight='bold',color=INK,va='top')

def methods(fig,rect,counts):
    ax=fig.add_axes(rect,facecolor=BG)
    labels=['Cost-utility','Cost-effectiveness','Cost-consequence','Cost-benefit']
    vals=[counts[x]/sum(counts.values())*100 for x in labels]
    ax.barh(range(4),vals,color=[BLUE,TEAL,GOLD,'#a4a49a'],height=.56)
    ax.set_yticks(range(4),labels,fontsize=11,color=INK);ax.invert_yaxis();ax.set_xlim(0,60)
    for i,(v,k) in enumerate(zip(vals,labels)):ax.text(v+.8,i,f'{v:.1f}%  ({counts[k]:,})',va='center',fontsize=11,color=INK)
    ax.set_xticks([]);ax.tick_params(length=0)
    for sp in ax.spines.values():sp.set_visible(False)

def publication_mix(fig,mix):
    """Reserve a full-width band above the existing integrated panels."""
    fig.set_size_inches(19,17)
    for text in list(fig.texts):
        x,y=text.get_position()
        if y<.90:text.set_position((x,y*.84))
    for ax in list(fig.axes):
        box=ax.get_position()
        ax.set_position([box.x0,box.y0*.84,box.width,box.height*.84])
    total=sum(mix.values());full=total-mix['Reviews without own evaluation']
    fig.text(.035,.891,'Publication mix',fontsize=16,fontweight='bold',color=INK,va='top')
    fig.text(.23,.891,f'{full:,} full economic evaluations ({100*full/total:.1f}%), including 667 reviews with their own evaluation',fontsize=13,color=INK,va='top')
    ax=fig.add_axes([.035,.828,.93,.035],facecolor=BG)
    left=0
    colours=[BLUE,TEAL,GOLD]
    for (label,n),colour in zip(mix.items(),colours):
        ax.barh(0,n,left=left,color=colour,height=.65,edgecolor=BG,linewidth=1)
        left+=n
    ax.set_xlim(0,total);ax.axis('off')
    for x,(label,n),colour in zip([.035,.37,.70],mix.items(),colours):
        fig.text(x,.806,'■',color=colour,fontsize=14,va='top')
        fig.text(x+.015,.806,f'{label}\n{n:,} ({100*n/total:.1f}%)',color=INK,fontsize=11,va='top',linespacing=1.5)
    fig.text(.035,.758,'Full evaluation: compares both costs and consequences of two or more alternatives. The three categories above are mutually exclusive.',fontsize=10,color=MUTED)

def save(fig,name,mix):
    publication_mix(fig,mix)
    for ext in ['png','svg']:fig.savefig(OUT/f'{name}.{ext}',dpi=180,facecolor=BG)
    plt.close(fig)

def main():
    OUT.mkdir(parents=True,exist_ok=True);csv.field_size_limit(10**9)
    web=json.loads((ROOT/'docs/data/studies.json').read_text())
    levels=json.loads((ROOT/'docs/data/dict.json').read_text())['levels']
    m={r['record_id']:r for r in read(ROOT/'data/raw/hee_analysis_master_v2_1.csv') if r['is_eligible']=='TRUE'}
    assert len(m)==41610
    counts=Counter(levels['econ_eval_type'][i] for i in web['econ_eval_type']);counts.pop('Review (no evaluation type)')
    review_levels=levels['review_label']
    is_review=[review_levels[v] in ['Systematic review','Other review'] for v in web['review_label']]
    typed=[levels['econ_eval_type'][v]!='Review (no evaluation type)' for v in web['econ_eval_type']]
    mix={'Evaluation, not classified as review':sum(t and not r for t,r in zip(typed,is_review)),
         'Review with own evaluation':sum(t and r for t,r in zip(typed,is_review)),
         'Reviews without own evaluation':sum(not t for t in typed)}
    assert list(mix.values())==[38958,667,1985],mix
    oa=Counter(r['is_oa'] for r in m.values());global_rate=100*oa['1']/(oa['1']+oa['0'])
    # Exactly reproduce the current Explorer income filters, including deduplication.
    geo=json.loads((ROOT/'docs/data/geo.json').read_text());countries=json.loads((ROOT/'docs/data/countries.json').read_text())
    sides=defaultdict(set)
    for i,c,y in zip(geo['s'],geo['c'],geo['y']):
        inc=countries[c]['income_y'][y-2010]
        if inc in ['Low income','Lower middle income']:sides['Low / lower-middle income'].add(i)
        if inc in ['Upper middle income','High income']:sides['Upper-middle / high income'].add(i)
    rates={}
    for side in ['Low / lower-middle income','Upper-middle / high income']:
        ids=sides[side]
        c=Counter(levels['oa_label'][web['oa_label'][i]] for i in ids)
        rates[side]=dict(open=c['Open access'],known=c['Open access']+c['Not open'],unknown=c['Unknown'])
    assert rates['Low / lower-middle income']['open']==1888
    assert rates['Upper-middle / high income']['open']==16318
    plt.rcParams.update({'font.family':'Arial','svg.fonttype':'none'})
    fig=plt.figure(figsize=(19,14),facecolor=BG)
    fig.text(.035,.967,'OPTION 1  |  THE ECONOMIC-EVIDENCE BASE AT A GLANCE',fontsize=24,fontweight='bold',color=INK,va='top')
    fig.text(.035,.928,'41,610 included publications  •  2010–2026 (2026 partial)  •  Standalone layout mockup',fontsize=14,color=MUTED)
    heading(fig,.035,.885,'A','Where studies are conducted')
    heading(fig,.535,.885,'B','Research availability relative to population')
    image_panel(fig,[.025,.485,.475,.37],'fig_dotmap_reconciled.webp')
    image_panel(fig,[.52,.485,.46,.37],'paper03_reconciled.webp')
    heading(fig,.035,.45,'C','Types of economic evaluation')
    fig.text(.061,.414,'39,625 records with an evaluation type',fontsize=11,color=MUTED)
    methods(fig,[.15,.19,.32,.19],counts)
    heading(fig,.535,.45,'D','Access to the evidence')
    fig.text(.56,.365,f'{global_rate:.1f}%',fontsize=44,fontweight='bold',color=BLUE)
    fig.text(.735,.372,'open access overall\n24,216 / 36,332 known-status records',fontsize=12,color=INK,linespacing=1.6)
    ax=fig.add_axes([.74,.19,.20,.12],facecolor=BG)
    for i,(label,c) in enumerate(rates.items()):
        val=100*c['open']/c['known'];ax.barh(i,val,color=TEAL if i==0 else BLUE,height=.5)
        ax.text(val+1,i,f'{val:.1f}%',va='center',fontsize=12,color=INK)
    ax.set_yticks([0,1],['Low / lower-middle income','Upper-middle / high income'],fontsize=10.5,color=INK);ax.invert_yaxis();ax.set_xlim(0,100);ax.set_xticks([]);ax.tick_params(length=0)
    for sp in ax.spines.values():sp.set_visible(False)
    fig.text(.56,.15,'Known OA status: 2,304 vs 23,507 records;\nunknown excluded: 304 vs 3,072. Country filters match Explorer.',fontsize=10.5,color=MUTED,linespacing=1.5)
    fig.text(.035,.085,'Reading the panels: A shows absolute study counts; B adjusts counts for population. C describes evaluation types; D describes access.',fontsize=11,color=INK)
    fig.text(.035,.056,'A–B reuse current map figures unchanged. A counts a record once per named country. C includes reviews with their own evaluation.\nD excludes unknown OA status; 5,278 unknown overall. Income groups can overlap for multicountry studies and omit unclassified settings.',fontsize=10,color=MUTED,linespacing=1.5)
    save(fig,'option_1_overview_four_panels',mix)

    # Full source geography, all eligible records: countries assigned to WHO regions as in the dataset.
    region_ids=defaultdict(set)
    for r in read(ROOT/'data/raw/hee_geo_long_v2_1.csv'):
        if r['record_id'] in m and r['is_special']=='FALSE' and r['who_region'] not in ['', 'NA']:
            region_ids[r['who_region']].add(r['record_id'])
    regions=[]
    for name,ids in region_ids.items():
        c=Counter(m[i]['is_oa'] for i in ids);known=c['1']+c['0']
        regions.append(dict(region=name,studies=len(ids),open=c['1'],known=known,unknown=len(ids)-known,oa_pct=100*c['1']/known))
    regions.sort(key=lambda r:-r['studies'])
    fig=plt.figure(figsize=(19,14),facecolor=BG)
    fig.text(.035,.967,'OPTION 2  |  GLOBAL OVERVIEW AND WHO REGIONAL PROFILES',fontsize=23,fontweight='bold',color=INK,va='top')
    fig.text(.035,.928,'41,610 included publications  •  2010–2026 (2026 partial)  •  Standalone layout mockup',fontsize=14,color=MUTED)
    heading(fig,.035,.885,'A','Global distribution of research')
    image_panel(fig,[.02,.49,.53,.37],'fig_dotmap_reconciled.webp')
    heading(fig,.60,.885,'B','Global evidence profile')
    fig.text(.625,.79,'66.7% open access',fontsize=28,fontweight='bold',color=BLUE)
    fig.text(.625,.752,'24,216 / 36,332 with known OA status\n5,278 records with unknown status',fontsize=12,color=MUTED,linespacing=1.6)
    methods(fig,[.71,.51,.235,.17],counts)
    fig.text(.625,.474,'Evaluation-type base: 39,625 records',fontsize=11,color=MUTED)
    heading(fig,.035,.44,'C','Regional study volume and open-access availability')
    # A count bar and an OA dot share aligned region rows; all denominators are visible.
    ax=fig.add_axes([.25,.13,.28,.225],facecolor=BG)
    ax.barh(range(len(regions)),[r['studies'] for r in regions],color=BLUE,height=.52)
    ax.set_yticks(range(len(regions)),[r['region'] for r in regions],fontsize=11,color=INK)
    ax.invert_yaxis();ax.set_xlim(0,max(r['studies'] for r in regions)*1.2)
    for i,r in enumerate(regions):ax.text(r['studies']+140,i,f"{r['studies']:,}",va='center',fontsize=11,color=INK)
    ax.set_xticks([]);ax.tick_params(length=0)
    for sp in ax.spines.values():sp.set_visible(False)
    fig.text(.25,.382,'UNIQUE RECORDS NAMING A REGION',fontsize=10.5,fontweight='bold',color=MUTED)
    ax2=fig.add_axes([.58,.13,.16,.225],facecolor=BG)
    for i,r in enumerate(regions):
        ax2.plot([0,r['oa_pct']],[i,i],color='#d8e5e7',lw=7,solid_capstyle='round');ax2.scatter(r['oa_pct'],i,color=TEAL,s=65,zorder=3)
        ax2.text(106,i,f"{r['oa_pct']:.1f}%",va='center',fontsize=12,color=INK)
        ax2.text(143,i,f"{r['open']:,} / {r['known']:,}",va='center',fontsize=11,color=MUTED)
        ax2.text(217,i,f"{r['unknown']:,}",va='center',fontsize=11,color=MUTED)
    ax2.set_xlim(0,100);ax2.set_ylim(ax.get_ylim());ax2.set_yticks([]);ax2.set_xticks([0,50,100],['0%','50%','100%'],fontsize=9,color=MUTED);ax2.tick_params(length=0)
    for sp in ax2.spines.values():sp.set_visible(False)
    fig.text(.58,.382,'OPEN ACCESS',fontsize=10.5,fontweight='bold',color=MUTED)
    fig.text(.809,.382,'OPEN / KNOWN',fontsize=10.5,fontweight='bold',color=MUTED)
    fig.text(.927,.382,'UNKNOWN',fontsize=10.5,fontweight='bold',color=MUTED)
    fig.text(.035,.075,'A reuses the current map figure. C counts each publication once within each region; multicountry publications can enter several regions.\nOA percentages exclude unknown status. Records without an assigned country/WHO region do not enter C, so regional totals do not sum to the global total.',fontsize=10.5,color=MUTED,linespacing=1.6)
    save(fig,'option_2_global_and_WHO_regions',mix)
    with (OUT/'regional_data.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(regions[0]));w.writeheader();w.writerows(regions)
    (OUT/'provenance.json').write_text(json.dumps(dict(eligible_records=len(m),publication_mix=mix,evaluation_types=dict(counts),income_oa=rates,global_oa=dict(oa),regions=regions,reused_images=['docs/figures/fig_dotmap_reconciled.webp','docs/figures/paper03_reconciled.webp'],map_modified=False),indent=2))
    (OUT/'README.md').write_text('''# Overview figure mockups

Both options include a publication-composition strip showing mutually exclusive evaluation-only, review-with-own-evaluation and review-only categories. Full evaluations total 39,625 (95.2%), including 667 reviews with their own evaluation.

Option 1 is a four-panel overview: existing map and population-density figures, with newly drawn evaluation-type and OA summaries. Option 2 combines the existing map with a global profile and WHO-region study-volume/OA comparison. PNG previews and SVG files (with embedded existing raster figures) are provided.

All newly computed numbers use the current 41,610-record dataset. Evaluation types use the website classifications, excluding 1,985 reviews without their own evaluation. Income OA groups reproduce Explorer's country list and publication-year income filters. The regional summary uses the full geography table and its assigned WHO regions, with unique records within each region. These are different geography universes and are documented, not summed together. Multi-setting studies can enter more than one region or income group. Known OA status is the denominator throughout; unknown counts are reported.

These are figure layout options, not a check of the manuscript's other numbers. Existing map images are reused unchanged. No website or manuscript files were modified.
''',encoding='utf-8')
    print(json.dumps(regions,indent=2));print('Saved two standalone mockups.')

if __name__=='__main__':main()
