"""Replicate Schmallenbach et al. (2025, Nature Medicine) Fig. 2a and Fig. 3 for
health economic evaluations: the research-disease divergence (KLD) over time,
and how much of its change comes from research versus disease burden.

Method, as in the paper (Methods, "Analyses"):
  KLD(p || q) = sum_x p(x) ln(p(x) / q(x))
  p = share of DALYs by GBD level-2 cause (the reference distribution),
  q = share of research by the same causes. A study naming several causes
  counts once for each (study-cause links), as their articles do.
Main cause set: the paper's 16 level-2 causes (other infectious, other
non-communicable, mental disorders and the three injury groups left out).
Sensitivity set: those 16 plus mental disorders and the three injury groups (20).

Differences from the paper, stated in the outputs:
  - the paper's Fig. 2a and Fig. 3 are global (all research vs global DALYs), so
    geography does not enter; the "all" group here does the same. The income
    groups are an extension, placing research by the country studied (the
    paper's regional analyses use first-author country);
  - groups: all studies vs global DALYs; studies naming a low- or middle-income
    country vs LMIC DALYs; studies naming a high-income country vs HIC DALYs.
    Income: the World Bank group in force on 1 January of the publication year
    (studies) or burden year (DALYs); a study naming countries in both groups
    counts in both;
  - q uses add-one (Laplace) smoothing in every year and group, which the paper
    ran as a sensitivity check, because yearly LMIC and HIC counts are small;
  - 95% intervals come from resampling studies within each year (1,000 draws),
    since small study counts, not DALY estimates, dominate our uncertainty.
Fig. 3 counterfactuals: research fixed at its 2010 mix while DALYs vary, and
DALYs fixed at their 2010 mix while research varies.

Inputs (data/raw, team export): hee_analysis_master_v2.csv, hee_geo_long_v2_1.csv,
hee_share_v2_1/gbd_disease_long.csv, denominator_gbd_source.csv and the GBD
Results tool exports in "GBD data/" (DALYs, 2010-2023, 204 locations).
Writes exports/kld_replication_<date>/ (figures, results CSV, method note).

Usage:
    python scripts/build_kld_replication.py [--raw data/raw] [--draws 1000]
"""
import argparse
import csv
import datetime
import glob
import math
import os
import random
import textwrap
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import build_income_pubyear as bp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YEARS = list(range(2010, 2024))  # DALYs run to 2023
BASE = 2010
COVID = (2020, 2021)
CAUSES_16 = [
    "Cardiovascular diseases", "Maternal and neonatal disorders", "Respiratory infections and tuberculosis",
    "Neoplasms", "Enteric infections", "Musculoskeletal disorders", "Chronic respiratory diseases",
    "Neglected tropical diseases and malaria", "Neurological disorders", "Digestive diseases",
    "Diabetes and kidney diseases", "HIV/AIDS and sexually transmitted infections", "Nutritional deficiencies",
    "Sense organ diseases", "Skin and subcutaneous diseases", "Substance use disorders"]
CAUSES_20 = CAUSES_16 + ["Mental disorders", "Transport injuries", "Unintentional injuries",
                         "Self-harm and interpersonal violence"]
HIC, LMIC = "High income", "Low & middle income"
# Burden-year income groups the World Bank history lacks (as in build_gbd_figures.py).
# South Sudan, part of Sudan until 2011, is first classified from FY2013, so 2011-12 take Sudan's FY10 group;
# Venezuela is unclassified since FY22, so 2022-23 take its last group (FY21).
BURDEN_INCOME_FALLBACK = {("VEN", 2022): "Upper middle income", ("VEN", 2023): "Upper middle income",
                          ("SSD", 2010): "Lower middle income", ("SSD", 2011): "Lower middle income",
                          ("SSD", 2012): "Lower middle income"}
GROUPS = [("all", "All studies (global DALYs)", "#1d1d1d"),
          ("lmic", "Studies about low- and middle-income countries (LMIC DALYs)", "#D98F7A"),
          ("hic", "Studies about high-income countries (HIC DALYs)", "#6D91BE")]
BG = "#FAF9F7"


def read(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_studies(raw):
    """Per eligible study: publication year, groups it belongs to, and its level-2 causes."""
    csv.field_size_limit(10 ** 9)
    year = {r["record_id"]: int(r["year"]) for r in read(os.path.join(raw, "hee_analysis_master_v2.csv"))
            if r["is_eligible"] == "TRUE"}
    groups = defaultdict(set)
    for r in read(os.path.join(raw, "hee_geo_long_v2_1.csv")):
        if r["record_id"] in year and r["is_special"] == "FALSE":
            inc = r["income_broad_pubyear"]
            if inc == HIC:
                groups[r["record_id"]].add("hic")
            elif inc == LMIC:
                groups[r["record_id"]].add("lmic")
    causes = defaultdict(set)
    for r in read(os.path.join(raw, "hee_share_v2_1", "gbd_disease_long.csv")):
        if r["record_id"] in year:
            causes[r["record_id"]].add(r["grp"])
    return [{"year": year[rid], "groups": groups[rid] | {"all"}, "causes": causes[rid]}
            for rid in year if causes[rid]]


def load_dalys(raw):
    """DALYs by year, group (all/lmic/hic) and level-2 cause."""
    hist = bp.load_history()
    iso = {r["location_id"]: r["iso3"] for r in read(os.path.join(raw, "denominator_gbd_source.csv"))}
    out = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    seen, left_out = set(), defaultdict(set)
    for path in sorted(glob.glob(os.path.join(raw, "GBD data", "IHME-GBD_2023_DATA-*.csv"))):
        for r in read(path):
            if (r["measure_id"], r["metric_name"], r["age_name"], r["sex_name"]) != ("2", "Number", "All ages", "Both"):
                continue
            key = (r["year"], r["location_id"], r["cause_name"])
            if key in seen:
                continue
            seen.add(key)
            y, c = int(r["year"]), iso[r["location_id"]]
            v = float(r["val"])
            out[y]["all"][r["cause_name"]] += v
            g = bp.group_at(hist, c, y) or BURDEN_INCOME_FALLBACK.get((c, y))
            if g is None:
                left_out[y].add(c)
                continue
            out[y]["hic" if g == HIC else "lmic"][r["cause_name"]] += v
    missing = [y for y in YEARS if y not in out]
    if missing:
        raise SystemExit(f"No DALYs for {missing}; add the GBD Results tool export for those years.")
    return out, left_out


def shares(counts, causes, smooth):
    total = sum(counts.get(c, 0) for c in causes) + smooth * len(causes)
    return [(counts.get(c, 0) + smooth) / total for c in causes]


def kld(p, q):
    return sum(pi * math.log(pi / qi) for pi, qi in zip(p, q) if pi > 0)


def links(studies, causes):
    """Study-cause link counts for one list of studies."""
    n = defaultdict(int)
    for s in studies:
        for c in s["causes"]:
            if c in causes:
                n[c] += 1
    return n


def analyse(studies, dalys, causes, draws, rng):
    rows = []
    cause_set = set(causes)
    for key, *_ in GROUPS:
        by_year = {y: [s for s in studies if s["year"] == y and key in s["groups"] and s["causes"] & cause_set]
                   for y in YEARS}
        p = {y: shares(dalys[y][key], causes, 0) for y in YEARS}
        q = {y: shares(links(by_year[y], cause_set), causes, 1) for y in YEARS}
        # Bootstrap: resample studies within each year; the base year is resampled too.
        boot = {y: [] for y in YEARS}
        for _ in range(draws):
            for y in YEARS:
                pool = by_year[y]
                boot[y].append(shares(links([rng.choice(pool) for _ in pool], cause_set), causes, 1))
        for y in YEARS:
            obs = [kld(p[y], qb) for qb in boot[y]]
            dal_fixed = [kld(p[BASE], qb) for qb in boot[y]]
            res_fixed = [kld(p[y], qb) for qb in boot[BASE]]
            rows.append({"group": key, "year": y, "n_studies": len(by_year[y]),
                         "n_links": sum(links(by_year[y], cause_set).values()),
                         "kld_observed": kld(p[y], q[y]), "observed_lo": pct(obs, 2.5), "observed_hi": pct(obs, 97.5),
                         "kld_dalys_fixed_2010": kld(p[BASE], q[y]), "dalys_fixed_lo": pct(dal_fixed, 2.5),
                         "dalys_fixed_hi": pct(dal_fixed, 97.5),
                         "kld_research_fixed_2010": kld(p[y], q[BASE]), "research_fixed_lo": pct(res_fixed, 2.5),
                         "research_fixed_hi": pct(res_fixed, 97.5)})
    return rows


def pct(vals, q):
    v = sorted(vals)
    k = (len(v) - 1) * q / 100
    lo, hi = math.floor(k), math.ceil(k)
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


def change(rows, key, col, y1):
    r0 = next(r for r in rows if r["group"] == key and r["year"] == BASE)
    r1 = next(r for r in rows if r["group"] == key and r["year"] == y1)
    return 100 * (r1[col] / r0[col] - 1)


def style(ax):
    ax.set_facecolor(BG)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color("#b9b2a6")
    ax.spines["bottom"].set_color("#b9b2a6")
    ax.tick_params(colors="#3b3832", labelsize=10)
    ax.axvspan(COVID[0] - .5, COVID[1] + .5, color="#ece6da", zorder=0)
    ax.text(sum(COVID) / 2, 1.0, "COVID-19\nyears", transform=ax.get_xaxis_transform(), ha="center", va="top",
            fontsize=8.5, color="#8a8378")
    ax.set_xticks(YEARS[::2])
    ax.grid(axis="y", color="#e6e1d8", linewidth=.8)


def fig2a(rows, label, path):
    fig, ax = plt.subplots(figsize=(10, 5.6), facecolor=BG)
    style(ax)
    for key, name, colour in GROUPS:
        g = [r for r in rows if r["group"] == key]
        ax.fill_between(YEARS, [r["observed_lo"] for r in g], [r["observed_hi"] for r in g], color=colour, alpha=.14, linewidth=0)
        ax.plot(YEARS, [r["kld_observed"] for r in g], color=colour, linewidth=2.2, marker="o", markersize=3.5, label=name)
        for y1 in (2019, 2023):
            v = next(r["kld_observed"] for r in g if r["year"] == y1)
            ax.annotate(f"{change(rows, key, 'kld_observed', y1):+.0f}%", (y1, v), xytext=(4, 6), textcoords="offset points",
                        fontsize=8.5, color=colour, fontweight="bold")
    ax.set_ylim(bottom=0)
    ax.set_ylabel("Research–disease divergence (KLD)", fontsize=11)
    ax.set_xlabel("Publication year (research) / burden year (DALYs)", fontsize=10)
    fig.suptitle("Divergence between health economic evaluations and disease burden, 2010–2023", x=.06, ha="left",
                 fontsize=14, fontweight="bold", color="#1d1d1d")
    ax.set_title(f"KLD of research share vs DALY share across {label}; labels: change since 2010. Shaded bands: 95% intervals.",
                 loc="left", fontsize=9.5, color="#5d574e")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    fig.tight_layout(rect=(0, 0, 1, .95))
    fig.savefig(path, dpi=150, facecolor=BG)
    plt.close(fig)


def fig3(rows, label, path):
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.2), facecolor=BG, sharey=False)
    lines = [("kld_observed", "observed", "Observed", "#3f6fb5"),
             ("kld_research_fixed_2010", "research_fixed", "Research fixed to 2010 (only DALYs change)", "#3f8f80"),
             ("kld_dalys_fixed_2010", "dalys_fixed", "DALYs fixed to 2010 (only research changes)", "#c2412d")]
    for ax, (key, name, _) in zip(axes, GROUPS):
        style(ax)
        g = [r for r in rows if r["group"] == key]
        for col, band, lab, colour in lines:
            ax.fill_between(YEARS, [r[band + "_lo"] for r in g], [r[band + "_hi"] for r in g], color=colour, alpha=.12, linewidth=0)
            ax.plot(YEARS, [r[col] for r in g], color=colour, linewidth=2, label=lab)
        ax.set_ylim(bottom=0)
        ax.set_title(name.replace(" (", "\n("), loc="left", fontsize=10.5, fontweight="bold", color="#1d1d1d")
        n0, n1 = g[0]["n_studies"], g[-1]["n_studies"]
        ax.text(.01, .02, f"n = {n0:,} studies in 2010, {n1:,} in 2023", transform=ax.transAxes, fontsize=8, color="#6b665d")
    axes[0].set_ylabel("Research–disease divergence (KLD)", fontsize=11)
    axes[0].legend(frameon=False, fontsize=8.5, loc="upper right")
    fig.suptitle("What drives the change in divergence: research or disease burden?", x=.04, ha="left",
                 fontsize=14, fontweight="bold", color="#1d1d1d")
    fig.text(.04, .925, textwrap.fill(f"Across {label}. If the observed line follows the green line, changing burden explains "
             "the trend; if it follows the red line, changing research does. Shaded bands: 95% intervals.", 190),
             fontsize=9.5, color="#5d574e", va="top")
    fig.tight_layout(rect=(0, 0, 1, .86))
    fig.savefig(path, dpi=150, facecolor=BG)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--raw", default=os.path.join(ROOT, "data", "raw"))
    ap.add_argument("--draws", type=int, default=1000)
    args = ap.parse_args()
    out_dir = os.path.join(ROOT, "exports", f"kld_replication_{datetime.date.today():%Y-%m-%d}")
    os.makedirs(out_dir, exist_ok=True)
    studies = load_studies(args.raw)
    dalys, left_out = load_dalys(args.raw)
    rng = random.Random(20261014)
    results = []
    for tag, causes, label in [("16causes", CAUSES_16, "the paper's 16 GBD level-2 causes"),
                               ("20causes", CAUSES_20, "20 GBD level-2 causes (the paper's 16 plus mental disorders and injuries)")]:
        rows = analyse(studies, dalys, causes, args.draws, rng)
        for r in rows:
            r["cause_set"] = tag
        results += rows
        fig2a(rows, label, os.path.join(out_dir, f"fig2a_kld_trend_{tag}.png"))
        fig3(rows, label, os.path.join(out_dir, f"fig3_decomposition_{tag}.png"))
        print(f"== {tag}")
        for key, name, _ in GROUPS:
            print(f"  {key}: KLD 2010 {next(r['kld_observed'] for r in rows if r['group']==key and r['year']==BASE):.3f}; "
                  f"change to 2019 {change(rows, key, 'kld_observed', 2019):+.0f}%, to 2023 {change(rows, key, 'kld_observed', 2023):+.0f}% | "
                  f"research fixed: {change(rows, key, 'kld_research_fixed_2010', 2019):+.0f}% / {change(rows, key, 'kld_research_fixed_2010', 2023):+.0f}% | "
                  f"DALYs fixed: {change(rows, key, 'kld_dalys_fixed_2010', 2019):+.0f}% / {change(rows, key, 'kld_dalys_fixed_2010', 2023):+.0f}%")
    cols = ["cause_set", "group", "year", "n_studies", "n_links", "kld_observed", "observed_lo", "observed_hi",
            "kld_research_fixed_2010", "research_fixed_lo", "research_fixed_hi",
            "kld_dalys_fixed_2010", "dalys_fixed_lo", "dalys_fixed_hi"]
    with open(os.path.join(out_dir, "kld_results.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in results:
            w.writerow({c: (round(r[c], 5) if isinstance(r[c], float) else r[c]) for c in cols})
    if any(left_out.values()):
        print("Countries without a burden-year income group (in 'all' only):",
              {y: v for y, v in left_out.items() if v})
    print("wrote", out_dir)


if __name__ == "__main__":
    main()
