"""Redraw the income-stratified gallery figures with income at publication year.

Five figures first drawn by the upstream build change their headline numbers
when each study's income group is the one in force on 1 January of its
publication year (build_income_pubyear.py). This script redraws them as new
versioned files next to the originals, which are kept:

  fig_equity_time.webp      -> fig_equity_time_pubyear.webp
  fig_metric.webp           -> fig_metric_pubyear.webp
  fig_intervention_mix.webp -> fig_intervention_mix_pubyear.webp
  paper05.webp              -> paper05_pubyear.webp
  fig_theme_rank.webp       -> fig_theme_rank_pubyear.webp

The numbers come from income_pubyear_figure_data.py, whose `current` coding
reproduces the published figures (checked when this was built). Open access
and the disease circular move by under 1.5 points and are not redrawn; paper04
could not be reproduced from the team export and is left to the upstream build.
The site swaps them in from docs/data/figure_updates.json (old file -> new file and caption).

Usage:
    python scripts/build_income_pubyear_figures.py [--raw data/raw]
"""
import argparse
import io
import json
import os
import sys
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import income_pubyear_figure_data as fd  # noqa: E402

ROOT = fd.ROOT
OUT = os.path.join(ROOT, "docs", "figures")
# Read by docs/app.js: old file -> redrawn file and its caption.
CAPTIONS = os.path.join(ROOT, "docs", "data", "figure_updates.json")
COL = fd.CODINGS["pubyear"]
BG = "#F7F4EE"
INK = "#1d1d1d"
MUTED = "#5e5a53"
GRID = "#e6e0d6"
ORANGE = "#E8693A"
BLUE = "#2E78D2"
GREYLINE = "#c3bdb3"
RED = "#D24A12"
TITLE_FONT = "Franklin Gothic Heavy"
BODY_FONT = "Franklin Gothic Book"
RULE = "Income group: the World Bank group the country studied was in when the study was published."

plt.rcParams.update({"font.family": BODY_FONT, "font.size": 11, "text.color": INK, "axes.edgecolor": GRID,
                     "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED,
                     "svg.fonttype": "path"})


def pct(x, d=0):
    return f"{100 * x:.{d}f}%"


def header(fig, title, lede, bold, top=.965, width=100):
    """Title (shrunk to fit), then a wrapped lede whose last sentence is bold."""
    t = fig.text(.06, top, title.upper(), fontsize=20, family=TITLE_FONT, va="top")
    fig.canvas.draw()
    while t.get_window_extent().transformed(fig.transFigure.inverted()).x1 > .97:
        t.set_fontsize(t.get_fontsize() - .5)
        fig.canvas.draw()
    y = top - .29 / fig.get_figheight()
    words = [(w, False) for w in lede.split()] + [(w, True) for w in bold.split()]
    line, n = [], 0
    lines = []
    for w, b in words:
        if n + len(w) > width and line:
            lines.append(line)
            line, n = [], 0
        line.append((w, b))
        n += len(w) + 1
    lines.append(line)
    for ln in lines:
        x = .06
        # Runs of the same weight on the line.
        runs = []
        for w, b in ln:
            if runs and runs[-1][1] == b:
                runs[-1][0].append(w)
            else:
                runs.append(([w], b))
        for ws, b in runs:
            t = fig.text(x, y, " ".join(ws) + " ", fontsize=12, va="top",
                         color="#4a463f" if b else MUTED, family="Franklin Gothic Demi" if b else BODY_FONT)
            fig.canvas.draw()
            x = t.get_window_extent().transformed(fig.transFigure.inverted()).x1
        y -= .2 / fig.get_figheight()
    return y


def footer(fig, text, y=.025, width=150):
    fig.text(.06, y, textwrap.fill(text, width), fontsize=9.5, color="#8a857c", va="bottom", linespacing=1.5)


def style(ax):
    ax.set_facecolor(BG)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.grid(axis="y", color=GRID, lw=.8)
    ax.tick_params(length=0, labelsize=11)


def save(fig, name):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, facecolor=BG)
    plt.close(fig)
    buf.seek(0)
    path = os.path.join(OUT, name)
    Image.open(buf).convert("RGB").save(path, "WEBP", quality=90, method=6)
    print("wrote", path)


def equity_time(rows):
    data, n = fd.equity_time(rows, COL)
    years = sorted(data)
    vals = [data[y] for y in years]
    fig = plt.figure(figsize=(9, 5.75))
    header(fig, "Studies of lower-income countries are growing but lag their health needs",
           "Share of each year's studies of a single country that are about low- and middle-income countries.",
           f"It rose from {pct(vals[0])} in {years[0]} to {pct(vals[-1])} in {years[-1]}, still far below the 83% "
           "of the world's disease burden those countries carry (dashed line).")
    ax = fig.add_axes([.09, .19, .88, .55])
    style(ax)
    ax.grid(axis="x", color=GRID, lw=.6)
    ax.fill_between(years, vals, .83, color="#f2ddd0", alpha=.55, lw=0)
    ax.axhline(.83, color=MUTED, ls=(0, (2, 2)), lw=1)
    ax.text(years[0], .80, "low- and middle-income countries' share of the world's disease burden: 83%", fontsize=10,
            color="#8a857c", va="top")
    ax.plot(years, vals, color=ORANGE, lw=3.2, marker="o", ms=5.5)
    ax.text(years[-1] + .25, vals[-1], pct(vals[-1]), color="#c0442a", fontsize=11, fontweight="bold", va="center")
    ax.set_ylim(0, 1)
    ax.set_xlim(years[0] - .8, years[-1] + 2)
    ax.set_yticks([0, .25, .5, .75, 1], ["0%", "25%", "50%", "75%", "100%"])
    ax.set_xticks(years[::2])
    ax.set_ylabel("Share about low- and middle-income countries", fontsize=11)
    footer(fig, f"Studies of a single country with a known income group, by year of publication ({n:,} studies); "
                f"2026 is incomplete and left out. {RULE} Disease burden: healthy years lost to illness and early "
                "death (DALYs), Global Burden of Disease 2023. The shaded band is the gap to that share.", width=135)
    save(fig, "fig_equity_time_pubyear.webp")
    return {"caption": f"Share of each year's single-country studies about low- and middle-income countries (LMICs): "
                       f"{pct(vals[0])} in {years[0]} → {pct(vals[-1])} in {years[-1]}, against the 83% of global disease "
                       "burden (GBD 2023 all-cause DALYs) those countries carry (dashed line). Studies "
                       f"naming a single country with a known income group ({n:,}); 2026 is partial and left out. Income "
                       "group: the World Bank group of the country studied, as classified on 1 January of the publication year (World Bank "
                       "historical classifications)."}


def metric(rows):
    m = fd.metric(rows, COL)
    labels = list(m)
    hi, lo = m["High income"], m["Low income"]
    fig = plt.figure(figsize=(9, 5.2))
    header(fig, "Studies in richer and poorer countries measure health gains differently",
           "Share of studies reporting each measure. A QALY is a year of life in full health; a DALY is a year of "
           "healthy life lost to illness or early death.",
           f"High-income studies mostly report QALYs ({pct(hi[0])}) and almost never DALYs ({pct(hi[1])}); "
           f"low-income studies do the reverse ({pct(lo[1])} DALYs, {pct(lo[0])} QALYs).")
    ax = fig.add_axes([.21, .1, .74, .62])
    ax.set_facecolor(BG)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xticks([])
    h = .36
    for i, k in enumerate(labels):
        y = -i
        q, d = m[k]
        ax.barh(y + h / 2 + .02, q, h, color=BLUE)
        ax.barh(y - h / 2 - .02, d, h, color=ORANGE)
        ax.text(q + .006, y + h / 2 + .02, pct(q), va="center", color=BLUE, fontweight="bold", fontsize=11)
        ax.text(d + .006, y - h / 2 - .02, pct(d), va="center", color=ORANGE, fontweight="bold", fontsize=11)
    ax.set_yticks([-i for i in range(len(labels))], labels, fontsize=11.5)
    ax.tick_params(length=0)
    ax.set_xlim(0, .62)
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=ORANGE), plt.Rectangle((0, 0), 1, 1, color=BLUE)],
              labels=["Reports a DALY", "Reports a QALY"], loc="lower center", bbox_to_anchor=(.5, 1.0), ncol=2,
              frameon=False, fontsize=11)
    al = m["All studies"]
    n_single = len(fd.single(rows, COL))
    footer(fig, f"Of all {len(rows):,} studies, {pct(al[0], 1)} report a QALY and {pct(al[1], 1)} a DALY. Income rows: "
                f"the {n_single:,} single-country studies with a known income group. A study may report "
                f"neither measure, one or both. {RULE}")
    save(fig, "fig_metric_pubyear_v2.webp")
    return {"caption": f"Share of eligible studies reporting each comparable metric. The metric flips with income: "
                       f"high-income research reports QALYs ({pct(hi[0])}) and almost no DALYs ({pct(hi[1])}); "
                       f"low-income research does the reverse ({pct(lo[1])} DALYs, {pct(lo[0])} QALYs) — so rich and poor "
                       f"settings are measured in different units. Of all {len(rows):,} eligible studies, {pct(al[0], 1)} report a QALY "
                       f"and {pct(al[1], 1)} a DALY. Base: {len(rows):,} eligible studies (income shown "
                       "for single-country studies, by the World Bank group of the country studied on 1 January of the publication year); "
                       "a study may report neither, one, or both."}


def intervention_mix(rows):
    mix, n = fd.intervention_mix(rows, COL)
    order = list(reversed(fd.GROUPS))  # High -> Low
    ph = [mix[g]["pharma"] for g in order]
    cm = [mix[g]["care_model_organisational"] for g in order]
    va = [mix[g]["vaccine"] for g in order]
    su = [mix[g]["surgical_procedural"] for g in order]
    de = [mix[g]["device_or_supply"] for g in order]
    if round(100 * cm[3]) == round(100 * ph[3]):
        lead = f"level with studies of how care is organised ({pct(cm[3])})"
    elif cm[3] > ph[3]:
        lead = f"overtaken by studies of how care is organised ({pct(cm[3])})"
    else:
        lead = f"just ahead of studies of how care is organised ({pct(cm[3])})"
    fig = plt.figure(figsize=(9, 6))
    header(fig, "What gets evaluated changes with country income",
           "Share of each income group's studies, by the main type of health care evaluated.",
           f"Medicines peak in upper-middle-income countries ({pct(ph[1])}) and fall to {pct(ph[3])} in low-income "
           f"countries, {lead}. Vaccines rise from {pct(va[0])} to {pct(va[3])} as income falls, while surgery and "
           "devices fall.")
    ax = fig.add_axes([.07, .2, .66, .48])
    style(ax)
    x = range(4)
    ends = []
    for k, label in fd.INTERVENTIONS.items():
        v = [mix[g][k] for g in order]
        hl = {"pharma": BLUE, "care_model_organisational": ORANGE}.get(k)
        ax.plot(x, v, color=hl or GREYLINE, lw=3.2 if hl else 1.4, marker="o", ms=7 if hl else 4,
                mfc=hl or "#a8a299", mec=hl or "#a8a299", zorder=3 if hl else 2)
        ends.append((v[3], label, hl))
    # Spread the end labels so they do not overlap.
    ends.sort(key=lambda e: -e[0])
    ys, last = [], None
    for v, *_ in ends:
        y = v if last is None else min(v, last - .028)
        ys.append(y)
        last = y
    lift = max(0, -.035 - ys[-1])
    ys = [y + lift for y in ys]
    for (v, label, hl), y in zip(ends, ys):
        ax.annotate(label, (3, v), (3.12, y), va="center", fontsize=10.5, fontweight="bold",
                    color=hl or "#8f897f", annotation_clip=False,
                    arrowprops=dict(arrowstyle="-", color="#8f897f", lw=.6, shrinkA=0, shrinkB=3))
    ax.text(1, ph[1] + .03, f"medicines peak at {pct(ph[1])} in upper-middle income", ha="center", color=BLUE, fontsize=10.5)
    ax.set_xticks(list(x), order, fontsize=11.5)
    ax.set_xlim(-.3, 3.3)
    ax.set_ylim(-.05, .5)
    ax.set_yticks([0, .1, .2, .3, .4, .5], ["0%", "10%", "20%", "30%", "40%", "50%"])
    footer(fig, f"Studies of a single country with a known income group ({n:,}). Main type of health care only, "
                "assigned by a large language model from each abstract and checked against keyword and topic "
                f"groupings. {RULE}")
    save(fig, "fig_intervention_mix_pubyear.webp")
    low = ("care-model and organisational studies " + f"({pct(cm[3], 1)}) narrowly become the most common class"
           if cm[3] > ph[3] else f"they stay narrowly ahead of care-model and organisational studies ({pct(cm[3], 1)})")
    return {"caption": f"Share of each income group's eligible single-country studies whose primary intervention class is "
                       f"the given type (the optional secondary class is not folded in). Pharmaceuticals peak in "
                       f"upper-middle-income settings ({pct(ph[1], 1)}) and fall to {pct(ph[3], 1)} at low income, where "
                       f"{low}; vaccines rise steadily with lower income ({pct(va[0], 1)} → {pct(va[3], 1)}) while surgery "
                       f"({pct(su[0], 1)} → {pct(su[3], 1)}) and devices ({pct(de[0], 1)} → {pct(de[3], 1)}) fall. Base: "
                       f"{n:,} eligible single-country studies whose country studied had a World Bank income group on 1 January "
                       "of the publication year. Intervention classes were assigned by a large language model from each "
                       "abstract (one pass), checked against a keyword list, the topic clusters and a second model; "
                       "they have not been checked by people."}


def paper05(rows, geo_groups):
    share, n = fd.paper05(rows, geo_groups, "pubyear")
    groups = fd.GROUPS
    # Rows from most low-income-concentrated to most high-income-concentrated,
    # by the ratio of the low-income to the high-income share.
    # Same row order as the published heatmap, so the two versions compare line by line.
    areas = ["Infectious", "Maternal & neonatal", "Other NCD", "Sense organ", "Injuries", "Mental & substance use",
             "Chronic respiratory", "Musculoskeletal", "Neurological", "Skin", "Metabolic & nutritional",
             "Digestive", "Cardiovascular", "Neoplasms"]
    assert set(areas) == set(share), set(share) ^ set(areas)
    fig = plt.figure(figsize=(9, 10))
    fig.text(.02, .975, "Which diseases are studied differs by country income", fontsize=19, fontweight="bold",
             family="Arial", va="top")
    fig.text(.02, .94, "% of each income group's studies that cover each disease area", fontsize=12.5,
             family="Arial", color=MUTED, va="top")
    ax = fig.add_axes([.3, .15, .61, .68])
    cmap = LinearSegmentedColormap.from_list("b", ["#d6e6fb", "#9cc3f0", "#3d8be0", "#0b3a73"])
    grid = [[100 * share[a][g] for g in groups] for a in areas]
    im = ax.imshow(grid, cmap=cmap, vmin=0, vmax=80, aspect="auto")
    for i, row in enumerate(grid):
        for j, v in enumerate(row):
            ax.text(j, i, f"{round(v)}", ha="center", va="center", fontsize=12.5, family="Arial",
                    color="white" if v >= 45 else INK)
    ax.set_xticks(range(4), ["Low income", "Lower\nmiddle\nincome", "Upper\nmiddle\nincome", "High\nincome"],
                  fontsize=12, family="Arial", fontweight="bold", color="#4a463f")
    ax.xaxis.tick_top()
    shown = {"Neoplasms": "Cancers (neoplasms)", "Other NCD": "Other non-communicable", "Sense organ": "Eye and ear"}
    ax.set_yticks(range(len(areas)), [shown.get(a, a) for a in areas], fontsize=12.5, family="Arial", color="#4a463f")
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xticks([x + .5 for x in range(3)], minor=True)
    ax.set_yticks([y + .5 for y in range(len(areas) - 1)], minor=True)
    ax.grid(which="minor", color=BG, lw=4)
    ax.tick_params(which="minor", length=0)
    cax = fig.add_axes([.935, .45, .015, .1])
    cb = fig.colorbar(im, cax=cax, ticks=[0, 20, 40, 60, 80])
    cb.outline.set_visible(False)
    cb.ax.tick_params(length=0, labelsize=11)
    footer(fig, "A study can cover several disease areas, so columns add up to more than 100%. A study about several "
                "countries counts in each income group it names. Studies with a disease area per group: low "
                f"{n['Low income']:,}, lower-middle {n['Lower middle income']:,}, upper-middle "
                f"{n['Upper middle income']:,}, high {n['High income']:,}. {RULE}", y=.015, width=135)
    save(fig, "paper05_pubyear.webp")
    inf = share["Infectious"]
    return {"caption": "Percentage of each income group's disease-coded "
                       "studies that name each disease area, across the 14 harmonised groups (maternal & "
                       "neonatal includes the MeSH pregnancy-complications branch C12.050.703; mental & substance use is "
                       "MeSH F03). Rows run from areas most concentrated in low-income research (top) to high-income "
                       f"research (bottom): infectious disease dominates lower-income groups ({pct(inf['Low income'])} of "
                       f"low-income and {pct(inf['Lower middle income'])} of lower-middle-income studies), neoplasms and "
                       "cardiovascular disease the high-income group. A study naming several areas appears in each, so "
                       "columns sum above 100%. Income group: the World Bank group of the country studied, as classified on "
                       "1 January of the publication year."}


# Plain names for topics, by cluster number (from each topic's keywords in
# topic_labels.csv); other topics fall back to their first keyword.
TOPIC_NAMES = {
    "11": "Dementia", "57": "Cancer medicines", "25": "Life support and heart pumps", "32": "Alcohol and opioids",
    "58": "Knee replacement", "40": "Urinary incontinence", "43": "Aortic aneurysm", "66": "Hospital-based trials",
    "4": "Heart valve replacement", "59": "Heart failure and cardiac rehab", "47": "Spinal surgery",
    "39": "Crohn's disease and colitis", "33": "Depression", "10": "Cancer immunotherapy", "53": "Back pain",
    "17": "Malaria and dengue", "5": "Tuberculosis", "23": "Maternal and newborn health", "8": "HIV",
    "64": "Clinical nutrition", "31": "Stomach cancer prevention", "45": "Lung cancer", "41": "Kidney stones",
    "49": "Gallbladder surgery", "7": "HPV vaccination", "27": "COVID-19", "65": "Heart failure medicines",
    "69": "High blood pressure", "16": "Pneumococcal vaccines", "54": "Breast cancer treatment",
}


def theme_rank(rows, labels):
    th, name, overall, n = fd.theme_rank(rows, labels, COL)
    name = {c: TOPIC_NAMES.get(c, v) for c, v in name.items()}
    hic = sorted(th, key=lambda c: th[c][0])[:15]
    lmic = sorted(th, key=lambda c: -th[c][0])[:15]
    lo_rng = (min(th[c][0] for c in lmic), max(th[c][0] for c in lmic))
    hi_rng = (min(th[c][0] for c in hic), max(th[c][0] for c in hic))
    overlap = set(hic) & set(lmic)
    fig = plt.figure(figsize=(9, 8.2))
    header(fig, "Research topics split sharply by country income",
           f"The research topics most and least focused on low- and middle-income countries (all topics: "
           f"{pct(overall)} of studies are about these countries).",
           f"In the 15 topics most about them, {pct(lo_rng[0])}–{pct(lo_rng[1])} of studies are about low- and "
           f"middle-income countries; in the 15 most about high-income countries, {pct(1 - hi_rng[1])}–"
           f"{pct(1 - hi_rng[0])} are about high-income countries.", width=105)
    for k, (cs, share_of, colour, ref, title) in enumerate([
            (hic, lambda c: 1 - th[c][0], "#bbb6ae", 1 - overall,
             "MOST ABOUT HIGH-INCOME COUNTRIES — % of the topic's studies about high-income countries"),
            (lmic, lambda c: th[c][0], RED, overall,
             "MOST ABOUT LOW- AND MIDDLE-INCOME COUNTRIES — % of the topic's studies about them")]):
        ax = fig.add_axes([.31, .5 - k * .34, .63, .27])
        ax.set_facecolor(BG)
        vals = [share_of(c) for c in cs]
        ax.barh(range(15), vals, color=colour, height=.72)
        for i, v in enumerate(vals):
            ax.text(v + .006, i, pct(v), va="center", fontsize=9.5, fontweight="bold")
        ax.set_yticks(range(15), [f"{name[c]}  ({th[c][1]:,})" for c in cs], fontsize=10)
        ax.invert_yaxis()
        ax.axvline(ref, color=MUTED, ls=(0, (2, 2)), lw=1)
        ax.set_xlim(0, 1)
        ax.set_xticks([])
        ax.tick_params(length=0)
        for s in ax.spines.values():
            s.set_visible(False)
        ax.set_title(title, loc="left", fontsize=11.5, family="Franklin Gothic Demi Cond", pad=6)
    fig.text(.57, .13, "Number of studies in brackets. Dashed line: all topics.", ha="center", fontsize=11, color=MUTED)
    footer(fig, f"Topics found by grouping studies with similar titles and abstracts ({len(th)} topics with at least 30 "
                f"studies). Studies of a single country with a known income group ({n:,}). {RULE}", width=140)
    save(fig, "fig_theme_rank_pubyear.webp")
    top_h, top_l = hic[0], lmic[0]
    return {"caption": f"The 15 most-LMIC and 15 most-high-income of {len(th)} research topics (found by clustering title-and-abstract embeddings) (all themes: {pct(overall)} "
                       f" LMIC). The high-income panel is shown first, plotted as each theme's high-income share "
                       f"({name[top_h].lower()} leads at {pct(1 - th[top_h][0])}); the LMIC panel as its LMIC share "
                       f"({name[top_l].lower()} leads at {pct(th[top_l][0])}): "
                       f"{pct(lo_rng[0])}–{pct(lo_rng[1])} LMIC vs {pct(hi_rng[0])}–{pct(hi_rng[1])} LMIC. n per theme = "
                       "single-country studies whose country studied had a World Bank income group on 1 January of the publication year."}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--raw", default=os.path.join(ROOT, "data", "raw"))
    args = ap.parse_args()
    rows, labels, geo_groups = fd.load(args.raw)
    captions = json.load(open(CAPTIONS, encoding="utf-8")) if os.path.exists(CAPTIONS) else {}
    income_captions = {
        "fig_equity_time.webp": {"file": "fig_equity_time_pubyear.webp", **equity_time(rows)},
        "fig_metric.webp": {"file": "fig_metric_pubyear_v2.webp", **metric(rows)},
        "fig_intervention_mix.webp": {"file": "fig_intervention_mix_pubyear.webp", **intervention_mix(rows)},
        "paper05.webp": {"file": "paper05_pubyear.webp", **paper05(rows, geo_groups)},
        "fig_theme_rank.webp": {"file": "fig_theme_rank_pubyear.webp", **theme_rank(rows, labels)},
    }
    for entry in income_captions.values():
        entry["caption"] += (" For 2026 publications only, missing FY2026 classifications use "
                             "FY2025 low income for Ethiopia and FY2021 upper-middle income for "
                             "Venezuela (FY2025 also unavailable); these are analysis exceptions.")
    captions.update(income_captions)
    with open(CAPTIONS, "w", encoding="utf-8", newline="\n") as f:
        json.dump(captions, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("wrote", CAPTIONS)


if __name__ == "__main__":
    main()
