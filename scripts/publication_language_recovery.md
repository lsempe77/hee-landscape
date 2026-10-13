# Publication language recovery: pending work

Status: documented for a future dataset update; recovery has not been run and no
study language values have been changed. The exploratory check only inspected
local data and tested one Europe PMC lookup.

As checked on 13 October 2026, publication language is missing for 8,783 of
41,657 eligible studies (21.1%) in `hee_analysis_master_v2_1.csv`. Of the missing
records, 6,339 have a DOI and 2,444 have no DOI. Recount these totals against the
latest master before starting.

## Recovery approach

1. Inspect original Scopus, MEDLINE and EPPI/library exports, if available, for
   publication-language fields that may not have reached the master. Match by
   record ID or DOI first.
2. Search PubMed/Europe PMC by DOI and use explicit publication-language metadata.
   For records without a DOI, require a unique bibliographic match supported by
   title, author, publication year and journal where available.
3. Check Crossref DOI metadata for an explicit language value when the first
   sources do not resolve the record.
4. Inspect publisher pages or freely accessible full texts for remaining cases.
   Retain Unknown when a match or the publication language is uncertain.

Use free endpoints, cache responses, respect rate limits and make the process
resumable. Start with a pilot of 100–200 records covering both DOI and no-DOI
cases, then process all missing records. Do not infer publication language from
an English title or abstract: a non-English publication may have English
metadata. OpenAlex's language field detects title/abstract metadata language,
so it must not be used as confirmation of full-text publication language.

## Evidence and dataset update

Produce a proposed-update CSV before applying changes. For every attempted
record, retain record ID, original language, proposed language(s), source,
source identifier/URL, matching method, retrieval date and resolution status.
Flag conflicting sources and ambiguous matches for review; preserve multilingual
publications rather than forcing them into a single language. Leave existing
nonmissing values unchanged unless a separately documented correction is made.

After verified updates, synchronise language fields across the current base,
WHO-region and publication-year-income master copies without changing other
fields. Rebuild `docs/data/languages.json` using `scripts/build_language_filter.py`
(extend language-code handling if newly recovered languages require it), and
update coverage notes and methods. Confirm that eligible IDs and study totals
are unchanged and report recovered, unresolved, conflicting and failed lookups.

## Source documentation

- PubMed publication-language fields: https://pubmed.ncbi.nlm.nih.gov/help/
- NCBI API limits: https://support.nlm.nih.gov/kbArticle/?pn=KA-05317
- Europe PMC API: https://europepmc.org/RestfulWebService
- Free Crossref access: https://www.crossref.org/documentation/retrieve-metadata/rest-api/access-and-authentication/
- OpenAlex language definition: https://help.openalex.org/data/works/attributes/#language
