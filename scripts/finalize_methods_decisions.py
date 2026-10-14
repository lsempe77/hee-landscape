"""Record the user's confirmed methods references, dates and publication policy."""
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'exports/publication_reconciliation'
timestamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
backup=OUT/'manuscript_backups'/timestamp;backup.mkdir(parents=True)
paths=[ROOT/'data/raw/HEE_METHODS_PUBLICATION-updated-Oct-14.md',ROOT/'data/raw/HEE_METHODS.md',OUT/'manuscript_reconciliation.json',OUT/'verification.json']
for p in paths:shutil.copy2(p,backup/p.name)
p=paths[0];text=p.read_text(encoding='utf-8')
assert '[protocol reference]' in text and '[search\ndates]' in text and '[access date]' in text
text=text.replace(' Items in [square brackets] need confirming before submission.','')
text=text.replace('financing research [protocol reference].','financing research (Marion et al., 2026).')
text=text.replace('(Ovid) [search\ndates], combining terms','(Ovid) between\n27 July and 3 August 2026, combining terms')
text=text.replace('World Bank API [access date].','World Bank API (latest access: 1 September 2026).')
text=text.replace('published economic evaluations were eligible.','published economic evaluations were eligible. Standalone preprints, working papers and other\nnon-article reports were retained when they met the same substantive eligibility criteria;\npublication format alone was not an exclusion criterion.')
text=text.replace('[Team decision required: retain standalone preprints and other non-article reports, exclude\nthem, or present a sensitivity analysis.]','Standalone preprints and other non-article reports were retained under the same eligibility\ncriteria; their findings may change in later publication versions.')
text+='''
## References

Marion P, Hutchinson B, Lee S et al. Protocol: Systematic mapping of recent global research on
health system financing using machine learning [version 1; peer review: awaiting peer review].
Wellcome Open Research. 2026;11:811. https://doi.org/10.12688/wellcomeopenres.27542.1
'''
p.write_text(text,encoding='utf-8')
p=paths[1];text=p.read_text(encoding='utf-8')
text=text.replace('Protocol reference, search dates, World Bank access date and standalone preprint/non-article policy remain open.',
                  'The user confirmed the protocol citation (Marion et al., Wellcome Open Research 2026;11:811; doi:10.12688/wellcomeopenres.27542.1), search period 27 July–3 August 2026, latest World Bank access date 1 September 2026, and retention of eligible standalone preprints/non-article reports. These four manuscript items are resolved. The access date and citation were supplied by the user; no fresh source-data retrieval was performed.')
p.write_text(text,encoding='utf-8')
p=paths[2];summary=json.loads(p.read_text(encoding='utf-8'))
summary['remaining_items']=[]
summary['confirmed_methods_decisions']={'source':'User confirmed in conversation, 14 October 2026','protocol_doi':'10.12688/wellcomeopenres.27542.1','search_start':'2026-07-27','search_end':'2026-08-03','world_bank_latest_access':'2026-09-01','standalone_preprints_nonarticle_policy':'Retain if otherwise eligible','backup':str(backup.relative_to(ROOT))}
p.write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
p=paths[3];v=json.loads(p.read_text(encoding='utf-8'))
v['manuscript_reconciliation']='manuscript_reconciliation.json; all four user-confirmed manuscript placeholders resolved'
p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
for token in ('[protocol reference]','[search\ndates]','[access date]','[Team decision required:'):
    assert token not in paths[0].read_text(encoding='utf-8'),token
assert '41,610' in paths[0].read_text(encoding='utf-8')
print('Protocol, search year/date range, user-supplied access date and retention policy recorded. No eligibility or count changes.')
