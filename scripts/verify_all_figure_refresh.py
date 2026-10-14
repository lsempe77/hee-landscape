"""Final integrity and independent denominator check for the refreshed gallery."""
import hashlib
import json
from pathlib import Path
import income_pubyear_figure_data as fd
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'exports/publication_reconciliation'
audit=json.loads((OUT/'figure_refresh/all_figure_audit.json').read_text(encoding='utf-8'))
counts=json.loads((OUT/'figure_refresh/remaining_figure_counts.json').read_text(encoding='utf-8'))
rows,labels,geo=fd.load(str(ROOT/'data/raw'))
oa,n=fd.openaccess(rows,'income_group_pubyear')
assert n==counts['openaccess_comparison_n']==22954
for figure in audit['figures']:
    p=ROOT/'docs/figures'/figure['shown_file']
    assert hashlib.sha256(p.read_bytes()).hexdigest()==figure['sha256'],p
assert len(rows)==counts['eligible']==41610
assert audit['gallery_figures_checked']==43 and audit['remaining_static_figures_rebuilt']==15
audit['master_sha256']=hashlib.sha256((ROOT/'data/raw/hee_analysis_master_v2_1.csv').read_bytes()).hexdigest()
audit['independent_openaccess_base_check']='Passed: 22,954; independently calculated by income_pubyear_figure_data.py'
(OUT/'figure_refresh/all_figure_audit.json').write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8')
verification=json.loads((OUT/'verification.json').read_text(encoding='utf-8'))
verification.update(figure_file_check=(OUT/'figure_refresh/file_checks.log').read_text(encoding='utf-8').splitlines()[0],
                    all_gallery_figures_reconciled=True,gallery_figures_checked=43,remaining_static_figures_rebuilt=15,
                    figure_audit='figure_refresh/all_figure_audit.json',
                    visual_check='15 rebuilt static figures reviewed as rendered previews; browser runtime not used')
(OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n',encoding='utf-8')
print('Independent open-access base check passed: 22,954.')
print(verification['figure_file_check'])
print('All 43 unique gallery figures have current rebuild provenance; artifact hashes pass.')
