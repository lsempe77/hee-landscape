"""Redraw the two evaluation-type figures without reviews that report no evaluation of their own.

Run: python scripts/build_eval_type_figures.py
Requires matplotlib. Reads data/raw/hee_analysis_master_v2_1.csv. Reviews with no
original evaluation (apply_review_eval_type.review_only) are not counted as a
cost-benefit, cost-consequence, cost-effectiveness or cost-utility analysis:
fig_method_stream_v2 shows them as a separate grey band, and
fig_decision_time_v2 (cost-utility and cost-effectiveness only) leaves them out.

Writes *_v2.svg/.png next to the upstream originals, which stay untouched, and
points their gallery entries in docs/data/content.json at the new files.
"""
import collections
import csv
import json
from pathlib import Path
try:
    from figure_style import BACKGROUND, INCOME_COLORS, tidy_svg
    from apply_review_eval_type import REVIEW_LEVEL, review_only
except ModuleNotFoundError:
    from scripts.figure_style import BACKGROUND, INCOME_COLORS, tidy_svg
    from scripts.apply_review_eval_type import REVIEW_LEVEL, review_only

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data" / "raw" / "hee_analysis_master_v2_1.csv"
DATA = ROOT / "docs" / "data"
OUT = ROOT / "docs" / "figures"
FIRST, LAST = 2010, 2025  # 2026 is a partial year and is left out.
TYPES = ["Cost-utility", "Cost-effectiveness", "Cost-consequence", "Cost-benefit"]
TYPE_COLORS = [INCOME_COLORS[3], INCOME_COLORS[2], INCOME_COLORS[1], INCOME_COLORS[0]]
REVIEW_COLOR = "#c5c2bb"
ELEMENTS = [("has_icer", "Cost per health gained (ICER)", INCOME_COLORS[3]),
            ("has_uncertainty", "Uncertainty analysis", INCOME_COLORS[2]),
            ("has_perspective", "Whose costs are counted (perspective)", "#8a857b"),
            ("has_threshold", "Cost-effectiveness threshold", INCOME_COLORS[0])]
INK, MUTED, GRID = "#10243e", "#5a564d", "#e6e1d8"
SOURCE = "Source: 3ie (2026). Health Economic Evaluation (HEE) Evidence Map. https://3ieimpact.pages.dev/hee/"


def load():
    csv.field_size_limit(10 ** 9)
    rows = []
    with MASTER.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["is_eligible"] not in ("TRUE", "True", "1") or not FIRST <= int(r["year"]) <= LAST:
                continue
            kind = REVIEW_LEVEL if review_only(r) else r["econ_eval_type"]
            if kind not in TYPES + [REVIEW_LEVEL]:
                raise ValueError(f"Unknown evaluation type {r['econ_eval_type']!r} for {r['record_id']}")
            rows.append({"year": int(r["year"]), "kind": kind,
                         **{col: r[col] == "1" for col, _, _ in ELEMENTS}})
    return rows


def frame(fig, title, subtitle, note):
    import matplotlib.pyplot as plt
    h = fig.get_figheight()
    fig.text(.03, 1 - .35 / h, title, fontsize=21, fontweight="bold", color=INK, va="top")
    fig.text(.03, 1 - .82 / h, subtitle, fontsize=13.5, color="#33475f", va="top", linespacing=1.45)
    fig.text(.03, .62 / h, note, fontsize=11.5, color=MUTED, va="bottom", linespacing=1.5)
    fig.add_artist(plt.Line2D([.03, .97], [.5 / h, .5 / h], color=GRID, linewidth=1))
    fig.text(.03, .17 / h, SOURCE, fontsize=11, color=MUTED, va="bottom")


def style(ax):
    ax.set_facecolor(BACKGROUND)
    for name, spine in ax.spines.items():
        spine.set_visible(name == "bottom")
        spine.set_color("#c9c2b4")
    ax.tick_params(axis="both", labelsize=12, colors=INK, length=0)
    ax.grid(axis="y", color=GRID, linewidth=.8)
    ax.set_axisbelow(True)


def save(fig, stem):
    import matplotlib.pyplot as plt
    svg = OUT / f"{stem}.svg"
    fig.savefig(svg, facecolor=BACKGROUND)
    tidy_svg(svg)
    fig.savefig(OUT / f"{stem}.png", dpi=100, facecolor=BACKGROUND)
    plt.close(fig)
    return f"{stem}.svg"


def fig_stream(rows):
    import matplotlib.pyplot as plt
    years = list(range(FIRST, LAST + 1))
    count = collections.Counter((r["year"], r["kind"]) for r in rows)
    series = [[count[(y, t)] for y in years] for t in TYPES]
    reviews = [count[(y, REVIEW_LEVEL)] for y in years]
    typed = [sum(s[i] for s in series) for i in range(len(years))]
    cu = [series[0][i] / typed[i] for i in range(len(years))]
    ce = [series[1][i] / typed[i] for i in range(len(years))]
    title = "More studies now measure health gains in QALYs or DALYs"
    fig = plt.figure(figsize=(15, 9.6), facecolor=BACKGROUND)
    frame(fig, title,
          f"Between {FIRST} and {LAST}, cost-utility studies rose from {cu[0]:.0%} to {cu[-1]:.0%} of studies "
          "with an evaluation type, while cost-effectiveness studies fell\n"
          f"from {ce[0]:.0%} to {ce[-1]:.0%}. Reviews that report no evaluation of their own are shown separately "
          "and not counted as a type.",
          "Cost-utility: health gains in QALYs or DALYs. Cost-effectiveness: health gains in natural units (e.g. deaths "
          "averted). Cost-consequence: costs and outcomes\nreported side by side. Cost-benefit: health gains valued in "
          f"money. {LAST + 1} is a partial year and is left out.")
    ax = fig.add_axes([.08, .17, .89, .6])
    style(ax)
    ax.stackplot(years, *series, reviews, colors=TYPE_COLORS + [REVIEW_COLOR],
                 labels=TYPES + ["Review (no evaluation type)"], edgecolor=BACKGROUND, linewidth=.6, alpha=.95)
    ax.set_xlim(FIRST, LAST)
    ax.set_xticks(range(FIRST, LAST + 1, 2))
    ax.set_ylabel("Studies published per year", fontsize=13, color=INK, labelpad=8)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.02), ncol=5, frameon=False, fontsize=12.5,
              handlelength=1.4, columnspacing=1.6, borderaxespad=0)
    n_typed, n_rev = sum(typed), sum(reviews)
    caption = (f"Studies by publication year and evaluation type, {FIRST}–{LAST} ({LAST + 1} partial, left out): "
               f"{n_typed:,} studies with an evaluation type and {n_rev:,} reviews that report no evaluation of their "
               "own, shown as a separate grey band and excluded from type shares. Reviews that also report the authors' "
               f"own evaluation keep its type. Cost-utility rose from {cu[0]:.1%} to {cu[-1]:.1%} of typed studies; "
               f"cost-effectiveness fell from {ce[0]:.1%} to {ce[-1]:.1%}.")
    return save(fig, "fig_method_stream_v2"), title, caption


def fig_decision(rows):
    import matplotlib.pyplot as plt
    years = list(range(FIRST, LAST + 1))
    base = [r for r in rows if r["kind"] in TYPES[:2]]
    by_year = collections.defaultdict(list)
    for r in base:
        by_year[r["year"]].append(r)
    shares = {col: [sum(r[col] for r in by_year[y]) / len(by_year[y]) for y in years] for col, _, _ in ELEMENTS}
    thr = shares["has_threshold"]
    title = "Study summaries increasingly report what decision-makers need"
    fig = plt.figure(figsize=(15, 9.6), facecolor=BACKGROUND)
    frame(fig, title,
          "Share of cost-utility and cost-effectiveness studies whose abstract reports each element, by year. "
          f"All four rose between {FIRST} and {LAST};\nthe cost-effectiveness threshold most, from {thr[0]:.0%} to "
          f"{thr[-1]:.0%}. Reviews that report no evaluation of their own are left out.",
          "Measures what the abstract states, not what the study did: an element missing from the abstract may still "
          f"be in the full paper.\nOnly these two evaluation types report thresholds and incremental ratios. "
          f"{LAST + 1} is a partial year and is left out.")
    ax = fig.add_axes([.08, .17, .8, .6])
    style(ax)
    for col, label, colour in ELEMENTS:
        ax.plot(years, shares[col], color=colour, linewidth=2.6, marker="o", markersize=5, label=label)
        ax.text(LAST + .25, shares[col][-1], f"{shares[col][-1]:.0%}", color=colour, fontsize=12.5,
                fontweight="bold", va="center")
    ax.set_xlim(FIRST - .3, LAST + .3)
    ax.set_xticks(range(FIRST, LAST + 1, 2))
    ax.set_ylim(0, max(max(v) for v in shares.values()) * 1.12)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_ylabel("Share of abstracts reporting the element", fontsize=13, color=INK, labelpad=8)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.02), ncol=4, frameon=False, fontsize=12.5,
              handlelength=1.6, columnspacing=1.6, borderaxespad=0)
    n_all = sum(1 for r in rows if r["kind"] != REVIEW_LEVEL)
    caption = (f"Base: {len(base):,} cost-utility and cost-effectiveness studies (of {n_all:,} studies with an "
               f"evaluation type, {FIRST}–{LAST}; {LAST + 1} partial, left out). Reviews that report no evaluation of "
               "their own are excluded; reviews that also report the authors' own evaluation keep its type. "
               "Only these two types report thresholds and incremental ratios. Keyword matches on the abstract. "
               f"The cost-effectiveness threshold rose most, {thr[0]:.0%} → {thr[-1]:.0%}.")
    return save(fig, "fig_decision_time_v2"), title, caption


BUILDERS = {"fig_method_stream.webp": fig_stream, "fig_decision_time.webp": fig_decision}


def main():
    import matplotlib
    matplotlib.use("Agg")
    rows = load()
    content_path = DATA / "content.json"
    content = json.loads(content_path.read_text(encoding="utf-8"))
    for old, build in BUILDERS.items():
        file, title, caption = build(rows)
        entries = [f for g in content["gallery"] for f in g["figs"] if f["file"] in (old, file)]
        if not entries:
            raise SystemExit(f"No gallery entry for {old} in content.json.")
        for entry in entries:  # fig_method_stream appears in two sections.
            entry.update(file=file, title=title, caption=caption)
        print(f"{old} -> {file}: {title}")
    content_path.write_text(json.dumps(content, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


if __name__ == "__main__":
    main()
