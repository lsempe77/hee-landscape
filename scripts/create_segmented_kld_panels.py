"""Standalone 16- and 22-cause KLD contribution panels, aligned with Fig. 2a."""
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
import build_kld_replication as reference
import argparse

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'exports/segmented_kld_2026-10-14'
DRAWS=1000;SEED=20261014
EARLY=range(2010,2013);LATE=range(2021,2024)
GROUPS=['cmnn','ncd','inj']
NAMES={'cmnn':'Communicable / maternal /\nneonatal / nutritional','ncd':'Non-communicable diseases','inj':'All injuries'}
def main():
    global OUT
    parser=argparse.ArgumentParser()
    parser.add_argument("--causes",type=int,choices=[16,22],required=True)
    args=parser.parse_args()
    size=args.causes
    OUT=OUT/f"{size}_causes"
    OUT.mkdir(parents=True,exist_ok=True)
    raw=str(ROOT/'data/raw')
    studies=reference.load_studies(raw)
    burden,missing_income=reference.load_dalys(raw)
    _,_,l1,_=gbd.load(raw)
    rows=[dict(year=r['year'],sides=r['groups'],gbd=r['causes']) for r in studies]
    all_causes=[c for c in gbd.LABEL if c not in gbd.NOT_STATED]
    causes=list(reference.CAUSES_16) if size==16 else all_causes.copy()
    global_burden={y:burden[y]['all'] for y in range(2010,2024)}
    zero_counts={}
    pooled={c:sum(global_burden[y][c] for y in range(2010,2024)) for c in causes}
    causes.sort(key=lambda c:(GROUPS.index(l1[c]),-pooled[c]))
    masks={g:np.array([l1[c]==g for c in causes]) for g in GROUPS}
    results={};exports=[]
    for panel_number,panel in enumerate(['all','lmic']):
        b={y:burden[y][panel] for y in range(2010,2024)}
        def p_of(years):
            p=np.array([sum(b[y][c] for y in years) for c in causes],dtype=float)
            return p/p.sum()
        p0,p1=p_of(EARLY),p_of(LATE)
        zero_counts[panel]={'point':{},'bootstrap_windows_with_zero':0,'bootstrap_windows':2*DRAWS}
        mats={}
        for y in [*EARLY,*LATE]:
            selected=[r for r in rows if r['year']==y and (panel=='all' or 'lmic' in r['sides']) and r['gbd']&set(causes)]
            mats[y]=np.array([[int(c in r['gbd']) for c in causes] for r in selected],dtype=np.int8).reshape(-1,size)
        def q(years,rng=None):
            count=np.zeros(size,dtype=float)
            for y in years:
                m=mats[y]
                if rng is not None:m=m[rng.integers(0,len(m),len(m))]
                count+=m.sum(axis=0)
            raw_count=count.copy()
            if (count==0).any():
                if rng is None:
                    zero_counts[panel]['point']['early' if years==EARLY else 'late']=[causes[i] for i in np.flatnonzero(count==0)]
                else:zero_counts[panel]['bootstrap_windows_with_zero']+=1
                count=np.where(count==0,.5,count)
            return count/count.sum(),raw_count
        q0,k0=q(EARLY);q1,k1=q(LATE)
        def terms(p,q):return p*np.log(p/q)-p+q
        c0=terms(p0,q0);c1=terms(p1,q1)
        assert np.all(c0>=-1e-12) and np.all(c1>=-1e-12)
        assert np.isclose(c0.sum(),np.sum(p0*np.log(p0/q0)))
        assert np.isclose(c1.sum(),np.sum(p1*np.log(p1/q1)))
        rng=np.random.default_rng(SEED if panel=='lmic' else SEED+1)
        boot=np.empty((DRAWS,size))
        for i in range(DRAWS):
            d0,_=q(EARLY,rng);d1,_=q(LATE,rng)
            boot[i]=terms(p1,d1)-terms(p0,d0)
        def summary(section,label,mask,group='',cause=''):
            draws=boot[:,mask].sum(axis=1)
            return dict(panel=panel,section=section,label=label,level1=group,cause=cause,
                        early_pp=float(c0[mask].sum()),late_pp=float(c1[mask].sum()),change_pp=float((c1-c0)[mask].sum()),
                        change_lo=float(np.percentile(draws,2.5)),change_hi=float(np.percentile(draws,97.5)))
        total=summary('overall',f'All {size} included causes',np.ones(size,dtype=bool))
        parents=[summary('level1',NAMES[g] if masks[g].any() else 'Injuries (outside 16-cause set)',masks[g],g) for g in GROUPS]
        leaves=[]
        for i,c in enumerate(causes):
            r=summary('level2',gbd.LABEL[c],np.arange(size)==i,l1[c],c)
            r.update(early_daly_share=float(p0[i]),late_daly_share=float(p1[i]),early_research_share=float(q0[i]),late_research_share=float(q1[i]),
                     early_cause_count=int(k0[i]),late_cause_count=int(k1[i]),pooled_global_dalys_2010_2023=pooled[c])
            leaves.append(r)
        assert np.isclose(sum(r['change_pp'] for r in leaves),total['change_pp'])
        assert np.isclose(sum(r['change_pp'] for r in parents),total['change_pp'])
        assert np.allclose(sum(boot[:,mask].sum(axis=1) for mask in masks.values()),boot.sum(axis=1))
        for parent in parents:
            assert np.isclose(parent['early_pp'],sum(r['early_pp'] for r in leaves if r['level1']==parent['level1']))
            assert np.isclose(parent['late_pp'],sum(r['late_pp'] for r in leaves if r['level1']==parent['level1']))
        results[panel]=dict(total=total,parents=parents,leaves=leaves,
                            early_n=sum(len(mats[y]) for y in EARLY),late_n=sum(len(mats[y]) for y in LATE),
                            early_links=int(k0.sum()),late_links=int(k1.sum()))
        exports.extend([total,*parents,*leaves])
        np.savez_compressed(OUT/(panel+'_bootstrap_changes.npz'),cause_names=np.array(causes),change_nats=boot)
    plt.rcParams.update({'font.family':'Arial','svg.fonttype':'none','pdf.fonttype':42})
    bg='#f7f4ee';ink='#252721';muted='#75766d';green='#25835f';red='#c34d36'
    fig=plt.figure(figsize=(20.2,15.5 if size==22 else 13.5),facecolor=bg)
    set_title='REFERENCE-PAPER SET' if size==16 else 'EXTENDED ALL-CAUSE SET'
    fig.text(.025,.975,f'KLD CONTRIBUTIONS: {size}-CAUSE {set_title}',fontsize=23,fontweight='bold',color=ink,va='top')
    fig.text(.025,.941,'2010–2012 → 2021–2023: research and DALY distributions both change, as in Fig. 2a.\nOverall, level-1 and level-2 sections show the same change at increasing detail.',fontsize=13,color=muted,va='top',linespacing=1.5)
    fig.legend(handles=[Line2D([0],[0],color=green,lw=6,label='Reduces mismatch'),Line2D([0],[0],color=red,lw=6,label='Increases mismatch'),
                        Line2D([0],[0],color='#77776e',marker='|',markersize=9,lw=1,label='95% bootstrap interval for change')],
               loc='upper left',bbox_to_anchor=(.235,.900),ncol=3,frameon=False,fontsize=11)
    slots=[];headers=[];y=0
    headers.append((y,'OVERALL',False));y+=1;slots.append((y,'overall',0));y+=1.5
    headers.append((y,'LEVEL 1 · GROUPED CONTRIBUTIONS',False));y+=1
    for i in range(3):slots.append((y,'parents',i));y+=1
    y+=.65;headers.append((y,'LEVEL 2 · INDIVIDUAL CAUSES',False));y+=1.2
    for g in GROUPS:
        headers.append((y,{'cmnn':'Communicable / maternal / neonatal / nutritional','ncd':'Non-communicable diseases','inj':'Injuries'}[g],True));y+=.8
        for i,c in enumerate(causes):
            if l1[c]==g:slots.append((y,'leaves',i));y+=1
        y+=.45
    extent=max(max(abs(r['change_lo']),abs(r['change_hi']),abs(r['change_pp'])) for r in exports)*1.12
    for panel_number,(panel,left) in enumerate([('all',.255),('lmic',.66)]):
        result=results[panel]
        ax=fig.add_axes([left,.195,.27,.63],facecolor=bg)
        title='A · All studies (HICs + L&MICs included)' if panel=='all' else 'B · L&MICs-focused studies'
        fig.text(left,.865,title,fontsize=14.3,fontweight='bold',color=ink)
        benchmark='Global DALYs; all eligible disease-coded records' if panel=='all' else 'L&MICs DALYs; records naming a low- or middle-income setting'
        fig.text(left,.843,benchmark,fontsize=10.7,color=muted)
        ax.set_xlim(-extent,extent);ax.set_ylim(y-.4,-1.2)
        ax.axvline(0,color='#8e8c82',linestyle=(0,(2,2)),lw=1)
        ax.grid(axis='x',color='#e3e0d8',lw=.7);ax.set_axisbelow(True)
        labels=[]
        for pos,section,i in slots:
            r=result['total'] if section=='overall' else result[section][i]
            if section=='parents' and not masks[r['level1']].any():
                ax.text(0,pos,'Not included',ha='center',va='center',fontsize=9,color=muted)
                labels.append(r['label']);continue
            value=r['change_pp'];colour=green if value<0 else red
            ax.barh(pos,value,height=.54,color=colour,alpha=.85,zorder=2)
            ax.plot([r['change_lo'],r['change_hi']],[pos,pos],color='#666960',lw=1,zorder=3)
            ax.scatter([r['change_lo'],r['change_hi']],[pos,pos],marker='|',s=20,color='#666960',zorder=4)
            if section=='overall':ax.scatter([value],[pos],s=16,color=colour,zorder=5)
            ax.text(1.025,pos,f"{r['early_pp']:.3f} → {r['late_pp']:.3f}",transform=ax.get_yaxis_transform(),va='center',color=muted,fontsize=9.8)
            labels.append(r['label'])
        ax.text(1.025,-.75,'KLD (nats)\nEarly → late',transform=ax.get_yaxis_transform(),color=muted,fontsize=9.5,va='bottom')
        ax.set_yticks([s[0] for s in slots],labels if panel_number==0 else ['']*len(slots),fontsize=10.1,color=muted)
        ax.tick_params(axis='both',length=0,pad=8,labelsize=10)
        for sp in ax.spines.values():sp.set_visible(False)
        ax.set_xlabel('Contribution to change in KLD (nats)\n← Less mismatch                    More mismatch →',fontsize=10.7,color=muted,labelpad=12)
        if panel_number==0:
            for pos,title,sub in headers:
                ax.text(-.845,pos,title,transform=ax.get_yaxis_transform(),color=muted if sub else ink,
                        fontsize=10.0 if sub else 11.6,fontweight='bold',va='center',clip_on=False)
        total=result['total']
        note=(f"Overall: {total['early_pp']:.3f} → {total['late_pp']:.3f}; change {total['change_pp']:+.3f} nats\n"
              f"95% interval {total['change_lo']:+.3f} to {total['change_hi']:+.3f}; n = {result['early_n']:,} → {result['late_n']:,}")
        fig.text(left,.14,note,fontsize=11.4,color=ink,fontweight='bold',va='top',linespacing=1.45)
    foot=(f'L&MICs = low- and middle-income countries (low-, lower-middle- and upper-middle-income groups). '
          f'{size} GBD level-2 causes; DALY shares p and study-cause-link shares q are separately normalised over this set. '
          'KLD = sum p ln(p/q), in nats. Nonnegative disease contributions use p ln(p/q) - p + q; their sum equals KLD. '
          'This disease allocation differs from signed p ln(p/q) terms, although the overall total is identical. '
          'Level-1 rows sum descendant contributions, retaining within-group mismatch; do not add across sections. '
          'Both research and burden change, so the change cannot be attributed solely to research. '
          'Intervals: 1,000 study bootstrap draws within year; DALY/coding uncertainty omitted. '
          'Zero-count causes receive 0.5 only when needed, following the existing Fig. 2a implementation; details in provenance. '
          'Common ordering: level-1 groups, then global DALYs summed over 2010-2023. '
          'Panel A includes unknown-country records; Panel B includes mixed-income studies naming an L&MICs setting. '
          'Research uses publication-year income; burden uses burden-year income. Latest window includes the COVID period. '
          'The 16-cause set excludes mental disorders, all injuries, other infectious and other non-communicable diseases; '
          'the 22-cause extension includes them. These are adaptations to economic-evaluation records, not exact replications of the reference sample.')
    fig.text(.025,.087,textwrap.fill(foot,250),fontsize=9.0,color=muted,va='top',linespacing=1.35)
    stem=OUT/f'KLD_segmented_{size}_causes_global_and_LandMICs'
    for ext in ['png','pdf','svg']:fig.savefig(stem.with_suffix('.'+ext),dpi=180,facecolor=bg)
    plt.close(fig)
    # Explicit units: the plotting implementation uses generic legacy field names internally only.
    exports=[{k.replace('_pp','_nats'):v for k,v in r.items()} for r in exports]
    fields=list(dict.fromkeys(k for r in exports for k in r))
    with (OUT/'contributions_both_panels.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(exports)
    meta={'eligible_master_records':41610,'cause_count':size,'cause_names':causes,
          'research_and_burden_windows':[[2010,2012],[2021,2023]],'burden_reference':'Contemporaneous; changes between windows',
          'metric':'KLD(p||q), natural logarithms, nats','allocation':'p*ln(p/q)-p+q',
          'zero_handling':zero_counts,'bootstrap_draws':DRAWS,'panel_seeds':{'all':SEED+1,'lmic':SEED},
          'panels':results,'additivity_checks':'Passed for point estimates and every bootstrap draw',
          'master_sha256':hashlib.sha256((ROOT/'data/raw/hee_analysis_master_v2_1.csv').read_bytes()).hexdigest(),
          'map_modified':False,'reference_cause_set':reference.CAUSES_16,
          'comparison_note':'Matches Fig. 2a method at these endpoints, not its earlier 2017-2019 endpoint; 22 causes is an extension.'}
    # Internal plot records retain legacy names; their units are nats, never percentage points.
    meta=json.loads(json.dumps(meta).replace('_pp"','_nats"'))
    (OUT/'provenance.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
    (OUT/'README.md').write_text(f"""# {size}-cause segmented KLD: global and L&MICs

Standalone adaptation of Fig. 2a using the current 41,610-record eligible master and GBD 2023 DALYs. L&MICs means all low-, lower-middle- and upper-middle-income countries. Both research and DALY distributions change from 2010-2012 to 2021-2023. The latter is the COVID-inclusive extension endpoint, not the earlier 2017-2019 comparison.

{foot}

The 16-cause figure follows the existing reference-paper cause set; the 22-cause figure extends it. Both re-normalise shares over their own cause sets, so their totals are not directly interchangeable. A multi-disease record contributes once to each named cause. Level-1 rows are sums of level-2 contributions, not a newly calculated KLD on three collapsed groups. The nonnegative allocation is explicit and is not the signed cause-term allocation used in some KLD displays. Changes can be negative or positive.

CSV values and bootstrap files are in nats. Provenance lists causes, counts, seeds, zero handling and master hash. All hierarchy sums were checked at each endpoint and for each bootstrap draw. Bootstrap intervals condition on fixed DALY estimates. No map files were changed.
""",encoding='utf-8')
    for panel,r in results.items():
        print(panel,json.dumps(r['total']),'; records',r['early_n'],r['late_n'])
    print('Both panels: exact point-estimate and 1,000-draw hierarchical additivity verified.')
if __name__=='__main__':main()
