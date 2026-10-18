"""Standalone reviewer-requested disease gap movement figure; never alters map files."""
import csv
import hashlib
import json
import math
import textwrap
from collections import Counter
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
import build_gbd_figures as gbd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'exports/gap_movement_feedback_2026-10-14'
EARLY=(2010,2012);LATE=(2021,2023)
def main():
    OUT.mkdir(exist_ok=True)
    rows,geo,l1,burden=gbd.load(str(ROOT/'data/raw'))
    assert len(rows)==41610
    assert all(y in burden for y in range(2010,2024)), 'Need complete pooled DALYs, 2010–2023'
    specific=set(gbd.LABEL)-gbd.NOT_STATED
    injury={c for c in specific if l1[c]=='inj'}
    causes=[c for c in gbd.LABEL if c in specific-injury]+['All injuries']
    groups={c:l1[c] for c in causes if c!='All injuries'}|{'All injuries':'inj'}
    def row_causes(record):
        disease=record['gbd']
        mapped=set(disease)&(specific-injury)
        if disease & (injury|{'Injuries, cause not stated'}):mapped.add('All injuries')
        return mapped
    def research(period):
        selected=[r for r in rows if 'lmic' in r['sides'] and period[0]<=r['year']<=period[1] and row_causes(r)]
        counts=Counter(c for r in selected for c in row_causes(r))
        return len(selected),counts
    n0,k0=research(EARLY);n1,k1=research(LATE)
    def pooled(years):
        count=Counter()
        for year in years:
            for c in specific:
                count['All injuries' if c in injury else c]+=burden[year]['lmic'][c]
        return count
    ordering=pooled(range(2010,2024));reference=pooled(range(2021,2024))
    total=sum(reference.values())
    assert len(causes)==20 and all(reference[c]>0 for c in causes)
    results=[]
    for c in causes:
        p=reference[c]/total;q0=k0[c]/n0;q1=k1[c]/n1
        gap0=abs(q0-p);gap1=abs(q1-p)
        status='Closer' if gap1<gap0-1e-12 else ('Farther' if gap1>gap0+1e-12 else 'Unchanged')
        results.append(dict(cause=c,label='All injuries' if c=='All injuries' else gbd.LABEL[c],level1=groups[c],
                            pooled_dalys_2010_2023=ordering[c],pooled_dalys_2021_2023=reference[c],
                            daly_share_2021_2023=p,early_count=k0[c],late_count=k1[c],early_n=n0,late_n=n1,
                            research_share_2010_2012=q0,research_share_2021_2023=q1,
                            ratio_early=q0/p,ratio_late=q1/p,absolute_gap_early_pp=100*gap0,
                            absolute_gap_late_pp=100*gap1,change_in_absolute_gap_pp=100*(gap1-gap0),status=status))
    results.sort(key=lambda r:(['cmnn','ncd','inj'].index(r['level1']),-r['pooled_dalys_2010_2023']))
    for group in ['cmnn','ncd','inj']:
        values=[r['pooled_dalys_2010_2023'] for r in results if r['level1']==group]
        assert values==sorted(values,reverse=True)
    plt.rcParams.update({'font.family':'Arial','svg.fonttype':'none','pdf.fonttype':42})
    bg='#f7f4ee';ink='#20211f';muted='#79786e'
    palette={'Closer':'#24835a','Farther':'#c34c35','Unchanged':'#858477'}
    # Linear ratios preserve zero-study observations; identical final burden reference for both points.
    fig=plt.figure(figsize=(12.2,12.4),facecolor=bg)
    fig.text(.035,.974,'WHICH RESEARCH GAPS ARE NARROWING, AND WHICH ARE NOT',fontsize=20.5,fontweight='bold',color=ink,va='top')
    subtitle=('LMIC research share in 2010–2012 (dot) and 2021–2023 (arrowhead), each divided by the same '
              '2021–2023 share of DALYs. The matched line marks proportional research and burden shares.')
    fig.text(.035,.935,textwrap.fill(subtitle,118),fontsize=11.7,color=muted,va='top',linespacing=1.5)
    fig.legend(handles=[Line2D([0],[0],color='#929084',marker='o',linestyle='',label='2010–2012 research share'),
                        Line2D([0],[0],color='#657d90',marker='>',linestyle='-',label='2021–2023 research share'),
                        Line2D([0],[0],color=palette['Closer'],linewidth=3,label='Closer to burden share'),
                        Line2D([0],[0],color=palette['Farther'],linewidth=3,label='Farther from burden share')],
               loc='upper left',bbox_to_anchor=(.23,.89),frameon=False,ncol=2,fontsize=10,columnspacing=2)
    ax=fig.add_axes([.325,.205,.50,.61],facecolor=bg)
    positions=[];headers=[];y=0;last=None
    heading={'cmnn':'Communicable, maternal, neonatal & nutritional','ncd':'Non-communicable diseases','inj':'Injuries (one combined group)'}
    for r in results:
        if r['level1']!=last:
            if last is not None:y+=.45
            headers.append((y,heading[r['level1']]));y+=1.0;last=r['level1']
        positions.append(y);y+=1
    max_ratio=max(max(r['ratio_early'],r['ratio_late']) for r in results)
    xmax=max(2,math.ceil(max_ratio*1.12*2)/2)
    ax.axvspan(0,1,color='#efe7dc',alpha=.55,zorder=0)
    ax.axvline(1,color='#747369',linestyle=(0,(2,2)),linewidth=1.2,zorder=1)
    ax.grid(axis='x',color='#e4e0d8',linewidth=.7);ax.set_axisbelow(True)
    for r,pos in zip(results,positions):
        a,b=r['ratio_early'],r['ratio_late'];colour=palette[r['status']]
        if not math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-12):
            ax.plot([a,b],[pos,pos],color=colour,linewidth=2.1,zorder=3)
            ax.scatter([b],[pos],marker='>' if b>a else '<',s=48,color=colour,zorder=4)
        else:ax.scatter([b],[pos],marker='>',s=32,color=colour,zorder=4)
        ax.scatter([a],[pos],s=27,color='#929084',zorder=5)
        ax.text(1.03,pos,r['status'],transform=ax.get_yaxis_transform(),color=colour,fontsize=10.6,va='center',fontweight='bold')
    for pos,label in headers:
        ax.text(-.575,pos,label,transform=ax.get_yaxis_transform(),fontsize=11.0,color=ink,va='center',fontweight='bold',clip_on=False)
    ax.set_xlim(0,xmax);ax.set_ylim(y-.2,-.7)
    ax.set_yticks(positions,[r['label'] for r in results],fontsize=10.7,color=muted)
    ticks=np.arange(0,xmax+.01,1 if xmax>4 else .5)
    ax.set_xticks(ticks,[('matched\n1×' if math.isclose(t,1) else f'{t:g}×') for t in ticks],fontsize=10.4,color=muted)
    ax.tick_params(axis='both',length=0,pad=8)
    for s in ax.spines.values():s.set_visible(False)
    ax.set_xlabel('Share of LMIC research ÷ share of LMIC DALYs in 2021–2023 (linear scale)',fontsize=11.0,color=muted,labelpad=13)
    foot=(f'Latest dataset: 41,610 included records. Research base: {n0:,} disease-coded LMIC records in 2010–2012 '
          f'and {n1:,} in 2021–2023; a record can contribute to several disease rows, but only once to All injuries. '
          'Rows are grouped by GBD level 1 and ordered within groups by summed LMIC DALYs across 2010–2023. '
          'The injury row includes all three level-2 injury causes and records naming an injury without its cause. '
          'Unspecified infections cannot be assigned to a level-2 row and are omitted unless another plotted cause is named. '
          'Both research periods use pooled 2021–2023 DALY shares as their fixed reference. Closer/farther compares the '
          'absolute percentage-point gap to that reference, including movement above or across the matched line. '
          'Country studied and publication-year income define research settings; burden-year income defines LMIC DALYs. '
          'No minimum-count rows are dropped; this is a descriptive comparison without uncertainty intervals.')
    fig.text(.035,.12,textwrap.fill(foot,160),fontsize=8.7,color=muted,va='top',linespacing=1.3)
    stem=OUT/'research_gap_movement_LMIC_2010-12_to_2021-23'
    for ext in ['png','pdf','svg']:fig.savefig(stem.with_suffix('.'+ext),dpi=200,facecolor=bg)
    # Alternative view: same values/order/reference/colours, more room below matched.
    minimum=min(min(r['ratio_early'],r['ratio_late']) for r in results)
    assert minimum>0,'Do not put a genuine zero observation on a log axis'
    ax.set_xscale('log');ax.set_xlim(minimum/1.35,xmax)
    ticks=[t for t in [.1,.2,.5,1,2,4,8] if minimum/1.35<=t<=xmax]
    ax.set_xticks(ticks,[('matched\n1×' if t==1 else f'{t:g}×') for t in ticks],fontsize=10.4,color=muted)
    ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set_xlabel('Share of LMIC research ÷ share of LMIC DALYs in 2021–2023 (log scale)',fontsize=11.0,color=muted,labelpad=13)
    logstem=OUT/'research_gap_movement_LMIC_2010-12_to_2021-23_log'
    for ext in ['png','pdf','svg']:fig.savefig(logstem.with_suffix('.'+ext),dpi=200,facecolor=bg)
    plt.close(fig)
    with (OUT/'figure_data.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(results[0]));w.writeheader();w.writerows(results)
    sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'data/raw/GBD data').glob('*.csv')}
    metadata={'eligible_records':41610,'early_window':EARLY,'late_window':LATE,'ordering_years':[2010,2023],
              'fixed_burden_reference':LATE,'early_n':n0,'late_n':n1,'rows':len(results),
              'alternative_axis':'Log view of identical ratios and identical absolute-share-gap colour decisions',
              'statuses':dict(Counter(r['status'] for r in results)),'axis':'linear research share / fixed late DALY share; matched = 1',
              'zero_research_rows':[r['cause'] for r in results if not r['early_count'] or not r['late_count']],
              'source_hashes':sources,'burden_unclassified_locations':burden['left_out'],'map_modified':False}
    (OUT/'provenance.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    (OUT/'README.md').write_text('''# Standalone disease-gap movement figure

The attached earlier version did not fully implement the feedback. This version:

- Groups communicable/maternal/neonatal/nutritional diseases first, NCDs next, and all injuries in one final row.
- Orders level-2 rows within each group by the sum of LMIC DALYs over all 14 years, 2010–2023. It does not average annual shares.
- Uses a grey dot for 2010–2012 research and an arrowhead for 2021–2023 research, the latest matching complete DALY window.
- Divides both research shares by the same pooled 2021–2023 DALY share; 1 is matched. The reference is fixed so movement reflects changes in research mix, not changes in the burden denominator.
- Uses green Closer or red Farther based on the change in absolute research-minus-burden percentage-point gap. An overshoot can therefore be farther even when it ends above matched.

The main file uses a linear ratio scale, which can include zero-research observations. The `_log` alternative uses the same values, ordering and colours; all current observations are positive. It better separates the small ratios because the observed range is approximately 0.15 to 7.4. No categories are dropped for low counts. Ratios describe relative shares, not whether research is sufficient. The population is studies about LMIC settings, including mixed-income multi-country studies and eligible reviews. Research shares have a unique disease-coded-record denominator within each window; they need not sum to 100% because records can name several causes.

The all-injuries row deduplicates records across injury codes and includes injuries with no specified level-2 cause. Its DALYs sum transport, unintentional and self-harm/interpersonal-violence injuries. Infections with no specified cause cannot be assigned to a displayed level-2 cause. This differs from the old figure's exclusion of unspecified injuries and its minimum-15-record rule.

Income rules are the current map rules: publication-year income for study settings, burden-year income for DALYs, with the existing recorded overrides. Missing burden-year classifications are listed in provenance.json. This is a descriptive movement comparison; the colour does not establish a statistically significant change or a causal response to burden.

figure_data.csv contains exact row counts, shares, ratios, pooled DALYs and closeness calculations. provenance.json records the source hashes and validation settings. No map files were changed.
''',encoding='utf-8')
    print(json.dumps(metadata,indent=2))
if __name__=='__main__':main()
