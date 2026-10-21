"""Add explicit DALY outcome flags to web studies, matched by record_id.

Run after regenerating docs/data/studies.json. An absent DALY outcome means
no DALY is recorded in the outcome export; it is not evidence of non-use.
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    path = ROOT / "docs/data/studies.json"
    studies = json.loads(path.read_text(encoding="utf-8"))
    with (ROOT / "data/raw/hee_outcomes_long.csv").open(encoding="utf-8-sig", newline="") as source:
        daly_ids = {row["record_id"] for row in csv.DictReader(source) if row["family"] == "DALYs"}
    studies["uses_daly"] = [int(str(record_id) in daly_ids) for record_id in studies["record_id"]]
    path.write_text(json.dumps(studies, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"DALY outcome recorded: {sum(studies['uses_daly']):,} / {len(studies['id']):,} studies")


if __name__ == "__main__":
    main()
