"""One World Bank income group per country, matched to study publication years.

Country-level figures (one dot or bar per country, all years pooled) need a
single group per country. Study-level analyses use the group in force on
1 January of each study's publication year (build_income_pubyear.py); this
script carries the same rule to countries:

  * a country with studies gets the group most of its study-country pairs were
    published under (each pair classified at its publication year); a tie goes
    to the group of the more recent publication;
  * a country with no study gets the group it held in most years 2010-2026
    (a tie goes to the more recent year), so zero-study countries still sit
    in a group in burden and deficit figures. The CSV covers every country in
    the World Bank history (scripts/wb_income_history.csv), not only the
    site's country list;
  * no classification in any year -> null.

Run after build_income_pubyear.py (needs countries.json `income_y`).

Writes:
  * scripts/country_income_pubyear.csv -> iso3, income_pub, basis, pairs,
                                          pairs_in_group, income_current (all
                                          countries; read by the figure scripts)
  * docs/data/countries.json           -> `income_pub` after `income_y`

Usage:
    python scripts/build_country_income_pubyear.py
"""
import csv
import json
import os
from collections import Counter

from build_income_pubyear import group_at, load_history, write_json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "docs", "data")
OUT_CSV = os.path.join(ROOT, "scripts", "country_income_pubyear.csv")


def read_json(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def modal(groups_by_year):
    """Most frequent group; ties go to the group seen most recently."""
    counts = Counter(g for _, g in groups_by_year if g)
    if not counts:
        return None, 0
    last = {g: y for y, g in sorted(groups_by_year) if g}
    best = max(counts, key=lambda g: (counts[g], last[g]))
    return best, counts[best]


def main():
    countries = read_json("countries.json")
    geo = read_json("geo.json")
    y0, y1 = read_json("dict.json")["meta"]["years"]
    if any("income_y" not in c or len(c["income_y"]) != y1 - y0 + 1 for c in countries):
        raise SystemExit("countries.json lacks a full income_y series: run build_income_pubyear.py first")

    pairs = [[] for _ in countries]
    seen = set()
    for s, c, y in zip(geo["s"], geo["c"], geo["y"]):
        if (s, c) in seen:
            continue
        seen.add((s, c))
        pairs[c].append((y, countries[c]["income_y"][y - y0]))

    hist = load_history()
    by_iso = {r["iso3"]: (pairs[c], r["income_y"], r["income"]) for c, r in enumerate(countries)}
    for iso in hist:
        if iso not in by_iso:
            ys = [group_at(hist, iso, y) for y in range(y0, y1 + 1)]
            by_iso[iso] = ([], ys, group_at(hist, iso, y1 + 1))

    rows, group_of = [], {}
    for iso, (ps, series, current) in sorted(by_iso.items()):
        if ps:
            group, n_in = modal(ps)
            basis = "studies"
        else:
            group, n_in = modal([(y0 + i, g) for i, g in enumerate(series)])
            basis = "years"
        group_of[iso] = group
        rows.append([iso, group or "NA", basis, len(ps), n_in, current or "NA"])

    new = []
    for r in countries:
        out = {}
        for k, v in r.items():
            if k == "income_pub":
                continue
            out[k] = v
            if k == "income_y":
                out["income_pub"] = group_of[r["iso3"]]
        new.append(out)

    with open(OUT_CSV, "w", encoding="utf-8", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["iso3", "income_pub", "basis", "pairs", "pairs_in_group", "income_current"])
        wr.writerows(sorted(rows))
    write_json(os.path.join(DATA, "countries.json"), new)
    moved = [r for r in rows if r[1] != r[5] and r[0] in {c["iso3"] for c in countries}]
    print(f"{len(rows)} countries; {sum(r[2] == 'studies' for r in rows)} from studies, "
          f"{sum(r[2] == 'years' for r in rows)} from years; {len(moved)} site countries differ from the current group:")
    for r in moved:
        print(f"  {r[0]}: {r[1]} (current {r[5]}; {r[4]}/{r[3]} pairs)")


if __name__ == "__main__":
    main()
