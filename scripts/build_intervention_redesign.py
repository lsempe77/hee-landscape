"""Redesign options for the intervention map ("What kinds of healthcare does the research cover?").

Not used by the site. Writes three figures (PNG at 300 dpi, plus PDF) to exports/intervention_redesign_<date>/ for review:

  option1_map_plus_circles.png  A: the topic map coloured by primary intervention (frozen
                                topic coordinates, as on the site); B: one circle of dots per
                                intervention class, LMIC dots filling from the bottom.
  option2_circles_fill.png      the dot circles alone (one dot = 20 studies).
  option3_circles_scatter.png   the dot circles alone, one dot per study placed at random,
                                LMIC dots mixed in.

Same data as the site figure (scripts/build_remaining_figures_reconciled.R): reconciled master
(hee_analysis_master_v2_1.csv, 41,610 eligible), primary intervention class
(hee_intervention_class.csv), frozen topic coordinates (topic_map.csv; HDBSCAN noise in grey).
LMIC shares: single-country studies with a World Bank group in force on 1 January of the
publication year (27,897). The circles do not use the topic coordinates.

Usage: python scripts/build_intervention_redesign.py
"""
import csv
import collections
import datetime
import math
import os
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
OUT = os.path.join(ROOT, "exports", f"intervention_redesign_{datetime.date.today():%Y-%m-%d}")
BG, INK, MUTED = "#FAF9F7", "#10243e", "#5d574e"
GROUPS = {"Low income", "Lower middle income", "Upper middle income", "High income"}
LABEL = dict(pharma="Pharmaceuticals", vaccine="Vaccines", screening_diagnostic="Screening & diagnosis",
             surgical_procedural="Surgery & procedures", device_or_supply="Devices & supplies",
             behavioural_preventive="Behavioural & preventive", care_model_organisational="Care models & organisation",
             financing_payment_policy="Financing & payment policy", other="Other")
COLOUR = dict(pharma="#6D91BE", vaccine="#D98F7A", screening_diagnostic="#9B87B8", surgical_procedural="#b23a48",
              device_or_supply="#D6B264", behavioural_preventive="#62A89B", care_model_organisational="#16a085",
              financing_payment_policy="#a0522d", other="#888888")
INCOME_NOTE = ("Income: World Bank group in force on 1 January of the publication year. Intervention: the primary class "
               "assigned to each study's abstract by a language model (secondary classes not counted).")


def read(name):
    csv.field_size_limit(10 ** 9)
    with open(os.path.join(RAW, name), encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load():
    master = [r for r in read("hee_analysis_master_v2_1.csv") if r["is_eligible"] == "TRUE"]
    assert len(master) == 41610
    cls = {r["record_id"]: r["intervention_class"] for r in read("hee_intervention_class.csv")}
    counts = collections.defaultdict(lambda: [0, 0])  # class -> [high income, LMIC]
    for r in master:
        if r["geo_scope"] == "single_country" and r["income_group_pubyear"] in GROUPS and cls.get(r["record_id"]):
            counts[cls[r["record_id"]]][0 if r["income_group_pubyear"] == "High income" else 1] += 1
    assert sum(sum(v) for v in counts.values()) == 27897
    ids = {r["record_id"] for r in master}
    pts = [(float(r["x"]), float(r["y"]), int(r["cluster"]), cls.get(r["record_id"]))
           for r in read("topic_map.csv") if r["record_id"] in ids]
    assert len(pts) == 41583
    return counts, pts


def lighter(hexc, f=.6):
    c = np.array([int(hexc[i:i + 2], 16) for i in (1, 3, 5)]) / 255
    return tuple(c + (1 - c) * f)


def circles(fig, gs_cells, counts, mode, per, order="lmic"):
    """One circle per class, ordered by LMIC share (or by size); area proportional to studies."""
    rng = np.random.default_rng(7)
    key = (lambda kv: -sum(kv[1])) if order == "size" else (lambda kv: -kv[1][1] / sum(kv[1]))
    items = sorted(counts.items(), key=key)
    maxn = max(sum(v) for v in counts.values())
    for cell, (k, (h, l)) in zip(gs_cells, items):
        ax = fig.add_subplot(cell)
        n = h + l
        nd, nl = max(1, round(n / per)), round(l / per)
        s = math.sqrt(n / maxn)
        if mode == "scatter":
            r, th = np.sqrt(rng.random(nd)), rng.random(nd) * 2 * math.pi
            x, y, dot = r * np.cos(th) * s, r * np.sin(th) * s, 2.2
            light_first = rng.permutation(nd)  # LMIC dots scattered among the rest
            x, y = x[light_first], y[light_first]
        else:
            i = np.arange(nd) + .5
            r, th = np.sqrt(i / nd), i * math.pi * (3 - math.sqrt(5))  # even sunflower packing
            x, y = r * np.cos(th), r * np.sin(th)
            idx = np.argsort(y)  # LMIC dots fill from the bottom
            x, y = x[idx] * s, y[idx] * s
            dot = 26 * min(1, .6 + .4 * s) if per > 1 else 1.4
        ax.scatter(x[nl:], y[nl:], s=dot, color=COLOUR[k], lw=0)
        ax.scatter(x[:nl], y[:nl], s=dot, color=lighter(COLOUR[k]), lw=0)
        ax.set_xlim(-1.08, 1.08); ax.set_ylim(-1.08, 1.08); ax.set_aspect("equal"); ax.axis("off")
        ax.set_title(f"{LABEL[k]}\n{100 * l / n:.0f}% L&MICs · {n:,} studies", fontsize=11, color=INK)


def circles_note(mode, per, order="lmic"):
    first = ("One dot = one single-country study, placed at random within its circle; darker = high-income settings, "
             "lighter = low- and middle-income settings." if mode == "scatter" else
             f"One dot = {per} single-country stud{'y' if per == 1 else 'ies'}; darker = high-income settings, lighter (filling from the bottom) = "
             "low- and middle-income settings.")
    by = "number of studies (largest first)" if order == "size" else "L&MICs share"
    return first + f" Circle area = number of studies. Ordered by {by}. Base: 27,897 single-country studies."


def standalone(counts, mode, per, path, order="lmic"):
    fig = plt.figure(figsize=(13, 13.6), facecolor=BG)
    gs = fig.add_gridspec(3, 3, left=.03, right=.97, top=.88, bottom=.06, hspace=.28)
    circles(fig, [gs[i, j] for i in range(3) for j in range(3)], counts, mode, per, order)
    fig.suptitle("Studies by main type of intervention, and the share set in low- and middle-income countries", x=.03, ha="left", y=.975,
                 fontsize=15.5, fontweight="bold", color=INK)
    fig.text(.03, .945, circles_note(mode, per, order), fontsize=10.5, color=MUTED, va="top", wrap=True)
    fig.text(.03, .02, INCOME_NOTE, fontsize=9, color=MUTED)
    fig.savefig(path, dpi=300, facecolor=BG)
    fig.savefig(path.replace('.png', '.pdf'), dpi=300, facecolor=BG)
    plt.close(fig)


def combined(counts, pts, path):
    fig = plt.figure(figsize=(22, 12.5), facecolor=BG)
    outer = fig.add_gridspec(1, 2, left=.02, right=.99, top=.83, bottom=.19, wspace=.06, width_ratios=[1.05, 1])
    ax = fig.add_subplot(outer[0])
    noise = [(x, y) for x, y, c, k in pts if c == -1 or not k]
    ax.scatter(*zip(*noise), s=2, color="#dddddd", lw=0, rasterized=True)
    for k in LABEL:
        xy = [(x, y) for x, y, c, kk in pts if c != -1 and kk == k]
        if xy:
            ax.scatter(*zip(*xy), s=4, color=COLOUR[k], alpha=.75, lw=0, rasterized=True)
    ax.set_aspect("equal"); ax.axis("off")
    fig.text(.02, .875, "A | What is studied: each dot is a study, placed near studies with similar abstracts", fontsize=13, color=INK)
    inner = outer[1].subgridspec(3, 3, hspace=.35)
    circles(fig, [inner[i, j] for i in range(3) for j in range(3)], counts, "fill", 20)
    fig.text(.535, .875, "B | Where it is studied: share of each intervention type in low- and middle-income settings",
             fontsize=13, color=INK)
    # One legend for both panels: the class colours, with their LMIC share.
    shares = {k: 100 * v[1] / sum(v) for k, v in counts.items()}
    handles = [Line2D([], [], marker="o", ls="", markersize=18, color=COLOUR[k],
                      label=f"{LABEL[k]} ({shares[k]:.0f}% L&MICs)") for k in sorted(LABEL, key=lambda k: LABEL[k])]
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(.02, .075), ncol=5, frameon=False, fontsize=13,
               title="Primary intervention", title_fontsize=14, alignment="left", handletextpad=.4, columnspacing=1.6,
               labelspacing=.9)
    fig.suptitle("Studies by main type of intervention, and the share set in low- and middle-income countries", x=.02, ha="left", y=.965,
                 fontsize=20, fontweight="bold", color=INK)
    fig.text(.02, .015, textwrap.fill("A: positions come from abstract wording (text embeddings, UMAP; frozen topic coordinates from the "
             "September run, filtered to the current studies), so studies group by topic, mainly disease area; the axes "
             "have no meaning. Grey: no topic cluster or no intervention label. 41,583 studies (27 have no coordinates). "
             "B: " + circles_note("fill", 20) + " " + INCOME_NOTE, 260), fontsize=9, color=MUTED)
    fig.savefig(path, dpi=300, facecolor=BG)
    fig.savefig(path.replace('.png', '.pdf'), dpi=300, facecolor=BG)
    plt.close(fig)


def main():
    os.makedirs(OUT, exist_ok=True)
    counts, pts = load()
    combined(counts, pts, os.path.join(OUT, "option1_map_plus_circles.png"))
    standalone(counts, "fill", 20, os.path.join(OUT, "option2_circles_fill.png"))
    standalone(counts, "scatter", 1, os.path.join(OUT, "option3_circles_scatter.png"))
    standalone(counts, "fill", 20, os.path.join(OUT, "option2b_circles_fill_by_size.png"), order="size")
    standalone(counts, "fill", 1, os.path.join(OUT, "option2c_circles_fill_by_size_one_dot_per_study.png"), order="size")
    for k, (h, l) in sorted(counts.items(), key=lambda kv: -kv[1][1] / sum(kv[1])):
        print(f"{LABEL[k]}: {h + l:,} studies, {100 * l / (h + l):.0f}% LMIC")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
