"""Exact additive disease contributions to research–burden mismatch, standalone."""
import csv
import hashlib
import json
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
OUT=ROOT/'exports/segmented_mismatch_2026-10-14'
EARLY=(2010,2012);LATE=(2021,2023);DRAWS=1000;SEED=20261014
def main():
    OUT.mkdir(exist_ok=True)
    rows,geo,l1,burden=gbd.load(str(ROOT/'data/raw'))
    assert len(rows)==41610
    causes=[c for c in gbd.LABEL if c not in gbd.NOT_STATED]
    assert len(causes)==22
    pooled={c:sum(burden[y]['lmic'][c] for y in range(2010,2024)) for c in causes}
    causes.sort(key=lambda c:(['cmnn','ncd','inj'].index(l1[c]),-pooled[c]))
    index={c:i for i,c in enumerate(causes)}
    p=np.array([sum(burden[y]['lmic'][c] for y in range(2021,2024)) for c in causes],dtype=float)
    p/=p.sum()
    matrices={}
    for y in [*range(2010,2013),*range(2021,2024)]:
        included=[r for r in rows if r['year']==y and 'lmic' in r['sides'] and r['gbd']&set(causes)]
        matrices[y]=np.array([[int(c in r['gbd']) for c in causes] for r in included],dtype=np.int8).reshape(-1,22)
    def q(period,rng=None):
        counts=np.zeros(22,dtype=float)
        for y in range(period[0],period[1]+1):
            matrix=matrices[y]
            if rng is not None:matrix=matrix[rng.integers(0,len(matrix),len(matrix))]
            counts+=matrix.sum(axis=0)
        return counts/counts.sum(),counts
    q0,k0=q(EARLY);q1,k1=q(LATE)
    c0=.5*np.abs(q0-p)*100;c1=.5*np.abs(q1-p)*100
    delta=c1-c0
    rng=np.random.default_rng(SEED)
    boot=np.empty((DRAWS,22))
    for draw in range(DRAWS):
        b0,_=q(EARLY,rng);b1,_=q(LATE,rng)
        boot[draw]=(.5*np.abs(b1-p)-.5*np.abs(b0-p))*100
    masks={g:np.array([l1[c]==g for c in causes]) for g in ['cmnn','ncd','inj']}
    assert np.isclose(p.sum(),1) and np.isclose(q0.sum(),1) and np.isclose(q1.sum(),1)
    assert np.isclose(sum(c0),50*sum(abs(q0-p))) and np.isclose(sum(c1),50*sum(abs(q1-p)))
    assert np.allclose(sum(boot[:,mask].sum(axis=1) for mask in masks.values()),boot.sum(axis=1))
    assert np.isclose(sum(delta),sum(c1)-sum(c0))
    def summary(kind,label,selected,group=None):
        draws=boot[:,selected].sum(axis=1)
        return {'section':kind,'label':label,'level1':group or '',
                'early_contribution_pp':float(c0[selected].sum()),'late_contribution_pp':float(c1[selected].sum()),
                'change_pp':float(delta[selected].sum()),'change_lo':float(np.percentile(draws,2.5)),
                'change_hi':float(np.percentile(draws,97.5))}
    overall=summary('overall','All 22 disease and injury causes',np.ones(22,dtype=bool))
    group_names={'cmnn':'Communicable, maternal, neonatal & nutritional','ncd':'Non-communicable diseases','inj':'All injuries'}
    parents=[summary('level1',group_names[g],masks[g],g) for g in masks]
    leaves=[]
    for i,c in enumerate(causes):
        mask=np.arange(22)==i
        r=summary('level2',gbd.LABEL[c],mask,l1[c])
        r.update(cause=c,pooled_dalys_2010_2023=pooled[c],daly_share_2021_2023=float(p[i]),
                 early_research_share=float(q0[i]),late_research_share=float(q1[i]),
                 early_cause_count=int(k0[i]),late_cause_count=int(k1[i]))
        leaves.append(r)
    assert np.isclose(sum(r['change_pp'] for r in leaves),overall['change_pp'])
    assert np.isclose(sum(r['change_pp'] for r in parents),overall['change_pp'])
    for parent in parents:
        assert np.isclose(sum(r['change_pp'] for r in leaves if r['level1']==parent['level1']),parent['change_pp'])
    n0=sum(len(matrices[y]) for y in range(2010,2013));n1=sum(len(matrices[y]) for y in range(2021,2024))
    plt.rcParams.update({'font.family':'Arial','svg.fonttype':'none','pdf.fonttype':42})
    bg='#f7f4ee';ink='#252721';muted='#75766d';green='#25835f';red='#c34d36'
    fig=plt.figure(figsize=(12.8,15.2),facecolor=bg)
    fig.text(.035,.972,'WHERE DOES THE CHANGE IN RESEARCH–BURDEN MISMATCH COME FROM?',fontsize=20,fontweight='bold',color=ink,va='top')
    subtitle=('LMIC research, 2010–2012 → 2021–2023, compared with a fixed 2021–2023 DALY reference. '
              'Disease contributions add to their level-1 group; the groups add to the overall change.')
    fig.text(.035,.937,textwrap.fill(subtitle,120),fontsize=11.4,color=muted,va='top',linespacing=1.4)
    fig.legend(handles=[Line2D([0],[0],color=green,lw=6,label='Reduces overall mismatch'),
                        Line2D([0],[0],color=red,lw=6,label='Increases overall mismatch'),
                        Line2D([0],[0],color='#85847b',marker='|',markersize=9,lw=1,label='95% bootstrap interval for change')],
               loc='upper left',bbox_to_anchor=(.24,.895),ncol=2,frameon=False,fontsize=10.4)
    ax=fig.add_axes([.335,.185,.435,.66],facecolor=bg)
    plotted=[];headers=[];y=0
    headers.append((y,'OVERALL'));y+=1
    plotted.append((y,overall));y+=1.6
    headers.append((y,'LEVEL 1 · GROUPED CONTRIBUTIONS'));y+=1
    for r in parents:plotted.append((y,r));y+=1
    y+=.65;headers.append((y,'LEVEL 2 · INDIVIDUAL CAUSES'));y+=1.25
    for g in masks:
        headers.append((y,group_names[g],True));y+=.85
        for r in leaves:
            if r['level1']==g:plotted.append((y,r));y+=1
        y+=.5
    low=min(min(r['change_pp'],r['change_lo']) for _,r in plotted)
    high=max(max(r['change_pp'],r['change_hi']) for _,r in plotted)
    span=max(abs(low),abs(high));ax.set_xlim(-span*1.12,span*1.12)
    ax.axvline(0,color='#8e8c82',lw=1.0,linestyle=(0,(2,2)))
    ax.grid(axis='x',color='#e3e0d8',linewidth=.7);ax.set_axisbelow(True)
    for pos,r in plotted:
        value=r['change_pp'];colour=green if value<0 else red
        ax.barh(pos,value,height=.55,color=colour,alpha=.8,zorder=2)
        ax.errorbar(value,pos,xerr=[[value-r['change_lo']],[r['change_hi']-value]],fmt='none',ecolor='#5d6259',capsize=2.5,elinewidth=1,zorder=3) if r['change_lo']<=value<=r['change_hi'] else ax.plot([r['change_lo'],r['change_hi']],[pos,pos],color='#5d6259',lw=1,zorder=3)
        ax.text(1.025,pos,f"{r['early_contribution_pp']:.2f} → {r['late_contribution_pp']:.2f}",transform=ax.get_yaxis_transform(),va='center',color=muted,fontsize=10.0)
    ax.text(1.025,-.68,'Contribution to mismatch\n2010–12 → 2021–23 (pp)',transform=ax.get_yaxis_transform(),color=muted,fontsize=9.4,va='bottom')
    for item in headers:
        pos,title=item[:2];sub=len(item)>2
        if sub:
            title={'Communicable, maternal, neonatal & nutritional':'Communicable / maternal / neonatal / nutritional','Non-communicable diseases':'Non-communicable diseases','All injuries':'Injuries'}[title]
        ax.text(-.675,pos,title,transform=ax.get_yaxis_transform(),color=muted if sub else ink,
                fontsize=9.8 if sub else 11.2,fontweight='bold',va='center',clip_on=False)
    labels=[]
    for _,r in plotted:
        label=r['label']
        if r['section']=='level1' and r['level1']=='cmnn':label='Communicable / maternal /\nneonatal / nutritional'
        labels.append(label)
    ax.set_yticks([pos for pos,_ in plotted],labels,fontsize=9.9,color=muted)
    ax.set_ylim(y-.4,-1.1);ax.tick_params(axis='both',length=0,pad=8,labelsize=10)
    for s in ax.spines.values():s.set_visible(False)
    ax.set_xlabel('Contribution to change in overall mismatch (percentage points)\n← Less mismatch                         More mismatch →',fontsize=10.9,color=muted,labelpad=12)
    headline=(f"Overall mismatch: {overall['early_contribution_pp']:.2f}% → {overall['late_contribution_pp']:.2f}%; "
              f"change {overall['change_pp']:+.3f} percentage points "
              f"(95% interval {overall['change_lo']:+.2f} to {overall['change_hi']:+.2f}).")
    fig.text(.035,.135,headline,fontsize=11.5,fontweight='bold',color=ink,va='top')
    foot=(f'Mismatch is total variation distance: ½ × Σ |research share − DALY share|. Each level-2 cause contributes '
          f'½ of its absolute share gap; level-1 bars sum these cause contributions, including within-group differences. '
          f'The three sections are alternative views of the same decomposition; do not add across sections. '
          f'Research shares are normalised study–cause links across all 22 GBD level-2 causes, including all three injury causes. '
          f'Base: {n0:,} eligible disease-coded LMIC records in 2010–2012 and {n1:,} in 2021–2023, from 41,610 included records. '
          f'Unspecified infection/injury codes are excluded here because they lack a level-2 assignment; no smoothing or minimum-count filter is used. '
          f'DALYs are summed across 2021–2023; rows within each level-1 group follow pooled LMIC DALYs across 2010–2023. '
          f'Intervals use {DRAWS:,} within-year study bootstrap resamples; DALY uncertainty is not propagated. '
          f'Colour indicates the estimated direction; intervals crossing zero mean the change is uncertain.')
    fig.text(.035,.099,textwrap.fill(foot,170),fontsize=8.7,color=muted,va='top',linespacing=1.35)
    stem=OUT/'LMIC_mismatch_segmented_overall_level1_level2'
    for ext in ['png','pdf','svg']:fig.savefig(stem.with_suffix('.'+ext),dpi=180,facecolor=bg)
    plt.close(fig)
    exported=[overall,*parents,*leaves]
    fields=list(dict.fromkeys(key for r in exported for key in r))
    with (OUT/'contributions.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(exported)
    np.savez_compressed(OUT/'bootstrap_changes.npz',cause_names=np.array(causes),change_pp=boot)
    meta={'metric':'Total variation distance, expressed as percent share mass','fixed_reference_years':[2021,2023],
          'research_windows':[EARLY,LATE],'causes':22,'included_records':41610,'early_n':n0,'late_n':n1,
          'early_links':int(k0.sum()),'late_links':int(k1.sum()),'overall':overall,'level1':parents,
          'bootstrap_draws':DRAWS,'seed':SEED,'exact_additivity_checks':'passed for point estimates and every bootstrap draw',
          'master_sha256':hashlib.sha256((ROOT/'data/raw/hee_analysis_master_v2_1.csv').read_bytes()).hexdigest(),
          'gbd_source_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'data/raw/GBD data').glob('*.csv')},
          'burden_unclassified_locations':burden['left_out'],'map_modified':False}
    (OUT/'provenance.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
    (OUT/'README.md').write_text('''# Segmented contribution figure

Three sections show the same mismatch change at increasing detail: overall, summed level-1 contributions and individual level-2 contributions. The setting remains LMIC research; “overall” means all 22 disease and injury causes, not all-country research. All three injury causes are retained individually at level 2 and summed at level 1.

## Exact decomposition

Research shares q are normalised unique study–cause links. Burden shares p are pooled LMIC DALYs in 2021–2023, normalised across the same 22 causes. Both research windows use that fixed p.

TV(p,q) = ½ Σ_i |q_i − p_i|. Disease contribution c_i = ½ |q_i − p_i|. Level-1 contribution C_g = Σ_(i in g) c_i. The overall value is Σ_g C_g = Σ_i c_i. Changes obey the same identity. The computations and graph use percentage-point units.

Level-1 bars are grouped contributions to the fine-grained overall mismatch, not total variation recomputed after collapsing the cause categories. Collapsing first can hide opposing gaps within a group and give a different result. These sections should never be added together.

TV avoids negative per-cause KLD terms and is finite when a cause has zero observed research. No artificial 0.5-study smoothing is required. This is a new metric, not a re-expression of the earlier KLD score, and its values must not be compared numerically with those KLD figures. It measures share-distribution mismatch, not study quality, funding need or a causal response to disease burden.

Research windows are 2010–2012 and 2021–2023. Rows are ordered within level-1 groups by summed LMIC DALYs over 2010–2023. The substantive dataset and geography/income rules are unchanged: eligible reports, country studied, publication-year income for research and burden-year income for DALYs, with the existing recorded overrides. Multi-disease studies count once per named level-2 cause. A mixed-income study may enter the LMIC set. Unspecified injury/infection records are not assigned to a level-2 cause here; unlike the preceding collapsed-injury arrow plot, this figure restricts both sides to the same 22 level-2 causes.

Confidence intervals are percentile intervals for change, from 1,000 study resamples within publication year. Each resampled study carries all its cause codes; shares are renormalised in every draw. Level-1 and total intervals are computed from sums in each draw, not by summing marginal interval endpoints. DALY uncertainty and extraction/coding uncertainty are not propagated. All point and per-draw additivity checks pass.

contributions.csv has exact values and intervals. bootstrap_changes.npz contains the 1,000 contribution-change vectors; provenance.json records sources and checks. No map files were changed.
''',encoding='utf-8')
    print(headline.replace('→','->'));print('Record bases:',n0,n1,'; cause-link totals:',int(k0.sum()),int(k1.sum()))
    print('Exact overall / level-1 / level-2 additivity checks passed for estimates and 1,000 bootstrap draws.')
if __name__=='__main__':main()
