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

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data"
OUT = ROOT / "docs" / "figures"
TITLE = "How does economic evaluation evidence compare with disease burden?"
GROUPS = ["Low income", "Lower middle income", "Upper middle income", "High income"]
COLORS = ["#eb6834", "#eda100", "#1baf7a", "#2a78d6"]


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
    matches = [f for g in content["gallery"] for f in g["figs"]
               if f["file"] in ("fig_burden.webp", "fig_research_burden_ratio.svg")]
    if len(matches) != 1:
        raise ValueError("Exactly one evidence-versus-burden gallery entry is required.")
    return rows, meta, content, matches[0], len(countries) - len(rows), studies


def main():
    try:
        rows, meta, content, entry, excluded, studies = load_inputs()
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.ticker import FixedLocator, FixedFormatter
    except (OSError, ValueError, KeyError, TypeError, ImportError) as exc:
        raise SystemExit(f"Stopped before writing outputs: {exc}") from exc
    ground = "#f7f4ee"
    fig, axes = plt.subplots(1, 4, figsize=(24, 16), facecolor=ground)
    ticks = [.01, .1, 1, 10, 100]
    extent = max(2.30103, max(abs(math.log10(c["ratio"])) for c in rows if c["ratio"] > 0) + .15)
    limits = (10 ** -extent, 10 ** extent)
    max_rows = max(sum(c["income"] == g for c in rows) for g in GROUPS)
    for ax, group, color in zip(axes, GROUPS, COLORS):
        group_rows = sorted((c for c in rows if c["income"] == group), key=lambda c: (-c["ratio"], c["country"]))
        ax.set_facecolor(ground)
        ax.set_xscale("log")
        ax.set_xlim(*limits)
        ax.set_ylim(max_rows, -1)
        ax.axvspan(limits[0], 1, color="#eee8df", zorder=0)
        ax.axvline(1, color="#10243e", linewidth=1.5, zorder=2)
        for y, c in enumerate(group_rows):
            ratio = c["ratio"]
            if ratio:
                ax.plot([min(ratio, 1), max(ratio, 1)], [y, y], color=color, alpha=.4, linewidth=1.3)
                ax.scatter(ratio, y, color=color, s=25, zorder=3)
            else:
                # A separate labelled gutter; zero is never assigned a log value.
                ax.text(-.025, y, "0", transform=ax.get_yaxis_transform(), ha="right", va="center",
                        fontsize=8, color=color, fontweight="bold")
        ax.set_yticks(range(len(group_rows)), [c["country"] for c in group_rows], fontsize=8)
        ax.tick_params(axis="y", length=0, pad=18)
        ax.xaxis.set_major_locator(FixedLocator(ticks))
        ax.xaxis.set_major_formatter(FixedFormatter(["0.01", "0.1", "1", "10", "100"]))
        ax.grid(axis="x", which="major", color="#ded9ce", linewidth=.6)
        ax.tick_params(axis="x", which="minor", bottom=False)
        ax.set_title(f"{group}\n{len(group_rows)} countries", fontsize=16, color=color, loc="left", pad=18, fontweight="bold")
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.set_xlabel("Research-to-burden ratio", fontsize=10, labelpad=10)
    fig.subplots_adjust(left=.12, right=.985, bottom=.15, top=.84, wspace=1.05)
    fig.text(.025, .965, TITLE, fontsize=26, fontweight="bold", color="#10243e")
    fig.text(.025, .925, "Country share of study-country counts divided by country share of DALYs", fontsize=17, color="#33475f")
    fig.text(.025, .891, "Below 1: less evidence relative to burden     |     1: proportional shares     |     Above 1: more evidence relative to burden", fontsize=14, color="#33475f")
    years = meta["years"]
    caption = (f"Base: {len(rows)} countries with positive burden data; {studies:,} study-country counts. "
               f"{excluded} country excluded because burden is unavailable.\n"
               f"Evaluations published {years[0]}–{years[1]} (final year partial); GBD 2023 all-cause DALYs. "
               "Both shares use the same countries, including those with zero studies.\n"
               "A study naming multiple countries contributes once to each country. "
               "Countries are ranked within income group. Zero-evidence countries are labelled 0 beside their names.\n"
               "The ratio axis is logarithmic. The benchmark describes proportionality, not adequacy or a recommended research allocation.")
    fig.text(.025, .045, caption, fontsize=11, color="#5a564d", linespacing=1.7)
    entry.update(file="fig_research_burden_ratio.svg", title=TITLE, caption=caption.replace("\n", " "))
    # Stage every output first; invalid input or rendering failure cannot replace the live figure.
    with tempfile.TemporaryDirectory(dir=OUT) as staging:
        staging = Path(staging)
        fig.savefig(staging / entry["file"], facecolor=ground)
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
    print(f"Success: {len(rows)} countries; {sum(c['studies'] == 0 for c in rows)} zero-evidence countries; {studies:,} study-country counts.")
    print(OUT / entry["file"])


if __name__ == "__main__":
    main()
