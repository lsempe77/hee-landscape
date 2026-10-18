"""Overview figure for the manuscript: one panel per overview paragraph.

  A  What the studies are: all 41,610 studies by evaluation type (one 100% bar).
  B  Where they are: studies per 10 million people, one dot per country, by income group.
  C  Who funds them: top reported funders, studies of high-income vs low- and middle-income settings.
  D  Access and authorship: open access and local authorship, LMIC vs high-income settings.

Styled as a companion to the HFF/HEE overview figure (Inter, warm HEE palette, letter
panels) with different chart forms. Every number is computed from the current data and
printed, so the manuscript text can match. Not used by the site.

Data: docs/data (studies, geo, countries, dict) for A and B; the reconciled master
(data/raw/hee_analysis_master_v2_1.csv) for open access; funder names grouped as in the
site's funder treemap (build_wellcome_analysis_gbd_v2.parent_funder); local authorship as in
build_authorship_figures.py. LMIC/high-income settings: single-country studies, World Bank
group in force on 1 January of the publication year. B uses each country's current (July
2026) group, as in the site's per-capita figure.

Writes exports/overview_figure_<date>/overview_figure.png (300 dpi) and .pdf.
Usage: python scripts/build_overview_figure.py
"""
import collections
import csv
import datetime
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
DATA, RAW = os.path.join(ROOT, "docs", "data"), os.path.join(ROOT, "data", "raw")
OUT = os.path.join(ROOT, "exports", f"overview_figure_{datetime.date.today():%Y-%m-%d}")

plt.rcParams.update({"font.family": "Inter", "font.size": 10.5, "axes.edgecolor": "#c9c3b8",
                     "axes.labelcolor": "#4a463f", "xtick.color": "#4a463f", "ytick.color": "#4a463f"})
FS, MS = 1.0, 1.0  # font and marker scale; set per output size in main()
BG, INK, MUTED, GRID = "#ffffff", "#1d2433", "#6b665d", "#ece8e1"
WARM = ["#7a3416", "#b5532a", "#de8a5a", "#f2bf98", "#fae3d2"]  # dark -> light HEE oranges
LMIC_C, HIC_C, REVIEW_C = "#d9773f", "#6f86b6", "#c7c9cf"
GROUPS = ["Low income", "Lower middle income", "Upper middle income", "High income"]


def load_json(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def panel_label(ax, letter, title):
    ax.text(-.02, 1.13, letter, transform=ax.transAxes, fontsize=17 * FS, fontweight="bold", color=INK, va="bottom", ha="right")
    ax.text(.0, 1.13, title, transform=ax.transAxes, fontsize=13 * FS, fontweight="bold", color=INK, va="bottom")


def clean(ax, grid_axis=None):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    if grid_axis:
        ax.grid(axis=grid_axis, color=GRID, linestyle=(0, (4, 3)), linewidth=.8)
        ax.set_axisbelow(True)


# ---------------------------------------------------------------- data
def composition():
    st, lv = load_json("studies.json"), load_json("dict.json")["levels"]
    et = collections.Counter(lv["econ_eval_type"][x] for x in st["econ_eval_type"])
    rl = [lv["review_label"][x] for x in st["review_label"]]
    ets = [lv["econ_eval_type"][x] for x in st["econ_eval_type"]]
    both = sum(1 for r, t in zip(rl, ets) if r != "Not a review" and t != "Review (no evaluation type)")
    gs = [lv["geo_scope"][x] for x in st["geo_scope"]]
    ee = [i for i, t in enumerate(ets) if t != "Review (no evaluation type)"]
    named = sum(1 for i in ee if gs[i] in ("Single country", "Multi-country"))
    return {"n": len(ets), "types": et, "both": both, "ee": len(ee), "ee_named": named}


def per_capita():
    rows = []
    for c in load_json("countries.json"):
        if c["pop"]:
            rows.append({"iso3": c["iso3"], "country": c["country"], "income": c["income"], "studies": c["studies"],
                         "rate": 1e7 * c["studies"] / c["pop"]})
    med = {g: float(np.median([r["rate"] for r in rows if r["income"] == g])) for g in GROUPS}
    return rows, med


def funders():
    import build_wellcome_analysis_gbd_v2 as wv
    rows, *_ = wv.load_inputs(wv.ROOT / "data" / "raw")
    funded = [r for r in rows if r["named_funders"]]
    per = collections.defaultdict(lambda: {"all": set(), "hic": set(), "lmic": set()})
    for r in funded:
        for name in r["named_funders"]:
            p = wv.parent_funder(name)
            per[p]["all"].add(r["record_id"])
            if r["setting"] == 0:
                per[p]["hic"].add(r["record_id"])
            elif r["setting"] == 1:
                per[p]["lmic"].add(r["record_id"])
    top = sorted(per.items(), key=lambda kv: -len(kv[1]["all"]))[:7]
    return len(rows), len(funded), [(k, len(v["all"]), len(v["hic"]), len(v["lmic"])) for k, v in top]


def access_authorship():
    import build_authorship_figures as af
    d = af.compute()
    side = lambda g: "hic" if g == "High income" else ("lmic" if g in GROUPS else None)
    loc = {s: [b["local"] for b in d["base"] if side(b["income"]) == s] for s in ("lmic", "hic")}
    loc.update({g: [b["local"] for b in d["base"] if b["income"] == g] for g in GROUPS})
    oa = {"lmic": [], "hic": [], **{g: [] for g in GROUPS}}
    oa_alt = {"lic_lmc": [], "umc_hic": []}
    csv.field_size_limit(10 ** 9)
    with open(os.path.join(RAW, "hee_analysis_master_v2_1.csv"), encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r["is_eligible"] != "TRUE" or r["geo_scope"] != "single_country" or r["is_oa"] not in ("0", "1", "TRUE", "FALSE"):
                continue
            g = r["income_group_pubyear"]
            if g not in GROUPS:
                continue
            v = r["is_oa"] in ("1", "TRUE")
            oa[side(g)].append(v)
            oa[g].append(v)
            oa_alt["lic_lmc" if g in GROUPS[:2] else "umc_hic"].append(v)
    pct = lambda xs: (100 * sum(xs) / len(xs), len(xs))
    return ({k: pct(v) for k, v in oa.items()}, {k: pct(v) for k, v in loc.items()}, {k: pct(v) for k, v in oa_alt.items()})


# ---------------------------------------------------------------- panels
def panel_a(ax, c):
    order = [("Cost-utility", "CUA", WARM[0]), ("Cost-effectiveness", "CEA", WARM[1]), ("Cost-consequence", "CCA", WARM[2]),
             ("Cost-benefit", "CBA", WARM[3]), ("Review (no evaluation type)", "Review, no own evaluation", REVIEW_C)]
    left, n = 0, c["n"]
    for level, short, colour in order:
        v = c["types"][level]
        w = 100 * v / n
        ax.add_patch(FancyBboxPatch((left + .15, .32), w - .3, .36, boxstyle="round,pad=0,rounding_size=1.2",
                                    facecolor=colour, edgecolor="white", linewidth=1.5, mutation_aspect=.02))
        if colour != REVIEW_C and w > 9:  # big types: label inside, % of full evaluations
            ax.text(left + w / 2, .5, f"{short}\n{v:,}\n{100 * v / c['ee']:.1f}%", ha="center", va="center", fontsize=10.5 * FS,
                    color="white", fontweight="bold")
        else:  # thin segments: label below with a leader line, staggered so they never collide
            ty = .1 if colour != REVIEW_C else -.12
            ax.plot([left + w / 2] * 2, [.31, ty + .03], color=MUTED, lw=.8)
            share = f"{100 * v / c['ee']:.1f}% of full evaluations" if colour != REVIEW_C else f"{w:.1f}% of all studies"
            ax.text(left + w / 2 + .6, ty, f"{short}: {v:,} ({share})", ha="right", va="top", fontsize=9.5 * FS, color=INK)
        left += w
    ee_w = 100 * c["ee"] / n
    ax.annotate("", xy=(0.3, .82), xytext=(ee_w - .3, .82), arrowprops=dict(arrowstyle="|-|", color=INK, lw=1, mutation_scale=4))
    ax.text(ee_w / 2, .88, f"Full economic evaluations: {c['ee']:,} ({ee_w:.0f}%)\nincluding {c['both']:,} reviews that also "
            "report their own evaluation", ha="center", va="bottom", fontsize=10 * FS, color=INK, linespacing=1.2)
    ax.text(0, .2, "Type shares: % of full economic evaluations.", fontsize=9.5 * FS, color=MUTED, va="top")
    ax.text(0, -.34, f"{c['ee_named']:,} of the full evaluations ({100 * c['ee_named'] / c['ee']:.1f}%) name one or more countries.",
            fontsize=10 * FS, color=MUTED, va="top")
    ax.set_xlim(0, 100); ax.set_ylim(-.45, 1.05); ax.axis("off")


def panel_b(ax, rows, med):
    rng = np.random.default_rng(3)
    floor = .3  # countries with no study are drawn on this floor line
    colours = [WARM[3], WARM[2], WARM[1], WARM[0]]
    for i, g in enumerate(GROUPS):
        rs = [r for r in rows if r["income"] == g]
        x = i + rng.uniform(-.28, .28, len(rs))
        y = [max(r["rate"], floor) for r in rs]
        ax.scatter(x, y, s=[(18 + 2 * np.sqrt(r["studies"])) * MS for r in rs], color=colours[i], alpha=.85,
                   edgecolor="white", linewidth=.6, zorder=3)
        ax.plot([i - .36, i + .36], [med[g]] * 2, color=INK, lw=2, zorder=4)
        ax.text(i + .38, med[g], f"median\n{med[g]:.1f}", va="center", fontsize=9 * FS, color=INK, fontweight="bold", linespacing=1,
                bbox=dict(facecolor="white", edgecolor="none", pad=1.5, alpha=.85), zorder=5)
        for r, xx, yy in zip(rs, x, y):
            if r["iso3"] in ("USA", "GBR", "CHN") or r["studies"] == 0:
                lab = {"USA": "United States", "GBR": "United Kingdom", "CHN": "China"}.get(r["iso3"], r["country"] + " (0)")
                ax.annotate(lab, (xx, yy), xytext=(6, 4), textcoords="offset points", fontsize=8.5 * FS, color=MUTED)
    ax.set_yscale("log")
    ax.set_xticks(range(4), ["Low", "Lower\nmiddle", "Upper\nmiddle", "High"])
    ax.set_xlim(-.6, 3.9)
    ax.set_ylabel("Studies per 10 million people (log scale)")
    ax.set_xlabel("Income group (July 2026); dot size = number of studies")
    clean(ax, "y")


def panel_c(ax, n_all, n_funded, top):
    names = [t[0] for t in top][::-1]
    hic = np.array([t[2] for t in top][::-1]); lmic = np.array([t[3] for t in top][::-1])
    tot = [t[1] for t in top][::-1]
    y = np.arange(len(names))
    ax.barh(y, -hic, color=HIC_C, height=.62, zorder=3)
    ax.barh(y, lmic, color=LMIC_C, height=.62, zorder=3)
    for yy, h, l, t in zip(y, hic, lmic, tot):
        ax.text(-h - 25, yy, f"{h:,}", ha="right", va="center", fontsize=9 * FS, color=HIC_C, fontweight="bold")
        ax.text(l + 25, yy, f"{l:,}", ha="left", va="center", fontsize=9 * FS, color=LMIC_C, fontweight="bold")
    ax.set_yticks(y, [f"{n}\n{t:,} studies ({100 * t / n_funded:.0f}%)" for n, t in zip(names, tot)], fontsize=9.5 * FS)
    ax.axvline(0, color=INK, lw=.8)
    lim = max(hic.max(), lmic.max()) * 1.25
    ax.set_xlim(-lim, lim)
    ticks = [v for v in (-800, -400, 0, 400, 800) if abs(v) < lim]
    ax.set_xticks(ticks, [f"{abs(v):,}" for v in ticks])
    ax.text(-lim * .5, len(names) - .25, "High-income settings", ha="center", fontsize=10 * FS, color=HIC_C, fontweight="bold")
    ax.text(lim * .5, len(names) - .25, "Low- and middle-income settings", ha="center", fontsize=10 * FS, color=LMIC_C, fontweight="bold")
    ax.set_xlabel(f"Single-country studies naming the funder.\nLabels: all studies naming it (% of the {n_funded:,} that "
                  f"report a funder; {100 * n_funded / n_all:.0f}% of all studies)", fontsize=9 * FS)
    clean(ax, "x"); ax.spines["left"].set_visible(False); ax.tick_params(axis="y", length=0)


GROUP_C = {"Low income": WARM[0], "Lower middle income": WARM[1], "Upper middle income": WARM[2], "High income": HIC_C}


def panel_d(ax, oa, loc):
    """One row per measure, one dot per income group of the country studied."""
    rows = [("Open access", oa), ("At least one author based\nin the country studied", loc)]
    for i, (lab, d) in enumerate(rows[::-1]):
        vals = [d[g][0] for g in GROUPS]
        ax.plot([min(vals), max(vals)], [i, i], color="#e2ddd4", lw=6, solid_capstyle="round", zorder=2)
        for k, g in enumerate(GROUPS):
            v = d[g][0]
            ax.scatter([v], [i], s=240 * MS, color=GROUP_C[g], zorder=3, edgecolor="white", linewidth=1.5)
            up = k % 2 == 1  # alternate labels above and below so close values never overlap
            ax.text(v, i + (.2 if up else -.2), f"{v:.0f}%", ha="center", va="bottom" if up else "top",
                    fontsize=10.5 * FS, color=GROUP_C[g], fontweight="bold")
    ax.set_yticks(range(len(rows)), [r[0] for r in rows[::-1]])
    ax.set_ylim(-.7, len(rows) - .2)
    ax.set_xlim(55, 100)
    ax.set_xlabel("Share of single-country studies (%)")
    for g in GROUPS:
        ax.scatter([], [], s=90 * MS, color=GROUP_C[g], label=g.replace(" income", ""))
    ax.legend(loc="lower left", ncol=4, frameon=False, fontsize=9.5 * FS, handletextpad=.3, columnspacing=1.2,
              bbox_to_anchor=(0, 1.0))
    clean(ax, "x"); ax.spines["left"].set_visible(False); ax.tick_params(axis="y", length=0)


# Output sizes: (file stem, figure size in inches, font scale, marker scale).
SIZES = [("overview_figure", (17, 11.5), 1.0, 1.0),
         # Landscape page, normal 1-inch margins: fits US Letter (9.0 x 6.5 in) and A4 (9.7 x 6.3 in).
         ("overview_figure_word_landscape", (9, 6.1), .66, .3)]


def main():
    os.makedirs(OUT, exist_ok=True)
    comp = composition()
    rows, med = per_capita()
    n_all, n_funded, top = funders()
    oa, loc, oa_alt = access_authorship()
    for stem, size, fs, ms in SIZES:
        draw(stem, size, fs, ms, comp, rows, med, n_all, n_funded, top, oa, loc)
    report(comp, med, rows, n_all, n_funded, top, oa, loc, oa_alt)


def draw(stem, size, fs, ms, comp, rows, med, n_all, n_funded, top, oa, loc):
    global FS, MS
    FS, MS = fs, ms
    plt.rcParams["font.size"] = 10.5 * fs

    fig = plt.figure(figsize=size, facecolor=BG)
    gs = fig.add_gridspec(2, 2, left=.12, right=.98, top=.9, bottom=.14 if FS < 1 else .12, hspace=.62 if FS < 1 else .48,
                          wspace=.34, height_ratios=[1, 1.15])
    ax_a, ax_b = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1])
    ax_c, ax_d = fig.add_subplot(gs[1, 0]), fig.add_subplot(gs[1, 1])
    panel_a(ax_a, comp); panel_label(ax_a, "A", f"Studies by evaluation type (n = {comp['n']:,})")
    panel_b(ax_b, rows, med); panel_label(ax_b, "B", "Studies per 10 million people, by country")
    panel_c(ax_c, n_all, n_funded, top); panel_label(ax_c, "C", "Top reported funders, by study setting")
    panel_d(ax_d, oa, loc); panel_label(ax_d, "D", "Open access and local authorship, by income group")
    note = ("Settings in C and D: single-country studies, by the World Bank income group in force on 1 January of the "
             "publication year. Funders grouped as on the map (NIHR and US NIH include their programmes and institutes). "
             "Local author: an author affiliation in the country studied,\namong studies with known author locations. "
             "In B, the two countries with no study are drawn on the floor line.")
    import textwrap
    fig.text(.02, .012, textwrap.fill(note.replace("\n", " "), int(size[0] * 13.5 / FS)), fontsize=9 * FS, color=MUTED, va="bottom")
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(OUT, f"{stem}.{ext}"), dpi=300, facecolor=BG)
    plt.close(fig)


def report(comp, med, rows, n_all, n_funded, top, oa, loc, oa_alt):

    t = comp["types"]
    print(f"A: {comp['n']:,} studies; full evaluations {comp['ee']:,} ({100 * comp['ee'] / comp['n']:.1f}%), incl. {comp['both']} "
          f"reviews with own evaluation; named country {comp['ee_named']:,} ({100 * comp['ee_named'] / comp['ee']:.1f}%)")
    for k in ("Cost-utility", "Cost-effectiveness", "Cost-consequence", "Cost-benefit"):
        print(f"   {k}: {t[k]:,} = {100 * t[k] / comp['ee']:.1f}% of full evaluations")
    print("B: medians per 10M:", {g: round(v, 1) for g, v in med.items()},
          "| countries with 0 studies:", [r["country"] for r in rows if r["studies"] == 0])
    print(f"C: {n_funded:,} of {n_all:,} report a funder ({100 * n_funded / n_all:.1f}%)")
    for name, tot, h, l in top:
        print(f"   {name}: {tot:,} ({100 * tot / n_funded:.1f}% of funded) | HIC {h} LMIC {l}")
    print("D: open access", {k: (round(v[0], 1), v[1]) for k, v in oa.items()}, "| alt grouping",
          {k: (round(v[0], 1), v[1]) for k, v in oa_alt.items()})
    print("   local author", {k: (round(v[0], 1), v[1]) for k, v in loc.items()})
    print("   open access by group", {k: (round(v[0], 1), v[1]) for k, v in oa.items() if k in GROUPS})
    print("wrote", OUT)


if __name__ == "__main__":
    main()
