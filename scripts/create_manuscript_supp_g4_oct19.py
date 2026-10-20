"""Standalone theme_hee Supplementary Figure G4: evaluation types and publications per year."""
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
    df=pd.DataFrame({'year':st['year'],'eval_type':[lv['econ_eval_type'][x] for x in st['econ_eval_type']]})
    n=len(df);full=df[df.eval_type!=REVIEW_TYPE];types=Counter(full.eval_type);last=df.year.max()
    since=int((df.year>=2020).sum())
    n_rev_eval=sum(t!=REVIEW_TYPE and lv['review_label'][r]!='Not a review' for t,r in zip(df.eval_type,st['review_label']))
    assert n_rev_eval==667
    assert (n,len(full),types['Cost-utility'],types['Cost-effectiveness'],types['Cost-consequence'],types['Cost-benefit'])==(41610,39625,19097,10150,9020,1358)
    by_year=pd.crosstab(df.year,df.eval_type)[[t for t,_,_ in TYPES]+[REVIEW_TYPE]]
    by_year.assign(all=by_year.sum(axis=1)).to_csv(h.DATA/'supp_g4_evaluation_types_by_year.csv')

    fig=plt.figure(figsize=(11,6.4));h.title(fig,'Evaluation types and growth of the evidence, 2010–2026')
    fig.legend(handles=[Patch(color=c,label=l) for _,l,c in TYPES]+[Patch(color=REVIEW,label='Review only (no evaluation of its own)')],
               loc='upper left',bbox_to_anchor=(.03,.935),ncol=5,handlelength=1.2,columnspacing=1.4)
    # A: overall shares among original evaluations
    fig.text(.035,.83,f'A  Share of original evaluations\n    (n = {len(full):,})',fontsize=10,weight='bold',va='top',linespacing=1.3)
    ax=fig.add_axes([.035,.2,.25,.52]);h.style(ax,None)
    vals=[types[t] for t,_,_ in TYPES];y=range(len(TYPES))
    ax.barh(y,vals,color=[c for _,_,c in TYPES],height=.45);ax.set_ylim(len(TYPES)-.5,-.75)
    ax.set_yticks([]);ax.set_xticks([]);ax.set_xlim(0,max(vals)*1.12)
    for i,(v,(_,l,_)) in enumerate(zip(vals,TYPES)):
        ax.text(0,i-.3,l,fontsize=8.3,color=h.SECONDARY,va='bottom')
        ax.text(v+max(vals)*.025,i,f'{v/len(full):.1%}',fontsize=9.5,weight='bold',va='center')
        ax.text(v+max(vals)*.025+max(vals)*.2,i,f'({v:,})',fontsize=7.5,color=h.SECONDARY,va='center')
    # B: publications per year by type
    fig.text(.36,.83,f'B  Publications per year (n = {n:,})',fontsize=10,weight='bold',va='top')
    ax=fig.add_axes([.39,.2,.575,.56]);h.style(ax,'y')
    ax.axvspan(2019.5,last+.5,color=h.GRID,alpha=.55,lw=0,zorder=0)
    for yy in by_year.index:
        bottom=0;partial=yy==last
        for t,c in [(t,c) for t,_,c in TYPES]+[(REVIEW_TYPE,REVIEW)]:
            v=by_year.loc[yy,t]
            ax.bar(yy,v,bottom=bottom,color=c,width=.74,lw=0,hatch='////' if partial else None,edgecolor=h.BG if partial else None);bottom+=v
    top=by_year.sum(axis=1).max()
    ax.set_ylim(0,top*1.2);ax.yaxis.set_major_formatter(lambda v,_:f'{v:,.0f}')
    ax.set_xticks([2010,2012,2014,2016,2018,2020,2022,2024,last],[*map(str,range(2010,2025,2)),f'{last}*'])
    ax.text(2020+(last-2020)/2,top*1.11,f'{since/n:.0%} of all publications ({since:,})\nappeared 2020–{last}',ha='center',va='center',fontsize=8.5,weight='bold',linespacing=1.2)
    ax.set_ylabel('Publications')

    caption=(f"Eligible publications, 2010–{last}. Panel A: original full economic evaluations, including {n_rev_eval:,} that also report a review; each has one primary type. "
             f"Panel B: all publications by evaluation type, with reviews that report no evaluation of their own in grey. Shading marks 2020 onwards. *{last} is incomplete (searches ran to August {last}), so its bar is hatched.")
    h.foot(fig,caption,190);h.save(fig,'supp_G4_evaluation_types_and_growth',caption)

if __name__=='__main__':main()
