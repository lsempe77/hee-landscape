"""Leaner redraw of fig_theme_rank_pubyear: less text in the figure, precise bases.

The numbers move to the site copy (figure_copy.json); the figure keeps only a
title, a one-line subtitle, short panel titles and a short footer. Writes to
exports/theme_rank_v2_2026-10-16/ and leaves docs/figures untouched.

Usage:
    python scripts/create_theme_rank_v2.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_income_pubyear_figures as b  # noqa: E402
import income_pubyear_figure_data as fd  # noqa: E402

plt = b.plt
OUT = os.path.join(fd.ROOT, "exports", "theme_rank_v2_2026-10-16")
# "Hospital-based trials" claimed more than the cluster's keywords
# (hospital / participants / medical) support.
NAMES = {**b.TOPIC_NAMES, "66": "Hospital care (general)"}


def main():
    os.makedirs(OUT, exist_ok=True)
    rows, labels, _ = fd.load(os.path.join(fd.ROOT, "data", "raw"))
    th, name, overall, _ = fd.theme_rank(rows, labels, b.COL)
    name = {c: NAMES.get(c, v) for c, v in name.items()}
    base = sum(n for _, n in th.values())
    hic = sorted(th, key=lambda c: th[c][0])[:15]
    lmic = sorted(th, key=lambda c: -th[c][0])[:15]

    fig = plt.figure(figsize=(9, 7.4))
    b.header(fig, "Topical focus and themes of health economic research, by country income strata",
             "Share of each topic's studies set in high-income, or in low- and middle-income, countries", "")
    for k, (cs, share_of, colour, ref, title) in enumerate([
            (hic, lambda c: 1 - th[c][0], "#bbb6ae", 1 - overall,
             "15 TOPICS WITH THE HIGHEST SHARE IN HIGH-INCOME COUNTRIES"),
            (lmic, lambda c: th[c][0], b.RED, overall,
             "15 TOPICS WITH THE HIGHEST SHARE IN LOW- AND MIDDLE-INCOME COUNTRIES")]):
        ax = fig.add_axes([.31, .53 - k * .4, .63, .32])
        ax.set_facecolor(b.BG)
        vals = [share_of(c) for c in cs]
        ax.barh(range(15), vals, color=colour, height=.72)
        for i, v in enumerate(vals):
            ax.text(v + .006, i, b.pct(v), va="center", fontsize=9.5, fontweight="bold")
        ax.set_yticks(range(15), [f"{name[c]}  ({th[c][1]:,})" for c in cs], fontsize=10)
        ax.invert_yaxis()
        ax.axvline(ref, color=b.MUTED, ls=(0, (2, 2)), lw=1)
        ax.text(ref + .008, 15.1, f"all topics {b.pct(ref)}", fontsize=9.5, color=b.MUTED, va="top")
        ax.set_xlim(0, 1)
        ax.set_ylim(15.2, -.6)
        ax.set_xticks([])
        ax.tick_params(length=0)
        for s in ax.spines.values():
            s.set_visible(False)
        ax.set_title(title, loc="left", fontsize=11.5, family="Franklin Gothic Demi Cond", pad=6)
    b.footer(fig, f"Number of studies in brackets. Studies of one country with a known income group, in the {len(th)} "
                  f"topics with at least 30 such studies ({base:,}). {b.RULE}", width=140)
    b.OUT = OUT
    b.save(fig, "fig_theme_rank_pubyear_v2.webp")
    print(f"base {base:,}; overall LMIC {b.pct(overall, 1)}; "
          f"LMIC panel {b.pct(th[lmic[-1]][0])}-{b.pct(th[lmic[0]][0])}; "
          f"HIC panel {b.pct(1 - th[hic[-1]][0])}-{b.pct(1 - th[hic[0]][0])}")


if __name__ == "__main__":
    main()
