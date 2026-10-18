"""Parallel global and LMIC panels of the exact additive TV decomposition."""
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

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'exports/segmented_mismatch_two_panels_2026-10-14'
DRAWS=1000;SEED=20261014
EARLY=range(2010,2013);LATE=range(2021,2024)
GROUPS=['cmnn','ncd','inj']
NAMES={'cmnn':'Communicable / maternal /\nneonatal / nutritional','ncd':'Non-communicable diseases','inj':'All injuries'}
def main():
    OUT.mkdir(exist_ok=True)
    rows,_,l1,lmic_burden=gbd.load(str(ROOT/'data/raw'))
    assert len(rows)==41610
    causes=[c for c in gbd.LABEL if c not in gbd.NOT_STATED]
    global_burden={y:Counter() for y in range(2010,2024)}
    seen=set()
    for file in sorted((ROOT/'data/raw/GBD data').glob('*.csv')):
        for r in gbd.read(str(file)):
            if (r['measure_id'],r['metric_name'],r['age_name'],r['sex_name'])!=('2','Number','All ages','Both'):continue
            key=(int(r['year']),r['location_id'],r['cause_name'])
            if key in seen:continue
            seen.add(key)
            assert r['cause_name'] in causes
            global_burden[key[0]][key[2]]+=float(r['val'])
    assert len(seen)==14*204*22
    pooled={c:sum(global_burden[y][c] for y in range(2010,2024)) for c in causes}
    causes.sort(key=lambda c:(GROUPS.index(l1[c]),-pooled[c]))
    masks={g:np.array([l1[c]==g for c in causes]) for g in GROUPS}
    results={};exports=[]
    for panel_number,panel in enumerate(['all','lmic']):
        b=global_burden if panel=='all' else {y:lmic_burden[y]['lmic'] for y in range(2010,2024)}
        p=np.array([sum(b[y][c] for y in LATE) for c in causes],dtype=float);p/=p.sum()
        mats={}
        for y in [*EARLY,*LATE]:
            selected=[r for r in rows if r['year']==y and (panel=='all' or 'lmic' in r['sides']) and r['gbd']&set(causes)]
            mats[y]=np.array([[int(c in r['gbd']) for c in causes] for r in selected],dtype=np.int8).reshape(-1,22)
        def q(years,rng=None):
            count=np.zeros(22,dtype=float)
            for y in years:
                m=mats[y]
                if rng is not None:m=m[rng.integers(0,len(m),len(m))]
                count+=m.sum(axis=0)
            return count/count.sum(),count
        q0,k0=q(EARLY);q1,k1=q(LATE)
        c0=.5*np.abs(q0-p)*100;c1=.5*np.abs(q1-p)*100
        rng=np.random.default_rng(SEED if panel=='lmic' else SEED+1)
        boot=np.empty((DRAWS,22))
        for i in range(DRAWS):
            d0,_=q(EARLY,rng);d1,_=q(LATE,rng)
            boot[i]=(.5*np.abs(d1-p)-.5*np.abs(d0-p))*100
        def summary(section,label,mask,group='',cause=''):
            draws=boot[:,mask].sum(axis=1)
            return dict(panel=panel,section=section,label=label,level1=group,cause=cause,
                        early_pp=float(c0[mask].sum()),late_pp=float(c1[mask].sum()),change_pp=float((c1-c0)[mask].sum()),
                        change_lo=float(np.percentile(draws,2.5)),change_hi=float(np.percentile(draws,97.5)))
        total=summary('overall','All 22 disease and injury causes',np.ones(22,dtype=bool))
        parents=[summary('level1',NAMES[g],masks[g],g) for g in GROUPS]
        leaves=[]
        for i,c in enumerate(causes):
            r=summary('level2',gbd.LABEL[c],np.arange(22)==i,l1[c],c)
            r.update(daly_share_2021_2023=float(p[i]),early_research_share=float(q0[i]),late_research_share=float(q1[i]),
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
        np.savez_compressed(OUT/(panel+'_bootstrap_changes.npz'),cause_names=np.array(causes),change_pp=boot)
    plt.rcParams.update({'font.family':'Arial','svg.fonttype':'none','pdf.fonttype':42})
    bg='#f7f4ee';ink='#252721';muted='#75766d';green='#25835f';red='#c34d36'
    fig=plt.figure(figsize=(20.2,15.5),facecolor=bg)
    fig.text(.025,.975,'RESEARCH–BURDEN MISMATCH: ALL STUDIES AND L&MICs-FOCUSED STUDIES',fontsize=23,fontweight='bold',color=ink,va='top')
    fig.text(.025,.941,'2010–2012 → 2021–2023 research, each compared with its own fixed 2021–2023 DALY reference.\nOverall, level-1 and level-2 sections show the same change at increasing detail.',fontsize=13,color=muted,va='top',linespacing=1.5)
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
            value=r['change_pp'];colour=green if value<0 else red
            ax.barh(pos,value,height=.54,color=colour,alpha=.85,zorder=2)
            ax.plot([r['change_lo'],r['change_hi']],[pos,pos],color='#666960',lw=1,zorder=3)
            ax.scatter([r['change_lo'],r['change_hi']],[pos,pos],marker='|',s=20,color='#666960',zorder=4)
            if section=='overall':ax.scatter([value],[pos],s=16,color=colour,zorder=5)
            ax.text(1.025,pos,f"{r['early_pp']:.2f} → {r['late_pp']:.2f}",transform=ax.get_yaxis_transform(),va='center',color=muted,fontsize=9.8)
            labels.append(r['label'])
        ax.text(1.025,-.75,'Mismatch (pp)\nEarly → late',transform=ax.get_yaxis_transform(),color=muted,fontsize=9.5,va='bottom')
        ax.set_yticks([s[0] for s in slots],labels if panel_number==0 else ['']*len(slots),fontsize=10.1,color=muted)
        ax.tick_params(axis='both',length=0,pad=8,labelsize=10)
        for sp in ax.spines.values():sp.set_visible(False)
        ax.set_xlabel('Contribution to change in mismatch (percentage points)\n← Less mismatch                    More mismatch →',fontsize=10.7,color=muted,labelpad=12)
        if panel_number==0:
            for pos,title,sub in headers:
                ax.text(-.845,pos,title,transform=ax.get_yaxis_transform(),color=muted if sub else ink,
                        fontsize=10.0 if sub else 11.6,fontweight='bold',va='center',clip_on=False)
        total=result['total']
        note=(f"Overall: {total['early_pp']:.2f}% → {total['late_pp']:.2f}%; change {total['change_pp']:+.3f} pp\n"
              f"95% interval {total['change_lo']:+.2f} to {total['change_hi']:+.2f}; n = {result['early_n']:,} → {result['late_n']:,}")
        fig.text(left,.14,note,fontsize=11.4,color=ink,fontweight='bold',va='top',linespacing=1.45)
    foot=('L&MICs = low- and middle-income countries: low-, lower-middle- and upper-middle-income groups. '
          'Mismatch is total variation distance: ½ × Σ |normalised research share − DALY share|. Each cause contributes half its absolute share gap; '
          'level-1 rows sum those contributions, including within-group differences. Each section sums to the same overall total; do not add across sections. '
          'Both panels use the same 22 GBD level-2 causes and common row order: level-1 grouping, then summed global DALYs over 2010–2023. '
          'Research shares are study–cause links; a multi-disease record contributes to each named cause. Unspecified infections/injuries are excluded from this level-2 analysis; '
          'zero counts require no smoothing. Panel A includes records without a stated country; Panel B requires a low- or middle-income study setting and may include mixed-income multi-country records. '
          'Publication-year income defines research settings; burden-year income defines L&MICs DALYs. Global DALYs retain all 204 national locations. '
          'Intervals resample studies within year, 1,000 draws; DALY and coding uncertainty are not propagated. Colour shows estimated direction; intervals crossing zero indicate uncertainty. '
          'Because the burden references differ, the panel comparison does not isolate an effect of adding or removing HIC studies.')
    fig.text(.025,.087,textwrap.fill(foot,250),fontsize=9.0,color=muted,va='top',linespacing=1.35)
    stem=OUT/'mismatch_segmented_all_studies_and_LMIC'
    for ext in ['png','pdf','svg']:fig.savefig(stem.with_suffix('.'+ext),dpi=180,facecolor=bg)
    plt.close(fig)
    fields=list(dict.fromkeys(k for r in exports for k in r))
    with (OUT/'contributions_both_panels.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(exports)
    meta={'eligible_records':41610,'panels':{k:{key:value for key,value in v.items() if key!='leaves'} for k,v in results.items()},
          'research_windows':[[2010,2012],[2021,2023]],'fixed_burden_window':[2021,2023],'ordering':'Common pooled global DALYs 2010–2023 within level-1 groups',
          'cause_count':22,'bootstrap_draws':1000,'seed':SEED,'panel_seeds':{'all':SEED+1,'lmic':SEED},'additivity_checks':'Passed for both panels and every bootstrap draw',
          'master_sha256':hashlib.sha256((ROOT/'data/raw/hee_analysis_master_v2_1.csv').read_bytes()).hexdigest(),'map_modified':False,
          'global_gbd_rows_checked':len(seen),'global_includes_unknown_country_studies':True}
    (OUT/'provenance.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
    (OUT/'README.md').write_text('''# Global and L&MICs segmented mismatch panels

L&MICs means low- and middle-income countries: all three World Bank low-, lower-middle- and upper-middle-income groups. It does not mean lower-middle-income countries alone. Internal `lmic` data keys and existing output filenames are retained for stable file references.

Panel A: all eligible disease-coded records, including HIC and LMIC settings and records without a stated country, compared with global DALYs across 204 national GBD locations. Panel B: records naming an LMIC study setting, compared with LMIC DALYs. Mixed-income multi-country records can enter Panel B. Panel B is a subset of Panel A, not an independent complementary population.

Both panels use 2010–2012 and 2021–2023 research, with their corresponding pooled 2021–2023 DALY distribution fixed for both research windows. Both use all 22 level-2 causes and identical row order: level-1 groups, then global DALYs summed across 2010–2023. This common global ordering differs from the earlier LMIC-only figure's LMIC ordering but permits direct row alignment. Global burden is summed directly from the deduplicated 14 × 204 × 22 number/all-ages/both-sexes rows; it does not exclude countries with missing income classification. LMIC burden retains the existing burden-year income rules.

The metric remains total variation distance, ½ Σ |q_i−p_i|, with q normalised study–cause links and p DALY shares. Contributions are nonnegative; their changes can be positive or negative. Every level-1 subtotal sums its level-2 causes, and all causes/groups sum to the overall total at each period and for change. The level-1 subtotals retain within-group mismatch; they are not a separate distance computed after collapsing causes. Do not sum across the three display sections.

Confidence intervals for change use 1,000 study bootstrap draws within publication year. Subtotal and overall intervals come from per-draw sums, not summed marginal interval bounds. These are descriptive comparisons and do not propagate DALY/coding uncertainty. The different global/LMIC references mean panel differences are not a causal or mechanical HIC-removal effect. This is the TV metric, not the earlier KLD score. Exact contributions and shares are in contributions_both_panels.csv; provenance and bootstrap matrices are saved alongside the figure.

No map files were changed.
''',encoding='utf-8')
    readme=OUT/'README.md'
    readme.write_text(readme.read_text(encoding='utf-8').replace('LMIC','L&MICs'),encoding='utf-8')
    for panel,r in results.items():
        print(panel,json.dumps(r['total']),'; records',r['early_n'],r['late_n'])
    print('Both panels: exact point-estimate and 1,000-draw hierarchical additivity verified.')
if __name__=='__main__':main()
