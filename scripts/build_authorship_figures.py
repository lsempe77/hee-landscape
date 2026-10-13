"""Rebuild the five author-location figures from the affiliation data.

Run: python scripts/build_authorship_figures.py
Requires matplotlib and pycountry. Reads data/raw/hee_affiliation_countries_v2.csv
(ISO2 affiliation countries per included study), data/raw/hee_geo_long_v2_1.csv
(study countries with WHO region and income at publication year) and
data/raw/hee_analysis_master_v2_1.csv (publication year). Author countries get
the World Bank group in force at publication (build_income_pubyear.group_at).

Writes *_v2.svg/.png next to the upstream originals, which stay untouched, and
points their gallery entries in docs/data/content.json at the new files.
"""
import collections
import csv
import json
import math
from pathlib import Path
try:
    from figure_style import BACKGROUND, INCOME_COLORS, LAVENDER, tidy_svg
    from build_income_pubyear import load_history, group_at
except ModuleNotFoundError:
    from scripts.figure_style import BACKGROUND, INCOME_COLORS, LAVENDER, tidy_svg
    from scripts.build_income_pubyear import load_history, group_at

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DATA = ROOT / "docs" / "data"
OUT = ROOT / "docs" / "figures"
GROUPS = ["Low income", "Lower middle income", "Upper middle income", "High income"]
COLOR = dict(zip(GROUPS, INCOME_COLORS))
REGION_SHORT = {"African Region": "Africa", "Region of the Americas": "Americas",
                "South-East Asia Region": "South-East Asia", "European Region": "Europe",
                "Eastern Mediterranean Region": "Eastern Mediterranean",
                "Western Pacific Region": "Western Pacific"}
MIN_REGION_N = 50
INK, MUTED, GRID = "#10243e", "#5a564d", "#e6e1d8"
SOURCE = "Source: 3ie (2026). Health Economic Evaluation (HEE) Evidence Map. https://3ieimpact.pages.dev/hee/"
ISO2_EXTRA = {"XK": "XKX"}  # Kosovo has no ISO 3166 code; the World Bank uses XKX.


def wilson(k, n, z=1.96):
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centre - half, centre + half


def load():
    import pycountry
    csv.field_size_limit(10 ** 9)
    aff = {}
    with (RAW / "hee_affiliation_countries_v2.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            codes = [c for c in r["affiliation_countries"].split(";") if c]
            iso3 = set()
            for c in codes:
                hit = pycountry.countries.get(alpha_2=c)
                if hit is None and c not in ISO2_EXTRA:
                    raise ValueError(f"Unknown affiliation country code {c!r} for {r['record_id']}")
                iso3.add(hit.alpha_3 if hit else ISO2_EXTRA[c])
            aff[r["record_id"]] = iso3
    year = {}
    with (RAW / "hee_analysis_master_v2_1.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["record_id"] in aff:
                year[r["record_id"]] = int(r["year"])
    if set(year) != set(aff):
        raise ValueError("Every study in the affiliation file needs a publication year in the master file.")
    places = collections.defaultdict(dict)
    with (RAW / "hee_geo_long_v2_1.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["record_id"] in aff and r["is_special"] == "FALSE" and r["iso3"] not in ("", "NA"):
                places[r["record_id"]][r["iso3"]] = r
    single = {k: next(iter(v.values())) for k, v in places.items() if len(v) == 1}
    return aff, year, single


def compute():
    aff, year, single = load()
    hist = load_history()
    inc = lambda iso, y: group_at(hist, iso, y)
    known = {k: v for k, v in aff.items() if v}
    # Single-country studies with at least one author location: the local-author base.
    base = []
    for rid, row in single.items():
        if not known.get(rid):
            continue
        g = row["income_group_pubyear"]
        base.append({"rid": rid, "iso3": row["iso3"], "income": g if g in GROUPS else None,
                     "region": REGION_SHORT.get(row["who_region"]), "local": row["iso3"] in known[rid]})
    # Co-author mix for studies with a local author (Panel B).
    mix = collections.defaultdict(collections.Counter)
    unclassified_foreign = 0
    for b in base:
        if not (b["local"] and b["income"]):
            continue
        foreign = known[b["rid"]] - {b["iso3"]}
        groups = {inc(c, year[b["rid"]]) for c in foreign}
        unclassified_foreign += None in groups
        groups.discard(None)
        if not groups:
            kind = "local"
        elif groups == {"High income"}:
            kind = "hic"
        elif "High income" in groups:
            kind = "mixed"
        else:
            kind = "lmic"
        mix[b["income"]][kind] += 1
    # Income groups of all author countries in every study (chord).
    team = {}
    unclassified_team = 0
    for rid, countries in known.items():
        groups = {inc(c, year[rid]) for c in countries}
        unclassified_team += None in groups
        groups.discard(None)
        if groups:
            team[rid] = groups
    return {"n_studies": len(aff), "n_known": len(known), "n_single": len(single),
            "n_single_known": len(base), "base": base, "mix": mix,
            "unclassified_foreign": unclassified_foreign, "team": team,
            "unclassified_team": unclassified_team}


def rates(base, key, levels, min_n=0):
    out = []
    for level in levels:
        rows = [b for b in base if b[key] == level]
        if len(rows) < min_n or not rows:
            continue
        k = sum(b["local"] for b in rows)
        lo, hi = wilson(k, len(rows))
        out.append({"label": level, "n": len(rows), "k": k, "p": k / len(rows), "lo": lo, "hi": hi})
    return out


def new_fig(w, h):
    import matplotlib.pyplot as plt
    return plt.figure(figsize=(w, h), facecolor=BACKGROUND)


def header(fig, title, subtitle):
    """Title and subtitle at fixed inch offsets from the top, whatever the figure height."""
    h = fig.get_figheight()
    fig.text(.025, 1 - .35 / h, title, fontsize=22, fontweight="bold", color=INK, va="top")
    fig.text(.025, 1 - .85 / h, subtitle, fontsize=14, color="#33475f", va="top", linespacing=1.45)


def footer(fig, note):
    import matplotlib.pyplot as plt
    h = fig.get_figheight()
    fig.text(.025, .6 / h, note, fontsize=12, color=MUTED, va="bottom", linespacing=1.5)
    fig.add_artist(plt.Line2D([.025, .975], [.48 / h, .48 / h], color=GRID, linewidth=1))
    fig.text(.025, .16 / h, SOURCE, fontsize=11.5, color=MUTED, va="bottom")


def tidy_axes(ax, keep=("bottom",)):
    ax.set_facecolor(BACKGROUND)
    for name, spine in ax.spines.items():
        spine.set_visible(name in keep)
        spine.set_color("#c9c2b4")


def save(fig, stem):
    import matplotlib.pyplot as plt
    svg = OUT / f"{stem}.svg"
    fig.savefig(svg, facecolor=BACKGROUND)
    tidy_svg(svg)
    fig.savefig(OUT / f"{stem}.png", dpi=100, facecolor=BACKGROUND)
    plt.close(fig)
    return f"{stem}.svg"


def pct(x):
    return f"{x * 100:.0f}%"


def stacked(ax, rows, segments, label_min=.05):
    """Horizontal 100% bars; rows = [(label, {segment: count})], segments = [(key, name, colour)]."""
    for y, (label, counts) in enumerate(rows):
        total = sum(counts.values())
        left = 0
        for key, _, colour in segments:
            share = counts.get(key, 0) / total
            ax.barh(y, share, left=left, height=.72, color=colour, edgecolor=BACKGROUND, linewidth=1, zorder=3)
            if share >= label_min:
                ax.text(left + share / 2, y, pct(share), ha="center", va="center", color="white",
                        fontsize=13, fontweight="bold", zorder=4)
            left += share
    ax.set_yticks(range(len(rows)), [r[0] for r in rows], fontsize=14, color=INK)
    ax.set_xlim(0, 1)
    ax.set_xticks([0, .25, .5, .75, 1], ["0%", "25%", "50%", "75%", "100%"], fontsize=12.5, color=INK)
    ax.tick_params(length=0)
    tidy_axes(ax, keep=())


def legend(ax, segments):
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=c, label=n) for _, n, c in segments], loc="lower left",
              bbox_to_anchor=(0, 1.03), ncol=2 if len(segments) > 2 else len(segments), frameon=False,
              fontsize=13, handlelength=1.6, columnspacing=2, borderaxespad=0)


def fig_pattern(d):
    a_rows = []
    for g in GROUPS:
        rows = [b for b in d["base"] if b["income"] == g]
        a_rows.append((g, {"yes": sum(b["local"] for b in rows), "no": sum(not b["local"] for b in rows)}))
    low = dict(a_rows)["Low income"]
    low_none = low["no"] / (low["yes"] + low["no"])
    seg_a = [("no", "No local author", COLOR["Low income"]), ("yes", "With a local author", COLOR["High income"])]
    seg_b = [("lmic", "Other authors all from low- and middle-income countries", COLOR["Low income"]),
             ("mixed", "Other authors from mixed income groups", LAVENDER),
             ("hic", "Other authors all from high-income countries", COLOR["High income"]),
             ("local", "Local authors only", COLOR["Upper middle income"])]
    b_rows = [(g, d["mix"][g]) for g in GROUPS]
    low_hic = d["mix"]["Low income"]["hic"] / sum(d["mix"]["Low income"].values())
    title = "Studies about low-income countries are least likely to include a local author"
    fig = new_fig(18, 16)
    header(fig, title, "Studies of one country, by the country's income group when the study was published.")
    fig.text(.025, .885, f"A. With and without an author based in the country studied. {pct(low_none)} of studies "
             "about low-income countries have no author based there.", fontsize=15, color=INK, fontweight="bold",
             va="top")
    ax = fig.add_axes([.17, .6, .79, .22])
    stacked(ax, a_rows, seg_a)
    legend(ax, seg_a)
    fig.text(.025, .51, f"B. Studies with a local author: where the other authors are based. In {pct(low_hic)} of "
             "these studies about low-income\ncountries, every other author is based in a high-income country.",
             fontsize=15, color=INK, fontweight="bold", va="top", linespacing=1.4)
    bx = fig.add_axes([.17, .1, .79, .28])
    stacked(bx, b_rows, seg_b)
    legend(bx, seg_b[::-1])
    footer(fig, "'Local' = at least one author based in the country studied.")
    n_a = sum(sum(c.values()) for _, c in a_rows)
    n_b = sum(sum(m.values()) for m in d["mix"].values())
    caption = (f"Panel A: {n_a:,} studies about a single country with at least one known author location and an "
               f"income group at publication (of {d['n_single']:,} single-country studies). Panel B: the {n_b:,} of "
               "these with a local author, by the income groups of the other authors' countries in the year of "
               f"publication. {d['unclassified_foreign']} studies had a co-author country without a World Bank group; "
               "those countries are left out of the mix. Author locations come from institutional affiliations; study "
               "countries come from the study text, so a study cannot count as local through its affiliations alone.")
    return save(fig, "fig_authorship_pattern_v2"), title, caption


def dot_rows(ax, rows, y0):
    for i, r in enumerate(rows):
        y = y0 - i
        colour = COLOR.get(r["label"], COLOR["High income"])
        ax.plot([r["lo"], r["hi"]], [y, y], color=colour, linewidth=2.6, solid_capstyle="round", zorder=3)
        ax.scatter(r["p"], y, s=150, color=colour, edgecolors="white", linewidths=1.2, zorder=4)
        ax.text(r["p"], y + .3, pct(r["p"]), ha="center", va="bottom", fontsize=13, fontweight="bold", color=INK)
    return [(y0 - i, r["label"]) for i, r in enumerate(rows)]


def pct_axis(ax, rows, label):
    lo = math.floor(min(r["lo"] for r in rows) * 10) / 10
    xt = [x / 10 for x in range(int(round(lo * 10)), 11)]
    ax.set_xlim(lo, 1.0)
    ax.set_xticks(xt, [pct(x) for x in xt], fontsize=12.5, color=INK)
    for x in xt:
        ax.axvline(x, color=GRID, linewidth=.7, zorder=0)
    ax.set_xlabel(label, fontsize=14, color=INK, labelpad=8)
    ax.tick_params(axis="y", length=0)


def fig_forest(d):
    regions = sorted(rates(d["base"], "region", REGION_SHORT.values(), MIN_REGION_N), key=lambda r: -r["p"])
    incomes = rates(d["base"], "income", GROUPS[::-1])
    k = sum(b["local"] for b in d["base"])
    n = len(d["base"])
    low_r, high_r = regions[-1], regions[0]
    title = f"Most studies about a country include an author based there; least often in {low_r['label']}"
    fig = new_fig(18, 13)
    header(fig, title, f"Studies of one country where author locations are known, 2010–2026. {low_r['label']} is "
           f"lowest at {low_r['p'] * 100:.1f}%; {high_r['label']} highest at {high_r['p'] * 100:.1f}%.\n"
           f"Dashed line: all these studies ({k / n * 100:.1f}%).")
    ax = fig.add_axes([.2, .13, .7, .68])
    tidy_axes(ax)
    gap_y = -len(regions) - .8
    ticks = dot_rows(ax, regions, 0) + dot_rows(ax, incomes, gap_y)
    ax.axvline(k / n, color="#7d776c", linewidth=1.3, linestyle=(0, (4, 3)), zorder=1)
    ax.set_yticks([t[0] for t in ticks], [t[1] for t in ticks], fontsize=14, color=INK)
    pct_axis(ax, regions + incomes, "Studies with an author based in the country studied")
    ax.set_ylim(ticks[-1][0] - .7, .9)
    for text, y in (("WHO region", -(len(regions) - 1) / 2), ("Income group", gap_y - (len(incomes) - 1) / 2)):
        ax.text(1.015, y, text, transform=ax.get_yaxis_transform(), rotation=270, va="center", ha="left",
                fontsize=14, fontweight="bold", color=INK)
    footer(fig, "Lines show the 95% uncertainty range. Income group is the country's group when the study was published.")
    caption = (f"Base: {n:,} studies about a single country with at least one known author location (of "
               f"{d['n_single']:,} single-country studies); 'local' = at least one author affiliation in the country "
               "studied. Regions are WHO regions (Taiwan and Hong Kong take the region of their UN sub-region); "
               f"regions with fewer than {MIN_REGION_N} such studies would be left out, and none are. Uncertainty "
               "ranges are 95% Wilson intervals. Income groups are the World Bank group in force at publication.")
    return save(fig, "fig_forest_v2"), title, caption


def fig_paper06(d):
    incomes = rates(d["base"], "income", GROUPS[::-1])
    share = 1 - incomes[-1]["p"]
    lead = "A third" if .3 <= share < .36 else pct(share)
    title = f"{lead} of studies about low-income countries have no author based there"
    fig = new_fig(18, 8.6)
    header(fig, title, "Studies of one country, by the country's income group when the study was published. "
           "The point is the observed share.")
    ax = fig.add_axes([.17, .22, .78, .54])
    tidy_axes(ax)
    ticks = dot_rows(ax, incomes, 0)
    ax.set_yticks([t[0] for t in ticks], [t[1] for t in ticks], fontsize=14, color=INK)
    pct_axis(ax, incomes, "Studies with an author based in the country studied")
    ax.set_ylim(-len(incomes) + .4, .9)
    footer(fig, f"Author locations known for {d['n_known'] / d['n_studies'] * 100:.0f}% of studies. "
           "Lines show the 95% uncertainty range.")
    caption = ("Share of single-country studies with at least one author based in the country studied, by income "
               "group at publication (point and 95% Wilson interval). n = " +
               ", ".join(f"{r['n']:,} {r['label'].lower()}" for r in incomes[::-1]) +
               f" studies. Author locations come from institutional affiliations and are known for "
               f"{d['n_known']:,} of {d['n_studies']:,} studies, 2010–2026.")
    return save(fig, "paper06_v2"), title, caption


def ribbon_path(a1, a2, b1, b2, r):
    """Closed chord ribbon from arc [a1, a2] to arc [b1, b2] (radians) on a circle of radius r."""
    import numpy as np
    from matplotlib.path import Path as MPath

    def arc(t0, t1):
        ts = np.linspace(t0, t1, max(8, int(abs(t1 - t0) * 60)))
        return [(r * math.cos(t), r * math.sin(t)) for t in ts]

    first, second = arc(a1, a2), arc(b1, b2)
    pts = first + [(0, 0), second[0]] + second[1:] + [(0, 0), first[0], first[0]]
    codes = ([MPath.MOVETO] + [MPath.LINETO] * (len(first) - 1) + [MPath.CURVE3] * 2 +
             [MPath.LINETO] * (len(second) - 1) + [MPath.CURVE3] * 2 + [MPath.CLOSEPOLY])
    return MPath(pts, codes)


def fig_chord(d):
    from matplotlib.patches import PathPatch, Wedge
    pairs, solo = collections.Counter(), collections.Counter()
    cross = with_hic = 0
    for gs in d["team"].values():
        if len(gs) == 1:
            solo[next(iter(gs))] += 1
            continue
        cross += 1
        with_hic += "High income" in gs
        for a in gs:
            for b in gs:
                if GROUPS.index(a) < GROUPS.index(b):
                    pairs[(a, b)] += 1
    order = ["High income", "Upper middle income", "Lower middle income", "Low income"]
    total = {g: sum(v for k, v in pairs.items() if g in k) for g in order}
    gap = math.radians(5)
    scale = (2 * math.pi - gap * len(order)) / sum(total.values())
    start, span, cursor = {}, {}, {}
    t = math.pi / 2  # Counter-clockwise from the top.
    for g in order:
        start[g], span[g], cursor[g] = t, total[g] * scale, t
        t += span[g] + gap
    seg = {}
    for g in order:
        # Partners furthest round the circle attach first, so ribbons do not cross themselves.
        for p in sorted((p for p in order if p != g), key=lambda p: -((order.index(p) - order.index(g)) % len(order))):
            w = pairs.get(tuple(sorted((g, p), key=GROUPS.index)), 0) * scale
            seg[(g, p)] = (cursor[g], cursor[g] + w)
            cursor[g] += w
    title = "High-income authors take part in most collaborations across income groups"
    fig = new_fig(16, 16)
    header(fig, title, "How authors from different country income groups work together. Each ribbon links two "
           f"income groups among a study's authors.\nMost studies stay within one group: {solo['High income']:,} "
           f"have only high-income-based authors; {solo['Low income']:,} only low-income-based authors.")
    ax = fig.add_axes([.08, .09, .84, .74])
    ax.set_aspect("equal")
    ax.axis("off")
    for (a, b), n in pairs.items():
        a1, a2 = seg[(a, b)]
        b1, b2 = seg[(b, a)]
        # The lower-income group of the pair colours the ribbon.
        ax.add_patch(PathPatch(ribbon_path(a1, a2, b1, b2, .97), facecolor=COLOR[a], alpha=.55,
                               edgecolor="none", zorder=2))
    for g in order:
        ax.add_patch(Wedge((0, 0), 1.08, math.degrees(start[g]), math.degrees(start[g] + span[g]),
                           width=.08, color=COLOR[g], zorder=3))
        mid = start[g] + span[g] / 2
        x, y = 1.15 * math.cos(mid), 1.15 * math.sin(mid)
        ax.text(x, y, f"{g}\n{total[g]:,} studies", ha="left" if x > .2 else "right" if x < -.2 else "center",
                va="bottom" if y > .9 else "top" if y < -.9 else "center", fontsize=15, fontweight="bold",
                color=INK, linespacing=1.3)
    ax.set_xlim(-1.75, 1.75)
    ax.set_ylim(-1.5, 1.5)
    footer(fig, f"{with_hic / cross * 100:.0f}% of the {cross:,} studies with authors in more than one income group "
           "include a high-income-based author.\nThe number at each group counts its links with other groups.")
    caption = (f"Base: {len(d['team']):,} of {d['n_studies']:,} studies with at least one author country that has "
               "a World Bank income group in the year of publication. Ribbons link pairs of income groups among a "
               "study's author countries; a study with authors in three groups adds a ribbon for each pair. "
               f"{d['unclassified_team']} studies had an author country without an income group; that country is "
               "left out. Author locations come from institutional affiliations.")
    return save(fig, "fig_collab_chord_v2"), title, caption


def fig_regions(d):
    regions = sorted(rates(d["base"], "region", REGION_SHORT.values(), MIN_REGION_N), key=lambda r: r["p"])
    low_r, high_r = regions[0], regions[-1]
    title = f"Studies about countries in {low_r['label']} are least likely to include a local author"
    fig = new_fig(18, 9.5)
    header(fig, title, "Share of studies of one country that include at least one author based there, by WHO region.")
    ax = fig.add_axes([.2, .19, .74, .62])
    tidy_axes(ax)
    bars = ax.barh(range(len(regions)), [r["p"] for r in regions], height=.7, color=COLOR["High income"], zorder=3)
    for bar, r in zip(bars, regions):
        ax.text(r["p"] + .008, bar.get_y() + bar.get_height() / 2, f"{r['p'] * 100:.1f}%  ({r['n']:,} studies)",
                va="center", fontsize=13, color=INK)
    ax.set_yticks(range(len(regions)), [r["label"] for r in regions], fontsize=14, color=INK)
    ax.set_xlim(0, 1.15)
    ax.set_xticks([0, .25, .5, .75, 1], ["0%", "25%", "50%", "75%", "100%"], fontsize=12.5, color=INK)
    for x in (.25, .5, .75, 1):
        ax.axvline(x, color=GRID, linewidth=.7, zorder=0)
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel("Share of the region's studies with a local author", fontsize=14, color=INK, labelpad=8)
    footer(fig, "'Local' = at least one author based in the country studied.")
    caption = (f"Share of each WHO region's single-country studies with at least one author based in the country "
               f"studied. {low_r['label']} is lowest at {low_r['p'] * 100:.1f}%, {high_r['label']} highest at "
               f"{high_r['p'] * 100:.1f}%. Base: {len(d['base']):,} single-country studies with known author "
               "locations. Taiwan and Hong Kong take the WHO region of their UN sub-region.")
    return save(fig, "fig_map_authorship_v2"), title, caption


# Upstream file each new figure replaces in the gallery.
BUILDERS = {"fig_authorship_pattern.webp": fig_pattern, "fig_forest.webp": fig_forest, "paper06.webp": fig_paper06,
            "fig_collab_chord.webp": fig_chord, "fig_map_authorship.webp": fig_regions}


def main():
    import matplotlib
    matplotlib.use("Agg")
    d = compute()
    content_path = DATA / "content.json"
    content = json.loads(content_path.read_text(encoding="utf-8"))
    entries = {f["file"]: f for g in content["gallery"] for f in g["figs"]}
    for old, build in BUILDERS.items():
        entry = entries.get(old) or entries.get(old.replace(".webp", "_v2.svg"))
        if entry is None:
            raise SystemExit(f"No gallery entry for {old} in content.json.")
        file, title, caption = build(d)
        entry.update(file=file, title=title, caption=caption)
        print(f"{old} -> {file}: {title}")
    content_path.write_text(json.dumps(content, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


if __name__ == "__main__":
    main()
