"""Redraw fig_equity_time_pubyear.webp with its burden reference computed from data.

Version 2 of build_income_pubyear_figures.py (kept; other scripts import it for its
house style). Only the equity-over-time figure changes: the dashed reference was a
hardcoded 83%, which matches the current (July 2026) income groups. It is now the
share of GBD 2023 all-cause DALYs across the 204 national GBD locations carried by
countries that were low or middle income on 1 January 2023 (FY23), the burden year,
as in the other burden figures. Venezuela, unclassified in FY23, uses its last
upper-middle-income group (as build_gbd_figures.py does); Cook Islands, Niue and
Tokelau have no World Bank group and are left out of both sides.

The other four figures are untouched. This version does not write
docs/data/figure_updates.json: it prints the caption to sync by hand.

Usage:
    python scripts/build_income_pubyear_figures_v2.py [--raw data/raw]
"""
import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_income_pubyear_figures as b  # noqa: E402
import income_pubyear_figure_data as fd  # noqa: E402
from build_income_pubyear import group_at, load_history  # noqa: E402

BURDEN_YEAR = 2023
BURDEN_FALLBACK = {"VEN": "Upper middle income"}  # Unclassified in FY23; matches build_gbd_figures.py.


def lmic_burden_share(raw):
    """Share of classified national all-cause DALYs in low- and middle-income countries in BURDEN_YEAR."""
    hist = load_history()
    with open(os.path.join(raw, "denominator_gbd_source.csv"), encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 204 or len({r["iso3"] for r in rows}) != 204:
        raise SystemExit("denominator_gbd_source.csv must hold the 204 national GBD locations once each.")
    total = lmic = 0.0
    for r in rows:
        group = group_at(hist, r["iso3"], BURDEN_YEAR) or BURDEN_FALLBACK.get(r["iso3"])
        if group is None:
            continue
        total += float(r["val"])
        if group != "High income":
            lmic += float(r["val"])
    return lmic / total


def equity_time(rows, share):
    data, n = fd.equity_time(rows, b.COL)
    years = sorted(data)
    vals = [data[y] for y in years]
    ref = b.pct(share)
    fig = b.plt.figure(figsize=(9, 5.75))
    b.header(fig, "Studies of lower-income countries are growing but lag their health needs",
             "Share of each year's studies of a single country that are about low- and middle-income countries.",
             f"It rose from {b.pct(vals[0])} in {years[0]} to {b.pct(vals[-1])} in {years[-1]}, still far below the {ref} "
             "of the world's disease burden those countries carry (dashed line).")
    ax = fig.add_axes([.09, .19, .88, .55])
    b.style(ax)
    ax.grid(axis="x", color=b.GRID, lw=.6)
    ax.fill_between(years, vals, share, color="#f2ddd0", alpha=.55, lw=0)
    ax.axhline(share, color=b.MUTED, ls=(0, (2, 2)), lw=1)
    ax.text(years[0], share - .03, f"low- and middle-income countries' share of the world's disease burden: {ref}",
            fontsize=10, color="#8a857c", va="top")
    ax.plot(years, vals, color=b.ORANGE, lw=3.2, marker="o", ms=5.5)
    ax.text(years[-1] + .25, vals[-1], b.pct(vals[-1]), color="#c0442a", fontsize=11, fontweight="bold", va="center")
    ax.set_ylim(0, 1)
    ax.set_xlim(years[0] - .8, years[-1] + 2)
    ax.set_yticks([0, .25, .5, .75, 1], ["0%", "25%", "50%", "75%", "100%"])
    ax.set_xticks(years[::2])
    ax.set_ylabel("Share about low- and middle-income countries", fontsize=11)
    b.footer(fig, f"Studies of a single country with a known income group, by year of publication ({n:,} studies); "
                  f"2026 is incomplete and left out. {b.RULE} Disease burden: healthy years lost to illness and early "
                  f"death (DALYs), Global Burden of Disease 2023, with countries grouped by the World Bank group on "
                  f"1 January {BURDEN_YEAR}. The shaded band is the gap to that share.", width=135)
    b.save(fig, "fig_equity_time_pubyear.webp")
    return {"caption": f"Share of each year's single-country studies about low- and middle-income countries (LMICs): "
                       f"{b.pct(vals[0])} in {years[0]} → {b.pct(vals[-1])} in {years[-1]}, against the {ref} of global "
                       "disease burden (GBD 2023 all-cause DALYs, 204 national locations) those countries carry "
                       f"(dashed line; countries grouped by the World Bank group on 1 January {BURDEN_YEAR}, the burden "
                       f"year). Studies naming a single country with a known income group ({n:,}); 2026 is partial and "
                       "left out. Income group: the World Bank group of the country studied, as classified on 1 January "
                       "of the publication year (World Bank historical classifications). For 2026 publications only, "
                       "missing FY2026 classifications use FY2025 low income for Ethiopia and FY2021 upper-middle income "
                       "for Venezuela (FY2025 also unavailable); these are analysis exceptions."}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--raw", default=os.path.join(b.ROOT, "data", "raw"))
    args = ap.parse_args()
    rows, _, _ = fd.load(args.raw)
    share = lmic_burden_share(args.raw)
    print(f"LMIC share of GBD 2023 all-cause DALYs (FY23 groups): {share:.4f}")
    print("Caption:", equity_time(rows, share)["caption"])


if __name__ == "__main__":
    main()
