"""Standalone variant of paper08: GBD level-1 grouping and pooled 2010–2023 DALYs."""
import csv
import hashlib
import json
import textwrap
from collections import Counter
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import build_gbd_figures as gbd
import build_kld_replication as source

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'exports/grouped_pooled_disease_ratios_2026-10-14'
BG='#f7f4ee';INK='#252721';MUTED='#79776e';ORANGE='#ed7138';BLUE='#337fcf'
GROUPS=['cmnn','ncd','inj']
GROUP_NAMES={'cmnn':'COMMUNICABLE / MATERNAL / NEONATAL / NUTRITIONAL',
             'ncd':'NON-COMMUNICABLE DISEASES','inj':'INJURIES'}

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    raw=str(ROOT/'data/raw')
    rows,_,l1,_=gbd.load(raw)
    assert len(rows)==41610
    # Same burden-year World Bank method and missing-year overrides as current KLD figures.
    burden,missing=source.load_dalys(raw)
    years=sorted(burden)
    assert years==list(range(2010,2024))
    causes=[c for c in gbd.LABEL if c not in gbd.NOT_STATED]
    assert len(causes)==22
    pooled_global={c:sum(burden[y]['all'][c] for y in years) for c in causes}
    causes.sort(key=lambda c:(GROUPS.index(l1[c]),-pooled_global[c]))
    result={};export=[]
    for side in ['lmic','hic']:
        coded=[r for r in rows if side in r['sides'] and r['gbd']&set(causes)]
        count=Counter(c for r in coded for c in r['gbd']&set(causes))
        dalys={c:sum(burden[y][side][c] for y in years) for c in causes}
        total=sum(dalys.values())
        result[side]={}
        for c in causes:
            research=count[c]/len(coded);bs=dalys[c]/total
            r=dict(setting=side,level1=l1[c],cause=c,label=gbd.LABEL[c],research_numerator=count[c],
                   research_denominator=len(coded),research_share=research,pooled_dalys=dalys[c],
                   pooled_daly_share=bs,ratio=research/bs,ordering_pooled_global_dalys=pooled_global[c])
            export.append(r);result[side][c]=r
        assert np.isclose(sum(r['pooled_daly_share'] for r in result[side].values()),1)
    plt.rcParams.update({'font.family':'Arial','svg.fonttype':'none','pdf.fonttype':42})
    fig=plt.figure(figsize=(12,14.2),facecolor=BG)
    fig.text(.04,.975,'RESEARCH SHARE RELATIVE TO POOLED DISEASE BURDEN',fontsize=21,fontweight='bold',color=INK,va='top')
    sub=('Diseases grouped by GBD level 1; within each group, ordered by total global DALYs over 2010–2023.\n'
         'Each dot is the share of studies divided by the share of DALYs summed across all 14 available years.\n'
         'Left of 1: a smaller share of research than of burden. The line connects the two income settings.')
    fig.text(.04,.934,sub,fontsize=12.1,color=MUTED,va='top',linespacing=1.6)
    fig.legend(handles=[Line2D([],[],marker='o',ls='',color=ORANGE,markersize=9,label='Low- and middle-income countries (L&MICs)'),
                        Line2D([],[],marker='o',ls='',color=BLUE,markersize=9,label='High-income countries (HICs)')],
               loc='upper left',bbox_to_anchor=(.30,.86),ncol=1,frameon=False,fontsize=11.5,labelspacing=.8)
    pos={};headers=[];y=0
    for group in GROUPS:
        headers.append((y,group));y+=1.05
        for c in causes:
            if l1[c]==group:pos[c]=y;y+=1
        y+=.5
    ax=fig.add_axes([.34,.19,.60,.59],facecolor=BG)
    vals=[r['ratio'] for r in export]
    assert min(vals)>0
    lo=min(.01,min(vals)/1.4);hi=max(12,max(vals)*1.5)
    ax.set_xscale('log');ax.set_xlim(lo,hi);ax.set_ylim(y-.3,-.6)
    ax.axvspan(lo,1,color='#eee4d7',alpha=.55,zorder=0)
    ax.axvline(1,color=MUTED,lw=1.2,ls=(0,(2,2)))
    ax.grid(axis='x',color='#e2ded5',lw=.8);ax.set_axisbelow(True)
    for c in causes:
        a,b=result['lmic'][c]['ratio'],result['hic'][c]['ratio']
        ax.plot([a,b],[pos[c],pos[c]],color='#c9c4b9',lw=3,zorder=2)
        ax.scatter([a,b],[pos[c],pos[c]],color=[ORANGE,BLUE],s=62,zorder=3)
    for p,g in headers:
        ax.text(-.50,p,GROUP_NAMES[g],transform=ax.get_yaxis_transform(),fontsize=10.0,fontweight='bold',color=INK,va='center',clip_on=False)
    ax.set_yticks([pos[c] for c in causes],[gbd.LABEL[c] for c in causes],fontsize=11,color=MUTED)
    ticks=[v for v in [.01,.03,.1,.3,1,3,10,30] if lo<=v<=hi]
    ax.set_xticks(ticks,['matched' if v==1 else f'{v:g}×' for v in ticks],fontsize=11,color=MUTED)
    ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.tick_params(length=0,pad=7)
    for sp in ax.spines.values():sp.set_visible(False)
    ax.set_xlabel('Share of research ÷ share of pooled DALYs (log scale)',fontsize=12,color=MUTED,labelpad=12)
    nl=export[0]['research_denominator'];nh=export[22]['research_denominator']
    foot=(f'Research: current eligible publications from 2010–2026 (2026 partial), naming a level-2 cause and a classified setting: '
          f'L&MICs n={nl:,}; HICs n={nh:,}. A publication counts once per named cause and can enter both settings; research shares can sum above 100%. '
          'Burden: GBD 2023-round DALY numbers, all ages, both sexes, summed across 2010–2023 and countries in each setting; '
          'cause shares are calculated from these sums, not averages of annual percentages. Research retains the original figure’s 2010–2026 period, '
          'which extends beyond the available burden years. Research uses publication-year income; burden uses burden-year income, with the same documented overrides as the KLD analysis. '
          'L&MICs includes low-, lower-middle- and upper-middle-income countries. All 22 level-2 causes remain separate, including the three injury causes. '
          'Unspecified infection/injury codes are excluded; injury coding may undercount research. Missing income classifications are excluded from setting-specific burden. '
          'Matching research to burden is a reference point, not an adequacy target. These ratios use study shares and are not KLD.')
    fig.text(.04,.115,textwrap.fill(foot,155),fontsize=9.5,color=MUTED,va='top',linespacing=1.45)
    stem=OUT/'disease_ratios_grouped_level1_pooled_DALYs_2010_2023'
    for ext in ['png','svg']:fig.savefig(stem.with_suffix('.'+ext),dpi=200,facecolor=BG)
    plt.close(fig)
    with (OUT/'figure_data.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(export[0]));w.writeheader();w.writerows(export)
    meta=dict(eligible_records=41610,disease_count=22,research_years=[2010,2026],burden_years=years,
              pooling='Sum absolute DALYs over country-year rows, then calculate shares',
              order='Level-1 groups CMNN, NCDs, injuries; descending pooled global DALYs within each',
              income='Research: publication year. Burden: burden year; existing KLD overrides.',
              missing_income_locations_by_year={y:sorted(v) for y,v in missing.items()},
              research_denominators={'lmic':nl,'hic':nh},map_modified=False,
              master_sha256=hashlib.sha256((ROOT/'data/raw/hee_analysis_master_v2_1.csv').read_bytes()).hexdigest())
    (OUT/'provenance.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    (OUT/'README.md').write_text('# Grouped disease ratios with pooled DALYs\n\n'+foot+'\n\n'+
        'Rows are grouped by GBD level 1 and ordered by summed global DALYs across 2010–2023 within each group. This is a grouped display of all 22 level-2 causes, not an aggregation into three dots. Research retains the original figure period. The burden distribution is now pooled across all available years and uses burden-year income, rather than the original 2023-only burden reference. PNG/SVG, exact source values and provenance are saved standalone. No map files were changed.\n',encoding='utf-8')
    print('Saved grouped pooled-burden figure;',nl,'L&MICs records;',nh,'HIC records; 14 years, 22 causes.')

if __name__=='__main__':main()
