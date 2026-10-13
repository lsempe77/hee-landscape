"""Figure data for the income-stratified gallery figures, under two income codings.

`current`  = income_group (World Bank FY27, as in the published figures)
`pubyear`  = income_group_pubyear (group in force on 1 January of the publication
             year; build_income_pubyear.py)

Recomputes the numbers behind eight figures first drawn by the upstream build
(fig_equity_time, fig_openaccess, fig_metric, fig_intervention_mix, paper04,
paper05, fig_disease_circular, fig_theme_rank) from the team export, so that
the `current` numbers can be checked against the published figures before the
`pubyear` versions are drawn (build_income_pubyear_figures.py).

Usage:
    python scripts/income_pubyear_figure_data.py [--raw data/raw]   # prints a check table
"""
import argparse
import csv
import math
import os
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GROUPS = ["Low income", "Lower middle income", "Upper middle income", "High income"]
HIC = "High income"
CODINGS = {"current": "income_group", "pubyear": "income_group_pubyear"}
LAST_FULL_YEAR = 2025
# paper04: MeSH C-tree categories shown, with their labels.
C_CATS = {"C01": "Infectious", "C04": "Neoplasms", "C08": "Respiratory", "C20": "Immune (incl. HIV)",
          "C14": "Cardiovascular", "C18": "Nutrition / metabolic", "C10": "Nervous system",
          "C26": "Injuries", "C23": "Signs / symptoms"}
ERAS = [("2010–2017", 2010, 2017), ("2018–2026", 2018, 2026)]
INTERVENTIONS = {
    "pharma": "Pharmaceuticals", "care_model_organisational": "Care models & organisation",
    "behavioural_preventive": "Behavioural & preventive", "vaccine": "Vaccines",
    "screening_diagnostic": "Screening & diagnosis", "financing_payment_policy": "Financing & payment policy",
    "surgical_procedural": "Surgery & procedures", "device_or_supply": "Devices & supplies", "other": "Other",
}


def read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load(raw):
    csv.field_size_limit(10 ** 9)
    rows = [r for r in read(os.path.join(raw, "hee_analysis_master_v2_1.csv")) if r["is_eligible"] == "TRUE"]
    daly = {r["record_id"] for r in read(os.path.join(raw, "hee_outcomes_long.csv")) if r["family"] == "DALYs"}
    interv = {r["record_id"]: r["intervention_class"] for r in read(os.path.join(raw, "hee_intervention_class.csv"))}
    cluster = {r["record_id"]: r["cluster"] for r in read(os.path.join(raw, "topic_map.csv"))}
    labels = {r["cluster"]: r["label"] for r in read(os.path.join(raw, "topic_labels.csv"))}
    ids = {r["record_id"] for r in rows}
    geo_groups = {k: defaultdict(set) for k in CODINGS}
    for r in read(os.path.join(raw, "hee_geo_long_v2_1.csv")):
        if r["record_id"] in ids:
            for k, col in CODINGS.items():
                if r[col] in GROUPS:
                    geo_groups[k][r["record_id"]].add(r[col])
    for r in rows:
        r["year"] = int(r["year"])
        r["daly"] = r["record_id"] in daly
        r["interv"] = interv.get(r["record_id"])
        r["cluster"] = cluster.get(r["record_id"], "")
        r["groups"] = [] if r["disease_groups"] == "NA" else r["disease_groups"].split(";")
        r["ccats"] = [] if r["disease_c_cats"] == "NA" else r["disease_c_cats"].split(";")
    return rows, labels, geo_groups


def single(rows, col):
    """Single-country studies with a known income group under the coding."""
    return [r for r in rows if r["geo_scope"] == "single_country" and r[col] in GROUPS]


def wilson(k, n, z=1.96):
    if not n:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def equity_time(rows, col):
    by = defaultdict(Counter)
    for r in single(rows, col):
        if r["year"] <= LAST_FULL_YEAR:
            by[r["year"]]["n"] += 1
            by[r["year"]]["lmic"] += r[col] != HIC
    return {y: c["lmic"] / c["n"] for y, c in sorted(by.items())}, sum(c["n"] for c in by.values())


def openaccess(rows, col):
    by = defaultdict(Counter)
    for r in single(rows, col):
        if r["year"] <= LAST_FULL_YEAR and r["is_oa"] in ("0", "1"):
            k = "hic" if r[col] == HIC else "lmic"
            by[r["year"]][k + "_n"] += 1
            by[r["year"]][k + "_oa"] += r["is_oa"] == "1"
    out = {y: {"hic": c["hic_oa"] / c["hic_n"], "lmic": c["lmic_oa"] / c["lmic_n"],
               "all": (c["hic_oa"] + c["lmic_oa"]) / (c["hic_n"] + c["lmic_n"])} for y, c in sorted(by.items())}
    return out, sum(c["hic_n"] + c["lmic_n"] for c in by.values())


def metric(rows, col):
    out = {"All studies": (sum(r["uses_qaly"] == "TRUE" for r in rows) / len(rows), sum(r["daly"] for r in rows) / len(rows))}
    s = single(rows, col)
    for g in reversed(GROUPS):
        gs = [r for r in s if r[col] == g]
        out[g] = (sum(r["uses_qaly"] == "TRUE" for r in gs) / len(gs), sum(r["daly"] for r in gs) / len(gs))
    return out


def intervention_mix(rows, col):
    s = single(rows, col)
    out = {}
    for g in reversed(GROUPS):
        gs = [r for r in s if r[col] == g]
        cnt = Counter(r["interv"] for r in gs)
        out[g] = {k: cnt[k] / len(gs) for k in INTERVENTIONS}
    return out, len(s)


def paper05(rows, geo_groups, coding):
    """A disease-coded study counts in every income group among the countries it
    names (multi-country studies included), as in the published heatmap."""
    n, out = Counter(), defaultdict(Counter)
    for r in rows:
        if not r["groups"]:
            continue
        for g in geo_groups[coding].get(r["record_id"], ()):
            n[g] += 1
            for x in set(r["groups"]):
                out[g][x] += 1
    areas = sorted({x for r in rows for x in r["groups"]})
    return {a: {g: out[g][a] / n[g] for g in GROUPS} for a in areas}, dict(n)


def paper04(rows, col):
    s = [r for r in single(rows, col) if r["ccats"]]
    out, n = {}, {}
    for side in ("lmic", "hic"):
        for era, y0, y1 in ERAS:
            gs = [r for r in s if y0 <= r["year"] <= y1 and (r[col] == HIC) == (side == "hic")]
            n[(side, era)] = len(gs)
            cnt = Counter(x for r in gs for x in set(r["ccats"]))
            for code in C_CATS:
                k = cnt[code]
                out[(side, era, code)] = (k / len(gs), *wilson(k, len(gs)), k)
    return out, n


def disease_lean(rows, col):
    """Circular figure: share of disease-coded studies per group (incl. C23), and
    log2 of the group's LMIC share / HIC share among single-country studies."""
    coded = [r for r in rows if r["groups"] or "C23" in r["ccats"]]
    def tags(r):
        return set(r["groups"]) | ({"Complications & symptoms"} if "C23" in r["ccats"] else set())
    share = Counter(x for r in coded for x in tags(r))
    s = [r for r in single(rows, col) if r["groups"] or "C23" in r["ccats"]]
    side = {k: [r for r in s if (r[col] == HIC) == (k == "hic")] for k in ("lmic", "hic")}
    cnt = {k: Counter(x for r in v for x in tags(r)) for k, v in side.items()}
    lean = {}
    for g in share:
        pl, ph = cnt["lmic"][g] / len(side["lmic"]), cnt["hic"][g] / len(side["hic"])
        lean[g] = math.log2(pl / ph) if pl and ph else None
    return {g: (share[g] / len(coded), lean[g]) for g in share}, len(coded)


def theme_rank(rows, labels, col, min_n=30):
    s = [r for r in single(rows, col) if r["cluster"] not in ("", "-1")]
    by = defaultdict(Counter)
    for r in s:
        by[r["cluster"]]["n"] += 1
        by[r["cluster"]]["lmic"] += r[col] != HIC
    themes = {c: (v["lmic"] / v["n"], v["n"]) for c, v in by.items() if v["n"] >= min_n}
    overall = sum(v["lmic"] for v in by.values()) / sum(v["n"] for v in by.values())
    name = {c: labels.get(c, c).split(" / ")[0].strip().capitalize() for c in themes}
    return themes, name, overall, len(single(rows, col))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--raw", default=os.path.join(ROOT, "data", "raw"))
    args = ap.parse_args()
    rows, labels, geo_groups = load(args.raw)
    pct = lambda x: f"{100 * x:.1f}%"
    for coding, col in CODINGS.items():
        print(f"\n===== {coding} ({col})")
        et, n = equity_time(rows, col)
        print(f"equity_time n={n:,}: 2010 {pct(et[2010])}, 2015 {pct(et[2015])}, 2020 {pct(et[2020])}, 2025 {pct(et[2025])}")
        oa, n = openaccess(rows, col)
        print(f"openaccess n={n:,}: 2010 HIC {pct(oa[2010]['hic'])} LMIC {pct(oa[2010]['lmic'])} | 2025 HIC {pct(oa[2025]['hic'])} LMIC {pct(oa[2025]['lmic'])}")
        m = metric(rows, col)
        print("metric (QALY, DALY):", {k: (pct(q), pct(d)) for k, (q, d) in m.items()})
        im, n = intervention_mix(rows, col)
        print(f"intervention n={n:,}: pharma", {g[:5]: pct(im[g]["pharma"]) for g in im},
              "care", {g[:5]: pct(im[g]["care_model_organisational"]) for g in im},
              "vacc", {g[:5]: pct(im[g]["vaccine"]) for g in im})
        p5, n = paper05(rows, geo_groups, coding)
        print("paper05 n:", n, "Infectious", {g[:5]: round(100 * p5["Infectious"][g]) for g in GROUPS},
              "Neoplasms", {g[:5]: round(100 * p5["Neoplasms"][g]) for g in GROUPS})
        p4, n = paper04(rows, col)
        print("paper04 n:", {f"{k[0]} {k[1]}": v for k, v in n.items()},
              "Infectious LMIC", [pct(p4[("lmic", e, "C01")][0]) for e, *_ in ERAS],
              "Neoplasms LMIC", [pct(p4[("lmic", e, "C04")][0]) for e, *_ in ERAS])
        dl, n = disease_lean(rows, col)
        print(f"circular n={n:,}:", {g[:12]: (pct(s), None if l is None else round(l, 2)) for g, (s, l) in sorted(dl.items())})
        th, name, overall, n = theme_rank(rows, labels, col)
        top = sorted(th, key=lambda c: -th[c][0])[:4]
        bot = sorted(th, key=lambda c: th[c][0])[:3]
        print(f"theme_rank n={n:,} themes={len(th)} overall {pct(overall)}; LMIC top:",
              [(name[c], pct(th[c][0]), th[c][1]) for c in top], "HIC top:", [(name[c], pct(1 - th[c][0]), th[c][1]) for c in bot])


if __name__ == "__main__":
    main()
