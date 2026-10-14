"""Create the requested slide-style transition figure without changing the map."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.image as mpimg
import matplotlib.ticker as ticker
import build_gbd_figures as gbd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'exports/transition_latest_dataset'
OUT.mkdir(exist_ok=True)
def main():
    rows,geo,l1,burden=gbd.load(str(ROOT/'data/raw'))
    assert len(rows)==41610
    blocks=['cmnn','ncd','inj'];years=list(range(2010,2026))
    colours={'cmnn':'#ee7544','ncd':'#2d7dce','inj':'#8d8c80'}
    names={'cmnn':'Communicable, maternal & nutritional','ncd':'Non-communicable','inj':'Injuries'}
    shares={};ns={};links={}
    for year in years:
        selected=[r for r in rows if 'lmic' in r['sides'] and r['year']==year and r['gbd']]
        count=Counter()
        for r in selected:
            count.update({l1[c] for c in r['gbd']})
        ns[year]=len(selected);links[year]=sum(count.values())
        shares[year]={b:count[b]/sum(count.values()) for b in blocks}
        assert abs(sum(shares[year].values())-1)<1e-12
    bshare={}
    for year in [2010,2023]:
        counts=Counter()
        for cause,value in burden[year]['lmic'].items():counts[l1[cause]]+=value
        bshare[year]={b:counts[b]/sum(counts.values()) for b in blocks}
    plt.rcParams.update({'font.family':'Arial','svg.fonttype':'none','pdf.fonttype':42})
    fig=plt.figure(figsize=(15.24,8.59),facecolor='white',dpi=100)
    navy='#00246d';body='#194a77'
    fig.patches.extend([
        patches.Rectangle((0,.887),.05,.057,transform=fig.transFigure,color='#0083ad',linewidth=0),
        patches.Rectangle((.074,.054),.884,.749,transform=fig.transFigure,color='#f7f4ee',linewidth=0),
        patches.Rectangle((.037,.12),.011,.709,transform=fig.transFigure,color='#f4f1eb',linewidth=0),
        patches.Rectangle((0,.046),1,.008,transform=fig.transFigure,color='#b1d1ee',linewidth=0),
        patches.Ellipse((.03,.05),.040,.071,transform=fig.transFigure,color='#b1d1ee',linewidth=0)])
    # Use the genuine logo and gradient assets from the user's 3ie presentation.
    axg=fig.add_axes([.040,.125,.006,.694],zorder=2);axg.imshow(mpimg.imread(OUT/'image3.png'),aspect='auto');axg.axis('off')
    axlogo=fig.add_axes([.0175,.018,.023,.060],zorder=5);axlogo.imshow(mpimg.imread(OUT/'image2.png'));axlogo.axis('off')
    title='Economic evidence in L&MICs shifted towards NCDs, mirroring disease burdens'
    fig.text(.08,.95,title,color=navy,fontsize=24,va='top')
    fig.text(.083,.876,'Disease mix of economic-evaluation research about L&MICs, across the three epidemiological-transition classes, against the',color=body,fontsize=16.8,va='top')
    fig.text(.083,.841,'burden at both ends of the period.',color=body,fontsize=16.8,va='top')
    ax=fig.add_axes([.13,.117,.827,.605],facecolor='#f7f4ee',zorder=3)
    for block in blocks:
        ax.plot(years,[shares[y][block] for y in years],color=colours[block],linewidth=3.1,marker='o',markersize=5.7,label=names[block])
        for year,x1,x2,tx,align in [(2010,2008.85,2009.65,2008.67,'right'),(2023,2025.4,2026.2,2026.35,'left')]:
            value=bshare[year][block]
            ax.plot([x1,x2],[value,value],color=colours[block],linewidth=2,linestyle=(0,(2,2)))
            ax.text(tx,value,f'{value:.0%}',ha=align,va='center',fontsize=12,color=colours[block],fontweight='bold')
    ax.text(2008.2,max(bshare[2010].values())+.035,'2010\nburden',ha='center',color='#939187',fontsize=12,linespacing=1.2)
    ax.text(2026.6,max(bshare[2023].values())+.035,'2023\nburden',ha='center',color='#939187',fontsize=12,linespacing=1.2)
    ax.set_xlim(2006.6,2027.6);ax.set_ylim(-.035,.733)
    ax.set_xticks(list(range(2010,2026,2)));ax.set_yticks([0,.2,.4,.6])
    ax.yaxis.set_major_formatter(ticker.PercentFormatter(1,decimals=0))
    ax.tick_params(axis='both',length=0,labelsize=12,pad=7,colors='#85847c')
    for sp in ax.spines.values():sp.set_visible(False)
    ax.grid(color='#e5e2da',linewidth=1,alpha=.8);ax.set_axisbelow(True)
    ax.set_ylabel('Share of LMIC research (disease mentions)',fontsize=12,color='#85847c',labelpad=3)
    ax.legend(loc='upper center',bbox_to_anchor=(.54,1.14),ncol=3,frameon=False,fontsize=12,labelcolor='#85847c',handlelength=1.2,columnspacing=1,handletextpad=.7)
    fig.text(.056,.026,'Systematic mapping of recent global research on health system financing using machine learning',color='#185ba5',fontsize=13,va='center')
    fig.text(.985,.026,'Advisory Group – Preliminary Findings',color='#185ba5',fontsize=13,va='center',ha='right')
    stem=OUT/'economic_evidence_LMIC_transition_updated_2026-10-14'
    for ext in ('png','svg','pdf'):
        fig.savefig(stem.with_suffix('.'+ext),dpi=200 if ext=='png' else 100,facecolor='white')
    plt.close(fig)
    with (OUT/'updated_transition_data.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['series','year','class','share','records','class_mentions']);w.writeheader()
        for y in years:
            for b in blocks:w.writerow({'series':'research','year':y,'class':names[b],'share':shares[y][b],'records':ns[y],'class_mentions':links[y]})
        for y in bshare:
            for b in blocks:w.writerow({'series':'burden','year':y,'class':names[b],'share':bshare[y][b]})
    provenance={'included_records':41610,'research_period':[2010,2025],'burden_years':[2010,2023],
                'master_sha256':hashlib.sha256((ROOT/'data/raw/hee_analysis_master_v2_1.csv').read_bytes()).hexdigest(),
                'research_endpoint_shares':{y:shares[y] for y in [2010,2025]},'burden_shares':bshare,
                'research_endpoint_n':{y:ns[y] for y in [2010,2025]},
                'counting':'Unique study–GBD level-1 class links, normalised over class links within year; a study spanning classes contributes once per class. Matches the current GBD transition calculation.',
                'geography':'Country studied; publication-year World Bank groups for research and burden-year groups for DALYs. A mixed-income study may enter the LMIC set.',
                'coding':'Latest title/abstract GBD coding; CMNN includes neonatal conditions despite the abbreviated legend. Not the earlier MeSH crosswalk.',
                'map_changed':False}
    (OUT/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(provenance,indent=2))
if __name__=='__main__':main()
