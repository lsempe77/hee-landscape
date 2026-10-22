"""Build the absolute evidence-shortfall companion to the scorecard (fig_funder_scorecard_absolute).

Version 2 of build_funder_scorecard_absolute.py (kept): countries are coloured by the
World Bank income group most of their studies were published under (via
build_funder_scorecard_v3.load_rows), not the current July 2026 group.

Run: python scripts/build_funder_scorecard_absolute_v2.py
Requires matplotlib. Companion to fig_funder_scorecard_v2 (relative gaps): same base
and style, but ranks countries by how many studies they are short of a
burden-proportional share, so populous countries rank high. Bubble area is
population. Does not touch docs/data/content.json.
"""
import csv
import math
try:
    from figure_style import BACKGROUND, INCOME_COLORS, tidy_svg
    from build_funder_scorecard_v3 import GROUPS, INCOME_NOTE, OUT, SHORT, SITE_URL, TOP_N, load_rows
except ModuleNotFoundError:
    from scripts.figure_style import BACKGROUND, INCOME_COLORS, tidy_svg
    from scripts.build_funder_scorecard_v3 import GROUPS, INCOME_NOTE, OUT, SHORT, SITE_URL, TOP_N, load_rows

STEM = "fig_funder_scorecard_absolute"
TITLE = "Where the gap between studies and disease burden is largest in absolute terms"
PER = 1e5  # Studies per 100,000 DALYs.
# Scatter label offsets for the top shortfalls, in log10 decades from the bubble: (dx, dy, alignment).
# Hand-placed because the largest shortfalls cluster at 30-100M DALYs.
LABELS = {
    "IND": (0, -.3, "center"), "NGA": (.11, 0, "left"), "CHN": (-.2, 0, "right"),
    "PAK": (.09, -.02, "left"), "IDN": (.09, -.05, "left"), "COD": (.07, 0, "left"),
    "BGD": (.02, -.11, "right"), "RUS": (.08, 0, "left"), "ETH": (0, .1, "center"),
    "PHL": (-.06, -.03, "right"), "EGY": (0, .09, "center"), "BRA": (.08, 0, "left"),
    "MEX": (-.06, 0, "right"), "MMR": (.06, 0, "left"), "NER": (.01, -.1, "right"),
}


def main():
    burdened, studies = load_rows()
    burden = sum(c["dalys"] for c in burdened)
    for c in burdened:
        c["expected"] = studies * c["dalys"] / burden
        c["shortfall"] = c["expected"] - c["studies"]
        c["per100k"] = c["studies"] / c["dalys"] * PER
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker
    from matplotlib.patches import Patch

    rows = [c for c in burdened if c["studies"] > 0]
    zero = sorted(c["country"] for c in burdened if c["studies"] == 0)
    top = sorted(burdened, key=lambda c: -c["shortfall"])[:TOP_N]
    color = dict(zip(GROUPS, INCOME_COLORS))
    ink, muted, grid = "#10243e", "#5a564d", "#e6e1d8"
    rate = studies / burden * PER  # Burden-proportional rate.
    max_pop = max(c["pop"] for c in rows)

    fig = plt.figure(figsize=(20, 11.8), facecolor=BACKGROUND)
    ax = fig.add_axes([.1, .2, .40, .57], facecolor=BACKGROUND)
    bx = fig.add_axes([.64, .2, .31, .57], facecolor=BACKGROUND)

    # Left: studies per 100,000 DALYs; below the line = fewer studies than a burden-proportional share.
    ax.set_xscale("log")
    ax.set_yscale("log")
    low = 10 ** math.floor(math.log10(min(c["per100k"] for c in rows)))
    high = 10 ** math.ceil(math.log10(max(c["per100k"] for c in rows)))
    ax.axhspan(low, rate, color="#F3E6E1", alpha=.7, zorder=0)
    ax.axhline(rate, color="#7d776c", linewidth=1.4, linestyle=(0, (5, 3)), zorder=1)
    ax.text(.99, rate, f"Burden-proportional ({rate:.2f})", transform=ax.get_yaxis_transform(), ha="right",
            va="bottom", fontsize=11.5, color=muted)
    for g in GROUPS:
        pts = sorted((c for c in rows if c["income"] == g), key=lambda c: -c["pop"])
        ax.scatter([c["dalys"] for c in pts], [c["per100k"] for c in pts],
                   s=[30 + 2200 * c["pop"] / max_pop for c in pts], color=color[g],
                   edgecolors="white", linewidths=.9, alpha=.85, zorder=3)
    for c in top:
        if c["studies"] == 0 or c["iso3"] not in LABELS:
            continue
        dx, dy, ha = LABELS[c["iso3"]]
        ax.annotate(SHORT.get(c["country"], c["country"]), (c["dalys"], c["per100k"]),
                    xytext=(c["dalys"] * 10 ** dx, c["per100k"] * 10 ** dy), textcoords="data",
                    ha=ha, va="center", fontsize=11, fontweight="bold", color=ink, zorder=4)
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(
        lambda v, _: f"{v / 1e6:g}M" if v >= 1e6 else f"{v / 1e3:g}K"))
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
    ax.set_ylim(low, high)
    for t in ax.get_yticks():
        if low < t < high:
            ax.axhline(t, color=grid, linewidth=.7, zorder=0)
    ax.set_ylabel("Studies per 100,000 DALYs (log scale)", fontsize=14, color=ink, labelpad=10)
    ax.set_xlabel("Disease burden (healthy years lost, DALYs, 2023, log scale)", fontsize=14, color=ink, labelpad=8)
    ax.tick_params(axis="both", labelsize=12.5, colors=ink)
    ax.tick_params(axis="y", length=0)

    # Right: the largest absolute shortfalls, with study counts.
    y = list(range(len(top)))[::-1]
    bars = bx.barh(y, [c["shortfall"] for c in top], height=.78,
                   color=[color[c["income"]] for c in top], zorder=3)
    span = top[0]["shortfall"]
    for bar, c in zip(bars, top):
        bx.text(bar.get_width() + span * .015, bar.get_y() + bar.get_height() / 2,
                f"{c['shortfall']:,.0f} fewer",
                ha="left", va="center", fontsize=11.5, color=ink, fontweight="bold", zorder=4)
    bx.set_yticks(y, [SHORT.get(c["country"], c["country"]) for c in top], fontsize=14, color=ink)
    bx.set_xlim(0, span * 1.15)
    bx.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    bx.grid(axis="x", color=grid, linewidth=.7, zorder=0)
    bx.tick_params(axis="x", labelsize=12.5, colors=ink)
    bx.tick_params(axis="y", length=0)
    bx.set_xlabel("Studies short of the burden-proportional number", fontsize=14, color=ink, labelpad=8)
    bx.set_title(f"The {TOP_N} largest shortfalls in number of studies", loc="left", fontsize=17,
                 fontweight="bold", color=ink, pad=12)

    for a in (ax, bx):
        for name, spine in a.spines.items():
            spine.set_visible(name in ("left", "bottom"))
            spine.set_color("#c9c2b4")

    fig.text(.02, .965, TITLE, fontsize=26, fontweight="bold", color=ink, va="top")
    fig.text(.02, .915, "Left: studies per 100,000 DALYs; below the dashed line, a country has fewer studies than its share "
             "of disease burden. Bubble area is population.\nRight: how many studies short of a burden-proportional "
             "number each country is. A study examining several countries counts for each.",
             fontsize=14.5, color="#33475f", va="top", linespacing=1.5)
    fig.legend(handles=[Patch(color=color[g], label=g) for g in GROUPS], loc="upper left",
               bbox_to_anchor=(.02, .865), ncol=4, frameon=False, fontsize=13, handlelength=2.2,
               columnspacing=2)
    caption = (f"Base: {len(burdened)} countries with GBD 2023 all-cause DALYs; all are ranked, and the {len(rows)} with at "
               f"least one identified study are plotted ({' and '.join(zero)} have none). Hong Kong has no separate GBD "
               "estimate and is excluded.\n"
               f"Burden-proportional number = {studies:,} study-country counts × the country's share of DALYs across "
               f"these {len(burdened)} countries. It is a reference point, not a target.\n" + INCOME_NOTE)
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
        writer = csv.DictWriter(handle, fieldnames=["iso3", "country", "income", "pop", "studies", "dalys",
                                                    "per100k", "expected", "shortfall"], extrasaction="ignore")
        writer.writeheader()
        writer.writerows(sorted(burdened, key=lambda c: -c["shortfall"]))
    print(f"Success: {len(rows)} countries plotted; zero-study: {', '.join(zero)}.")
    print("Top shortfalls:", ", ".join(f"{c['country']} ({c['shortfall']:,.0f})" for c in top))
    print(svg)


if __name__ == "__main__":
    main()
