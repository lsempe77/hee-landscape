"""Small-multiples redraw of fig_intervention_mix_pubyear: one panel per intervention type.

The original draws nine lines on one chart, seven of them grey and bunched under
15%, so their trends are hard to follow. Here each type gets its own panel, its
line coloured by direction (rising or falling as country income falls) over the
other types in faint grey. Same numbers and base as the original. Writes to
exports/intervention_mix_v2_2026-10-17/ and leaves docs/figures untouched.

Usage:
    python scripts/create_intervention_mix_v2.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_income_pubyear_figures as b  # noqa: E402
import income_pubyear_figure_data as fd  # noqa: E402

plt = b.plt
OUT = os.path.join(fd.ROOT, "exports", "intervention_mix_v2_2026-10-17")
RISE, FALL, FLAT = b.RED, b.BLUE, "#6b665d"
SHORT = ["High", "Upper\nmiddle", "Lower\nmiddle", "Low"]


def main():
    os.makedirs(OUT, exist_ok=True)
    rows, _, _ = fd.load(os.path.join(fd.ROOT, "data", "raw"))
    mix, n = fd.intervention_mix(rows, b.COL)
    order = list(reversed(fd.GROUPS))  # High -> Low
    series = {k: [mix[g][k] for g in order] for k in fd.INTERVENTIONS}
    # Panels from the largest type to the smallest, "Other" last.
    keys = sorted((k for k in series if k != "other"), key=lambda k: -sum(series[k])) + ["other"]
    ph, cm, va = series["pharma"], series["care_model_organisational"], series["vaccine"]
    if round(100 * cm[3]) == round(100 * ph[3]):
        lead = f"level with care models ({b.pct(cm[3])})"
    elif cm[3] > ph[3]:
        lead = f"overtaken by care models ({b.pct(cm[3])})"
    else:
        lead = f"just ahead of care models ({b.pct(cm[3])})"

    fig = plt.figure(figsize=(9, 8.6))
    y = b.header(fig, "What gets evaluated changes with country income",
                 "Share of each income group's studies, by the main type of health care evaluated; income of the "
                 "country studied falls from left to right. Red: share rises as income falls; blue: falls; dark "
                 "grey: changes by under 2 points.",
                 f"Medicines peak in upper-middle-income countries ({b.pct(ph[1])}) and fall to {b.pct(ph[3])} in "
                 f"low-income countries, {lead}. Vaccines rise from {b.pct(va[0])} "
                 f"to {b.pct(va[3])}.")
    left, right, top, bottom = .07, .97, y - .035, .13
    cols, nrows = 3, 3
    gx, gy = .045, .065
    w = (right - left - gx * (cols - 1)) / cols
    h = (top - bottom - gy * (nrows - 1)) / nrows
    x = range(4)
    for i, k in enumerate(keys):
        r, c = divmod(i, cols)
        ax = fig.add_axes([left + c * (w + gx), top - (r + 1) * h - r * gy, w, h])
        b.style(ax)
        ax.tick_params(labelsize=9)
        for other in keys:
            if other != k:
                ax.plot(x, series[other], color="#ddd7cd", lw=1, zorder=1)
        v = series[k]
        d = v[3] - v[0]
        colour = RISE if d >= .02 else FALL if d <= -.02 else FLAT
        ax.plot(x, v, color=colour, lw=2.6, marker="o", ms=5, zorder=3)
        for j, ha, dx in ((0, "right", -.12), (3, "left", .12)):
            ax.text(j + dx, v[j], b.pct(v[j]), ha=ha, va="center", fontsize=9.5, color=colour,
                    family="Franklin Gothic Demi")
        if k == "pharma":
            ax.text(1, v[1] + .04, b.pct(v[1]), ha="center", fontsize=9.5, color=colour,
                    family="Franklin Gothic Demi")
        ax.set_title(fd.INTERVENTIONS[k], loc="left", fontsize=11, family="Franklin Gothic Demi", color=b.INK,
                     pad=4)
        ax.set_xlim(-.55, 3.55)
        ax.set_ylim(0, .52)
        ax.set_yticks([0, .25, .5], ["0%", "25%", "50%"] if c == 0 else [])
        ax.set_xticks(list(x), SHORT if r == nrows - 1 else [])
    b.footer(fig, f"Studies of a single country with a known income group ({n:,}). Main type of health care only, "
                  "assigned by a large language model from each abstract and checked against keyword and topic "
                  f"groupings. {b.RULE}", y=.012, width=140)
    b.OUT = OUT
    b.save(fig, "fig_intervention_mix_pubyear_v2.webp")


if __name__ == "__main__":
    main()
