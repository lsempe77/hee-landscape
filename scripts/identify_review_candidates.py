"""Identify review candidates from titles without changing eligibility or source data.

Run: python scripts/identify_review_candidates.py
Outputs a searchable Markdown list and structured JSON in data/raw/review_screening.
Title flags are screening signals, not verified review status or primary-study status.
"""
import csv
from collections import Counter
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "raw" / "hee_analysis_master.csv"
OUT = ROOT / "data" / "raw" / "review_screening"
SYSTEMATIC = re.compile(r"\bsystematic(?:[ -]+(?:literature|evidence))?[ -]+reviews?\b", re.I)
META = re.compile(r"\bmeta[ -]?analys\w*", re.I)
OTHER = re.compile(r"\b(?:scoping|umbrella|narrative|rapid|integrative|literature|evidence|systematic mapping)[ -]+reviews?\b|\breview of (?:the )?literature\b|\boverview of reviews\b", re.I)
HISTORICAL = re.compile(r"systematic review|meta-analys|meta analys|literature review|scoping review|umbrella review", re.I)


def main():
    with SOURCE.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        needed = {"record_id", "is_eligible", "title", "year", "doi", "url", "econ_eval_type", "design_basis", "publication_type"}
        if not needed.issubset(reader.fieldnames or []):
            raise SystemExit("Stopped: required master columns are missing.")
        rows = [r for r in reader if r["is_eligible"] == "TRUE"]
    expected = json.loads((ROOT / "docs" / "data" / "dict.json").read_text(encoding="utf-8"))["meta"]["n_studies"]
    if not rows or len(rows) != expected or len({r["record_id"] for r in rows}) != len(rows):
        raise SystemExit("Stopped: eligible master records do not match the web dataset or IDs are duplicated.")
    groups = {"explicit_systematic_review": [], "meta_analysis_without_explicit_sr": [], "other_review_title": []}
    for r in rows:
        sr, meta, other = SYSTEMATIC.search(r["title"]), META.search(r["title"]), OTHER.search(r["title"])
        group = "explicit_systematic_review" if sr else "meta_analysis_without_explicit_sr" if meta else "other_review_title" if other else None
        if not group:
            continue
        hybrid = bool(re.search(r"\b(?:trial|model(?:ling|ing)?|economic evaluation|cost[ -]effectiveness analysis)\b", r["title"], re.I))
        record = {k: r[k] for k in needed if k != "is_eligible"}
        record.update(title_signal=group, matched_text=(sr or meta or other).group(),
                      design_requires_review=r["design_basis"] != "Literature/registry synthesis",
                      possible_hybrid_title=hybrid, verification_status="Not yet checked against abstract/full text")
        groups[group].append(record)
    for records in groups.values():
        records.sort(key=lambda r: (int(r["year"]), r["title"].casefold(), r["record_id"]))
    summary = {"eligible_records": len(rows), "exact_phrase_systematic_review": sum("systematic review" in r["title"].lower() for r in rows),
               "historical_strict_review_proxy": sum(bool(HISTORICAL.search(r["title"])) for r in rows),
               "candidate_counts": {k: len(v) for k, v in groups.items()},
               "explicit_sr_evaluation_types": dict(Counter(r["econ_eval_type"] for r in groups["explicit_systematic_review"])),
               "explicit_sr_design_requires_review": sum(r["design_requires_review"] for r in groups["explicit_systematic_review"])}
    lines = ["# Review candidates in the eligible HEE dataset", "",
             f"Source: `{SOURCE.name}`; {len(rows):,} eligible records. No source records or inclusion decisions were changed.", "",
             f"**Likely systematic reviews with an explicit title label: {len(groups['explicit_systematic_review']):,}.** "
             "These include systematic literature/evidence reviews and hyphenated wording. This is a title-screen count, not a verified total.", "",
             "The exact phrase `systematic review` identifies 1,411 records. The historical strict review proxy identifies 1,706, including meta-analyses and other review types.", "",
             "Confirm abstract/full-text review methods before treating a record as a systematic review or excluding it as secondary evidence. "
             "A paper can combine a review and a new economic evaluation. Absence from this list does not establish primary-study status.", "",
             "`Literature/registry synthesis` is broader than reviews. `publication_type` is publication format. "
             "The flags below are not validated classifications; model/trial wording is only a prompt to check for a hybrid paper.", ""]
    labels = {"explicit_systematic_review": "Explicit systematic-review title matches",
              "meta_analysis_without_explicit_sr": "Meta-analysis title matches without an explicit systematic-review label",
              "other_review_title": "Other review-title candidates (includes non-systematic review types)"}
    for group, records in groups.items():
        lines += [f"## {labels[group]} ({len(records):,})", ""]
        for r in records:
            url = r["url"] if r["url"].startswith(("https://", "http://")) else "https://doi.org/" + r["doi"] if r["doi"] not in ("", "NA") else ""
            title = r["title"].replace("[", "\\[").replace("]", "\\]")
            title = f"[{title}](<{url}>)" if url else title
            lines += [f"- **{r['record_id']} · {r['year']}** — {title}",
                      f"  - Evaluation: {r['econ_eval_type']}; design: {r['design_basis']}; publication format: {r['publication_type']}.",
                      f"  - Title match: `{r['matched_text']}`. " +
                      ("Design code needs checking. " if r["design_requires_review"] else "") +
                      ("Check for a combined review and primary evaluation. " if r["possible_hybrid_title"] else "") + "Abstract/full text not yet verified.", ""]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "review_candidates.md").write_text("\n".join(lines), encoding="utf-8")
    (OUT / "review_candidates.json").write_text(json.dumps({"summary": summary, "groups": groups}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(OUT / "review_candidates.md")


if __name__ == "__main__":
    main()
