"""Apply EPPI RIS links to the analysis master and matching web studies.

Run after data/raw/url_lookup/update_study_links_from_ris.py. Existing DOIs
are preserved; missing DOIs and HTTP(S) URLs are recovered by record_id.
Web v2/v3/current row mappings are validated against the master. Legacy v1
uses unique title/year matches from its own study-text shards.
"""

import csv
import html
import json
import re
import shutil
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
LOOKUP = RAW / "url_lookup"
SITES = [ROOT / "docs", *(ROOT / "docs" / v for v in ("v1", "v2", "v3"))]
MISSING = {"", "na", "nan", "null", "none"}


def text(value):
    value = str(value or "").strip()
    return "" if value.lower() in MISSING else value


def doi(value):
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", text(value), flags=re.I)
    return value if re.fullmatch(r"10\.\d{4,9}/\S+", value, flags=re.I) else ""


def url(value):
    value = text(value)
    try:
        parsed = urlsplit(value)
        return value if parsed.scheme.lower() in {"http", "https"} and parsed.hostname else ""
    except ValueError:
        return ""


def title_key(value):
    return " ".join(html.unescape(value or "").split()).casefold()


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, data):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    temporary.replace(path)


def main():
    csv.field_size_limit(10**9)
    master_path = RAW / "hee_analysis_master.csv"
    columns, master = read_csv(master_path)
    _, updates = read_csv(LOOKUP / "EPPI_updated_studies.csv")
    by_id = {r["record_id"]: r for r in master}
    assert len(by_id) == len(master), "Duplicate master record IDs"
    update_ids = {r["record_id"] for r in updates}
    assert len(update_ids) == len(updates), "Duplicate update record IDs"
    assert update_ids <= by_id.keys(), "Update record IDs missing from master"

    added_dois = added_urls = 0
    for update in updates:
        row = by_id[update["record_id"]]
        assert title_key(row["title"]) == title_key(update["title"]), "Title mismatch for record ID"
        assert row["year"] == update["year"], "Year mismatch for record ID"
        recovered_doi = doi(update["ris_doi"])
        if recovered_doi and not text(row["doi"]):
            row["doi"] = recovered_doi
            row["doi_source"] = "EPPI RIS: DO"
            added_dois += 1
        recovered_url = url(update.get("url"))
        if recovered_url:
            added_urls += not bool(url(row.get("url")))
            row["url"] = recovered_url
            row["url_source"] = update.get("url_source", "")
        row["url_match_status"] = update["url_match_status"]

    eligible = [r for r in master if r["is_eligible"] == "TRUE"]
    titles = defaultdict(list)
    for row in master:
        if title_key(row["title"]):
            titles[(title_key(row["title"]), row["year"])].append(row)

    # Validate every mapping before writing any dataset.
    prepared = []
    for site in SITES:
        studies = read_json(site / "data/studies.json")
        dictionary = read_json(site / "data/dict.json")
        n = len(studies["id"])
        shards = [(f, read_json(f)) for f in sorted((site / "data/drill").glob("*.json"))]
        if site.name != "v1":
            assert n == len(eligible), f"Unexpected study count: {site}"
            for i, row in enumerate(eligible):
                assert str(studies["year"][i]) == row["year"], f"Year order mismatch: {site}, {i}"
                assert dictionary["levels"]["econ_eval_type"][studies["econ_eval_type"][i]] == row["econ_eval_type"], f"Evaluation order mismatch: {site}, {i}"
            mapping = dict(enumerate(eligible))
            for _, shard in shards:
                for i, title in zip(shard["s"], shard["t"]):
                    if title:
                        assert title_key(title) == title_key(mapping[i]["title"]), f"Title order mismatch: {site}, {i}"
        else:
            mapping = {}
            for _, shard in shards:
                for i, title in zip(shard["s"], shard["t"]):
                    candidates = titles.get((title_key(title), str(studies["year"][i])), [])
                    if len(candidates) == 1:
                        mapping[i] = candidates[0]

        for key in ("record_id", "doi", "url", "url_source", "doi_source"):
            studies[key] = [""] * n
        for i, row in mapping.items():
            studies["record_id"][i] = row["record_id"]
            studies["doi"][i] = doi(row["doi"])
            studies["url"][i] = url(row.get("url"))
            studies["url_source"][i] = text(row.get("url_source"))
            studies["doi_source"][i] = text(row.get("doi_source"))

        counts = {
            "n_studies": n,
            "n_mapped": len(mapping),
            "n_doi": sum(bool(v) for v in studies["doi"]),
            "n_url": sum(bool(v) for v in studies["url"]),
            "n_doi_or_url": sum(bool(d or u) for d, u in zip(studies["doi"], studies["url"])),
            "n_ris_updates_matched": sum(r["record_id"] in update_ids for r in mapping.values()),
        }
        dictionary["meta"]["publication_access"] = counts
        prepared.append((site, studies, dictionary, counts))

    # Keep the pre-enrichment master once; reruns are safe.
    backup = LOOKUP / "hee_analysis_master_before_ris_links.csv"
    if not backup.exists():
        shutil.copy2(master_path, backup)
    for key in ("url", "url_source", "doi_source", "url_match_status"):
        if key not in columns:
            columns.append(key)
    temporary = master_path.with_suffix(".csv.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(master)
    temporary.replace(master_path)

    # Refresh coverage for the enriched fields; retain other columns' definitions.
    coverage_path = RAW / "column_coverage.csv"
    coverage_columns, coverage = read_csv(coverage_path)
    coverage_by_name = {r["column"]: r for r in coverage}
    for key in ("doi", "url", "url_source", "doi_source", "url_match_status"):
        values = [text(r.get(key)) for r in master]
        included_values = [text(r.get(key)) for r in eligible]
        row = coverage_by_name.get(key)
        if row is None:
            row = {"column": key, "type": "character"}
            coverage.append(row)
        row.update(
            pct_present=round(100 * sum(bool(v) for v in values) / len(values), 1),
            pct_present_eligible=round(100 * sum(bool(v) for v in included_values) / len(included_values), 1),
            n_distinct=len(set(filter(None, values))),
        )
    with coverage_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=coverage_columns)
        writer.writeheader()
        writer.writerows(coverage)

    for site, studies, dictionary, counts in prepared:
        write_json(site / "data/studies.json", studies)
        write_json(site / "data/dict.json", dictionary)
        print(site.relative_to(ROOT), json.dumps(counts))
    print(f"Master: {added_dois:,} DOIs and {added_urls:,} URLs added")


if __name__ == "__main__":
    main()
