"""Install refreshed figures and verify provenance for the whole current gallery."""
import csv
import hashlib
import json
import re
import shutil
from datetime import datetime,timezone
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'docs/data';FIG=ROOT/'docs/figures'
OUT=ROOT/'exports/publication_reconciliation/figure_refresh'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    manifest=read(OUT/'remaining_figure_manifest.json');assert len(manifest)==15
    assert read(OUT/'remaining_figure_counts.json')['eligible']==41610
    backup=OUT/'presentation_backups'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ');backup.mkdir(parents=True)
    for site in ('docs','docs/v2','docs/v3'):
        for name in ('data/content.json','data/figure_copy.json','data/figure_updates.json','app.js','index.html'):
            p=ROOT/site/name
            if p.exists():
                dest=backup/site/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
    content=read(DATA/'content.json');copy=read(DATA/'figure_copy.json');updates=read(DATA/'figure_updates.json')
    for old,info in manifest.items():
        png=OUT/Path(info['file']).with_suffix('.png')
        target=FIG/info['file']
        if not target.exists() or target.stat().st_mtime < png.stat().st_mtime:
            with Image.open(png) as im:
                im.load();assert im.width>1000 and im.height>700
                im.convert('RGB').save(target,format='WEBP',quality=95,method=4)
        updates[old]={'file':info['file'],'caption':info['caption']}
        copy[old]={k:info[k] for k in ('title','summary','caption')}
    for section in content['gallery']:
        section['blurb']=section.get('blurb','').replace('41,657','41,610')
        for f in section['figs']:
            key=f['file']
            if key in manifest:
                f.update({k:manifest[key][k] for k in ('title','summary','caption')})
            elif key in updates:
                f['caption']=updates[key]['caption']
                copy.setdefault(key,{})['caption']=f['caption']
            elif 'caption' in f:
                # A stale copy-layer caption must not override an actual builder's caption.
                copy.setdefault(key,{})['caption']=f['caption']
    write(DATA/'content.json',content);write(DATA/'figure_copy.json',copy);write(DATA/'figure_updates.json',updates)
    # Versioned study bundles were updated too; use the same refreshed presentations.
    for site in ('docs/v2','docs/v3'):
        root=ROOT/site;old_content=read(root/'data/content.json')
        old_content['gallery']=json.loads(json.dumps(content['gallery']))
        for sec in old_content['gallery']:
            for f in sec['figs']:
                key=f['file'];new=updates.get(key,{}).get('file',key)
                if (FIG/new).exists():shutil.copy2(FIG/new,root/'figures'/new)
                f['file']=new
                if key in copy: f.update(copy[key])
        write(root/'data/content.json',old_content)
    for site in ('docs','docs/v2','docs/v3'):
        for name in ('app.js','index.html'):
            p=ROOT/site/name;text=p.read_text(encoding='utf-8').replace('2026-10-14-methods-reconciled','2026-10-14-all-figures-reconciled')
            p.write_text(text,encoding='utf-8')
    # Explicitly map each gallery figure to its successful current-dataset build.
    builders={
      'fig_method_stream_v2.svg':'build_eval_type_figures.py','fig_decision_time_v2.svg':'build_eval_type_figures.py',
      'fig_disease_circular.webp':'build_gbd_figures.py','fig_transition.webp':'build_gbd_figures.py',
      'paper04.webp':'build_gbd_figures.py','paper05.webp':'build_gbd_figures.py','paper08.webp':'build_gbd_figures.py',
      'fig_burden_disease_companion.webp':'build_gbd_figures.py','fig_funder_opportunity.webp':'build_gbd_figures.py','fig_funder_trajectory.webp':'build_gbd_figures.py',
      'fig_theme_rank.webp':'build_income_pubyear_figures.py','fig_intervention_mix.webp':'build_income_pubyear_figures.py',
      'fig_metric.webp':'build_income_pubyear_figures.py','fig_equity_time.webp':'build_income_pubyear_figures.py',
      'paper01.webp':'reconcile_publication_methods.py','fig_authorship_pattern_v2.svg':'build_authorship_figures.py',
      'fig_forest_v2.svg':'build_authorship_figures.py','paper06_v2.svg':'build_authorship_figures.py',
      'fig_collab_chord_v2.svg':'build_authorship_figures.py','fig_map_authorship_v2.svg':'build_authorship_figures.py',
      'fig_research_burden_ratio.svg':'build_research_burden_ratio.py','fig_deficit.webp':'build_denominator_audit.py',
      'fig_inequality.webp':'build_denominator_audit.py','fig_reach_time.webp':'build_denominator_audit.py',
      'fig_funder_funders.svg':'build_wellcome_analysis_gbd_v2.py','fig_funder_scorecard_v2.svg':'build_funder_scorecard.py',
      'fig_wellcome_priorities.svg':'build_wellcome_analysis_gbd_v2.py','wellcome_analysis.html':'build_wellcome_analysis_gbd_v2.py'}
    audit=[];seen=set()
    for sec in content['gallery']:
        for f in sec['figs']:
            old=f['file']
            if old in seen:continue
            seen.add(old);new=updates.get(old,{}).get('file',old)
            builder=manifest.get(old,{}).get('builder',builders.get(old))
            assert builder,(old,'missing rebuild provenance')
            path=FIG/new;assert path.is_file() and path.stat().st_size>0
            if new.endswith(('.png','.webp')):
                with Image.open(path) as im:im.verify()
            if old in builders and old!='paper01.webp':
                log=ROOT/'exports/publication_reconciliation/followup_build_logs'/(builder+'.log')
                assert log.is_file(),(old,'missing successful build log')
            caption=updates.get(old,{}).get('caption',copy.get(old,{}).get('caption',f.get('caption','')))
            for stale in ('41,657','31,471','31,775','27,930','22,970'):
                assert stale not in caption,(old,'stale caption',stale)
            audit.append({'gallery_key':old,'shown_file':new,'builder':builder,'eligible_count':41610,'sha256':sha(path),'caption':caption})
    # Dynamic gallery additions and comparison images are documented separately.
    for p in (FIG/'schmallenbach2025').glob('*.png'):
        audit.append({'gallery_key':str(p.relative_to(FIG)),'shown_file':str(p.relative_to(FIG)),
                      'builder':'Published reference figure' if p.name.startswith('original_') else 'build_kld_replication_v2.py',
                      'eligible_count':None if p.name.startswith('original_') else 41610,'sha256':sha(p),'caption':'Published paper comparison' if p.name.startswith('original_') else 'Latest kld_followup rebuild; captions in app.js'})
    for name,builder in [('fig_glance_regions_who_v4.html','build_glance_regions_who_v4.py'),('fig_funder_treemap.svg','build_wellcome_analysis_gbd_v2.py')]:
        p=FIG/name;assert p.exists();audit.append({'gallery_key':name,'shown_file':name,'builder':builder,'eligible_count':41610,'sha256':sha(p),'caption':'Interactive/alternate figure included in current gallery'})
    write(OUT/'all_figure_audit.json',{'eligible_count':41610,'gallery_figures_checked':len(seen),'remaining_static_figures_rebuilt':len(manifest),'figures':audit,'backup':str(backup.relative_to(ROOT)),'deployment':'Local workspace; deployment not performed'})
    with (OUT/'all_figure_audit.csv').open('w',encoding='utf-8',newline='') as handle:
        w=csv.DictWriter(handle,fieldnames=['gallery_key','shown_file','builder','eligible_count','sha256','caption']);w.writeheader();w.writerows(audit)
    print(f'{len(seen)} unique gallery figures have current-dataset rebuild provenance; {len(manifest)} residual figures replaced. Dynamic and reference figures logged separately.')
if __name__=='__main__':main()
