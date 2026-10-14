"""Refresh current outputs after the follow-up publication decisions."""
import json
import csv
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'exports/publication_reconciliation'
LOG=OUT/'followup_build_logs'
LOG.mkdir(exist_ok=True)
names=['verify_publication_reconciliation.py','build_disease_gbd_data.py','build_funder_filter.py',
       'apply_review_eval_type.py','build_region_disease_themes_who_ee.py','build_glance_regions_who_v4.py',
       'build_income_pubyear_figures.py','build_gbd_figures.py','build_eval_type_figures.py',
       'build_authorship_figures.py','build_denominator_audit.py','build_research_burden_ratio.py',
       'build_funder_scorecard.py','build_wellcome_analysis_gbd_v2.py','build_kld_replication_v2.py']
for name in names:
    args=[sys.executable,str(ROOT/'scripts'/name)]
    if name=='build_kld_replication_v2.py':args+=['--out',str(OUT/'kld_followup')]
    with (LOG/(name+'.log')).open('w',encoding='utf-8') as f:
        p=subprocess.run(args,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
    print(name+': '+str(p.returncode),flush=True)
    if p.returncode:raise SystemExit('Build failed; see '+str(LOG/(name+'.log')))
for p in (OUT/'kld_followup').glob('*.png'):shutil.copy2(p,ROOT/'docs/figures/schmallenbach2025'/p.name)
with (OUT/'kld_followup/kld_decomposition.csv').open(encoding='utf-8') as f:
    result={r['group']:r for r in csv.DictReader(f) if r['cause_set']=='16causes'}
with (OUT/'kld_followup/kld_windows.csv').open(encoding='utf-8') as f:
    windows={(r['group'],r['window']):r for r in csv.DictReader(f) if r['cause_set']=='16causes'}
def interval(group,key):
    r=result[group]; return f"{float(r[key+'_lo']):+.0f}% to {float(r[key+'_hi']):+.0f}%"
summary2=(f"From 2010–12 to 2017–19, divergence for all studies changed by {float(result['all']['observed_change_pct']):+.0f}% "
          f"(95% interval {interval('all','observed_change')}). For studies of low- and middle-income countries, "
          f"it changed by {float(result['lmic']['observed_change_pct']):+.0f}% ({interval('lmic','observed_change')}): no clear change. "
          "Open the figure to compare it with the paper's original.")
summary3=(f"For all studies, burden changes alone changed divergence by {float(result['all']['only_dalys_change_research_fixed_pct']):+.0f}%, "
          f"while research changes alone changed it by {float(result['all']['only_research_changes_dalys_fixed_pct']):+.0f}% "
          f"({interval('all','only_research_changes_dalys_fixed')}). For low- and middle-income settings, burden changes alone "
          f"changed it by {float(result['lmic']['only_dalys_change_research_fixed_pct']):+.0f}% "
          f"({interval('lmic','only_dalys_change_research_fixed')}), and research changes alone by "
          f"{float(result['lmic']['only_research_changes_dalys_fixed_pct']):+.0f}% "
          f"({interval('lmic','only_research_changes_dalys_fixed')}). These scenarios need not add up to the observed change.")
p=ROOT/'docs/app.js';text=p.read_text(encoding='utf-8')
for file,summary in [('main_fig2a_16causes.png',summary2),('main_fig3_16causes.png',summary3)]:
    pattern=r'(\{ file: KLD_DIR \+ "'+file+r'",.*?summary: )(.+?)(,\s*caption:)'
    text,n=re.subn(pattern,lambda m:m[1]+json.dumps(summary,ensure_ascii=False)+m[3],text,count=1,flags=re.S)
    assert n==1,file
# Update sample-size statement from the rebuilt windows rather than an older snapshot.
lm0=int(windows[('lmic','2010–12')]['n_studies']); lm1=int(windows[('lmic','2017–19')]['n_studies'])
al0=int(windows[('all','2010–12')]['n_studies']); al1=int(windows[('all','2017–19')]['n_studies'])
text=re.sub(r'Small numbers: \d+ studies',f'Small numbers: {lm0:,} studies',text)
text=re.sub(r'"\d+ in 2017–19 \(all studies: [\d,]+ and [\d,]+\)',f'"{lm1:,} in 2017–19 (all studies: {al0:,} and {al1:,})',text)
p.write_text(text,encoding='utf-8')
for site in ('docs','docs/v2','docs/v3'):
    for name in ('app.js','index.html'):
        p=ROOT/site/name
        text=p.read_text(encoding='utf-8').replace('2026-10-14-publication-reconciliation','2026-10-14-publication-followup')
        p.write_text(text,encoding='utf-8')
for name in ['verify_publication_reconciliation.py','check_site_figures.py']:
    with (LOG/(name+'.log')).open('w',encoding='utf-8') as f:
        p=subprocess.run([sys.executable,str(ROOT/'scripts'/name)],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
    assert p.returncode==0,name
verification=json.loads((OUT/'verification.json').read_text(encoding='utf-8'))
verification.update(eligible_count=41610,pending_records_retained=0,excluded_total=47,
                    geography_correction='Title/abstract sample location not reported; Turkey removed',
                    affected_builds='passed; followup_build_logs',kld_output='kld_followup')
(OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n',encoding='utf-8')
print('All follow-up checks and builds passed.',flush=True)
