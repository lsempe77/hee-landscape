"""Write the site's GBD 2023 disease groups: docs/data/disease_gbd.json.

Replaces the 14 MeSH-based groups of docs/data/disease.json (kept) with the
team share v2.1 coding (data/raw/hee_share_v2_1/gbd_disease_long.csv): 22 GBD
level-2 causes plus two groups for studies naming an infection or an injury
without its cause. Same layout as disease.json (study index `s`, group index
`g`, one pair per study and group), plus the group names `grps` and each
group's GBD level 1 `l1`, so the Explore filter, charts and CSV download
(docs/app.js) and the regional glance cards read the labels from this file.

Groups run by GBD level 1 (communicable, maternal, neonatal & nutritional;
non-communicable; injuries), then by number of studies; labels are the plain
names used on the figures (build_gbd_figures.py).

Usage:
    python scripts/build_disease_gbd_data.py [--raw data/raw]
"""
import argparse
import csv
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_gbd_figures import L1, LABEL, SHARE  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "docs", "data")
L1_NAMES = {"cmnn": "Communicable, maternal, neonatal & nutritional", "ncd": "Non-communicable", "inj": "Injuries"}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--raw", default=os.path.join(ROOT, "data", "raw"))
    args = ap.parse_args()
    with open(os.path.join(DATA, "studies.json"), encoding="utf-8") as f:
        index = {str(r): i for i, r in enumerate(json.load(f)["record_id"])}
    with open(os.path.join(args.raw, SHARE, "gbd_disease_long.csv"), encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    with open(os.path.join(args.raw, "hee_analysis_master_v2.csv"), encoding="utf-8", newline="") as f:
        excluded = {r["record_id"] for r in csv.DictReader(f) if r["is_eligible"] != "TRUE"}
    missing = {r["record_id"] for r in rows} - set(index) - excluded
    if missing:
        raise SystemExit(f"{len(missing)} coded records are not in studies.json, e.g. {sorted(missing)[:3]}")
    rows = [r for r in rows if r["record_id"] in index]
    l1 = {r["grp"]: L1[r["l1"]] for r in rows}
    n = Counter(r["grp"] for r in rows)
    order = sorted(n, key=lambda g: (list(L1_NAMES).index(l1[g]), -n[g]))
    code = {g: i for i, g in enumerate(order)}
    pairs = sorted({(index[r["record_id"]], code[r["grp"]]) for r in rows})
    out = {"grps": [LABEL[g] for g in order], "l1": [L1_NAMES[l1[g]] for g in order],
           "gbd": order, "s": [s for s, _ in pairs], "g": [g for _, g in pairs]}
    path = os.path.join(DATA, "disease_gbd.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"wrote {path}: {len(pairs):,} pairs, {len(set(out['s'])):,} studies, {len(order)} groups")


if __name__ == "__main__":
    main()
