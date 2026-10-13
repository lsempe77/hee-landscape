"""Build the size-neutral evidence-gap scorecard (fig_funder_scorecard_v2).

Run: python scripts/build_funder_scorecard.py
Requires matplotlib. Replaces the upstream scorecard's absolute shortfall ranking,
which scales with country size, with each country's research share divided by
its disease-burden share. Also points the scorecard's gallery entry in
docs/data/content.json at the new figure.
"""
import csv
import json
import math
from pathlib import Path
try:
    from figure_style import BACKGROUND, INCOME_COLORS, tidy_svg
except ModuleNotFoundError:
    from scripts.figure_style import BACKGROUND, INCOME_COLORS, tidy_svg

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data"
OUT = ROOT / "docs" / "figures"
STEM = "fig_funder_scorecard_v2"
TITLE = "Where research coverage is low relative to disease burden"
GROUPS = ["Low income", "Lower middle income", "Upper middle income", "High income"]
TOP_N = 15
SITE_URL = "https://3ieimpact.pages.dev/hee/"
LABEL_N = 8  # Lowest-ratio countries considered for a scatter label; crowded ones are skipped.
SHORT = {"Democratic Republic of the Congo": "DR Congo", "Central African Republic": "CAR",
         "Republic of the Congo": "Rep. of the Congo"}


def load_rows():
    countries = json.loads((DATA / "countries.json").read_text(encoding="utf-8"))
    for c in countries:
        if c["income"] not in GROUPS or not isinstance(c["studies"], int) or c["studies"] < 0:
            raise ValueError(f"Invalid income or study count for {c['iso3']}")
    burdened = [dict(c) for c in countries if c["dalys"] and c["dalys"] > 0]
    studies = sum(c["studies"] for c in burdened)
    burden = sum(c["dalys"] for c in burdened)
    if not studies or not burden:
        raise ValueError("Positive study and burden totals are required.")
    for c in burdened:
        c["ratio"] = (c["studies"] / studies) / (c["dalys"] / burden)
        c["log2_ratio"] = math.log2(c["ratio"]) if c["ratio"] > 0 else None
    return burdened, studies


def multiple(log2):
    """Plain-language label for a log2 ratio, e.g. -4 -> '16× lower'."""
    if abs(log2) < 1e-9:
        return "Proportional"
    times = 2 ** abs(log2)
    return f"{times:.0f}× {'lower' if log2 < 0 else 'higher'}"


def main():
    burdened, studies = load_rows()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker
    from matplotlib.patches import Patch

    rows = [c for c in burdened if c["log2_ratio"] is not None]
    zero = sorted(c["country"] for c in burdened if c["log2_ratio"] is None)
    ranked = sorted(rows, key=lambda c: c["log2_ratio"])
    top = ranked[:TOP_N]
    color = dict(zip(GROUPS, INCOME_COLORS))
    ink, muted, grid = "#10243e", "#5a564d", "#e6e1d8"
    low = math.floor(min(c["log2_ratio"] for c in rows)) - .7
    high = math.ceil(max(c["log2_ratio"] for c in rows)) + .5
    ticks = [t for t in range(-6, 7, 2) if low <= t <= high]

    fig = plt.figure(figsize=(20, 11.8), facecolor=BACKGROUND)
    ax = fig.add_axes([.1, .17, .40, .6], facecolor=BACKGROUND)
    bx = fig.add_axes([.64, .17, .33, .6], facecolor=BACKGROUND)

    # Left: every country with at least one study; below the line = less research than burden share.
    ax.set_xscale("log")
    ax.axhspan(low, 0, color="#F3E6E1", alpha=.7, zorder=0)
    ax.axhline(0, color="#7d776c", linewidth=1.4, linestyle=(0, (5, 3)), zorder=1)
    for t in ticks:
        ax.axhline(t, color=grid, linewidth=.7, zorder=0)
    for g in GROUPS:
        pts = [c for c in rows if c["income"] == g]
        ax.scatter([c["dalys"] for c in pts], [c["log2_ratio"] for c in pts], s=70, color=color[g],
                   edgecolors="white", linewidths=.9, alpha=.92, zorder=3)
    placed = []
    for c in ranked[:LABEL_N]:
        spot = (math.log10(c["dalys"]), c["log2_ratio"])
        if any(abs(spot[0] - x) < .45 and abs(spot[1] - y) < .6 for x, y in placed):
            continue  # Skip a label that would collide with one already placed.
        placed.append(spot)
        dx = 9
        ax.annotate(SHORT.get(c["country"], c["country"]), (c["dalys"], c["log2_ratio"]),
                    xytext=(dx, -2), textcoords="offset points", ha="left" if dx > 0 else "right",
                    va="center", fontsize=11, fontweight="bold", color=ink, zorder=4)
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(
        lambda v, _: f"{v / 1e6:g}M" if v >= 1e6 else f"{v / 1e3:g}K"))
    ax.set_ylim(low, high)
    ax.set_yticks(ticks, [multiple(t) for t in ticks], fontsize=12.5, color=ink)
    ax.set_ylabel("Research share relative to burden share", fontsize=14, color=ink, labelpad=10)
    ax.set_xlabel("Disease burden (healthy years lost, DALYs, 2023, log scale)", fontsize=14, color=ink, labelpad=8)
    ax.tick_params(axis="x", labelsize=12.5, colors=ink)
    ax.tick_params(axis="y", length=0)

    # Right: the largest relative gaps, with study counts so thin bases are visible.
    y = list(range(len(top)))[::-1]
    bars = bx.barh(y, [c["log2_ratio"] for c in top], height=.78,
                   color=[color[c["income"]] for c in top], zorder=3)
    for bar, c in zip(bars, top):
        n = c["studies"]
        bx.text(-.12, bar.get_y() + bar.get_height() / 2,
                f"{multiple(c['log2_ratio'])} · {n} {'study' if n == 1 else 'studies'}",
                ha="right", va="center", fontsize=11.5, color="white", fontweight="bold", zorder=4)
    bx.set_yticks(y, [SHORT.get(c["country"], c["country"]) for c in top], fontsize=14, color=ink)
    bar_ticks = [t for t in ticks if t <= 0]
    bx.set_xlim(min(low, top[0]["log2_ratio"] - .3), 0)
    bx.set_xticks(bar_ticks, [multiple(t) for t in bar_ticks], fontsize=12.5, color=ink)
    bx.axvline(0, color="#7d776c", linewidth=1.2, linestyle=(0, (5, 3)), zorder=2)
    for t in bar_ticks:
        bx.axvline(t, color=grid, linewidth=.7, zorder=0)
    bx.tick_params(axis="y", length=0)
    bx.set_xlabel("Research share relative to burden share", fontsize=14, color=ink, labelpad=8)
    bx.set_title(f"The {TOP_N} largest relative evidence gaps", loc="left", fontsize=17,
                 fontweight="bold", color=ink, pad=12)

    for a in (ax, bx):
        for name, spine in a.spines.items():
            spine.set_visible(name in ("left", "bottom"))
            spine.set_color("#c9c2b4")

    fig.text(.02, .965, TITLE, fontsize=26, fontweight="bold", color=ink, va="top")
    fig.text(.02, .915, "Each country's share of economic evaluations divided by its share of global disease burden. "
             "Country size does not drive the ranking. It is a benchmark, not a funding recommendation.",
             fontsize=14.5, color="#33475f", va="top")
    fig.legend(handles=[Patch(color=color[g], label=g) for g in GROUPS], loc="upper left",
               bbox_to_anchor=(.02, .865), ncol=4, frameon=False, fontsize=13, handlelength=2.2,
               columnspacing=2)
    caption = (f"Base: {len(burdened)} countries with GBD 2023 burden data; {len(rows)} with at least one identified "
               f"study are plotted and ranked. {' and '.join(zero)} have no identified studies.\n"
               f"{studies:,} study-country counts: a study naming several countries counts once for each. "
               "Ratios resting on few studies are less stable; study counts are shown on each bar.")
    fig.text(.02, .055, caption, fontsize=11.5, color=muted, linespacing=1.6)
    fig.add_artist(plt.Line2D([.02, .98], [.04, .04], color=grid, linewidth=1))
    fig.text(.02, .012, f"Source: 3ie (2026). Health Economic Evaluation (HEE) Evidence Map: evidence gaps relative "
             f"to disease burden. {SITE_URL}", fontsize=12.5, color=muted)

    OUT.mkdir(parents=True, exist_ok=True)
    svg = OUT / f"{STEM}.svg"
    fig.savefig(svg, facecolor=BACKGROUND)
    tidy_svg(svg)
    fig.savefig(OUT / f"{STEM}.png", dpi=100, facecolor=BACKGROUND)
    plt.close(fig)
    with (OUT / f"{STEM}.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["iso3", "country", "income", "studies", "dalys", "ratio", "log2_ratio"],
                                extrasaction="ignore")
        writer.writeheader()
        writer.writerows(sorted(burdened, key=lambda c: c["ratio"]))
    content_path = DATA / "content.json"
    content = json.loads(content_path.read_text(encoding="utf-8"))
    entries = [f for g in content["gallery"] for f in g["figs"]
               if f["file"] in ("fig_funder_scorecard.webp", f"{STEM}.svg")]
    if len(entries) != 1:
        raise SystemExit("Expected exactly one scorecard gallery entry in content.json.")
    entries[0].update(file=f"{STEM}.svg", title=TITLE, caption=(
        "Each country's share of economic evaluations divided by its share of global disease burden "
        "(GBD 2023 all-cause DALYs), so country size does not drive the ranking. " + caption.replace("\n", " ") +
        " Proportional is a reference point, not a measure of adequacy or a recommended allocation. "
        f"Full country values: {STEM}.csv."))
    content_path.write_text(json.dumps(content, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Success: {len(rows)} countries plotted; zero-study: {', '.join(zero)}.")
    print("Top gaps:", ", ".join(f"{c['country']} ({multiple(c['log2_ratio'])})" for c in top))
    print(svg)


if __name__ == "__main__":
    main()
