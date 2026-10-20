"""Render the country concentration summary from the supplied manuscript statistics."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

OUT = Path(__file__).resolve().parents[1] / 'output' / 'figures'
OUT.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11,
                     'svg.fonttype': 'none', 'pdf.fonttype': 42})
navy, teal, pale, grey = '#16384A', '#007F82', '#E3EEEE', '#536570'
fig = plt.figure(figsize=(13, 8.5), facecolor='white')
fig.text(.065, .94, 'Health economic evidence is concentrated in a few countries',
         fontsize=22, weight='bold', color=navy)
fig.text(.065, .897, 'Broad geographic coverage masks a highly uneven distribution of studies',
         fontsize=12, color=grey)

ax = fig.add_axes([.065, .385, .56, .415])
labels = ['Top 3 countries', 'Top 5 countries', 'Top 10 countries']
values = [49.7, 57.7, 70.7]
ys = [2, 1, 0]
for y, v, label in zip(ys, values, labels):
    ax.barh(y, 100, height=.21, color=pale)
    ax.barh(y, v, height=.21, color=teal)
    ax.text(0, y+.24, label, color=navy, weight='bold', fontsize=12)
    ax.text(v+1.5, y, f'{v:.1f}%', va='center', color=navy, weight='bold', fontsize=13)
details = [
    'United States, United Kingdom and China',
    '+ Canada and the Netherlands',
    '+ Australia, Spain, Japan, Germany and Italy',
]
for y, detail in zip(ys, details):
    ax.text(0, y-.25, detail, va='center', color=grey, fontsize=10)
ax.set(xlim=(0, 100), ylim=(-.65, 2.7), yticks=[], xticks=[0, 25, 50, 75, 100])
ax.set_xticklabels(['0', '25', '50', '75', '100%'], color=grey)
ax.tick_params(axis='both', length=0)
for spine in ax.spines.values(): spine.set_visible(False)
ax.set_xlabel('Cumulative share of studies that name a country', color=grey, labelpad=11)
fig.text(.065, .825, 'A  |  Study concentration', color=navy, weight='bold', fontsize=13)

fig.add_artist(Rectangle((.675,.39), .26,.43, transform=fig.transFigure,
                         facecolor='#F2F6F7', edgecolor='none'))
fig.text(.697,.775,'B  |  Geographic coverage',color=navy,weight='bold',fontsize=12)
fig.text(.697,.705,'187 / 204',color=teal,weight='bold',fontsize=29)
fig.text(.697,.665,'countries or territories represented',color=grey,fontsize=10)
fig.text(.697,.596,'98.7%',color=teal,weight='bold',fontsize=27)
fig.text(.697,.552,'of geographies with >1 million people\nhad at least one evaluation',color=grey,fontsize=10,linespacing=1.5)
fig.text(.697,.467,'71.9% of evaluations named\none or more countries.',color=navy,fontsize=11,linespacing=1.5)

fig.text(.065,.305,'C  |  Evidence relative to population',color=navy,weight='bold',fontsize=13)
fig.text(.065,.268,'Median evaluations per 10 million people',color=grey,fontsize=10)
ax2=fig.add_axes([.065,.135,.40,.105])
ax2.barh([1,0],[6.4,84.1],height=.48,color=['#87B7B8',teal])
for y,v,label in [(1,6.4,'Low-income countries'),(0,84.1,'High-income countries')]:
    ax2.text(0,y+.31,label,color=grey,fontsize=10)
    ax2.text(v+2,y,f'{v:.1f}',va='center',weight='bold',color=navy,fontsize=12)
ax2.set(xlim=(0,105),ylim=(-.5,1.6)); ax2.axis('off')
fig.text(.505,.237,'13.1×',color=teal,fontsize=29,weight='bold')
fig.text(.505,.187,'higher median in\nhigh-income countries',color=grey,fontsize=10,linespacing=1.5)
fig.text(.712,.237,'0.84',color=teal,fontsize=29,weight='bold')
fig.text(.712,.187,'Gini coefficient of\ncountry-level study counts',color=grey,fontsize=10,linespacing=1.5)

fig.text(.065,.086,'Notes: Country groups in panel A are cumulative; multi-country studies are counted once within each group.',fontsize=8,color=grey)
fig.text(.065,.066,'Panel C includes countries with >1 million people. Gini includes represented countries, counting studies once per country;',fontsize=8,color=grey)
fig.text(.065,.046,'including countries with no studies gives 0.842. Coverage exceptions among geographies with >1 million people: Eritrea and Mauritius.',fontsize=8,color=grey)
fig.text(.065,.026,'Source: supplied manuscript summary statistics. Ratios calculated from the reported medians.',fontsize=8,color=grey)
for ext in ['png','svg','pdf']:
    fig.savefig(OUT / f'health_economic_evidence_concentration.{ext}',dpi=300,facecolor='white')
print(OUT / 'health_economic_evidence_concentration.png')
