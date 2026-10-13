"""Give reviews without their own evaluation a separate evaluation-type group on the site.

Run: python scripts/apply_review_eval_type.py
Reads data/raw/hee_analysis_master_v2_1.csv. A study is "review only" when
review_type is a review and review_has_original_evaluation is not "Yes"; its
econ_eval_type on the site becomes REVIEW_LEVEL, so it no longer counts as a
cost-benefit, cost-consequence, cost-effectiveness or cost-utility analysis.
Reviews that also report the authors' own evaluation keep their type.

It also writes review_label (REVIEW_LABELS) so the Explorer can filter
systematic and other reviews, whether or not they report their own evaluation.

Every study's type is first restored from the master, so reruns are safe.
Writes docs/data/studies.json (econ_eval_type and review_label codes) and
docs/data/dict.json (the extra levels and meta.review_only).
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data" / "raw" / "hee_analysis_master_v2_1.csv"
DATA = ROOT / "docs" / "data"
REVIEW_LEVEL = "Review (no evaluation type)"
NOT_REVIEW = "Not identified as a review"
# Master review_type -> site review_label.
REVIEW_LABELS = {NOT_REVIEW: "Not a review", "Systematic review": "Systematic review",
                 "Review (non-systematic)": "Other review"}


def review_only(row):
    return row["review_type"] != NOT_REVIEW and row["review_has_original_evaluation"] != "Yes"


def main():
    csv.field_size_limit(10 ** 9)
    with MASTER.open(encoding="utf-8") as f:
        master = {r["record_id"]: r for r in csv.DictReader(f) if r["is_eligible"] in ("TRUE", "True", "1")}
    studies = json.loads((DATA / "studies.json").read_text(encoding="utf-8"))
    dictionary = json.loads((DATA / "dict.json").read_text(encoding="utf-8"))
    levels = dictionary["levels"]["econ_eval_type"]
    if REVIEW_LEVEL not in levels:
        levels.append(REVIEW_LEVEL)
    missing = [rid for rid in studies["record_id"] if rid not in master]
    if missing or len(master) != len(studies["record_id"]):
        raise SystemExit(f"Site studies and eligible master records differ ({len(missing)} site IDs not in the master).")
    review_levels = dictionary["levels"]["review_label"] = list(REVIEW_LABELS.values())
    codes, review_codes, n_review = [], [], 0
    for rid in studies["record_id"]:
        row = master[rid]
        if row["review_type"] not in REVIEW_LABELS:
            raise SystemExit(f"Unknown review type {row['review_type']!r} for {rid}")
        review_codes.append(review_levels.index(REVIEW_LABELS[row["review_type"]]))
        if review_only(row):
            codes.append(levels.index(REVIEW_LEVEL))
            n_review += 1
        else:
            if row["econ_eval_type"] not in levels:
                raise SystemExit(f"Unknown evaluation type {row['econ_eval_type']!r} for {rid}")
            codes.append(levels.index(row["econ_eval_type"]))
    studies["econ_eval_type"] = codes
    studies["review_label"] = review_codes
    dictionary["meta"]["review_only"] = n_review
    (DATA / "studies.json").write_text(json.dumps(studies, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (DATA / "dict.json").write_text(json.dumps(dictionary, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{n_review:,} review-only studies moved to '{REVIEW_LEVEL}'; "
          f"{len(codes) - n_review:,} keep their evaluation type.")


if __name__ == "__main__":
    main()
