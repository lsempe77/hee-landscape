"""Top disease themes by World Bank region, for the at-a-glance infographic.

Reads the internal team export in data/raw (not in the repository) plus
scripts/topic_disease_map.csv, which maps the topic model's research themes
to plain disease names (themes about a procedure or setting rather than a
disease are left out). Writes aggregate shares only, to
scripts/region_disease_themes.json, which build_glance_regions.py reads.

A study counts for a region if it names at least one of the region's countries
(the countries in the map's country data). The share is the region's included
studies whose research theme maps to the disease; each study has at most one
theme, so a disease's share is a plain proportion of the region's studies.

Usage:
    python scripts/build_region_disease_themes.py [--raw data/raw]
"""
import argparse
import csv
import json
import os
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "scripts", "region_disease_themes.json")
TOP_N = 3


def read_csv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--raw", default=os.path.join(ROOT, "data", "raw"), help="folder with the team export")
    args = ap.parse_args()
    csv.field_size_limit(10 ** 9)

    with open(os.path.join(ROOT, "docs", "data", "countries.json"), encoding="utf-8") as f:
        map_isos = {c["iso3"] for c in json.load(f)}
    region_of = {r["iso3"]: r["wb_region_code"] for r in read_csv(os.path.join(ROOT, "scripts", "wb_regions.csv"))}
    themes = {r["cluster"]: r for r in read_csv(os.path.join(ROOT, "scripts", "topic_disease_map.csv"))}

    master = read_csv(os.path.join(args.raw, "hee_analysis_master_v2.csv"))
    included = {r["record_id"] for r in master if r["is_eligible"] == "TRUE"}
    cluster_of = {r["record_id"]: r["cluster"] for r in read_csv(os.path.join(args.raw, "topic_map.csv"))}

    regions_of_study = defaultdict(set)
    for r in read_csv(os.path.join(args.raw, "hee_geo_long.csv")):
        if r["record_id"] in included and r["iso3"] in map_isos:
            regions_of_study[r["record_id"]].add(region_of[r["iso3"]])

    n = Counter()
    by_disease = defaultdict(Counter)
    for rid, regs in regions_of_study.items():
        theme = themes.get(cluster_of.get(rid, ""))
        for reg in regs:
            n[reg] += 1
            if theme:
                by_disease[reg][theme["disease"]] += 1

    category = {t["disease"]: t["category"] for t in themes.values()}
    out = {"source": "data/raw team export (v2, 2026-10-11): topic_map.csv + hee_geo_long.csv",
           "n_included": len(included), "regions": {}}
    for reg in sorted(n):
        top = by_disease[reg].most_common(TOP_N)
        out["regions"][reg] = {
            "n": n[reg],
            "top": [{"disease": d, "category": category[d], "n": k, "share": k / n[reg]} for d, k in top],
        }
        print(f"{reg} n={n[reg]:,}: " + "; ".join(f"{d} {100 * k / n[reg]:.1f}%" for d, k in top))
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
