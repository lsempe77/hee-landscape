"""Match studies_without_doi.csv to three ExportedRis*.txt files beside this script.

Run: python data/raw/url_lookup/update_study_links_from_ris.py
"""

import csv
import re
from pathlib import Path


folder = Path(__file__).resolve().parent


def read_ris(path):
    records = []
    record = {}

    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            match = re.match(r"^([A-Z][A-Z0-9])  - ?(.*)", line.rstrip())

            if match:
                tag, value = match.groups()

                if tag == "TY":
                    record = {}

                if tag == "ER":
                    records.append(record)
                    record = {}
                else:
                    record.setdefault(tag, []).append(value.strip())

    return records


def main():
    # Read all three RIS exports.
    ris_files = sorted(folder.glob("ExportedRis*.txt"))

    if len(ris_files) != 3:
        raise ValueError(f"Expected 3 RIS files in {folder}, found {len(ris_files)}")

    records = {}

    for file in ris_files:
        for record in read_ris(file):
            if record.get("U1"):
                records[record["U1"][0]] = record

    # Read original CSV.
    with open(folder / "studies_without_doi.csv",
              encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        original_columns = reader.fieldnames
        if not original_columns or "record_id" not in original_columns:
            raise ValueError("Input CSV must have a record_id column")
        studies = list(reader)

    # Update study URLs and DOIs.
    for study in studies:
        study_id = study["record_id"]
        record = records.get(study_id)

        study["ris_doi"] = ""
        study["url_match_status"] = "not_in_ris_export"
        study["url_source_type"] = ""

        if not record:
            continue

        doi = record.get("DO", [""])[0].strip()
        doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi, flags=re.I)
        if doi.lower() in {"na", "nan", "null", "none"}:
            doi = ""
        study["ris_doi"] = doi

        urls = [
            u.strip() for u in record.get("UR", [])
            if u.strip().startswith(("https://", "http://"))
        ]

        if urls:
            study["url"] = urls[0]
            study["url_source"] = "EPPI RIS: UR"
            study["url_match_status"] = "matched_ris_url"
            study["url_source_type"] = "RIS URL"
        elif doi.startswith("10."):
            study["url"] = "https://doi.org/" + doi
            study["url_source"] = "EPPI RIS: DO (DOI resolver fallback)"
            study["url_match_status"] = "matched_doi_fallback"
            study["url_source_type"] = "DOI resolver"
        else:
            study["url_match_status"] = "matched_no_link"

    # Keep original column order and add any missing output columns once.
    columns = list(original_columns)
    for column in ("url", "url_source", "ris_doi", "url_match_status", "url_source_type"):
        if column not in columns:
            columns.append(column)

    output = folder / "EPPI_updated_studies.csv"
    with open(output, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(studies)

    # Save records without links separately.
    missing = [
        s for s in studies
        if not s.get("url") and not s.get("ris_doi")
    ]

    with open(folder / "EPPI_169_missing_links.csv",
              "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(missing)

    print("Total studies:", len(studies))
    print("Studies with links:", len(studies) - len(missing))
    print("Studies without links:", len(missing))
    print("Updated CSV saved:", output)


if __name__ == "__main__":
    main()
