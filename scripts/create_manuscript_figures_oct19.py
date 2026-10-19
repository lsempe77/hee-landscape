"""Standalone manuscript versions of the six supplied figures. Never writes docs/."""
import sys
sys.dont_write_bytecode = True
import csv
import hashlib
import json
import math
import re
import shutil
import textwrap
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.patches import Polygon, Patch
from matplotlib.collections import PatchCollection
from matplotlib.lines import Line2D
from matplotlib.ticker import PercentFormatter, NullFormatter
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'manuscript figures Oct 19'
DATA = OUT / 'source data'
THEME = (ROOT / 'docs/theme_hee.R').read_text(encoding='utf-8')
def hex_for(key):
    return re.search(r'\b' + key + r'\s*=\s*"(#[0-9a-fA-F]{6})"', THEME)[1]
BLUE, ORANGE, AQUA = [hex_for(k) for k in ['blue','orange','aqua']]
INK, SECONDARY, MUTED, GRID, BG = [hex_for(k) for k in ['primary','secondary','muted','grid','surface']]
SEQ = re.findall(r'#[0-9a-fA-F]{6}', re.search(r'hee_seq <- c\((.*?)\)', THEME, re.S)[1])
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Arial','DejaVu Sans'],
    'font.size':9,'text.color':INK,'axes.labelcolor':SECONDARY,'xtick.color':SECONDARY,
    'ytick.color':SECONDARY,'axes.titleweight':'bold','axes.titlesize':10,'axes.labelsize':8.3,
    'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8,'legend.frameon':False,
    'figure.facecolor':BG,'axes.facecolor':BG,'savefig.facecolor':BG,'pdf.fonttype':42,'svg.fonttype':'none'})
CAPTIONS = {}
HOUSE_RC = dict(plt.rcParams)
def style(ax, grid='x'):
    for s in ax.spines.values(): s.set_visible(False)
    ax.tick_params(which='both',length=0)
    ax.set_axisbelow(True)
    if grid: ax.grid(axis=grid,color=GRID,lw=.3)
def title(fig, s): fig.text(.035,.975,s,fontsize=13,weight='bold',va='top')
def foot(fig,s,width=145,y=.025): fig.text(.035,y,textwrap.fill(s,width),fontsize=7.2,color=MUTED,va='bottom',linespacing=1.3)
def save(fig,stem,caption):
    CAPTIONS[stem]=caption
    for ext in ['png','pdf','svg']:
        fig.savefig(OUT/f'{stem}.{ext}',dpi=300)
    plt.close(fig)
    print('Saved',stem,flush=True)
def income_legend(fig,y=.92):
    fig.legend(handles=[Patch(color=BLUE,label='High-income settings'),Patch(color=ORANGE,label='Low- and middle-income settings')],
               loc='upper left',bbox_to_anchor=(.035,y),ncol=2)
def read(name): return pd.read_csv(ROOT/'data/raw'/name, dtype=str,keep_default_na=False)

def glance():
    import build_glance_regions_who_v4 as g
    captured={}
    def capture(v): captured.update(v); return ''
    g.render=capture
    g.OUT=str(DATA/'glance_calculation.txt')
    g.main()
    (DATA/'glance_calculation.txt').unlink()
    v=captured
    (DATA/'regional_profiles.json').write_text(json.dumps({k:v[k] for k in ['regions','themes','trend_years','trend_all','utility_linked']},indent=2),encoding='utf-8')
    pd.DataFrame(v['map_rows']).to_csv(DATA/'country_evaluation_counts.csv',index=False)
    pd.DataFrame(v['rate_rows']).to_csv(DATA/'country_evaluation_rates.csv',index=False)
    shapes=DATA/'natural_earth_countries.geojson'
    if not shapes.exists():
        urllib.request.urlretrieve('https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson',shapes)
    features=json.loads(shapes.read_text(encoding='utf-8'))['features']
    counts={r['iso3']:r['n'] for r in v['map_rows']}
    fig=plt.figure(figsize=(11.5,6.8));title(fig,'The evidence at a glance')
    kpis=[(f"{v['n_studies']:,}",'studies, 2010–2026'),(f"{v['ee_share']:.0%}",'full economic evaluations'),(str(v['n_named']),'countries or territories'),(f"{v['oa_known']:.0%}",'open access'),(f"{v['funder_share']:.0%}",'report a funder')]
    for i,(val,lab) in enumerate(kpis):
        x=.035+i*.193
        fig.text(x,.875,val,fontsize=20,weight='bold');fig.text(x,.837,lab,fontsize=8,color=SECONDARY)
    ax=fig.add_axes([.035,.16,.93,.61]);ax.set_xlim(-180,180);ax.set_ylim(-60,85);ax.set_aspect('equal');ax.axis('off')
    cmap=LinearSegmentedColormap.from_list('hee_sequential',SEQ)
    norm=Normalize(v['count_zmin'],v['count_zmax']);patches=[];colors=[]
    for f in features:
        p=f['properties'];iso=p.get('ADM0_A3');iso={'SDS':'SSD'}.get(iso,iso)
        if iso=='ATA':continue
        geom=f['geometry'];polys=geom['coordinates'] if geom['type']=='MultiPolygon' else [geom['coordinates']]
        r=counts.get(iso)
        col=cmap(norm(math.log10(r))) if r else GRID
        for poly in polys: patches.append(Polygon(poly[0]));colors.append(col)
    ax.add_collection(PatchCollection(patches,facecolors=colors,edgecolors=BG,linewidths=.25))
    for code,(lon,lat) in g.REGION_TAG_POS.items():
        ax.text(lon,lat,code,color=BG,weight='bold',fontsize=9,ha='center',va='center',bbox=dict(facecolor=INK,edgecolor='none',pad=3))
    ca=fig.add_axes([.16,.13,.68,.017]);cb=fig.colorbar(matplotlib.cm.ScalarMappable(norm=norm,cmap=cmap),cax=ca,orientation='horizontal')
    ticks=np.arange(math.ceil(v['count_zmin']),math.floor(v['count_zmax'])+1)
    cb.set_ticks(ticks,labels=[f'{10.**t:g}' for t in ticks]);cb.outline.set_visible(False)
    cb.set_label('Number of full economic evaluations (log colour scale)')
    fig.text(.035,.78,f"A  Geographic distribution of full economic evaluations (n = {len(v['ees']):,})",fontsize=10,weight='bold')
    fig.legend(handles=[Patch(color=GRID,label='No recorded full economic evaluations')],loc='lower right',bbox_to_anchor=(.98,.06),fontsize=7)
    caption='Eligible studies, 2010–2026; 2026 is incomplete. Panel A shows full evaluation counts using complete study geography, without disease-burden matching. Each evaluation counts once per named country; multi-country evaluations appear in several countries. Evaluations without a named country are not located. Grey: no recorded full evaluations. Small territories may not be visible at this scale.'
    foot(fig,caption,170);save(fig,'01_evidence_at_a_glance',caption)
    # Six aligned regional profiles, retaining the source values and top-three diseases.
    fig=plt.figure(figsize=(13,9.8));title(fig,'Profile of studies by WHO region')
    fig.text(.035,.945,textwrap.fill(v['burden_coverage_note'],210),fontsize=7,color=SECONDARY,va='top',linespacing=1.3)
    for i,(val,lab) in enumerate([(f"{v['ee_rate']:.1f}",'evaluations per 100,000 DALYs'),(f"{v['utility_all']:.0%}",'report QALYs or DALYs'),(f"{v['model_all']:.0%}",'use some modelling')]):
        fig.text(.035+i*.32,.875,val,fontsize=19,weight='bold');fig.text(.035+i*.32,.847,lab,fontsize=9,color=SECONDARY)
    cats=g.CATEGORIES;cols=[BLUE,ORANGE,AQUA]
    fig.legend(handles=[Patch(color=c,label=l) for c,l in zip(cols,cats)],loc='upper left',bbox_to_anchor=(.035,.84),ncol=3)
    for j,r in enumerate(v['regions']):
        x=.035+j*.16;w=.143
        fig.text(x,.755,r['code'],fontsize=12,weight='bold')
        fig.text(x,.718,textwrap.fill(r['name'],20),fontsize=8.3,color=SECONDARY,va='top')
        fig.text(x,.661,f"n = {r['n']:,}",fontsize=9)
        fig.text(x,.626,f"{r['rate']:.2f} per 100,000 DALYs",fontsize=7.5,color=SECONDARY)
        ax=fig.add_axes([x,.426,w,.17]);ax.axis('off');ax.set_xlim(-.6,9.6);ax.set_ylim(-1.5,10)
        shares=[r['disease'][c] for c in cats];n=np.array(shares)*100;n=np.floor(n).astype(int)
        for k in np.argsort(-(np.array(shares)*100-n))[:100-sum(n)]:n[k]+=1
        cc=np.repeat(cols,n);ax.scatter(np.tile(np.arange(10),10),np.repeat(np.arange(9,-1,-1),10),c=cc,s=14,lw=0)
        for k,(s,c) in enumerate(zip(shares,cols)):ax.text(k*3.5,-1.1,f'{s:.0%}',color=c,fontsize=8,ha='left')
        fig.text(x,.402,'Top three diseases',fontsize=8,weight='bold')
        for k,d in enumerate(v['themes'][r['code']]['top']):
            fig.text(x,.373-k*.043,textwrap.fill(d['disease'],22),fontsize=7.5,color=SECONDARY,va='top')
            fig.text(x+w,.373-k*.043,f"{d['share']:.0%}",fontsize=7.5,ha='right',va='top')
        fig.text(x,.219,f"{r['utility']:.0%} report QALYs or DALYs",fontsize=8,weight='bold')
        ax=fig.add_axes([x,.187,w,.015]);ax.barh(0,1,color=GRID);ax.barh(0,r['utility'],color=BLUE);ax.axvline(v['utility_linked'],color=ORANGE,lw=1);ax.set_xlim(0,1);ax.axis('off')
        ax=fig.add_axes([x,.075,w,.085]);style(ax,'y')
        ax.plot(v['trend_years'],v['trend_all'],color=MUTED,lw=.7)
        ax.plot(v['trend_years'],r['trend1'],color=INK,lw=.9)
        ax.plot(v['trend_years'],r['trend2'],color=INK,lw=.9,ls='--')
        ax.set_ylim(0,105);ax.set_yticks([0,100],['0%','100%']);ax.set_xticks([2010,2025]);ax.tick_params(labelsize=6)
    caption='Full economic evaluations only; studies naming multiple regions contribute to each. Disease dots show fractional shares across three GBD classes among disease-coded evaluations; one dot is about 1%. Utility bar: QALY or DALY reporting; orange marker: all linked evaluations. Trends: cumulative share of countries with ≥1 evaluation (solid), ≥2 (dashed), all regions ≥1 (grey); 2026 excluded as incomplete.'
    foot(fig,caption,200,y=.012);save(fig,'02_regional_profiles',caption)

def interventions():
    import build_intervention_redesign as b
    counts,_=b.load();fig=plt.figure(figsize=(10,10.4));title(fig,'Studies by intervention and country income')
    income_legend(fig,.947)
    gs=fig.add_gridspec(3,3,left=.035,right=.965,top=.87,bottom=.10,hspace=.38,wspace=.15)
    rows=[]
    for idx,(k,(h,l)) in enumerate(sorted(counts.items(),key=lambda kv:-sum(kv[1]))):
        n=h+l;i=np.arange(n)+.5;rad=np.sqrt(i/n);theta=i*math.pi*(3-math.sqrt(5));x=rad*np.cos(theta);y=rad*np.sin(theta)
        sort=np.argsort(y);x=x[sort]*math.sqrt(n/9917);y=y[sort]*math.sqrt(n/9917)
        ax=fig.add_subplot(gs[idx//3,idx%3]);ax.scatter(x[l:],y[l:],s=.8,color=BLUE,lw=0);ax.scatter(x[:l],y[:l],s=.8,color=ORANGE,lw=0)
        ax.set(xlim=(-1.08,1.08),ylim=(-1.08,1.08),aspect='equal');ax.axis('off')
        ax.set_title(f'{b.LABEL[k]}\n{l/n:.0%} L&MICs · {n:,} studies',fontsize=9,color=INK,fontweight='normal')
        rows.append(dict(intervention=k,label=b.LABEL[k],high_income=h,low_middle_income=l,lmic_share=l/n))
    pd.DataFrame(rows).to_csv(DATA/'interventions.csv',index=False)
    caption='One dot = one study; circle area is proportional to study count. Orange dots fill from the bottom. Base: 27,897 single-country eligible studies with a known publication-year World Bank income group. Includes reviews, matching the supplied figure. Intervention is the primary class assigned from the abstract. L&MICs includes low-, lower-middle- and upper-middle-income settings.'
    foot(fig,caption,150);save(fig,'03_intervention_circles',caption)

def outcomes(master):
    single=master[(master.geo_scope=='single_country') & master.income_group_pubyear.isin(['High income','Upper middle income','Lower middle income','Low income'])].copy()
    single['setting']=np.where(single.income_group_pubyear=='High income','High income','Low & middle income')
    o=read('hee_outcomes_long.csv')[['record_id','family']].drop_duplicates();o=o.merge(single[['record_id','year','setting']],on='record_id')
    ns=single.groupby('setting').size();ct=o.groupby(['family','setting']).size().unstack(fill_value=0)
    shares=ct.div(ns,axis='columns');keep=[s for s in shares.index if s.lower()!='other clinical' and shares.loc[s].max()>=.05]
    original_order=['QALYs','Survival / mortality','Adverse events / harms','Symptoms / clinical scores','Quality of life / function','Major clinical events','Life-years','Incidence / cases detected','DALYs','Biomarkers / physiological','Disease progression']
    keep.sort(key=lambda f:original_order.index(f) if f in original_order else len(original_order));shares.to_csv(DATA/'outcome_family_shares.csv')
    fig=plt.figure(figsize=(11,6.4));title(fig,'Consequences measured by health economic evaluations, by income setting');income_legend(fig,.94)
    ax=fig.add_axes([.225,.19,.35,.64]);style(ax);yy=np.arange(len(keep))
    for k,(setting,col) in enumerate([('Low & middle income',ORANGE),('High income',BLUE)]):
        vals=shares.loc[keep,setting].values;ys=yy+(k-.5)*.36;ax.barh(ys,vals,height=.31,color=col)
        for y,val in zip(ys,vals):ax.text(val+.005,y,f'{val:.0%}',fontsize=7,color=SECONDARY,va='center')
    ax.set_yticks(yy,keep);ax.invert_yaxis();ax.set_xlim(0,.64);ax.xaxis.set_major_formatter(PercentFormatter(1));ax.set_xticks([0,.2,.4,.6]);ax.set_xlabel('Share of single-country evaluations');ax.set_title('A  Consequences measured',loc='left')
    ax=fig.add_axes([.68,.19,.285,.64]);style(ax,'y');export=[]
    for setting,col in [('High income',BLUE),('Low & middle income',ORANGE)]:
        den=single[(single.setting==setting)&(single.year.astype(int)<=2025)].groupby('year').size()
        for fam,ls in [('QALYs','-'),('DALYs',(0,(3,2)))]:
            num=o[(o.setting==setting)&(o.family==fam)].groupby('year').size();val=num.reindex(den.index,fill_value=0)/den
            ax.plot(den.index.astype(int),val,color=col,lw=1.2,ls=ls)
            export.extend(dict(setting=setting,family=fam,year=y,share=v,n=int(den[y])) for y,v in val.items())
    ax.set_ylim(0,.65);ax.set_xticks([2010,2015,2020,2025]);ax.set_yticks([0,.2,.4,.6]);ax.yaxis.set_major_formatter(PercentFormatter(1));ax.set_ylabel('Share of single-country evaluations');ax.set_title('B  QALYs and DALYs over time',loc='left')
    ax.legend(handles=[Line2D([],[],color=INK,lw=1.2,label='QALYs'),Line2D([],[],color=INK,lw=1.2,ls='--',label='DALYs')],loc='lower right')
    pd.DataFrame(export).to_csv(DATA/'outcomes_over_time.csv',index=False)
    caption=f'Base: {len(single):,} single-country eligible studies with a known publication-year World Bank income group ({ns["High income"]:,} high income; {ns["Low & middle income"]:,} low and middle income). A study can report several outcome families. Panel A omits the residual other-clinical family and families below 5% in both settings. Panel B excludes incomplete 2026. Consequences are extracted from titles and abstracts; reporting does not establish quality.'
    foot(fig,caption,170);save(fig,'04_consequences_by_income',caption)

def topics():
    import income_pubyear_figure_data as fd
    import build_income_pubyear_figures as b
    plt.rcParams.update(HOUSE_RC)
    rows,labels,_=fd.load(str(ROOT/'data/raw'));th,names,overall,n=fd.theme_rank(rows,labels,fd.CODINGS['pubyear'])
    names={c:b.TOPIC_NAMES.get(c,s) for c,s in names.items()}
    fig=plt.figure(figsize=(10,9));title(fig,'Research topics with the strongest income focus');income_legend(fig,.95);export=[]
    for k,(cs,col,ref,lab) in enumerate([(sorted(th,key=lambda c:th[c][0])[:15],BLUE,1-overall,'A  Highest shares in high-income settings'),(sorted(th,key=lambda c:-th[c][0])[:15],ORANGE,overall,'B  Highest shares in low- and middle-income settings')]):
        ax=fig.add_axes([.33,.55-k*.415,.62,.32]);style(ax)
        vals=[1-th[c][0] if k==0 else th[c][0] for c in cs];ax.barh(range(15),vals,color=col,height=.65)
        for i,(c,val) in enumerate(zip(cs,vals)):
            ax.text(val+.007,i,f'{val:.0%}',fontsize=8,va='center');export.append(dict(panel=k,topic=c,name=names[c],n=th[c][1],share=val))
        ax.set_yticks(range(15),[f'{names[c]}  ({th[c][1]:,})' for c in cs]);ax.invert_yaxis();ax.axvline(ref,color=MUTED,ls='--',lw=.7)
        ax.set_xlim(0,1);ax.set_xticks([0,.25,.5,.75,1]);ax.xaxis.set_major_formatter(PercentFormatter(1));ax.set_title(lab,loc='left')
    pd.DataFrame(export).to_csv(DATA/'topic_rankings.csv',index=False)
    caption=f'Number of studies in brackets. Dashed line: the corresponding income share across all topic-assigned studies. Topics group similar titles and abstracts; {len(th)} topics with at least 30 classified single-country studies qualify. Income is the World Bank group in force on 1 January of publication year. Includes eligible reviews, matching the supplied figure; 2026 is incomplete.'
    foot(fig,caption,145);save(fig,'05_topics_by_income',caption)

def ratios():
    src=ROOT/'exports/grouped_pooled_disease_ratios_2026-10-14';df=pd.read_csv(src/'figure_data.csv')
    shutil.copy2(src/'figure_data.csv',DATA/'disease_burden_ratios.csv');shutil.copy2(src/'provenance.json',DATA/'disease_burden_provenance.json')
    fig=plt.figure(figsize=(10,11));title(fig,'Research share relative to pooled disease burden');income_legend(fig,.95)
    ax=fig.add_axes([.36,.16,.60,.70]);style(ax);ax.set_xscale('log');pos={};headers=[];y=0
    names={'cmnn':'Communicable, maternal, neonatal & nutritional','ncd':'Non-communicable diseases','inj':'Injuries'}
    for group in ['cmnn','ncd','inj']:
        headers.append((y,group));y+=1.15
        for cause in df[df.level1==group].cause.drop_duplicates():pos[cause]=y;y+=1
        y+=.5
    for cause,yy in pos.items():
        d=df[df.cause==cause].set_index('setting');a=d.loc['hic','ratio'];b=d.loc['lmic','ratio']
        ax.plot([a,b],[yy,yy],color=GRID,lw=1.3);ax.scatter([a,b],[yy,yy],color=[BLUE,ORANGE],s=23,zorder=3)
    for yy,g in headers:ax.text(-.54,yy,textwrap.fill(names[g],40),transform=ax.get_yaxis_transform(),weight='bold',fontsize=8,va='center')
    labels=df.drop_duplicates('cause').set_index('cause').label
    ax.set_yticks(list(pos.values()),[labels[c] for c in pos]);ax.set_ylim(y,-.6);ax.axvline(1,color=MUTED,ls='--',lw=.7)
    ax.set_xlim(.008,20);ticks=[.01,.03,.1,.3,1,3,10];ax.set_xticks(ticks,[f'{t:g}×' for t in ticks]);ax.xaxis.set_minor_formatter(NullFormatter());ax.set_xlabel('Share of research ÷ share of pooled DALYs (log scale)')
    caption='Research: eligible 2010–2026 publications (2026 incomplete), naming a level-2 cause and classified setting. Burden: GBD 2023 DALYs summed over 2010–2023. Research uses publication-year income; burden uses burden-year income. Multi-cause and multi-setting studies can contribute more than once. Groups follow GBD level 1; rows follow global pooled burden. The 1× reference indicates equal shares, not an adequacy target. See source data for denominators and provenance.'
    foot(fig,caption,145);save(fig,'06_research_relative_to_burden',caption)

def main():
    OUT.mkdir(exist_ok=True);DATA.mkdir(exist_ok=True)
    shutil.copy2(ROOT/'docs/theme_hee.R',DATA/'theme_hee.R')
    glance();interventions()
    m=read('hee_analysis_master_v2_1.csv');m=m[m.is_eligible=='TRUE'];assert len(m)==41610
    outcomes(m);topics();ratios()
    (OUT/'README.md').write_text('# Manuscript figures — 19 October 2026\n\nSix standalone figures in PNG (300 dpi), PDF and editable-text SVG. No visual-map or site files are changed.\n\nStyle follows docs/theme_hee.R: white paper, sans-serif type, fixed income colours, first three categorical colours for regional disease dots, sequential blue map for magnitude, thin marks, recessive one-direction grids and legends. Python/Matplotlib implements the R style because the existing data builders are Python. The source theme is copied into source data; its stale denominator notes are not used.\n\nThe supplied figures have different populations: the overview/regional profiles use full evaluations for their analytic panels; intervention circles, outcomes, topics and burden ratios retain their original eligible-study populations, including eligible reviews. These differences are stated in captions.\n\n'+ '\n\n'.join(f'## {k}\n\n{v}' for k,v in CAPTIONS.items())+'\n\nRebuild: python -B scripts/create_manuscript_figures_oct19.py\nNatural Earth country boundaries: https://github.com/nvkelso/natural-earth-vector (110m admin-0 countries).\n',encoding='utf-8')
    (DATA/'build_provenance.json').write_text(json.dumps({'date':'2026-10-19','theme_sha256':hashlib.sha256(THEME.encode()).hexdigest(),'master_sha256':hashlib.sha256((ROOT/'data/raw/hee_analysis_master_v2_1.csv').read_bytes()).hexdigest(),'eligible_n':len(m),'colours':{'high_income':BLUE,'low_middle_income':ORANGE,'third_category':AQUA},'site_modified':False},indent=2),encoding='utf-8')

if __name__=='__main__':main()
