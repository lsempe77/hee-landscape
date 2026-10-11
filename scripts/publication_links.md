# Publication links from EPPI RIS exports

Run from the repository root:

```powershell
python data/raw/url_lookup/update_study_links_from_ris.py
python scripts/apply_publication_links.py
```

The first script matches the three `ExportedRis*.txt` files to
`studies_without_doi.csv` by RIS `U1` / EPPI `record_id`. The second enriches
`data/raw/hee_analysis_master.csv` with recovered DOIs, URLs and their sources,
refreshes column coverage, and writes link fields to all four web study datasets.
A copy of the original master is kept in `data/raw/url_lookup` before the first
update. Reapply after regenerating the web datasets; reruns are idempotent.

Current, v2 and v3 mappings are checked against eligible master row order,
years, evaluation types and available titles. Legacy v1 has a different order:
only unique title/year matches from its own country shards are enriched.
Unmapped legacy studies retain empty link fields, so their empty fields do not
prove that the original publication lacks a DOI. Dated XLSX exports remain
historical snapshots; the current website's filtered CSV download includes the
enriched DOI, URL, provenance and resolved publication link fields.

The current Overview card counts each study once when it has a valid DOI or
HTTP(S) URL. This is link availability, not evidence of free full-text access;
the OpenAlex open-access percentage is unchanged. Study lists show a
publication link, preferring the recorded URL to a DOI resolver.

The initial lookup total of 5,106 included three literal `NA` DOI placeholders.
After treating those as missing, 5,103 studies have usable recovered links and
169 remain without one. Two further malformed DOIs are excluded from DOI
recovery, while their valid URLs are retained. The master gains 2,828 DOIs;
41,488 of 41,657 included studies (99.6%) have a DOI or URL.
