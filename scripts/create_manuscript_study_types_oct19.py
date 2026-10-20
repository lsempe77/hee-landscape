"""Standalone theme_hee figure: study types, evaluation types and growth over time."""
import sys
sys.dont_write_bytecode = True
from collections import Counter
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import pandas as pd
import create_manuscript_figures_oct19 as h
from build_glance_regions_who_v4 import load

LIGHT_BLUE, REVIEW = h.SEQ[3], '#c9c8c3'
TYPES = [('Cost-utility','Cost-utility analysis (CUA)'),('Cost-effectiveness','Cost-effectiveness analysis (CEA)'),
         ('Cost-consequence','Cost-consequence analysis (CCA)'),('Cost-benefit','Cost-benefit analysis (CBA)')]

def main():
    h.OUT.mkdir(exist_ok=True);h.DATA.mkdir(exist_ok=True)
    lv=load('dict.json')['levels'];st=load('studies.json')
    etype=[lv['econ_eval_type'][x] for x in st['econ_eval_type']]
    rev=[lv['review_label'][x]!='Not a review' for x in st['review_label']]
    kind=['Review only' if t=='Review (no evaluation type)' else 'Evaluation with review' if r else 'Stand-alone evaluation' for t,r in zip(etype,rev)]
    df=pd.DataFrame({'year':st['year'],'kind':kind,'eval_type':etype})
    n=len(df);k=Counter(df.kind);full=df[df.kind!='Review only']
    assert (n,k['Stand-alone evaluation'],k['Evaluation with review'],k['Review only'])==(41610,38958,667,1985)
    types=Counter(full.eval_type);since=(df.year>=2020).sum()
    by_year=pd.crosstab(df.year,df.kind!='Review only').rename(columns={True:'original_evaluations',False:'reviews_only'})
    by_year['all']=by_year.sum(axis=1)
    by_year.to_csv(h.DATA/'study_types_by_year.csv')
    pd.DataFrame([{'group':'Publication type','category':c,'n':k[c],'denominator':n} for c in ['Stand-alone evaluation','Evaluation with review','Review only']]+
                 [{'group':'Evaluation type (original evaluations)','category':t,'n':types[t],'denominator':len(full)} for t,_ in TYPES]
                 ).assign(share=lambda d:d.n/d.denominator).to_csv(h.DATA/'study_types_counts.csv',index=False)

    fig=plt.figure(figsize=(11,7.4));h.title(fig,'What kind of evidence is it, and how fast is it growing?')
    # A: one bar of all publications
    fig.text(.035,.905,f'A  Publication type (n = {n:,})',fontsize=10,weight='bold')
    ax=fig.add_axes([.035,.775,.93,.065]);ax.axis('off');ax.set_xlim(0,n);ax.set_ylim(0,1)
    left=0
    for c,col in [('Stand-alone evaluation',h.BLUE),('Evaluation with review',LIGHT_BLUE),('Review only',REVIEW)]:
        ax.barh(.5,k[c],left=left,height=1,color=col,edgecolor=h.BG,lw=.8);left+=k[c]
    ax.text(k['Stand-alone evaluation']/2,.5,f"Stand-alone full economic evaluation  {k['Stand-alone evaluation']:,} ({k['Stand-alone evaluation']/n:.1%})",color=h.BG,weight='bold',ha='center',va='center',fontsize=9)
    x_rev=k['Stand-alone evaluation']+k['Evaluation with review']
    ax.annotate(f"Evaluation that also includes a review  {k['Evaluation with review']:,} ({k['Evaluation with review']/n:.1%})",
                xy=(k['Stand-alone evaluation']+k['Evaluation with review']/2,0),xytext=(x_rev-200,-.55),ha='right',va='top',fontsize=8,color=h.SECONDARY,
                arrowprops=dict(arrowstyle='-',color=h.MUTED,lw=.6),annotation_clip=False)
    ax.annotate(f"Review only  {k['Review only']:,} ({k['Review only']/n:.1%})",xy=(x_rev+k['Review only']/2,1),xytext=(n,1.55),ha='right',va='bottom',fontsize=8,color=h.SECONDARY,
                arrowprops=dict(arrowstyle='-',color=h.MUTED,lw=.6),annotation_clip=False)
    fig.text(.035,.705,f"Original full economic evaluations: {len(full):,} ({len(full)/n:.1%})",fontsize=8.5,weight='bold',color=h.BLUE)

    # B: evaluation types among original evaluations
    fig.text(.035,.635,f'B  Evaluation type, original evaluations (n = {len(full):,})',fontsize=10,weight='bold')
    ax=fig.add_axes([.235,.17,.25,.43]);h.style(ax,None)
    vals=[types[t] for t,_ in TYPES];y=range(len(TYPES))
    ax.barh(y,vals,color=h.BLUE,height=.68);ax.set_yticks(list(y),[l for _,l in TYPES]);ax.invert_yaxis()
    ax.set_xlim(0,max(vals)*1.4);ax.set_xticks([])
    for i,v in zip(y,vals):ax.text(v+max(vals)*.03,i,f'{v/len(full):.1%}  ({v:,})',va='center',fontsize=8.3)

    # C: publications per year
    fig.text(.535,.635,f'C  Publications per year, {df.year.min()}–{df.year.max()}',fontsize=10,weight='bold')
    ax=fig.add_axes([.56,.17,.405,.39]);h.style(ax,'y')
    yrs=by_year.index;last=yrs.max()
    ax.axvspan(2019.5,last+.5,color=h.GRID,alpha=.55,lw=0,zorder=0)
    for yy in yrs:
        partial=yy==last;o,r=by_year.loc[yy,['original_evaluations','reviews_only']]
        ax.bar(yy,o,color=h.BLUE,width=.72,hatch='////' if partial else None,edgecolor=h.BG if partial else None,lw=0)
        ax.bar(yy,r,bottom=o,color=REVIEW,width=.72,hatch='////' if partial else None,edgecolor=h.BG if partial else None,lw=0)
    ax.set_xticks([2010,2014,2018,2020,2022,2026],['2010','2014','2018','2020','2022',f'{last}*']);ax.set_ylim(0,by_year['all'].max()*1.22)
    ax.yaxis.set_major_formatter(lambda v,_:f'{v:,.0f}')
    ax.text(2020+(last-2020)/2,by_year['all'].max()*1.13,f'{since/n:.0%} of all publications\n({since:,}) appeared 2020–{last}',ha='center',va='center',fontsize=8.3,weight='bold',color=h.INK,linespacing=1.2)
    ax.legend(handles=[Patch(color=h.BLUE,label='Original evaluations'),Patch(color=REVIEW,label='Reviews only')],loc='upper left',bbox_to_anchor=(0,1.02),fontsize=7.5)

    caption=(f"Eligible publications, 2010–{last}. Original full economic evaluations compare both costs and consequences; {k['Evaluation with review']:,} of them also report a review "
             f"(for example, a systematic review followed by the authors' own evaluation). Reviews only synthesise published evaluations and report no evaluation of their own. "
             f"Panel B: each original evaluation has one primary type. Panel C: shading marks 2020 onwards; *{last} is incomplete (searches ran to August {last}), so its bar is hatched.")
    h.foot(fig,caption,205);h.save(fig,'08_study_types_and_growth',caption)

if __name__=='__main__':main()
