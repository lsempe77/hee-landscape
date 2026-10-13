"""Funder data for the Explorer's funder filter.

Reads the funders recorded for each eligible study in the team export and
normalises the names with the same rules as the Top donors figure
(build_wellcome_analysis.funders_of), so the filter and the figure agree.
Writes docs/data/funders.json:

  names  funder names offered in the filter, most studies first
  n      studies per name
  s, f   one entry per study-funder pair: study index (as in studies.json)
         and index into names
  any    indices of the studies reporting at least one funder (for the
         "Any funder reported" option, which also counts funders not listed)

Funders reported by fewer than MIN_STUDIES studies are left out of the list
(they still count towards `any`). Funding is as reported in the publication
metadata (CrossRef), which covers about a quarter of studies.

Usage:
    python scripts/build_funder_filter.py [--raw data/raw]
"""
import argparse
import csv
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_wellcome_analysis import funders_of  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "docs", "data")
MIN_STUDIES = 5


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--raw", default=os.path.join(ROOT, "data", "raw"))
    args = ap.parse_args()
    csv.field_size_limit(10 ** 9)

    with open(os.path.join(DATA, "studies.json"), encoding="utf-8") as f:
        index = {str(rid): i for i, rid in enumerate(json.load(f)["record_id"])}
    of_study = {}
    with open(os.path.join(args.raw, "hee_analysis_master_v2.csv"), encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["is_eligible"] == "TRUE" and r["funders"] not in ("", "NA"):
                names = funders_of(r["funders"])
                if names:
                    of_study[r["record_id"]] = names
    missing = [rid for rid in of_study if rid not in index]
    if missing:
        raise SystemExit(f"{len(missing)} funded studies are not in docs/data/studies.json, e.g. {missing[:3]}; "
                         "rebuild the web data first")

    counts = Counter(name for names in of_study.values() for name in names)
    names = [name for name, k in sorted(counts.items(), key=lambda x: (-x[1], x[0].casefold())) if k >= MIN_STUDIES]
    pos = {name: i for i, name in enumerate(names)}
    pairs = sorted((index[rid], pos[name]) for rid, ns in of_study.items() for name in ns if name in pos)
    out = {"names": names, "n": [counts[n] for n in names],
           "s": [p[0] for p in pairs], "f": [p[1] for p in pairs],
           "any": sorted(index[rid] for rid in of_study)}
    path = os.path.join(DATA, "funders.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"wrote {path}: {len(of_study):,} studies report a funder; {len(names):,} funders with "
          f">= {MIN_STUDIES} studies, {len(pairs):,} study-funder pairs; top: "
          + ", ".join(f"{n} ({counts[n]})" for n in names[:5]))


if __name__ == "__main__":
    main()
