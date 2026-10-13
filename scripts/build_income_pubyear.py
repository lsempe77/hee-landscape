"""World Bank income group at each study's publication year.

Rule: a study published in year Y gets its country's World Bank income group in
force on 1 January of Y, i.e. fiscal year FY(Y) (each classification runs from
1 July of Y-1 to 30 June of Y). The current group (`income_group`, FY27,
published July 2026) is kept unchanged: country views use it, because a
country sits in one group on a map.

Source: World Bank historical income classifications, OGHIST.xlsx, sheet
"Country Analytical History" (the "as published on 1 July" groups). With
--oghist, the sheet is extracted to scripts/wb_income_history.csv (FY10-FY27,
tracked in git); without it, that CSV is read.

Writes:
  * scripts/income_pubyear.csv      -> iso3, year, income group in force
  * docs/data/countries.json        -> `income_y`: group per year, aligned to
                                       dict.json meta.years; null = not classified
  * data/raw (team export)          -> versioned copies hee_analysis_master_v2_1.csv
                                       and hee_geo_long_v2_1.csv: the WHO-region
                                       copies (*_who.csv, from build_who_regions.py)
                                       plus `income_group_pubyear` and
                                       `income_broad_pubyear` after `income_broad`

Taiwan keeps the recorded High-income decision (Q3, 2026-10-05) in every year.

Usage:
    python scripts/build_income_pubyear.py [--oghist data/raw/OGHIST_2026_10_08.xlsx] [--skip-raw]
"""
import argparse
import csv
import json
import os
import re
import zipfile
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HIST_CSV = os.path.join(ROOT, "scripts", "wb_income_history.csv")
OUT_CSV = os.path.join(ROOT, "scripts", "income_pubyear.csv")
DATA = os.path.join(ROOT, "docs", "data")
SHEET = "Country Analytical History"
FIRST_FY, LAST_FY = 10, 27
CODES = {"L": "Low income", "LM": "Lower middle income", "UM": "Upper middle income", "H": "High income"}
OVERRIDE = {"TWN": "High income"}
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}


def xlsx_sheet(path, name):
    """One sheet of an .xlsx as a list of rows (standard library only)."""
    z = zipfile.ZipFile(path)
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS):
            shared.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["m"])))
    rels = {r.get("Id"): r.get("Target") for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
    for s in ET.fromstring(z.read("xl/workbook.xml")).find("m:sheets", NS):
        if s.get("name") != name:
            continue
        target = rels[s.get("{%s}id" % NS["r"])].lstrip("/")
        target = target if target.startswith("xl/") else "xl/" + target
        rows = []
        for row in ET.fromstring(z.read(target)).iter("{%s}row" % NS["m"]):
            vals = {}
            for c in row.findall("m:c", NS):
                v = c.find("m:v", NS)
                if c.get("t") == "s" and v is not None:
                    val = shared[int(v.text)]
                elif c.get("t") == "inlineStr":
                    val = "".join(x.text or "" for x in c.iter("{%s}t" % NS["m"]))
                else:
                    val = v.text if v is not None else ""
                col = 0
                for ch in re.match(r"[A-Z]+", c.get("r")).group(0):
                    col = col * 26 + ord(ch) - 64
                vals[col - 1] = val
            rows.append([vals.get(i, "") for i in range(max(vals) + 1)] if vals else [])
        return rows
    raise SystemExit(f"{path}: no sheet named {name!r}")


def extract(oghist):
    rows = xlsx_sheet(oghist, SHEET)
    header = next(r for r in rows if len(r) > 1 and r[1] == "Bank's fiscal year:")
    fys = [f"FY{n:02d}" for n in range(FIRST_FY, LAST_FY + 1)]
    missing = [f for f in fys if f not in header]
    if missing:
        raise SystemExit(f"{oghist}: fiscal years not found: {missing}")
    idx = [header.index(f) for f in fys]
    with open(HIST_CSV, "w", encoding="utf-8", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["iso3", "country"] + fys)
        n = 0
        for r in rows:
            if r and re.fullmatch(r"[A-Z]{3}", r[0] or ""):
                wr.writerow([r[0], r[1]] + [r[i] if i < len(r) else "" for i in idx])
                n += 1
    print(f"wrote {HIST_CSV}: {n} economies, {fys[0]}-{fys[-1]} (from {os.path.basename(oghist)})")


def load_history():
    with open(HIST_CSV, encoding="utf-8") as f:
        return {r["iso3"]: r for r in csv.DictReader(f)}


def group_at(hist, iso, year):
    """Income group in force on 1 January of `year`, or None if not classified."""
    if iso in OVERRIDE:
        return OVERRIDE[iso]
    if iso not in hist:
        return None
    return CODES.get(hist[iso].get(f"FY{year % 100:02d}", ""))


def broad(group):
    if group is None:
        return "NA"
    return "High income" if group == "High income" else "Low & middle income"


def write_json(path, obj):
    """Rewrite a web data file in its existing compact style and line ending."""
    with open(path, "rb") as f:
        tail = f.read()[-2:]
    end = "\r\n" if tail == b"\r\n" else "\n" if tail.endswith(b"\n") else ""
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + end)


def rewrite_csv(src, dst, iso_col, hist):
    """Copy src to dst with the publication-year income columns after income_broad."""
    changed = unclassified = n = 0
    with open(src, encoding="utf-8", newline="") as fi, open(dst, "w", encoding="utf-8", newline="") as fo:
        rd = csv.DictReader(fi)
        cols = list(rd.fieldnames)
        at = cols.index("income_broad") + 1
        cols[at:at] = ["income_group_pubyear", "income_broad_pubyear"]
        wr = csv.DictWriter(fo, fieldnames=cols)
        wr.writeheader()
        for r in rd:
            iso = r[iso_col]
            if iso and iso != "NA" and r["year"] not in ("", "NA"):
                g = group_at(hist, iso, int(r["year"]))
                r["income_group_pubyear"], r["income_broad_pubyear"] = g or "NA", broad(g)
                if g is None:
                    unclassified += 1
                elif r["income_group"] in CODES.values() and g != r["income_group"]:
                    changed += 1
            else:
                r["income_group_pubyear"] = r["income_broad_pubyear"] = "NA"
            wr.writerow(r)
            n += 1
    print(f"wrote {dst}: {n:,} rows; {changed:,} with a different group at publication, "
          f"{unclassified:,} not classified that year")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--oghist", help="World Bank OGHIST.xlsx to (re)extract scripts/wb_income_history.csv from")
    ap.add_argument("--raw", default=os.path.join(ROOT, "data", "raw"), help="folder with the team export")
    ap.add_argument("--skip-raw", action="store_true", help="do not write the versioned team-export copies")
    args = ap.parse_args()
    csv.field_size_limit(10 ** 9)
    if args.oghist:
        extract(args.oghist)
    hist = load_history()

    path = os.path.join(DATA, "dict.json")
    with open(path, encoding="utf-8") as f:
        y0, y1 = json.load(f)["meta"]["years"]
    path = os.path.join(DATA, "countries.json")
    with open(path, encoding="utf-8") as f:
        countries = json.load(f)

    # The current group must equal the latest classification, or the two
    # sources have drifted apart.
    latest = f"FY{LAST_FY:02d}"
    drift = [c["iso3"] for c in countries
             if c["iso3"] not in OVERRIDE and CODES.get(hist.get(c["iso3"], {}).get(latest, "")) != c["income"]]
    if drift:
        raise SystemExit(f"current income differs from {latest} for: {', '.join(drift)}")

    with open(OUT_CSV, "w", encoding="utf-8", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["iso3", "year", "fiscal_year", "income_group_pubyear"])
        for c in sorted(countries, key=lambda c: c["iso3"]):
            for y in range(y0, y1 + 1):
                wr.writerow([c["iso3"], y, f"FY{y % 100:02d}", group_at(hist, c["iso3"], y) or "NA"])
    print(f"wrote {OUT_CSV}: {len(countries)} countries x {y0}-{y1}")

    new = []
    for c in countries:
        row = {k: v for k, v in c.items() if k != "income_y"}
        out = {}
        for k, v in row.items():
            out[k] = v
            if k == "income":
                out["income_y"] = [group_at(hist, c["iso3"], y) for y in range(y0, y1 + 1)]
        new.append(out)
    write_json(path, new)
    moved = sum(1 for c in new if len(set(c["income_y"])) > 1)
    print(f"updated {path}: income_y for {len(new)} countries ({moved} change group over {y0}-{y1})")

    if not args.skip_raw:
        rewrite_csv(os.path.join(args.raw, "hee_analysis_master_v2_who.csv"),
                    os.path.join(args.raw, "hee_analysis_master_v2_1.csv"), "country_iso3", hist)
        rewrite_csv(os.path.join(args.raw, "hee_geo_long_who.csv"),
                    os.path.join(args.raw, "hee_geo_long_v2_1.csv"), "iso3", hist)


if __name__ == "__main__":
    main()
