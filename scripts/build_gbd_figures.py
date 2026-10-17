"""Redraw the gallery's disease figures on the GBD 2023 disease coding (team share v2.1).

The team's v2.1 share (data/raw/hee_share_v2_1) replaces the 14 MeSH-based
disease groups with GBD 2023 level-2 causes coded from each study's title and
abstract (gbd_disease_long.csv: 22 causes plus two groups for studies naming
an infection or an injury without its cause). The share ships its own GBD
figures, but they predate local changes, so these are drawn locally instead:
income group in force when the study was published (build_income_pubyear.py),
"studies" wording for a base that includes reviews, and no funding-allocation
language. New versioned files; the originals are kept:

  fig_disease_circular.webp         -> fig_disease_circular_gbd.webp
  paper04.webp                      -> paper04_gbd.webp
  paper05.webp                      -> paper05_gbd.webp   (replaces paper05_pubyear)
  paper08.webp                      -> paper08_gbd.webp
  fig_burden_disease_companion.webp -> fig_burden_disease_companion_gbd.webp
  fig_funder_trajectory.webp        -> fig_funder_trajectory_gbd.webp

  fig_funder_opportunity.webp       -> fig_funder_opportunity_gbd.webp
  fig_transition.webp               -> fig_transition_gbd.webp

Burden: GBD 2023 DALYs by country and level-2 cause from the GBD Results tool
(data/raw/GBD data/), summed by the World Bank income group in force on 1
January of the burden year (2023; 2010 for the transition figure), matching
the publication-year rule for studies.
The site swaps the figures in from docs/data/figure_updates.json (old file ->
new file and caption) and takes titles and summaries from figure_copy.json.

Usage:
    python scripts/build_gbd_figures.py [--raw data/raw]
"""
import argparse
import csv
import json
import math
import os
import sys
import textwrap
from collections import Counter, defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import income_pubyear_figure_data as fd  # noqa: E402
import build_income_pubyear_figures as pf  # noqa: E402  (house style: header, footer, save)

ROOT = fd.ROOT
SHARE = "hee_share_v2_1"
# GBD Results tool export: DALYs by country and level-2 cause, 2010 and 2015-2023.
GBD_DIR = "GBD data"
# Burden-year income groups the World Bank history lacks: Venezuela has been
# unclassified since FY22 (its last group, FY21, is used, as for 2026 studies);
# South Sudan, part of Sudan until 2011, takes Sudan's FY10 group.
BURDEN_INCOME_FALLBACK = {("VEN", 2023): "Upper middle income", ("SSD", 2010): "Lower middle income"}
CAPTIONS = os.path.join(ROOT, "docs", "data", "figure_updates.json")
COPY = os.path.join(ROOT, "docs", "data", "figure_copy.json")
COL = fd.CODINGS["pubyear"]
GROUPS, HIC = fd.GROUPS, fd.HIC
BG, INK, MUTED, GRID = pf.BG, pf.INK, pf.MUTED, pf.GRID
ORANGE, BLUE, GREY = "#E8693A", "#2E78D2", "#8a857c"
pct = pf.pct

L1 = {"Communicable, maternal, neonatal, and nutritional diseases": "cmnn",
      "Non-communicable diseases": "ncd", "Injuries": "inj"}
L1_LABEL = {"cmnn": "Communicable, maternal,\nneonatal & nutritional", "ncd": "Non-communicable", "inj": "Injuries"}
L1_COLOR = {"cmnn": ORANGE, "ncd": BLUE, "inj": GREY}
# GBD level-2 cause name -> plain label used on the site (figures and Explore).
LABEL = {
    "HIV/AIDS and sexually transmitted infections": "HIV/AIDS & STIs",
    "Respiratory infections and tuberculosis": "Respiratory infections & TB",
    "Enteric infections": "Enteric (diarrhoeal) infections",
    "Neglected tropical diseases and malaria": "Malaria & neglected tropical diseases",
    "Other infectious diseases": "Other infectious",
    "Infections, disease not stated": "Infection, type not stated",
    "Maternal and neonatal disorders": "Maternal & neonatal",
    "Nutritional deficiencies": "Nutritional deficiencies",
    "Neoplasms": "Cancers (neoplasms)",
    "Cardiovascular diseases": "Cardiovascular",
    "Chronic respiratory diseases": "Chronic respiratory",
    "Digestive diseases": "Digestive",
    "Neurological disorders": "Neurological",
    "Mental disorders": "Mental disorders",
    "Substance use disorders": "Substance use",
    "Diabetes and kidney diseases": "Diabetes & kidney",
    "Skin and subcutaneous diseases": "Skin",
    "Sense organ diseases": "Eye and ear",
    "Musculoskeletal disorders": "Musculoskeletal",
    "Other non-communicable diseases": "Other non-communicable",
    "Transport injuries": "Transport injuries",
    "Unintentional injuries": "Unintentional injuries",
    "Self-harm and interpersonal violence": "Self-harm & violence",
    "Injuries, cause not stated": "Injury, cause not stated",
}
SHORT = {"Neglected tropical diseases and malaria": "Malaria & NTDs",
         "Enteric infections": "Diarrhoeal infections"}
NOT_STATED = {"Infections, disease not stated", "Injuries, cause not stated"}
CODING = ("Disease groups: GBD 2023 causes coded from each study's title and abstract (the condition the "
          "evaluated intervention targets).")
SOURCE_BURDEN = "Burden: GBD 2023 DALYs (IHME)."
MIN_N = 15


def read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load(raw):
    rows, _, geo_groups = fd.load(raw)
    gbd, l1 = defaultdict(set), {}
    for r in read(os.path.join(raw, SHARE, "gbd_disease_long.csv")):
        gbd[r["record_id"]].add(r["grp"])
        l1[r["grp"]] = L1[r["l1"]]
    assert set(l1) == set(LABEL), set(l1) ^ set(LABEL)
    for r in rows:
        r["gbd"] = gbd.get(r["record_id"], set())
        # Broad income settings the study names (a multi-country study can name both).
        inc = geo_groups["pubyear"].get(r["record_id"], set())
        r["sides"] = {"hic" if g == HIC else "lmic" for g in inc}
    return rows, geo_groups, l1, load_burden(raw)


def load_burden(raw):
    """GBD DALYs (number, all ages, both sexes) by year, income group and level-2 cause,
    summed over countries; a country's income group is the World Bank group in force
    on 1 January of the burden year, as for the studies. Returns
    {year: {"by4": {group: {cause: dalys}}, "hic"/"lmic": {cause: dalys}}, "left_out": {year: [iso3]}}."""
    import glob
    import build_income_pubyear as bp
    hist = bp.load_history()
    iso = {r["location_id"]: r["iso3"] for r in read(os.path.join(raw, "denominator_gbd_source.csv"))}
    files = sorted(glob.glob(os.path.join(raw, GBD_DIR, "IHME-GBD_2023_DATA-*.csv")))
    if not files:
        raise SystemExit(f"No GBD Results tool export in {os.path.join(raw, GBD_DIR)}")
    out = defaultdict(lambda: {"by4": defaultdict(lambda: defaultdict(float)),
                               "hic": defaultdict(float), "lmic": defaultdict(float)})
    left_out, seen = defaultdict(set), set()
    for path in files:
        for r in read(path):
            if (r["measure_id"], r["metric_name"], r["age_name"], r["sex_name"]) != ("2", "Number", "All ages", "Both"):
                continue
            key = (r["year"], r["location_id"], r["cause_name"])
            if key in seen:
                continue  # the same row in two downloads
            seen.add(key)
            year, country = int(r["year"]), iso[r["location_id"]]
            group = bp.group_at(hist, country, year) or BURDEN_INCOME_FALLBACK.get((country, year))
            if group is None:
                left_out[year].add(country)
                continue
            v = float(r["val"])
            out[year]["by4"][group][r["cause_name"]] += v
            out[year]["hic" if group == HIC else "lmic"][r["cause_name"]] += v
    causes = {c for y in out.values() for g in y["by4"].values() for c in g}
    assert causes == set(LABEL) - NOT_STATED, causes ^ (set(LABEL) - NOT_STATED)
    return {**out, "left_out": {y: sorted(v) for y, v in left_out.items()}}


def single(rows):
    return [r for r in fd.single(rows, COL) if r["gbd"]]


def side_of(r):
    return "hic" if r[COL] == HIC else "lmic"


def wilson(k, n):
    return fd.wilson(k, n)


# ---------------------------------------------------------------- disease circular
def circular(rows, l1):
    coded = [r for r in rows if r["gbd"]]
    share = Counter(g for r in coded for g in r["gbd"])
    s = single(rows)
    sides = {k: [r for r in s if side_of(r) == k] for k in ("lmic", "hic")}
    cnt = {k: Counter(g for r in v for g in r["gbd"]) for k, v in sides.items()}
    lean = {}
    for g in share:
        pl, ph = cnt["lmic"][g] / len(sides["lmic"]), cnt["hic"][g] / len(sides["hic"])
        lean[g] = math.log2(pl / ph) if pl and ph else None
    shown = [g for g in share if share[g] / len(coded) >= .01]
    small = sorted((g for g in share if g not in shown), key=lambda g: -share[g])
    order = []
    for blk in ("cmnn", "ncd", "inj"):
        order += sorted((g for g in shown if l1[g] == blk), key=lambda g: -share[g])
    vals = [share[g] / len(coded) for g in order]

    fig = plt.figure(figsize=(9, 11))
    top_lmic = sorted((g for g in order if lean[g] is not None), key=lambda g: -lean[g])[:3]
    top_hic = sorted((g for g in order if lean[g] is not None), key=lambda g: lean[g])[:3]
    lead = sorted(order, key=lambda g: -share[g])[:3]
    names = lambda gs: ", ".join(LABEL[g].lower() if g not in ("HIV/AIDS and sexually transmitted infections",)
                                 else LABEL[g] for g in gs)
    y = pf.header(fig, "Which diseases do the studies focus on?",
                  "Bar length: each GBD cause group's share of the studies that name a disease. Colour: whether "
                  "research on it leans toward high-income or toward low- and middle-income countries.",
                  f"{LABEL[lead[0]]}, {LABEL[lead[1]].lower()} and {LABEL[lead[2]].lower()} lead. Research leans "
                  f"toward lower-income countries for {names(top_lmic)}, and toward high-income countries for "
                  f"{names(top_hic)}.", width=98)
    ax = fig.add_axes([.1, .22, .8, y - .3], projection="polar")
    ax.set_facecolor(BG)
    n = len(order)
    gap = .035
    width = 2 * math.pi / n
    theta = np.arange(n) * width + width / 2
    inner = .55
    scale = (1.0 - inner) / max(vals)
    cmap = LinearSegmentedColormap.from_list("lean", [BLUE, "#9aa3c4", "#c9c3b6", "#e0a888", ORANGE])
    norm = TwoSlopeNorm(vcenter=0, vmin=-2, vmax=2)
    ax.bar(theta, [v * scale for v in vals], width=width - gap, bottom=inner,
           color=[cmap(norm(lean[g])) if lean[g] is not None else "#ddd" for g in order], edgecolor=BG, lw=.5)
    for t, g, v in zip(theta, order, vals):
        deg = math.degrees(t)
        rot = 90 - deg
        flip = 180 < deg < 360
        ax.text(t, inner + v * scale + .03, f"{LABEL[g]}  {pct(v)}", rotation=rot + (180 if flip else 0),
                rotation_mode="anchor", ha="right" if flip else "left", va="center", fontsize=9.5,
                family="Franklin Gothic Demi Cond", color=INK)
    ax.text(0, 0, f"{len(coded):,}\nstudies", ha="center", va="center", fontsize=15, family=pf.TITLE_FONT)
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_ylim(0, 1.0)
    ax.axis("off")
    cax = fig.add_axes([.38, .178, .24, .011])
    cb = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cax, orientation="horizontal", ticks=[-2, 0, 2])
    cb.ax.set_xticklabels(["Leans high-income", "Balanced", "Leans lower-income"], fontsize=9.5, color=MUTED)
    cb.outline.set_visible(False)
    cb.ax.tick_params(length=0)
    pf.footer(fig, f"{CODING} Groups under 1% of studies are not drawn ("
                   + "; ".join(f"{LABEL[g]} {share[g]:,}" for g in small) + "). Base: "
                   f"{len(coded):,} of {len(rows):,} studies name at least one disease group; a study can name "
                   "several, so shares add up to more than 100%. Colour: log2 of the group's share of single-country "
                   "studies about low- and middle-income countries divided by its share of those about high-income "
                   f"countries. {pf.RULE}", y=.012, width=125)
    pf.save(fig, "fig_disease_circular_gbd.webp")
    return {"caption": f"Share of the {len(coded):,} studies that name a disease (of {len(rows):,}) by GBD 2023 cause "
                       f"group; {LABEL[lead[0]].lower()} ({pct(share[lead[0]] / len(coded))}), "
                       f"{LABEL[lead[1]].lower()} ({pct(share[lead[1]] / len(coded))}) and {LABEL[lead[2]].lower()} "
                       f"({pct(share[lead[2]] / len(coded))}) lead. Colour shows whether a group's research leans "
                       "toward low- and middle-income or high-income countries (single-country studies). A study can "
                       "name several groups. Disease groups coded from titles and abstracts to GBD 2023 causes. "
                       "Income group: the World Bank group of the country studied, as classified on 1 January of the publication year."}


# ---------------------------------------------------------------- paper04 (eras)
def paper04(rows, l1):
    s = single(rows)
    data, n = {}, {}
    for side in ("lmic", "hic"):
        for era, y0, y1 in fd.ERAS:
            gs = [r for r in s if y0 <= r["year"] <= y1 and side_of(r) == side]
            n[(side, era)] = len(gs)
            cnt = Counter(g for r in gs for g in r["gbd"])
            for g in LABEL:
                k = cnt[g]
                data[(side, era, g)] = (k / len(gs), *wilson(k, len(gs)), k)
    shown = [g for g in LABEL if any(data[(sd, e, g)][0] >= .05 for sd in ("lmic", "hic") for e, *_ in fd.ERAS)]
    e1, e2 = fd.ERAS[0][0], fd.ERAS[1][0]
    trend = {}
    for g in shown:
        a, b = data[("lmic", e1, g)], data[("lmic", e2, g)]
        trend[g] = "up" if b[1] > a[2] else "down" if b[2] < a[1] else "flat"
    colour = {"up": BLUE, "down": ORANGE, "flat": "#9a958c"}
    rising = sorted((g for g in shown if trend[g] == "up"), key=lambda g: -(data[("lmic", e2, g)][0] - data[("lmic", e1, g)][0]))
    falling = sorted((g for g in shown if trend[g] == "down"), key=lambda g: data[("lmic", e2, g)][0] - data[("lmic", e1, g)][0])

    fig = plt.figure(figsize=(9, 10))
    def lst(gs):
        gs = [LABEL[g].lower() if not g.startswith("HIV") else LABEL[g] for g in gs[:2]]
        return " and ".join(gs) if gs else "no group"
    y = pf.header(fig, "Disease priorities are shifting in lower-income countries",
                  "Share of each income setting's disease-coded studies on each GBD cause group, 2010–2017 vs "
                  "2018–2026.",
                  f"In low- and middle-income research, {lst(falling)} fall as a share while {lst(rising)} rise; the "
                  "high-income mix changes less.", width=100)
    ymax = max(data[(sd, e, g)][2] for sd in ("lmic", "hic") for e, *_ in fd.ERAS for g in shown) * 1.05
    for k, (side, title) in enumerate([("lmic", "Low- and middle-income countries"), ("hic", "High-income countries")]):
        ax = fig.add_axes([.09 + k * .46, .17, .25, y - .27])
        pf.style(ax)
        ax.set_title(title, loc="left", fontsize=12, family="Franklin Gothic Demi", color=INK, pad=10)
        ends = []
        for g in shown:
            c = colour[trend[g]]
            pts = [data[(side, e, g)] for e, *_ in fd.ERAS]
            lw = 2.6 if trend[g] != "flat" else 1.6
            ax.plot([0, 1], [p[0] for p in pts], color=c, lw=lw, zorder=3 if trend[g] != "flat" else 2)
            for x, p in zip((0, 1), pts):
                ax.plot([x, x], [p[1], p[2]], color=c, lw=1, alpha=.7)
                ax.scatter([x], [p[0]], s=10 + p[3] / 25, color=c, zorder=4)
            ends.append([pts[1][0], g])
        # Spread end labels so they do not overlap.
        ends.sort()
        gapy = ymax * .032
        for i in range(1, len(ends)):
            ends[i][0] = max(ends[i][0], ends[i - 1][0] + gapy)
        for yy, g in ends:
            ax.annotate(SHORT.get(g, LABEL[g]), (1, data[(side, e2, g)][0]), xytext=(1.08, yy), fontsize=9.5,
                        color=colour[trend[g]] if trend[g] != "flat" else MUTED, va="center",
                        arrowprops=dict(arrowstyle="-", color=GRID, lw=.6), annotation_clip=False)
        ax.set_xlim(-.15, 1.05)
        ax.set_ylim(0, ymax)
        ax.set_xticks([0, 1], [e1, e2])
        ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1, decimals=0))
        if k:
            ax.set_yticklabels([])
        else:
            ax.set_ylabel("Share of the setting's disease-coded studies", fontsize=11)
    for k, (t, c) in enumerate([("Falling in lower-income research", ORANGE), ("Little change", "#9a958c"),
                                ("Rising in lower-income research", BLUE)]):
        fig.text(.09 + k * .3, y - .01, "● " + t, color=c, fontsize=10.5, va="top")
    pf.footer(fig, f"{CODING} Drawn: the {len(shown)} of 24 groups that reach 5% of disease-coded studies in at least "
                   "one period and setting. Falling or rising: the 95% intervals (Wilson; vertical bars) of the two "
                   "periods do not overlap. Point size shows the number of studies. A study naming several causes "
                   "counts in each. Single-country studies with a disease group: low- and middle-income "
                   f"{n[('lmic', e1)]:,} in {e1}, {n[('lmic', e2)]:,} in {e2}; high-income {n[('hic', e1)]:,} and "
                   f"{n[('hic', e2)]:,}. {pf.RULE}", y=.012, width=140)
    pf.save(fig, "paper04_gbd.webp")
    desc = lambda g, sd: f"{LABEL[g].lower() if not g.startswith('HIV') else LABEL[g]} ({pct(data[(sd, e1, g)][0])} → {pct(data[(sd, e2, g)][0])})"
    return {"caption": f"Disease mix of single-country studies by period ({e1}, {e2}) and income setting, on GBD 2023 "
                       f"cause groups. In low- and middle-income research, "
                       + ("; ".join(desc(g, "lmic") for g in falling[:2]) + " fall" if falling else "no group falls")
                       + " while "
                       + ("; ".join(desc(g, "lmic") for g in rising[:2]) + " rise" if rising else "no group rises")
                       + ". Falling or rising: non-overlapping 95% intervals. Bars are 95% intervals; point size is "
                       "the number of studies. Disease groups coded from titles and abstracts. Income group: the "
                       "World Bank group of the country studied, as classified on 1 January of the publication year.",
            "falling": falling, "rising": rising}


# ---------------------------------------------------------------- paper05 (heatmap)
def paper05(rows, geo_groups, l1):
    n, out = Counter(), defaultdict(Counter)
    for r in rows:
        if not r["gbd"]:
            continue
        for g in geo_groups["pubyear"].get(r["record_id"], ()):
            n[g] += 1
            for x in r["gbd"]:
                out[g][x] += 1
    share = {a: {g: out[g][a] / n[g] for g in GROUPS} for a in LABEL}
    blocks = []
    for blk in ("cmnn", "ncd", "inj"):
        gs = [a for a in LABEL if l1[a] == blk]
        gs.sort(key=lambda a: -math.log((share[a]["Low income"] + .002) / (share[a]["High income"] + .002)))
        blocks.append((blk, gs))
    areas = [a for _, gs in blocks for a in gs]
    fig = plt.figure(figsize=(9, 11.5))
    fig.text(.02, .978, "Which diseases are studied differs by country income", fontsize=19, fontweight="bold",
             family="Arial", va="top")
    fig.text(.02, .952, "% of each income group's studies that cover each GBD cause group", fontsize=12.5,
             family="Arial", color=MUTED, va="top")
    ax = fig.add_axes([.46, .13, .46, .74])
    cmap = LinearSegmentedColormap.from_list("b", ["#d6e6fb", "#9cc3f0", "#3d8be0", "#0b3a73"])
    cmap.set_bad(BG)
    # A blank header row, named for its GBD level-1 group, above each block.
    grid, labels, heads = [], [], []
    for blk, gs in blocks:
        heads.append((len(grid), blk))
        grid.append([np.nan] * 4)
        labels.append("")
        for a in gs:
            grid.append([100 * share[a][g] for g in GROUPS])
            labels.append(LABEL[a])
    im = ax.imshow(np.ma.masked_invalid(grid), cmap=cmap, vmin=0, vmax=30, aspect="auto")
    for i, row in enumerate(grid):
        for j, v in enumerate(row):
            if not np.isnan(v):
                ax.text(j, i, f"{round(v)}", ha="center", va="center", fontsize=11.5, family="Arial",
                        color="white" if v >= 18 else INK)
    ax.set_xticks(range(4), ["Low income", "Lower\nmiddle\nincome", "Upper\nmiddle\nincome", "High\nincome"],
                  fontsize=11.5, family="Arial", fontweight="bold", color="#4a463f")
    ax.xaxis.tick_top()
    ax.set_yticks(range(len(labels)), labels, fontsize=11.5, family="Arial", color="#4a463f")
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xticks([x + .5 for x in range(3)], minor=True)
    ax.set_yticks([y + .5 for y in range(len(labels) - 1)], minor=True)
    ax.grid(which="minor", color=BG, lw=3)
    ax.tick_params(which="minor", length=0)
    for row, blk in heads:
        ax.text(-.9, row + .15, L1_LABEL[blk].replace("\n", " ").upper(), ha="left", va="center", fontsize=10.5,
                family="Arial", fontweight="bold", color=L1_COLOR[blk], transform=ax.get_yaxis_transform())
    cax = fig.add_axes([.94, .45, .015, .1])
    cb = fig.colorbar(im, cax=cax, ticks=[0, 10, 20, 30])
    cb.outline.set_visible(False)
    cb.ax.tick_params(length=0, labelsize=10)
    pf.footer(fig, "A study can cover several groups, so columns add up to more than 100%. A study about several "
                   "countries counts in each income group it names. Rows are grouped by GBD level 1 and run from the "
                   "groups most concentrated in low-income research to those most concentrated in high-income "
                   "research; colour saturates at 30%. " + CODING + " Studies with a disease group per income group: "
                   f"low {n['Low income']:,}, lower-middle {n['Lower middle income']:,}, upper-middle "
                   f"{n['Upper middle income']:,}, high {n['High income']:,}. {pf.RULE}", y=.012, width=135)
    pf.save(fig, "paper05_gbd.webp")
    hiv, mal, neo = (share["HIV/AIDS and sexually transmitted infections"], share["Neglected tropical diseases and malaria"],
                     share["Neoplasms"])
    return {"caption": "Percentage of each income group's disease-coded studies that name each GBD 2023 cause group "
                       "(22 level-2 causes plus studies naming an infection or injury without its cause), grouped by "
                       f"GBD level 1. Malaria and neglected tropical diseases ({pct(mal['Low income'])} of low-income "
                       f"studies vs {pct(mal['High income'])} of high-income) and HIV/AIDS ({pct(hiv['Low income'])} vs "
                       f"{pct(hiv['High income'])}) concentrate in low-income research; cancers in upper-middle- and "
                       f"high-income research ({pct(neo['Upper middle income'])}, {pct(neo['High income'])}). A study "
                       "naming several groups or countries appears in each, so columns sum above 100%. Income group: "
                       "the World Bank group of the country studied, as classified on 1 January of the publication year.",
            "share": share}


# ---------------------------------------------------------------- research vs burden (HIC / LMIC)
def research_vs_burden(rows, burden):
    causes = [g for g in LABEL if g not in NOT_STATED]
    res = {}
    for side in ("lmic", "hic"):
        coded = [r for r in rows if side in r["sides"] and r["gbd"] - NOT_STATED]
        cnt = Counter(g for r in coded for g in r["gbd"] - NOT_STATED)
        tot = sum(burden[side][g] for g in causes)
        res[side] = {"n": len(coded), "k": cnt,
                     "rs": {g: cnt[g] / len(coded) for g in causes},
                     "bs": {g: burden[side][g] / tot for g in causes}}
        res[side]["ratio"] = {g: res[side]["rs"][g] / res[side]["bs"][g] if cnt[g] else None for g in causes}
    return causes, res


def burden_footer(res, extra=""):
    return (f"{CODING} Research: share of the studies naming a level-2 cause in each setting (low- and "
            f"middle-income {res['lmic']['n']:,}, high-income {res['hic']['n']:,}; a study naming countries in both "
            "counts in each). Studies that name an infection or injury without its cause have no burden counterpart "
            "and are left out of both sides, so injury ratios are lower bounds. Burden: GBD 2023 DALYs for the same "
            "22 causes, summed over the countries in each setting (World Bank group on 1 January 2023). Matching research to "
            f"burden is a reference point, not a target. {extra}{pf.RULE}")


def paper08(rows, burden):
    causes, res = research_vs_burden(rows, burden)
    order = sorted(causes, key=lambda g: res["lmic"]["ratio"][g] or 1e-9)
    fig = plt.figure(figsize=(9, 9.4))
    low = order[:3]
    mat = "Maternal and neonatal disorders"
    y = pf.header(fig, "Some diseases get far less research than their burden",
                  "For each GBD cause group, its share of studies divided by its share of disease burden, in low- "
                  "and middle-income and in high-income countries. Left of 1: less research than burden.",
                  "The largest gaps in lower-income settings are "
                  + ", ".join(f"{LABEL[g].lower()} ({res['lmic']['ratio'][g]:.2g}×)" for g in low)
                  + f". Maternal & neonatal research runs {res['lmic']['ratio'][mat]:.2g}× its burden share in "
                  f"lower-income settings and {res['hic']['ratio'][mat]:.2g}× in high-income ones.", width=100)
    ax = fig.add_axes([.3, .19, .64, y - .24])
    pf.style(ax)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=GRID, lw=.8)
    ax.axvspan(1e-3, 1, color="#f1e7dc", alpha=.6, zorder=0)
    for i, g in enumerate(order):
        a, b = res["lmic"]["ratio"][g], res["hic"]["ratio"][g]
        pts = [v for v in (a, b) if v]
        if len(pts) == 2:
            ax.plot(pts, [i, i], color="#cfc8bc", lw=3.2, zorder=2)
        if b:
            ax.scatter([b], [i], s=70, color=BLUE, zorder=3)
        if a:
            ax.scatter([a], [i], s=70, color=ORANGE, zorder=4)
    ax.axvline(1, color=MUTED, ls=(0, (2, 2)), lw=1)
    ax.set_xscale("log")
    ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    vals = [v for sd in ("lmic", "hic") for v in res[sd]["ratio"].values() if v]
    ax.set_xlim(min(vals) / 1.6, max(vals) * 1.6)
    ticks = [t for t in (.01, .03, .1, .3, 1, 3, 10, 30) if min(vals) / 1.6 <= t <= max(vals) * 1.6]
    ax.set_xticks(ticks, [f"{t:g}×" if t != 1 else "matched" for t in ticks])
    ax.set_yticks(range(len(order)), [LABEL[g] for g in order], fontsize=10.5)
    ax.set_ylim(-.7, len(order) - .3)
    ax.set_xlabel("Share of research ÷ share of disease burden (log scale)", fontsize=11)
    fig.text(.3, y - .02, "● Low- and middle-income countries", color=ORANGE, fontsize=10.5, va="top")
    fig.text(.62, y - .02, "● High-income countries", color=BLUE, fontsize=10.5, va="top")
    pf.footer(fig, burden_footer(res), y=.012, width=140)
    pf.save(fig, "paper08_gbd.webp")
    return {"caption": "Research share divided by disease-burden share for the 22 GBD 2023 level-2 causes, in low- "
                       "and middle-income and in high-income countries; left of 1, a cause has a smaller share of "
                       "research than of burden. The largest lower-income gaps: "
                       + ", ".join(f"{LABEL[g].lower()} ({res['lmic']['ratio'][g]:.2g}×)" for g in low)
                       + f"; maternal & neonatal runs {res['lmic']['ratio'][mat]:.2g}× its burden share in "
                       f"lower-income settings and {res['hic']['ratio'][mat]:.2g}× in high-income ones. Disease groups "
                       "coded from titles and abstracts to the same GBD causes as the burden, so no crosswalk is "
                       "needed; studies naming an injury without its cause are left out, so injury ratios are lower "
                       "bounds. Burden: GBD 2023 DALYs. Income group: the World Bank group "
                       "of the country studied, as classified on 1 January of the publication year.", "res": res, "low": low}


def companion(rows, burden):
    causes, res = research_vs_burden(rows, burden)
    fig = plt.figure(figsize=(9, 9.6))
    order = sorted(causes, key=lambda g: -res["lmic"]["bs"][g])
    under = [g for g in order if res["lmic"]["rs"][g] < res["lmic"]["bs"][g]]
    big_under = sorted(under, key=lambda g: res["lmic"]["rs"][g] - res["lmic"]["bs"][g])[:3]
    y = pf.header(fig, "Does research attention match the burden of each disease?",
                  "Each GBD cause group's share of studies (bar) against its share of disease burden (line), in "
                  "low- and middle-income and in high-income countries.",
                  "In lower-income settings the widest shortfalls in percentage points are "
                  + ", ".join(f"{LABEL[g].lower()} ({pct(res['lmic']['rs'][g])} of studies, "
                              f"{pct(res['lmic']['bs'][g])} of burden)" for g in big_under) + ".", width=100)
    for k, (side, title, c) in enumerate([("lmic", "Low- and middle-income countries", ORANGE),
                                          ("hic", "High-income countries", BLUE)]):
        ax = fig.add_axes([.3 + k * .34, .17, .29, y - .23])
        pf.style(ax)
        ax.grid(axis="y", visible=False)
        ax.grid(axis="x", color=GRID, lw=.8)
        ys = np.arange(len(order))
        ax.barh(ys, [res[side]["rs"][g] for g in order], color=c, alpha=.75, height=.62)
        for i, g in enumerate(order):
            b = res[side]["bs"][g]
            ax.plot([b, b], [i - .42, i + .42], color=INK, lw=1.8)
        ax.set_yticks(ys, [LABEL[g] for g in order] if not k else [], fontsize=10.5)
        ax.invert_yaxis()
        mx = max(max(res[sd]["rs"].values()) for sd in res) * 1.08
        mx = max(mx, max(max(res[sd]["bs"].values()) for sd in res) * 1.08)
        ax.set_xlim(0, mx)
        ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1, decimals=0))
        ax.set_title(title, loc="left", fontsize=11.5, family="Franklin Gothic Demi", color=INK, pad=8)
    fig.text(.3, y - .015, "Bar: share of studies     │ line: share of disease burden (DALYs)", color=MUTED,
             fontsize=10.5, va="top")
    pf.footer(fig, "Rows are sorted by the cause's share of lower-income burden. " + burden_footer(res), y=.012,
              width=140)
    pf.save(fig, "fig_burden_disease_companion_gbd.webp")
    return {"caption": "Each GBD 2023 level-2 cause's share of studies against its share of disease burden (DALYs), "
                       "in low- and middle-income and in high-income countries. The widest lower-income shortfalls: "
                       + ", ".join(f"{LABEL[g].lower()} ({pct(res['lmic']['rs'][g])} of studies vs "
                                   f"{pct(res['lmic']['bs'][g])} of burden)" for g in big_under)
                       + ". Studies naming an infection or injury without its cause are left out. Burden: GBD 2023 "
                       "DALYs. Income group: the World Bank group of the country studied, "
                       "as classified on 1 January of the publication year.", "big_under": big_under, "res": res}


# ---------------------------------------------------------------- trajectory (LMIC, two periods)
def trajectory(rows, burden):
    causes = [g for g in LABEL if g not in NOT_STATED]
    tot = sum(burden["lmic"][g] for g in causes)
    bs = {g: burden["lmic"][g] / tot for g in causes}
    out, ns = {}, {}
    for era, y0, y1 in fd.ERAS:
        coded = [r for r in rows if "lmic" in r["sides"] and y0 <= r["year"] <= y1 and r["gbd"] - NOT_STATED]
        cnt = Counter(g for r in coded for g in r["gbd"] - NOT_STATED)
        ns[era] = len(coded)
        for g in causes:
            out[(era, g)] = (cnt[g] / len(coded) / bs[g], cnt[g])
    e1, e2 = fd.ERAS[0][0], fd.ERAS[1][0]
    drawn = [g for g in causes if out[(e1, g)][1] >= MIN_N and out[(e2, g)][1] >= MIN_N]
    dropped = [g for g in causes if g not in drawn]
    def status(g):
        a, b = out[(e1, g)][0], out[(e2, g)][0]
        if b >= 1:
            return "above"
        return "closing" if b >= a * 1.05 else "stuck"
    col = {"above": "#2163b5", "closing": "#E8A400", "stuck": "#C24A2E"}
    order = sorted(drawn, key=lambda g: -out[(e2, g)][0])
    stuck = sorted((g for g in drawn if status(g) == "stuck"), key=lambda g: out[(e2, g)][0])
    closing = [g for g in drawn if status(g) == "closing"]
    fig = plt.figure(figsize=(9, 8.6))
    y = pf.header(fig, "Which research gaps are narrowing, and which are not",
                  f"For each GBD cause group, lower-income countries' share of studies divided by their share of "
                  f"its burden, {e1} (dot) vs {e2} (arrowhead).",
                  "Still below burden and not closing: " + ", ".join(LABEL[g].lower() for g in stuck[:4]) + "."
                  + (" Closing: " + ", ".join(LABEL[g].lower() for g in closing) + "." if closing else ""), width=100)
    ax = fig.add_axes([.3, .22, .64, y - .28])
    pf.style(ax)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=GRID, lw=.8)
    ax.axvspan(1e-3, 1, color="#f1e7dc", alpha=.6, zorder=0)
    for i, g in enumerate(order):
        a, b = out[(e1, g)][0], out[(e2, g)][0]
        c = col[status(g)]
        ax.annotate("", xy=(b, i), xytext=(a, i), arrowprops=dict(arrowstyle="-|>", color=c, lw=2.4,
                                                                   shrinkA=0, shrinkB=0, mutation_scale=14))
        ax.scatter([a], [i], s=28, color="#8a857c", zorder=4)
    ax.axvline(1, color=MUTED, ls=(0, (2, 2)), lw=1)
    ax.set_xscale("log")
    ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    vals = [out[(e, g)][0] for g in drawn for e in (e1, e2)]
    lo, hi = min(vals) / 1.4, max(vals) * 1.4
    ax.set_xlim(lo, hi)
    ticks = [t for t in (.1, .25, .5, 1, 2, 4, 8) if lo <= t <= hi]
    ax.set_xticks(ticks, [f"{t:g}×" if t != 1 else "matched" for t in ticks])
    ax.set_yticks(range(len(order)), [LABEL[g] for g in order], fontsize=10.5)
    ax.invert_yaxis()
    ax.set_xlabel(f"Lower-income share of studies ÷ share of burden (log scale; {e1} → {e2})", fontsize=11)
    for k, (t, c) in enumerate([("Below burden, not closing", col["stuck"]), ("Below burden, closing", col["closing"]),
                                ("At or above burden share", col["above"])]):
        fig.text(.3 + k * .22, y - .015, "→ " + t, color=c, fontsize=10.5, va="top")
    pf.footer(fig, f"{CODING} Research: studies naming a low- or middle-income country and a level-2 cause "
                   f"({ns[e1]:,} in {e1}, {ns[e2]:,} in {e2}). Burden: 2023 GBD DALYs in low- and middle-income "
                   "countries for the same cause, used for both periods. Closing: the second-period ratio is at least "
                   f"5% above the first. Not drawn (fewer than {MIN_N} studies in a period): "
                   + ", ".join(LABEL[g] for g in dropped) + ". Studies naming an infection or injury without its "
                   f"cause are left out. Matching research to burden is a reference point, not a target. {pf.RULE}",
              y=.012, width=140)
    pf.save(fig, "fig_funder_trajectory_gbd.webp")
    return {"caption": f"Lower-income countries' share of studies divided by their share of burden, for each GBD 2023 "
                       f"level-2 cause, {e1} vs {e2}. Below burden and not closing: "
                       + ", ".join(LABEL[g].lower() for g in stuck) + "."
                       + (" Below burden but closing: " + ", ".join(LABEL[g].lower() for g in closing) + "." if closing else "")
                       + f" Closing means the {e2} ratio is at least 5% above the {e1} ratio. Burden: GBD 2023 DALYs "
                       "in low- and middle-income countries, a fixed reference for both periods. Past publication "
                       "trends describe what happened, not future research needs. Income group: the World Bank "
                       "group of the country studied, as classified on 1 January of the publication year.",
            "stuck": stuck, "closing": closing}


# ---------------------------------------------------------------- opportunity matrix (4 income groups)
def opportunity(rows, b):
    causes = [g for g in LABEL if g not in NOT_STATED]
    s = [r for r in fd.single(rows, COL) if r["gbd"] - NOT_STATED]
    k, n = defaultdict(Counter), Counter()
    for r in s:
        n[r[COL]] += 1
        for g in r["gbd"] - NOT_STATED:
            k[r[COL]][g] += 1
    ratio = {}
    for grp in GROUPS:
        tot = sum(b["by4"][grp][c] for c in causes)
        for c in causes:
            ratio[(c, grp)] = (k[grp][c] / n[grp]) / (b["by4"][grp][c] / tot) if k[grp][c] >= MIN_N else None
    def score(c):
        v = [math.log(ratio[(c, g)]) for g in GROUPS if ratio[(c, g)]]
        return sum(v) / len(v) if v else 9
    order = sorted(causes, key=score)
    lmic_groups = GROUPS[:3]
    worst = sorted(((ratio[(c, g)], c, g) for c in causes for g in lmic_groups if ratio[(c, g)]))[:4]
    short = {"Low income": "low-income", "Lower middle income": "lower-middle-income",
             "Upper middle income": "upper-middle-income", "High income": "high-income"}
    fig = plt.figure(figsize=(9, 11))
    y = pf.header(fig, "Where evidence is thinnest relative to health needs",
                  "For each GBD cause group and income group, its share of single-country studies divided by its "
                  "share of that income group's disease burden. Blue: less research than burden; red: more.",
                  "The thinnest evidence relative to burden: "
                  + "; ".join(f"{LABEL[c].lower()} in {short[g]} countries ({v:.2g}×)" for v, c, g in worst)
                  + f". Grey cells have too few studies (under {MIN_N}) to estimate.", width=100)
    ax = fig.add_axes([.33, .14, .55, y - .2])
    cmap = LinearSegmentedColormap.from_list("gap", ["#2c4fa3", "#8d9fd3", "#efe4d6", "#e58c6c", "#c2412d"])
    norm = TwoSlopeNorm(vcenter=0, vmin=-3, vmax=3)
    for i, c in enumerate(order):
        for j, g in enumerate(GROUPS):
            v = ratio[(c, g)]
            colour = cmap(norm(max(-3, min(3, math.log2(v))))) if v else "#e6e1d8"
            ax.add_patch(matplotlib.patches.Rectangle((j + .03, i + .06), .94, .88, color=colour, lw=0))
            ax.text(j + .5, i + .5, f"{v:.2g}×" if v else f"n={k[g][c]}", ha="center", va="center",
                    fontsize=10 if v else 8.5, color=INK if v else "#9a958c",
                    family="Franklin Gothic Demi" if v else pf.BODY_FONT)
    ax.set_xlim(0, 4)
    ax.set_ylim(len(order), 0)
    ax.set_xticks([j + .5 for j in range(4)], ["Low\nincome", "Lower\nmiddle\nincome", "Upper\nmiddle\nincome",
                                               "High\nincome"], fontsize=10.5, family="Franklin Gothic Demi")
    ax.xaxis.tick_top()
    ax.set_yticks([i + .5 for i in range(len(order))], [LABEL[c] for c in order], fontsize=10.5)
    ax.tick_params(length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    cax = fig.add_axes([.91, .45, .014, .16])
    cb = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cax, ticks=[-3, -2, -1, 0, 1, 2, 3])
    cb.ax.set_yticklabels(["⅛×", "¼×", "½×", "matched", "2×", "4×", "8×"], fontsize=9.5, color=MUTED)
    cb.outline.set_visible(False)
    cb.ax.tick_params(length=0)
    counts = ", ".join(f"{short[g].replace('-income', '')} {n[g]:,}" for g in GROUPS)
    pf.footer(fig, f"{CODING} Research: single-country studies naming a level-2 cause, by the income group of the "
                   f"country studied ({counts}). Burden: GBD 2023 DALYs for the same cause, summed over "
                   "the countries in each income group (World Bank group on 1 January 2023). Studies naming an "
                   "infection or injury without its cause are left out, so injury ratios are lower bounds. Rows run "
                   "from the thinnest evidence relative to burden (top). Matching research to burden is a reference "
                   f"point, not a target. {pf.RULE}", y=.012, width=140)
    pf.save(fig, "fig_funder_opportunity_gbd.webp")
    return {"caption": "Research share divided by disease-burden share for each GBD 2023 level-2 cause and World Bank "
                       "income group (single-country studies). The thinnest evidence relative to burden: "
                       + "; ".join(f"{LABEL[c].lower()} in {short[g]} countries ({v:.2g}×)" for v, c, g in worst)
                       + f". Cells with fewer than {MIN_N} studies are grey. Studies naming an infection or injury "
                       "without its cause are left out, so injury ratios are lower bounds. Burden: GBD 2023 DALYs by "
                       "income group (classification on 1 January 2023). Matching research to burden is a reference "
                       "point, not a target. Income group of studies: the World Bank "
                       "group of the country studied, as classified on 1 January of the publication year.", "worst": worst}


# ---------------------------------------------------------------- epidemiological transition (LMIC)
def transition(rows, burden, l1):
    blocks = ["cmnn", "ncd", "inj"]
    names = {"cmnn": "Communicable, maternal, neonatal & nutritional", "ncd": "Non-communicable", "inj": "Injuries"}
    years = list(range(2010, fd.LAST_FULL_YEAR + 1))
    share, nyear = {}, {}
    for yr in years:
        cnt = Counter()
        rs = [r for r in rows if "lmic" in r["sides"] and r["year"] == yr and r["gbd"]]
        nyear[yr] = len(rs)
        for r in rs:
            for blk in {l1[g] for g in r["gbd"]}:
                cnt[blk] += 1
        tot = sum(cnt.values())
        share[yr] = {blk: cnt[blk] / tot for blk in blocks}
    bshare = {}
    for yr in (2010, 2023):
        by = Counter()
        for c, v in burden[yr]["lmic"].items():
            by[l1[c]] += v
        tot = sum(by.values())
        bshare[yr] = {blk: by[blk] / tot for blk in blocks}
    y0, y1 = years[0], years[-1]
    fig = plt.figure(figsize=(9, 7.4))
    y = pf.header(fig, "Lower-income research has shifted toward non-communicable disease",
                  "Disease mix of studies about low- and middle-income countries by GBD level 1, against the "
                  "burden in those countries in 2010 and 2023 (dashes).",
                  f"In {y0}, {pct(share[y0]['cmnn'])} of the research was on communicable, maternal, neonatal and "
                  f"nutritional conditions, {pct(bshare[2010]['cmnn'])} of the 2010 burden; by {y1} it was "
                  f"{pct(share[y1]['cmnn'])}, against {pct(bshare[2023]['cmnn'])} of the 2023 burden. "
                  f"Non-communicable research ({pct(share[y1]['ncd'])}) now exceeds its burden share "
                  f"({pct(bshare[2023]['ncd'])}); injuries stay below theirs ({pct(share[y1]['inj'])} vs "
                  f"{pct(bshare[2023]['inj'])}).", width=100)
    ax = fig.add_axes([.12, .2, .76, y - .27])
    pf.style(ax)
    for blk in blocks:
        c = L1_COLOR[blk]
        ax.plot(years, [share[yr][blk] for yr in years], color=c, lw=2.6, marker="o", ms=4)
        for yr, x, ha in ((2010, y0 - 1.6, "right"), (2023, y1 + 1.6, "left")):
            v = bshare[yr][blk]
            xs = (y0 - 1.4, y0 - .4) if yr == 2010 else (y1 + .4, y1 + 1.4)
            ax.plot(xs, [v, v], color=c, lw=2, ls=(0, (2, 1.5)))
            ax.text(x, v, pct(v), color=c, fontsize=10, va="center", ha=ha, family="Franklin Gothic Demi")
    ax.text(y0 - .9, .78,"2010\nburden", ha="center", fontsize=9.5, color=MUTED)
    ax.text(y1 + .9, .78, "2023\nburden", ha="center", fontsize=9.5, color=MUTED)
    ax.set_xlim(y0 - 3, y1 + 3)
    ax.set_ylim(0, .85)
    ax.set_xticks(range(y0, y1 + 1, 2))
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1, decimals=0))
    ax.set_ylabel("Share of lower-income research (disease mentions)", fontsize=11)
    for kx, blk in enumerate(blocks):
        fig.text((.12, .6, .82)[kx], y - .015, "● " + names[blk], color=L1_COLOR[blk], fontsize=10.5, va="top")
    pf.footer(fig, f"{CODING} Research: studies naming a low- or middle-income country and a disease group, by "
                   f"publication year ({nyear[y0]:,} in {y0} to {nyear[y1]:,} in {y1}; 2026 is partial and left out); "
                   "a study with causes in two level-1 groups counts in both. Burden: GBD 2023-round DALYs for 2010 "
                   "and 2023, all 22 level-2 causes rolled up to level 1, summed over low- and middle-income countries "
                   f"(World Bank group on 1 January of each year). {pf.RULE}", y=.012, width=140)
    pf.save(fig, "fig_transition_gbd.webp")
    return {"caption": f"Disease mix of studies about low- and middle-income countries by GBD 2023 level 1, {y0}–{y1}, "
                       f"against those countries' 2010 and 2023 burden. Communicable, maternal, neonatal and "
                       f"nutritional conditions fell from {pct(share[y0]['cmnn'])} of the research in {y0} to "
                       f"{pct(share[y1]['cmnn'])} in {y1} (burden {pct(bshare[2010]['cmnn'])} in 2010, "
                       f"{pct(bshare[2023]['cmnn'])} in 2023); non-communicable research rose to "
                       f"{pct(share[y1]['ncd'])} (burden {pct(bshare[2023]['ncd'])}); injuries stayed at "
                       f"{pct(share[y1]['inj'])} (burden {pct(bshare[2023]['inj'])}). A study with causes in two "
                       "groups counts in both. Burden: GBD 2023-round DALYs. Income group: the World Bank "
                       "group of each country, as classified on 1 January of the publication year (for studies) or the burden year (for burden).",
            "share": share, "bshare": bshare, "years": (y0, y1)}


# Titles and summaries shown above each figure (figure_copy.json, keyed by original file).
def copy_text(r):
    p4, p5, p8, comp, traj = r["paper04"], r["paper05"], r["paper08"], r["companion"], r["trajectory"]
    lab = lambda g: LABEL[g] if g.startswith("HIV") else LABEL[g].lower()
    return {
        "fig_disease_circular.webp": {
            "title": "Which diseases does the economic evidence focus on?",
            "summary": "This chart shows which disease groups, as defined by the Global Burden of Disease study, "
                       "receive the most research attention, and whether that research leans toward richer or "
                       "poorer countries. A study can cover several groups, so the percentages can add up to more "
                       "than 100%. Only studies that name a disease are included."},
        "paper04.webp": {
            "title": "Disease priorities are changing in lower-income countries",
            "summary": "Compare the diseases studied in earlier and later years. In research about lower-income "
                       f"countries, {' and '.join(lab(g) for g in p4['falling'][:2]) or 'no group'} account for a "
                       f"smaller share, while {' and '.join(lab(g) for g in p4['rising'][:2]) or 'no group'} account "
                       "for more. Studies can cover several disease groups."},
        "paper05.webp": {
            "title": "The diseases studied differ by country income",
            "summary": "Malaria, HIV/AIDS and other infections feature more often in research about lower-income "
                       "countries. Cancer and heart disease feature more often in higher-income settings. A study "
                       "can appear in more than one disease group."},
        "paper08.webp": {
            "title": "Some disease groups receive less research attention relative to their burden",
            "summary": "Injuries, especially self-harm, violence and road injuries, and mental disorders show the "
                       "largest differences between research attention and disease burden. The comparison is a "
                       "reference point, not a target."},
        "fig_burden_disease_companion.webp": {
            "title": "Does research attention match the burden of different diseases?",
            "summary": "Compare each disease group's share of research with its share of illness and early death, "
                       "in lower-income and high-income countries. This helps identify areas receiving relatively "
                       "less research attention."},
        "fig_funder_opportunity.webp": {
            "title": "Evidence gaps: where is research scarce relative to health needs?",
            "summary": "Explore disease groups and income levels with relatively little evidence compared with "
                       "disease burden. These comparisons help identify questions for further investigation; they "
                       "do not estimate the cost or benefit of new research."},
        "fig_transition.webp": {
            "title": "Research in lower-income countries is shifting towards long-term illnesses",
            "summary": "Research about lower-income countries has moved from infections and maternal and child "
                       "health towards non-communicable diseases, broadly in step with the changing disease burden; "
                       "research on injuries stays well below their share of the burden."},
        "fig_funder_trajectory.webp": {
            "title": "Gap trends: which evidence gaps are narrowing over time?",
            "summary": "Compare changes in research coverage over time. Past publication trends show what has "
                       "happened, rather than predicting future research or funding needs."},
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--raw", default=os.path.join(ROOT, "data", "raw"))
    args = ap.parse_args()
    rows, geo_groups, l1, burden = load(args.raw)
    b23 = burden[2023]
    print("burden left out (no income group):", burden["left_out"])
    r = {"circular": circular(rows, l1), "paper04": paper04(rows, l1), "paper05": paper05(rows, geo_groups, l1),
         "paper08": paper08(rows, b23), "companion": companion(rows, b23), "trajectory": trajectory(rows, b23),
         "opportunity": opportunity(rows, b23), "transition": transition(rows, burden, l1)}
    files = {"fig_funder_opportunity.webp": ("fig_funder_opportunity_gbd.webp", "opportunity"),
             "fig_transition.webp": ("fig_transition_gbd.webp", "transition"),
             "fig_disease_circular.webp": ("fig_disease_circular_gbd.webp", "circular"),
             "paper04.webp": ("paper04_gbd.webp", "paper04"),
             "paper05.webp": ("paper05_gbd.webp", "paper05"),
             "paper08.webp": ("paper08_gbd.webp", "paper08"),
             "fig_burden_disease_companion.webp": ("fig_burden_disease_companion_gbd.webp", "companion"),
             "fig_funder_trajectory.webp": ("fig_funder_trajectory_gbd.webp", "trajectory")}
    captions = json.load(open(CAPTIONS, encoding="utf-8"))
    for old, (new, key) in files.items():
        captions[old] = {"file": new, "caption": r[key]["caption"] + (
            " For 2026 publications only, missing FY2026 classifications use FY2025 low income for Ethiopia and "
            "FY2021 upper-middle income for Venezuela (FY2025 also unavailable); these are analysis exceptions.")}
    with open(CAPTIONS, "w", encoding="utf-8", newline="\n") as f:
        json.dump(captions, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("wrote", CAPTIONS)
    fig_copy = json.load(open(COPY, encoding="utf-8"))
    for old, text in copy_text(r).items():
        fig_copy.setdefault(old, {}).update(text)
    with open(COPY, "w", encoding="utf-8", newline="\n") as f:
        json.dump(fig_copy, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("wrote", COPY)


if __name__ == "__main__":
    main()
