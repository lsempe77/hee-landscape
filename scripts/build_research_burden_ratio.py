"""Build the country research-to-burden ratio figure.

Run: python scripts/build_research_burden_ratio.py
Requires matplotlib. Validates the published country data before writing outputs.
Uses study-country counts and DALYs across the same country set, including zeros.
"""
import csv
import json
import math
import os
from pathlib import Path
import tempfile
try:
    from figure_style import BACKGROUND, INCOME_COLORS
except ModuleNotFoundError:
    from scripts.figure_style import BACKGROUND, INCOME_COLORS

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data"
OUT = ROOT / "docs" / "figures"
TITLE = "Lower-income countries have less economic evidence relative to their disease burden"
GROUPS = ["Low income", "Lower middle income", "Upper middle income", "High income"]
COLORS = INCOME_COLORS
LOW_N = 5  # Ratios resting on fewer studies than this are drawn hollow.
ZERO_Y = .0025  # Plot position of the separate "No studies" band, below the ratio axis.
FLOOR = .0045  # Bottom of the ratio axis; the band sits beneath a dashed break.


def load_inputs():
    countries = json.loads((DATA / "countries.json").read_text(encoding="utf-8"))
    meta = json.loads((DATA / "dict.json").read_text(encoding="utf-8"))["meta"]
    content = json.loads((DATA / "content.json").read_text(encoding="utf-8"))
    if not countries or len({c["iso3"] for c in countries}) != len(countries):
        raise ValueError("Country data must be nonempty and contain unique ISO3 codes.")
    for c in countries:
        if c["income"] not in GROUPS or not isinstance(c["studies"], int) or c["studies"] < 0:
            raise ValueError(f"Invalid income or study count for {c['iso3']}")
        if c["dalys"] is not None and (not math.isfinite(c["dalys"]) or c["dalys"] < 0):
            raise ValueError(f"Invalid burden for {c['iso3']}")
    rows = [dict(c) for c in countries if c["dalys"] and c["dalys"] > 0]
    studies = sum(c["studies"] for c in rows)
    burden = sum(c["dalys"] for c in rows)
    if not rows or not studies or not burden or any(not any(c["income"] == g for c in rows) for g in GROUPS):
        raise ValueError("Positive study and burden totals and all four income groups are required.")
    for c in rows:
        c["evidence_share"] = c["studies"] / studies
        c["burden_share"] = c["dalys"] / burden
        c["ratio"] = c["evidence_share"] / c["burden_share"]
    if any(0 < c["ratio"] < FLOOR for c in rows):
        raise ValueError("A nonzero ratio falls below the axis floor; lower FLOOR and ZERO_Y.")
    matches = [f for g in content["gallery"] for f in g["figs"]
               if f["file"] in ("fig_burden.webp", "fig_research_burden_ratio.svg")]
    if len(matches) != 1:
        raise ValueError("Exactly one evidence-versus-burden gallery entry is required.")
    return rows, meta, content, matches[0], len(countries) - len(rows), studies


def times(ratio):
    """Plain-language multiplier relative to proportional shares."""
    if ratio >= 1:
        return f"{ratio:.1f}× more" if ratio < 10 else f"{ratio:.0f}× more"
    inverse = 1 / ratio
    return f"{inverse:.1f}× less" if inverse < 10 else f"{inverse:.0f}× less"


def main():
    try:
        rows, meta, content, entry, excluded, studies = load_inputs()
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except (OSError, ValueError, KeyError, TypeError, ImportError) as exc:
        raise SystemExit(f"Stopped before writing outputs: {exc}") from exc
    ground, ink, muted = BACKGROUND, "#10243e", "#5a564d"
    fig, ax = plt.subplots(figsize=(14, 11), facecolor=ground)
    ax.set_facecolor(ground)
    ax.set_yscale("log")
    top = max(c["ratio"] for c in rows) * 2.2
    ax.set_ylim(.0018, top)
    ax.set_xlim(-.6, len(GROUPS) - .4)
    ax.axhspan(FLOOR, 1, color="#F3EEE9", zorder=0)
    ax.axhline(1, color="#7d776c", linewidth=1.3, linestyle=(0, (5, 3)), zorder=1)
    ax.axhline(FLOOR * .82, color="#b9b2a5", linewidth=.8, linestyle=(0, (2, 3)), zorder=1)
    ax.text(-.55, 1.12, "Proportional: research share = burden share", fontsize=11, color=muted, va="bottom")
    ax.text(-.55, top * .8, "↑ More research than burden share", fontsize=11, color=muted, va="top")
    ax.text(-.55, FLOOR * 1.1, "↓ Less research than burden share", fontsize=11, color=muted, va="bottom")
    rng = np.random.default_rng(7)  # Fixed jitter keeps rebuilds identical.
    zero_names = []
    for x, (group, color) in enumerate(zip(GROUPS, COLORS)):
        group_rows = sorted((c for c in rows if c["income"] == group), key=lambda c: c["ratio"])
        plotted = [c for c in group_rows if c["ratio"] > 0]
        for c in group_rows:
            c["_x"] = x + rng.uniform(-.22, .22)
            hollow = c["studies"] < LOW_N
            if c["ratio"] > 0:
                ax.scatter(c["_x"], c["ratio"], s=62, zorder=3, linewidths=1.4,
                           facecolors="none" if hollow else color, edgecolors=color if hollow else "white",
                           alpha=1 if hollow else .9)
            else:
                # Zero is shown in its own band, never as a value on the log ratio axis.
                ax.scatter(c["_x"], ZERO_Y, marker="x", s=55, color=color, linewidths=2, zorder=3)
                ax.annotate(c["country"], (c["_x"], ZERO_Y), xytext=(8, 0), textcoords="offset points",
                            fontsize=10, color=ink, va="center", fontweight="bold")
                zero_names.append(c["country"])
        median = float(np.median([c["ratio"] for c in group_rows]))
        ax.plot([x - .26, x + .26], [median, median], color=ink, linewidth=3.5, solid_capstyle="butt", zorder=4)
        ax.annotate(f"Median {median:.2f}\n({times(median)})", (x + .27, median), xytext=(4, 0),
                    textcoords="offset points", fontsize=10.5, color=ink, va="center", fontweight="bold",
                    bbox=dict(boxstyle="round,pad=.25", facecolor=ground, edgecolor="none", alpha=.9), zorder=5)
        # Label the lowest country in each group, plus the highest in the top group.
        label_rows = plotted[:1] + (plotted[-1:] if x == len(GROUPS) - 1 else [])
        for c in label_rows:
            ax.annotate(c["country"], (c["_x"], c["ratio"]), xytext=(0, -13 if c["ratio"] < 1 else 9),
                        textcoords="offset points", ha="center", fontsize=10, color=ink, fontweight="bold")
        below = sum(c["ratio"] < 1 for c in group_rows)
        ax.text(x, -.075, f"{below} of {len(group_rows)} below proportional", transform=ax.get_xaxis_transform(),
                ha="center", va="top", fontsize=11, color=muted)
    ax.set_xticks(range(len(GROUPS)), GROUPS, fontsize=14, color=ink)
    ax.tick_params(axis="x", length=0, pad=8)
    ticks = [.01, .1, 1, 10]
    ax.set_yticks(ticks + [ZERO_Y], ["100× less", "10× less", "Proportional", "10× more", "No studies"],
                  fontsize=12, color=ink)
    ax.yaxis.set_minor_locator(plt.NullLocator())
    ax.tick_params(axis="y", length=0)
    for t in ticks:
        ax.axhline(t, color="#e3ded4", linewidth=.7, zorder=0)
    ax.set_ylabel("Research share relative to disease-burden share (log scale)", fontsize=12.5, color=ink, labelpad=12)
    for name, spine in ax.spines.items():
        spine.set_visible(name == "left")
    ax.spines["left"].set_color("#c9c2b4")
    # The legend explains marker meaning only; income colour is named on the x-axis.
    ax.scatter([], [], s=62, color="#8a857b", edgecolors="white", label=f"{LOW_N}+ studies")
    ax.scatter([], [], s=62, facecolors="none", edgecolors="#8a857b", linewidths=1.4,
               label=f"Fewer than {LOW_N} studies (less stable)")
    ax.scatter([], [], marker="x", s=55, color="#8a857b", linewidths=2, label="No studies")
    ax.plot([], [], color=ink, linewidth=3.5, label="Group median")
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.01), ncol=4, frameon=False, fontsize=11,
              handletextpad=.4, columnspacing=1.6)
    below_all = sum(c["ratio"] < 1 for c in rows)
    lic = [c for c in rows if c["income"] == GROUPS[0]]
    fig.subplots_adjust(left=.13, right=.89, bottom=.2, top=.74)
    fig.text(.03, .965, TITLE.replace(" relative", "\nrelative"), fontsize=21, va="top", linespacing=1.15, fontweight="bold", color=ink)
    fig.text(.03, .862, "Each point is a country: its share of studies divided by its share of global disease burden.",
             fontsize=13.5, color="#33475f")
    fig.text(.03, .826, f"{below_all} of {len(rows)} countries have a smaller research share than burden share, "
             f"including {sum(c['ratio'] < 1 for c in lic)} of {len(lic)} low-income countries.",
             fontsize=13.5, color=ink, fontweight="bold")
    years = meta["years"]
    caption = (f"Base: {len(rows)} countries with positive burden data; {studies:,} study-country counts. "
               f"{excluded} country excluded because burden is unavailable. {' and '.join(zero_names)} have no identified studies.\n"
               f"Studies published {years[0]}–{years[1]} (final year partial); GBD 2023 all-cause DALYs. "
               "A study naming multiple countries counts once for each country.\n"
               "Ratios compare shares, so countries well above proportional push others below it. "
               "Proportional is a reference point, not a measure of adequacy or a recommended allocation.\n"
               "Horizontal position within a group is random jitter. Full country values: research_burden_ratios.csv.")
    fig.text(.03, .03, caption, fontsize=10.5, color=muted, linespacing=1.6)
    entry.update(file="fig_research_burden_ratio.svg", title=TITLE, caption=caption.replace("\n", " "))
    for c in rows:
        c.pop("_x", None)
    # Stage every output first; invalid input or rendering failure cannot replace the live figure.
    with tempfile.TemporaryDirectory(dir=OUT) as staging:
        staging = Path(staging)
        fig.savefig(staging / entry["file"], facecolor=ground)
        svg_path = staging / entry["file"]
        svg_path.write_text("\n".join(line.rstrip() for line in svg_path.read_text(encoding="utf-8").splitlines()) + "\n", encoding="utf-8")
        fig.savefig(staging / "fig_research_burden_ratio.png", dpi=100, facecolor=ground)
        with (staging / "research_burden_ratios.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["iso3", "country", "income", "studies", "dalys", "evidence_share", "burden_share", "ratio"], extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        (staging / "content.json").write_text(json.dumps(content, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        for filename in (entry["file"], "fig_research_burden_ratio.png", "research_burden_ratios.csv"):
            os.replace(staging / filename, OUT / filename)
        os.replace(staging / "content.json", DATA / "content.json")
    plt.close(fig)
    print(f"Success: {len(rows)} countries; {len(zero_names)} zero-evidence countries; {studies:,} study-country counts.")
    print(OUT / entry["file"])


if __name__ == "__main__":
    main()
