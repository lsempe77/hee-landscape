"""Standalone theme_hee figure for the whole study-type paragraph: publication type, evaluation type and growth."""
import sys
sys.dont_write_bytecode = True
from collections import Counter
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import pandas as pd
import create_manuscript_figures_oct19 as h
from build_glance_regions_who_v4 import load

REVIEW_TYPE, REVIEW = 'Review (no evaluation type)', '#c9c8c3'
TYPES = [('Cost-utility','Cost-utility (CUA)',h.BLUE),('Cost-effectiveness','Cost-effectiveness (CEA)',h.ORANGE),
         ('Cost-consequence','Cost-consequence (CCA)',h.AQUA),('Cost-benefit','Cost-benefit (CBA)',h.hex_for('yellow'))]

def main():
    h.OUT.mkdir(exist_ok=True);h.DATA.mkdir(exist_ok=True)
    lv=load('dict.json')['levels'];st=load('studies.json')
    df=pd.DataFrame({'year':st['year'],'eval_type':[lv['econ_eval_type'][x] for x in st['econ_eval_type']],
                     'review':[lv['review_label'][x]!='Not a review' for x in st['review_label']]})
    df['kind']=['Review only' if t==REVIEW_TYPE else 'Evaluation with review' if r else 'Stand-alone evaluation' for t,r in zip(df.eval_type,df.review)]
    n=len(df);k=Counter(df.kind);full=df[df.eval_type!=REVIEW_TYPE];types=Counter(full.eval_type);last=df.year.max()
    since=int((df.year>=2020).sum())
    assert (n,k['Stand-alone evaluation'],k['Evaluation with review'],k['Review only'])==(41610,38958,667,1985)
    assert [types[t] for t,_,_ in TYPES]==[19097,10150,9020,1358]
    by_year=pd.crosstab(df.year,df.eval_type)[[t for t,_,_ in TYPES]+[REVIEW_TYPE]]
    by_year.assign(all=by_year.sum(axis=1)).to_csv(h.DATA/'evidence_types_by_year.csv')
    pd.DataFrame([{'group':'Publication type','category':c,'n':k[c],'denominator':n} for c in ['Stand-alone evaluation','Evaluation with review','Review only']]+
                 [{'group':'Evaluation type (original evaluations)','category':t,'n':types[t],'denominator':len(full)} for t,_,_ in TYPES]
                 ).assign(share=lambda d:d.n/d.denominator).to_csv(h.DATA/'evidence_types_counts.csv',index=False)

    fig=plt.figure(figsize=(11,8.2));h.title(fig,'Types of health economic evidence and their growth, 2010–2026')
    # A: all publications by publication type
    fig.text(.035,.915,f'A  Publication type (n = {n:,})',fontsize=10,weight='bold')
    ax=fig.add_axes([.035,.8,.93,.055]);ax.axis('off');ax.set_xlim(0,n);ax.set_ylim(0,1)
    sa,wr,ro=k['Stand-alone evaluation'],k['Evaluation with review'],k['Review only']
    for left,w,col in [(0,sa,h.SECONDARY),(sa,wr,h.MUTED),(sa+wr,ro,REVIEW)]:
        ax.barh(.5,w,left=left,height=1,color=col,edgecolor=h.BG,lw=.8)
    ax.text(sa/2,.5,f'Stand-alone full economic evaluation  {sa:,} ({sa/n:.1%})',color=h.BG,weight='bold',ha='center',va='center',fontsize=9)
    ax.annotate(f'Evaluation that also includes a review  {wr:,} ({wr/n:.1%})',xy=(sa+wr/2,1),xytext=(sa-4800,1.6),ha='right',va='bottom',fontsize=8,color=h.SECONDARY,
                arrowprops=dict(arrowstyle='-',color=h.MUTED,lw=.6),annotation_clip=False)
    ax.annotate(f'Review only  {ro:,} ({ro/n:.1%})',xy=(sa+wr+ro/2,1),xytext=(n,1.6),ha='right',va='bottom',fontsize=8,color=h.SECONDARY,
                arrowprops=dict(arrowstyle='-',color=h.MUTED,lw=.6),annotation_clip=False)
    # bracket over the two original-evaluation segments
    ax.plot([0,0,sa+wr,sa+wr],[-.35,-.5,-.5,-.35],color=h.SECONDARY,lw=.8,clip_on=False)
    ax.text(0,-.62,f'Original full economic evaluations  {len(full):,} ({len(full)/n:.1%})',fontsize=8.5,weight='bold',color=h.INK,va='top')

    fig.legend(handles=[Patch(color=c,label=l) for _,l,c in TYPES]+[Patch(color=REVIEW,label='Review only')],
               loc='upper left',bbox_to_anchor=(.03,.7),ncol=5,handlelength=1.2,columnspacing=1.4)
    # B: shares among original evaluations
    fig.text(.035,.6,f'B  Evaluation type\n    (original evaluations, n = {len(full):,})',fontsize=10,weight='bold',va='top',linespacing=1.3)
    ax=fig.add_axes([.035,.16,.25,.36]);h.style(ax,None)
    vals=[types[t] for t,_,_ in TYPES];m=max(vals)
    ax.barh(range(len(TYPES)),vals,color=[c for _,_,c in TYPES],height=.45);ax.set_ylim(len(TYPES)-.5,-.75)
    ax.set_yticks([]);ax.set_xticks([]);ax.set_xlim(0,m*1.12)
    for i,(v,(_,l,_)) in enumerate(zip(vals,TYPES)):
        ax.text(0,i-.3,l,fontsize=8.3,color=h.SECONDARY,va='bottom')
        ax.text(v+m*.025,i,f'{v/len(full):.1%}',fontsize=9.5,weight='bold',va='center')
        ax.text(v+m*.225,i,f'({v:,})',fontsize=7.5,color=h.SECONDARY,va='center')
    # C: publications per year by type
    fig.text(.36,.6,f'C  Publications per year (n = {n:,})',fontsize=10,weight='bold',va='top')
    ax=fig.add_axes([.39,.16,.575,.4]);h.style(ax,'y')
    ax.axvspan(2019.5,last+.5,color=h.GRID,alpha=.55,lw=0,zorder=0)
    for yy in by_year.index:
        bottom=0;partial=yy==last
        for t,c in [(t,c) for t,_,c in TYPES]+[(REVIEW_TYPE,REVIEW)]:
            v=by_year.loc[yy,t]
            ax.bar(yy,v,bottom=bottom,color=c,width=.74,lw=0,hatch='////' if partial else None,edgecolor=h.BG if partial else None);bottom+=v
    top=by_year.sum(axis=1).max()
    ax.set_ylim(0,top*1.22);ax.yaxis.set_major_formatter(lambda v,_:f'{v:,.0f}')
    ax.set_xticks([*range(2010,2025,2),last],[*map(str,range(2010,2025,2)),f'{last}*'])
    ax.text(2020+(last-2020)/2,top*1.12,f'{since/n:.0%} of all publications ({since:,})\nappeared 2020–{last}',ha='center',va='center',fontsize=8.5,weight='bold',linespacing=1.2)
    ax.set_ylabel('Publications')

    caption=(f"Eligible publications, 2010–{last}. Original full economic evaluations compare both costs and consequences; {wr:,} of them also report a review "
             f"(for example, a systematic review followed by the authors' own evaluation). Reviews only synthesise published evaluations and report no evaluation of their own. "
             f"Panel B: each original evaluation has one primary type. Panel C: shading marks 2020 onwards; *{last} is incomplete (searches ran to August {last}), so its bar is hatched.")
    h.foot(fig,caption,200);h.save(fig,'09_evidence_types_and_growth',caption)

if __name__=='__main__':main()
