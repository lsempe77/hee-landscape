"""WHO regions for every country in the HEE data, with UN M49 as the fallback.

Writes scripts/who_regions.csv (iso3 -> WHO region), then adds a WHO region
next to the archived UN M49 sub-region (`un_region`, kept unchanged):

  * docs/data/countries.json  -> `who_region` per country
  * docs/data/dict.json       -> `REGIONS` = WHO regions; the old UN list is
                                 kept as `REGIONS_UN`
  * docs/data/content.json    -> the "Colour by" region option reads `who_region`
  * data/raw (team export)    -> versioned copies hee_analysis_master_v2_who.csv
                                 and hee_geo_long_who.csv with `who_region` and
                                 `who_region_source`; the v2 files are not touched

Names, the source column and the fallback rule match the HFF evidence map's
data/raw/country_regions_v2_4.json, so the two maps use one classification.

WHO regions come from WHO's own list (scripts/who_gho_country_regions.csv,
from the GHO API), which includes Indonesia's move from the South-East Asia
Region to the Western Pacific Region, approved by the Seventy-eighth World
Health Assembly (May 2025).

Places WHO gives no region (Taiwan, Hong Kong, Kosovo) take the WHO region of
the other countries in their UN M49 sub-region (FALLBACK below), and
`who_region_source` says so. Membership is a separate question: the United
States and Argentina left the WHO in 2026 but WHO's list keeps them in the
Region of the Americas, and so do we.

Usage:
    python scripts/build_who_regions.py [--raw data/raw] [--skip-raw]
"""
import argparse
import csv
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_CSV = os.path.join(ROOT, "scripts", "who_regions.csv")
DATA = os.path.join(ROOT, "docs", "data")

# WHO's official region names (as in the HFF map), in WHO's usual order.
WHO_REGIONS = {
    "AFR": "African Region",
    "AMR": "Region of the Americas",
    "SEAR": "South-East Asia Region",
    "EUR": "European Region",
    "EMR": "Eastern Mediterranean Region",
    "WPR": "Western Pacific Region",
}

# WHO's own country -> region list, from the Global Health Observatory API
# (https://ghoapi.azureedge.net/api/DIMENSION/COUNTRY/DimensionValues,
# downloaded 2026-10-13; Code and ParentCode kept). It already places Indonesia
# in WPR and also gives regions for territories such as Puerto Rico or Guam.
GHO_CSV = os.path.join(ROOT, "scripts", "who_gho_country_regions.csv")

# Places WHO gives no region (Hong Kong and Kosovo have a blank region; Taiwan
# is not listed): UN M49 sub-region -> the WHO region covering the other countries of
# that sub-region. Taiwan is not listed in M49 either; it is treated as
# Eastern Asia, as in the archived `un_region` source.
FALLBACK = {
    "HKG": ("Eastern Asia", "WPR"),
    "TWN": ("Eastern Asia", "WPR"),
    "XKX": ("Southern Europe", "EUR"),
}


def crosswalk():
    out = {}
    with open(GHO_CSV, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["ParentCode"]:
                assert r["ParentCode"] in WHO_REGIONS, r
                out[r["Code"]] = (r["ParentCode"], "WHO", "")
    for iso, (m49, code) in FALLBACK.items():
        assert iso not in out, iso
        out[iso] = (code, f"no WHO region; WHO region of its UN M49 sub-region ({m49})", m49)
    return out


def write_json(path, obj):
    """Rewrite a web data file in its existing compact style and line ending."""
    with open(path, "rb") as f:
        tail = f.read()[-2:]
    end = "\r\n" if tail == b"\r\n" else "\n" if tail.endswith(b"\n") else ""
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + end)


def rewrite_csv(src, dst, iso_col, cw):
    """Copy src to dst with who_region/who_region_source inserted after un_region."""
    with open(src, encoding="utf-8", newline="") as fi, open(dst, "w", encoding="utf-8", newline="") as fo:
        rd = csv.DictReader(fi)
        cols = list(rd.fieldnames)
        at = cols.index("un_region") + 1
        cols[at:at] = ["who_region", "who_region_source"]
        wr = csv.DictWriter(fo, fieldnames=cols)
        wr.writeheader()
        n = unmapped = 0
        for r in rd:
            iso = r[iso_col]
            if iso and iso != "NA":
                if iso not in cw:
                    raise SystemExit(f"{src}: no WHO region for {iso}")
                code, basis, _ = cw[iso]
                r["who_region"], r["who_region_source"] = WHO_REGIONS[code], basis
            else:
                r["who_region"] = r["who_region_source"] = "NA"
                unmapped += 1
            wr.writerow(r)
            n += 1
    print(f"wrote {dst}: {n:,} rows ({unmapped:,} with no country)")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--raw", default=os.path.join(ROOT, "data", "raw"), help="folder with the team export")
    ap.add_argument("--skip-raw", action="store_true", help="do not write the versioned team-export copies")
    args = ap.parse_args()
    csv.field_size_limit(10 ** 9)
    cw = crosswalk()

    with open(OUT_CSV, "w", encoding="utf-8", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["iso3", "who_region_code", "who_region", "who_region_source", "m49_subregion_used"])
        for iso in sorted(cw):
            code, basis, m49 = cw[iso]
            wr.writerow([iso, code, WHO_REGIONS[code], basis, m49])
    print("wrote", OUT_CSV, f"({len(cw)} places)")

    # ---- Web data ----
    path = os.path.join(DATA, "countries.json")
    with open(path, encoding="utf-8") as f:
        countries = json.load(f)
    missing = [c["iso3"] for c in countries if c["iso3"] not in cw]
    if missing:
        raise SystemExit("No WHO region for: " + ", ".join(missing))
    new = []
    for c in countries:
        row = {}
        for k, val in c.items():
            if k != "who_region":
                row[k] = val
            if k == "un_region":
                row["who_region"] = WHO_REGIONS[cw[c["iso3"]][0]]
        new.append(row)
    write_json(path, new)
    print(f"updated {path}: who_region for {len(new)} countries "
          f"({sum(cw[c['iso3']][1] != 'WHO' for c in new)} by UN M49 fallback)")

    path = os.path.join(DATA, "dict.json")
    with open(path, encoding="utf-8") as f:
        dic = json.load(f)
    if "REGIONS_UN" not in dic:
        dic["REGIONS_UN"] = dic["REGIONS"]
    dic["REGIONS"] = list(WHO_REGIONS.values())
    write_json(path, dic)
    print(f"updated {path}: REGIONS = WHO, REGIONS_UN archived")

    path = os.path.join(DATA, "content.json")
    with open(path, encoding="utf-8") as f:
        content = json.load(f)
    for tv in content["registries"]["trend_vars"]:
        if tv["column"] in ("un_region", "who_region"):
            tv["label"], tv["column"] = "WHO region", "who_region"
    write_json(path, content)
    print(f"updated {path}: trend 'Colour by' region uses who_region")

    # ---- Team export: versioned copies ----
    if not args.skip_raw:
        rewrite_csv(os.path.join(args.raw, "hee_analysis_master_v2.csv"),
                    os.path.join(args.raw, "hee_analysis_master_v2_who.csv"), "country_iso3", cw)
        rewrite_csv(os.path.join(args.raw, "hee_geo_long.csv"),
                    os.path.join(args.raw, "hee_geo_long_who.csv"), "iso3", cw)


if __name__ == "__main__":
    main()
