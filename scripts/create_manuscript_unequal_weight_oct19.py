"""Standalone theme_hee version of the map's country deficit figure."""
import sys
sys.dont_write_bytecode = True
import json
from collections import Counter
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.text import Text
from matplotlib.ticker import FuncFormatter
import pandas as pd
import create_manuscript_figures_oct19 as h
from build_income_pubyear import load_history

def main():
    h.OUT.mkdir(exist_ok=True);h.DATA.mkdir(exist_ok=True)
    master=h.read('hee_analysis_master_v2_1.csv')
    ids=set(master.loc[master.is_eligible=='TRUE','record_id'])
    geo=h.read('hee_geo_long_v2_1.csv')
    geo=geo[geo.record_id.isin(ids)&(geo.is_special=='FALSE')&~geo.iso3.isin(['','NA'])]
    pairs=geo[['record_id','iso3']].drop_duplicates()
    counts=Counter(pairs.iso3)
    national=h.read('denominator_gbd_source.csv')
    assert len(national)==204 and national.iso3.nunique()==204
    n=sum(counts[i] for i in national.iso3)
    assert n==31592
    history=load_history()
    countries=json.loads((h.ROOT/'docs/data/countries.json').read_text(encoding='utf-8'))
    names={r['iso3']:r['country'] for r in countries}
    national['observed']=national.iso3.map(counts).fillna(0).astype(int)
    national['expected']=n*national.val.astype(float)/national.val.astype(float).sum()
    national['difference']=national.observed-national.expected
    national['country']=[names.get(i,history.get(i,{}).get('country',i)) for i in national.iso3]
    def group(i):
        return 'High income' if i=='TWN' else {'H':'High income','UM':'Upper middle income','LM':'Lower middle income','L':'Low income'}.get(history.get(i,{}).get('FY27'),'Not reported')
    national['income_group']=national.iso3.map(group)
    national['income_setting']=national.income_group.map(lambda x:'High-income settings' if x=='High income' else 'Income not reported' if x=='Not reported' else 'Low- and middle-income settings')
    assert abs(national.difference.sum())<1e-7
    chosen=pd.concat([national.nsmallest(16,'difference'),national.nlargest(8,'difference')]).sort_values('difference',ascending=False)
    national[['iso3','country','income_group','income_setting','observed','expected','difference']].to_csv(h.DATA/'unequal_weight_all_204_countries.csv',index=False)
    chosen[['iso3','country','income_group','observed','expected','difference']].to_csv(h.DATA/'unequal_weight_displayed_countries.csv',index=False)
    fig=plt.figure(figsize=(12,10.6))
    h.title(fig,'(Un)equal weight: research output compared with disease burden')
    fig.text(.035,.933,'The 16 largest deficits and 8 largest surpluses in study–country pairs',fontsize=10,color=h.SECONDARY)
    colours={'High-income settings':h.BLUE,'Low- and middle-income settings':h.ORANGE,'Income not reported':h.MUTED}
    handles=[Patch(color=c,label=g) for g,c in colours.items() if g in set(chosen.income_setting)]
    fig.legend(handles=handles,loc='upper left',bbox_to_anchor=(.035,.911),ncol=len(handles),borderaxespad=0)
    ax=fig.add_axes([.21,.20,.735,.65]);h.style(ax,'x')
    ys=list(range(len(chosen)))
    ax.barh(ys,chosen.difference,color=[colours[g] for g in chosen.income_setting],height=.61)
    ax.set_yticks(ys,chosen.country);ax.invert_yaxis();ax.tick_params(axis='y',pad=8,labelsize=9)
    ax.axvline(0,color=h.SECONDARY,lw=.7)
    lo,hi=chosen.difference.min(),chosen.difference.max();span=hi-lo;pad=span*.012
    ax.set_xlim(lo-span*.13,hi+span*.15)
    for y,value in zip(ys,chosen.difference):
        ax.text(value+pad if value>=0 else value-pad,y,f'{value:+,.0f}',ha='left' if value>=0 else 'right',va='center',fontsize=8,color=h.SECONDARY)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x,pos:f'{x:,.0f}'))
    ax.set_xlabel('Observed study–country pairs minus burden-proportional expected pairs',labelpad=12)
    ax.text(.02,1.015,'Fewer than expected',transform=ax.transAxes,color=h.SECONDARY,fontsize=8)
    ax.text(.98,1.015,'More than expected',transform=ax.transAxes,ha='right',color=h.SECONDARY,fontsize=8)
    caption=('Base: all 204 national GBD 2023 locations, including zero-study locations; 31,592 unique study–country pairs. '
        'Expected pairs = 31,592 × each country’s share of DALYs across these same 204 locations. '
        'Hong Kong, Cayman Islands, French Guiana and Guadeloupe have no row in this national GBD export and are excluded. '
        'A multi-country study counts once per named country. Studies span 2010–2026; 2026 is incomplete. '
        'Burden: GBD 2023 all-cause DALYs. Income colours use July 2026 classifications, combining the three low- and middle-income groups. '
        'Proportionality is a reference point, not an adequacy target. Labels are rounded to whole pairs.')
    h.foot(fig,caption,width=175,y=.035)
    # Inspect actual rendered bounds, including title, legend and all end labels.
    fig.canvas.draw();renderer=fig.canvas.get_renderer();bounds=fig.bbox
    outside=[]
    for text in fig.findobj(Text):
        if not text.get_visible() or not text.get_text():continue
        if text in ax.get_xticklabels() and not ax.get_xlim()[0]<=text.get_position()[0]<=ax.get_xlim()[1]:continue
        b=text.get_window_extent(renderer)
        if b.x0<0 or b.x1>bounds.width or b.y0<0 or b.y1>bounds.height:outside.append(text.get_text())
    assert not outside, f'Text outside figure: {outside}'
    h.save(fig,'07_unequal_weight_country_gaps',caption)
    (h.OUT/'07_unequal_weight_caption.txt').write_text(caption+'\n',encoding='utf-8')
    (h.DATA/'unequal_weight_verification.json').write_text(json.dumps({'national_locations':204,'study_country_pairs':n,'displayed_countries':len(chosen),'deficits':16,'surpluses':8,'text_bounds_check':'All visible text within canvas','right_margin_fraction':.055,'site_modified':False},indent=2),encoding='utf-8')
    readme=h.OUT/'README.md'
    text=readme.read_text(encoding='utf-8')
    section='\n\n## 07_unequal_weight_country_gaps\n\n'+caption+'\n\nRebuild: python -B scripts/create_manuscript_unequal_weight_oct19.py\n'
    if '## 07_unequal_weight_country_gaps' not in text:readme.write_text(text+section,encoding='utf-8')

if __name__=='__main__':main()
