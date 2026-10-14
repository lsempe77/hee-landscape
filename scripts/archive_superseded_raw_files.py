"""Archive explicitly superseded raw-folder documents without breaking build inputs."""
import csv
import hashlib
import json
import os
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw'
csv.field_size_limit(10**9)
def checked(path):
    path.resolve().relative_to(RAW.resolve())
    return path
def main():
    archive=checked(RAW/'Archive')
    existing=checked(RAW/'archive')
    # Canonicalise the existing directory's case on Windows, without overwriting it.
    if existing.exists() and existing.name in [p.name for p in RAW.iterdir()]:
        temp=checked(RAW/'archive_case_rename_tmp')
        assert not temp.exists()
        os.rename(existing,temp);os.rename(temp,archive)
    archive.mkdir(exist_ok=True)
    destination=checked(archive/'superseded_2026-10-14');destination.mkdir(exist_ok=True)
    docs=['HEE_METHODS_PUBLICATION.md','V2_DATASET_README.md','CODEBOOK.md','DATA_QUALITY_AUDIT.md','data_dictionary.md','README.md','column_coverage.csv']
    share_docs=docs+['HEE_METHODS.md','burden_gbd_l2_ratios.csv','fig_burden_gbd_l2.png','hee-paper_v2_gbd.html']
    paths=[RAW/n for n in docs]+[RAW/'hee_share_v2_1'/n for n in share_docs]
    manifest=[]
    for source in paths:
        checked(source);assert source.is_file(),source
        target=checked(destination/source.relative_to(RAW));assert not target.exists(),target
        target.parent.mkdir(parents=True,exist_ok=True)
        digest=hashlib.sha256(source.read_bytes()).hexdigest()
        size=source.stat().st_size
        os.rename(source,target)
        assert hashlib.sha256(target.read_bytes()).hexdigest()==digest
        manifest.append({'original':source.relative_to(RAW).as_posix(),'archived':target.relative_to(RAW).as_posix(),'bytes':size,'sha256':digest,'reason':'Pre-reconciliation document, coverage table or rendered output; superseded by October 14 dataset/methods/figure outputs'})
    with (destination/'column_coverage.csv').open(encoding='utf-8-sig',newline='') as f:
        old={r['column']:r for r in csv.DictReader(f)}
    master=RAW/'hee_analysis_master_v2_1.csv'
    with master.open(encoding='utf-8-sig',newline='') as f:
        rd=csv.DictReader(f);fields=rd.fieldnames;rows=list(rd)
    included=[r for r in rows if r['is_eligible']=='TRUE']
    assert len(rows)==72845 and len(included)==41610
    missing={'','NA','na'}
    with (RAW/'column_coverage.csv').open('w',encoding='utf-8',newline='') as f:
        wr=csv.DictWriter(f,fieldnames=['column','type','pct_present','pct_present_eligible','n_distinct']);wr.writeheader()
        for field in fields:
            values=[r[field] for r in rows];inc=[r[field] for r in included]
            kind=old.get(field,{}).get('type','character')
            wr.writerow({'column':field,'type':kind,'pct_present':round(100*sum(v not in missing for v in values)/len(values),1),
                         'pct_present_eligible':round(100*sum(v not in missing for v in inc)/len(inc),1),'n_distinct':len({v for v in values if v not in missing})})
    (RAW/'README.md').write_text('''# Current HEE raw data and methods

Reconciled 14 October 2026. **41,610 included records** within 72,845 extracted records.
Filter `is_eligible == TRUE` when analysing the master; excluded records remain for traceability.

## Files to share

- `hee_analysis_master_v2_1.csv`: current master with publication-year income classifications.
- `HEE_METHODS_PUBLICATION-updated-Oct-14.md`: current publication methods draft.
- `HEE_METHODS.md`: detailed methodological decisions and current reconciliation addendum.

## Current build inputs

The v2, v2_1, WHO and review-explanations master variants are all reconciled, current files, not older datasets. Build and verification scripts require their existing paths. Long-form geography, outcomes, intervention, affiliation and topic files are source/join tables; filter them using eligible master IDs. Frozen topic coordinates and the original review-screening upload remain source evidence and are not refitted or overwritten.

`hee_share_v2_1/gbd_disease_long.csv` contains the current GBD disease coding, with its hierarchy and coding documentation. `GBD data/` contains today's GBD 2023 burden exports. `denominator_gbd_source.csv` and `denominator_geography_source.csv` support the checked country universe; the national all-cause burden values match today's exports. `OGHIST_2026_10_08.xlsx` is the historical World Bank income source used by the current pipeline. Age of a source file alone does not make it obsolete.

`column_coverage.csv` is regenerated from the current v2_1 master. New lineage fields have descriptive storage types; coverage does not establish validation or accuracy.

## Historical files and audit evidence

`Archive/superseded_2026-10-14/` holds superseded documents, old coverage tables and pre-reconciliation report outputs, preserving their original subfolder structure. Its manifest records original paths and SHA256 checks. The older v1 master remains in `Archive/`.

The existing `review_screening/`, `publication_reconciliation/`, `url_lookup/` and `funder_classification/` folders retain provenance and backups at the paths cited in audit reports. Historical reports in those folders describe their original audit dates; current consolidated verification is `exports/publication_reconciliation/verification.json`.

The dataset is an internal/co-author working export. The pre-existing source-data redistribution restrictions still apply; archiving is not a public-release clearance.
''',encoding='utf-8')
    (RAW/'hee_share_v2_1/README.md').write_text('''# HEE GBD source tables and reconciled companion master

Current eligibility: **41,610 included records** in `hee_analysis_master.csv`; all 72,845 original extracted rows remain. The preferred full sharing master is `../hee_analysis_master_v2_1.csv`, and the publication methods are `../HEE_METHODS_PUBLICATION-updated-Oct-14.md`.

The current builds read `gbd_disease_long.csv` here for title/abstract GBD disease coding. GBD hierarchies, risk coding, coding rules and crosswalks remain source evidence. Other long-form tables in this source share preserve the received export; use the current masters and root-level reconciled geography when analysing them.

Earlier share-level methods, summaries, codebooks, coverage tables and rendered burden outputs were moved to `../Archive/superseded_2026-10-14/hee_share_v2_1/`. They describe the pre-reconciliation 41,657-record vintage and should not be used as current counts. Original source-data redistribution restrictions continue to apply.
''',encoding='utf-8')
    record={'date':'2026-10-14','files_archived':len(manifest),'files':manifest,'eligible_records':41610,'masters_moved':False,'active_gbd_inputs_moved':False,'coverage_source':'hee_analysis_master_v2_1.csv'}
    (destination/'manifest.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    (archive/'README.md').write_text('''# Historical raw-data files

`superseded_2026-10-14/` contains documents, coverage tables and rendered outputs superseded by the October 14 reconciliation. See its `manifest.json` for original paths, reasons and SHA256 checks. `hee_analysis_master_v1.csv` is the earlier v1 dataset and remains unchanged.

Use the files identified in `../README.md` for current sharing and analysis. No current master, GBD source export or active build input was moved here.
''',encoding='utf-8')
    print(json.dumps({k:v for k,v in record.items() if k!='files'},indent=2))
if __name__=='__main__':main()
