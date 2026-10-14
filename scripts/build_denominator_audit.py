"""Reconcile country denominators and rebuild inequality/reach figures.

First run export_country_audit_sources.R with the upstream HEE project path.
Inputs in data/raw are local source exports; public outputs record aggregated
counts and the country sets used, without duplicating the external GBD export.
"""
import csv
import hashlib
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from build_income_pubyear import load_history, group_at
from figure_style import INCOME_COLORS

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs/data"
OUT = ROOT / "docs/figures"
RAW = ROOT / "data/raw"
GROUPS = ["Low income", "Lower middle income", "Upper middle income", "High income"]
COLORS = dict(zip(GROUPS, INCOME_COLORS))
BG = "#F7F4EE"


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def save(fig, stem, title, caption):
    fig.suptitle(title, x=.09, ha="left", fontsize=18, fontweight="bold", y=.96)
    fig.savefig(OUT / (stem + ".svg"), facecolor=BG)
    png_stage = OUT / (stem + ".refresh.tmp.png")
    fig.savefig(png_stage, facecolor=BG, dpi=130)
    os.replace(png_stage, OUT / (stem + ".png"))
    plt.close(fig)
    return {"file": stem + ".svg", "title": title, "caption": caption}


def main():
    csv.field_size_limit(10**9)
    countries = read_json(DATA / "countries.json")
    geo_web = read_json(DATA / "geo.json")
    master_path = RAW / "hee_analysis_master_v2_1.csv"
    eligible = {r["record_id"]: r for r in read_csv(master_path) if r["is_eligible"] == "TRUE"}
    pairs = {(r["record_id"], r["iso3"]) for r in read_csv(RAW / "hee_geo_long_v2_1.csv")
             if r["record_id"] in eligible and r["iso3"] not in ("", "NA") and r["is_special"] == "FALSE"}
    counts = Counter(iso for _, iso in pairs)
    known_oa = Counter(iso for rid, iso in pairs if eligible[rid]["is_oa"] not in ("", "NA"))
    national = read_csv(RAW / "denominator_gbd_source.csv")
    assert len(national) == 204 and len({r["iso3"] for r in national}) == 204
    national_ids = {r["iso3"] for r in national}
    burden = [c for c in countries if c["dalys"] is not None and c["dalys"] > 0]
    assert len(pairs) == sum(counts.values())
    assert len(set(zip(geo_web["s"], geo_web["c"]))) == sum(c["studies"] for c in countries)
    for c in countries:
        assert counts[c["iso3"]] == c["studies"]
    totals = {
        "countries_known_oa_at_least_5": sum(n >= 5 for n in known_oa.values()),
        "countries_at_least_5": sum(n >= 5 for n in counts.values()),
        "website_burden_and_studies": sum(c["studies"] > 0 for c in burden),
        "website_with_studies": sum(c["studies"] > 0 for c in countries),
        "website_with_burden": len(burden), "website_country_list": len(countries),
        "full_geography_countries": len(counts), "full_geography_pairs": len(pairs),
        "website_pairs": sum(c["studies"] for c in countries),
        "website_burden_pairs": sum(c["studies"] for c in burden),
        "national_gbd_country_list": len(national),
        "national_gbd_pairs": sum(counts[i] for i in national_ids),
        "national_gbd_countries_with_studies": sum(counts[i] > 0 for i in national_ids),
    }
    excluded = {i: n for i, n in counts.items() if i not in national_ids}
    assert totals["full_geography_pairs"] - sum(excluded.values()) == totals["national_gbd_pairs"]
    import textwrap
    hist = load_history()
    names = {c["iso3"]: c["country"] for c in countries}
    total_national_burden = sum(float(r["val"]) for r in national)
    deficits = []
    for r in national:
        iso = r["iso3"]
        expected = totals["national_gbd_pairs"] * float(r["val"]) / total_national_burden
        deficits.append({"iso3": iso, "country": names.get(iso, hist.get(iso, {}).get("country", iso)),
                         "observed": counts[iso], "expected": expected, "deficit": counts[iso] - expected})
    assert abs(sum(r["deficit"] for r in deficits)) < 1e-7
    selected = sorted(deficits, key=lambda r: r["deficit"])[:16] + sorted(deficits, key=lambda r: -r["deficit"])[:8]
    selected.sort(key=lambda r: r["deficit"])
    fig, ax = plt.subplots(figsize=(12, 10), facecolor=BG)
    fig.subplots_adjust(left=.22, right=.96, top=.84, bottom=.19)
    ax.set_facecolor(BG)
    current_group = lambda iso: "High income" if iso == "TWN" else {
        "L": GROUPS[0], "LM": GROUPS[1], "UM": GROUPS[2], "H": GROUPS[3]
    }.get(hist.get(iso, {}).get("FY27"))
    ax.barh([r["country"] for r in selected], [r["deficit"] for r in selected],
            color=[COLORS.get(current_group(r["iso3"]), "#999") for r in selected])
    ax.axvline(0, color="#333", lw=1)
    ax.grid(axis="x", alpha=.2)
    ax.set_xlabel("Observed study–country pairs minus burden-proportional expected pairs")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=COLORS[g], label=g) for g in GROUPS], loc="lower right", frameon=False)
    india = next(r for r in deficits if r["iso3"] == "IND")
    fig.text(.09, .89, f"India has {abs(india['deficit']):,.0f} fewer study–country pairs than a burden-proportional share.", fontsize=12)
    deficit_caption = (f"Base: all {totals['national_gbd_country_list']} national GBD 2023 locations, including "
                       f"zero-study locations; {totals['national_gbd_pairs']:,} unique study–country pairs. "
                       "Expected studies = this pair total × the country's share of DALYs across the same 204 locations. "
                       "Hong Kong, Cayman Islands, French Guiana and Guadeloupe have no row in the national GBD export "
                       "and their pairs are excluded. Bars show the 16 largest deficits and 8 largest surpluses. "
                       f"This larger country set differs from the {totals['website_with_burden']}-country website burden analysis ({totals['website_burden_pairs']:,} pairs). "
                       "Country colours use July 2026 income groups. Studies published 2010–2026, final year partial; "
                       "GBD 2023 all-cause DALYs. Proportionality is a reference point.")
    fig.text(.09, .035, textwrap.fill(deficit_caption, 138), va="bottom", fontsize=9, linespacing=1.5)
    updated_deficit = save(fig, "fig_deficit_checked", "Where research counts differ most from burden shares", deficit_caption)

    # Country-level inequality uses the July 2026 group, matching country views.
    # No study is assigned an invented single-country income for this summary.
    lm = sorted([c for c in burden if c["income"] != "High income"],
                key=lambda c: (c["studies"] / c["dalys"], c["studies"], c["iso3"]))
    total_s, total_b = sum(c["studies"] for c in lm), sum(c["dalys"] for c in lm)
    x = np.r_[0, np.cumsum([c["dalys"] for c in lm]) / total_b]
    y = np.r_[0, np.cumsum([c["studies"] for c in lm]) / total_s]
    k = int(np.searchsorted(x, .5))
    top_s = sorted(lm, key=lambda c: c["studies"], reverse=True)[:5]
    top_b = sorted(lm, key=lambda c: c["dalys"], reverse=True)[:5]
    share = lambda rows, col, denominator: sum(c[col] for c in rows) / denominator
    inequality = {
        "countries": len(lm), "pairs": total_s, "top_study_countries": [c["iso3"] for c in top_s],
        "top_study_evidence_share": share(top_s, "studies", total_s),
        "top_study_burden_share": share(top_s, "dalys", total_b),
        "top_burden_countries": [c["iso3"] for c in top_b],
        "top_burden_evidence_share": share(top_b, "studies", total_s),
        "top_burden_burden_share": share(top_b, "dalys", total_b),
        "least_served_countries_crossing_half": k, "least_served_burden_share": float(x[k]),
        "least_served_evidence_share": float(y[k]), "least_served_pairs": sum(c["studies"] for c in lm[:k]),
        "interpolated_evidence_share_at_half": float(np.interp(.5, x, y)),
        "gini": float(1 - np.sum(np.diff(x) * (y[1:] + y[:-1]))),
    }
    fig, ax = plt.subplots(figsize=(11, 9), facecolor=BG)
    fig.subplots_adjust(left=.1, right=.96, top=.78, bottom=.24)
    ax.set_facecolor(BG)
    ax.plot(x, y, color=COLORS["Low income"], lw=3)
    ax.fill_between(x, y, x, color=COLORS["Low income"], alpha=.12)
    ax.plot([0, 1], [0, 1], ls="--", color="#aaa398")
    ax.plot([x[k], x[k]], [0, y[k]], ls=":", color="#444")
    ax.scatter([x[k]], [y[k]], color="#222", zorder=5)
    ax.annotate(f"{k} least-served countries\n{x[k]:.1%} of burden; {y[k]:.1%} of evidence",
                (x[k], y[k]), xytext=(.60, .24), textcoords="axes fraction",
                arrowprops={"arrowstyle": "-", "color": "#555"}, fontsize=11)
    ax.set(xlim=(0, 1), ylim=(0, 1), xlabel="Cumulative share of LMIC disease burden (DALYs)",
           ylabel="Cumulative share of LMIC study–country pairs")
    for axis in [ax.xaxis, ax.yaxis]:
        axis.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
    ax.grid(alpha=.2)
    fig.text(.1, .88, f"The five countries with the most studies hold {share(top_s, 'studies', total_s):.1%} of evidence\n"
             f"and {share(top_s, 'dalys', total_b):.1%} of LMIC burden.", fontsize=13, va="top")
    caption = (f"Base: {len(lm)} LMIC countries with GBD 2023 all-cause DALYs; {total_s:,} study–country pairs; "
               f"{sum(c['studies'] == 0 for c in lm)} countries have no study. Countries ordered by studies per DALY. "
               f"The first {k} countries crossing 50% of burden carry {x[k]:.1%} of burden and "
               f"{inequality['least_served_pairs']:,} pairs ({y[k]:.1%}); the marker is at these actual coordinates. "
               f"The five countries with the greatest burden (India, China, Nigeria, Indonesia, Pakistan) instead carry "
               f"{share(top_b, 'dalys', total_b):.1%} of burden and {share(top_b, 'studies', total_s):.1%} of evidence. "
               f"Gini = {inequality['gini']:.2f}. Country grouping uses July 2026 income classifications; "
               "studies span 2010–2026, final year partial. Each multi-country study counts once per country.")
    fig.text(.1, .04, textwrap.fill(caption, 122), va="bottom", fontsize=9, linespacing=1.5)
    updated_inequality = save(fig, "fig_inequality_checked", "Research concentration within lower-income countries", caption)

    # Annual reach denominators change with each year's classification. The
    # geography is fixed, but unavailable country-year groups are excluded.
    ne = read_csv(RAW / "denominator_geography_source.csv")
    geography = {r["iso_a3_eh"] for r in ne if r["type"] in ("Sovereign country", "Country")
                 and r["iso_a3_eh"] not in ("", "-99")}
    first = {}
    for rid, iso in pairs:
        yr = int(eligible[rid]["year"])
        first[iso] = min(first.get(iso, yr), yr)
    web_ids = {c["iso3"] for c in countries}
    coverage = []
    for year in range(2010, 2026):
        for tag, ids in [("Website country list", web_ids), ("Natural Earth countries, no population floor", geography)]:
            for group in GROUPS:
                members = sorted(i for i in ids if group_at(hist, i, year) == group)
                reached = sum(first.get(i, 9999) <= year for i in members)
                coverage.append({"year": year, "universe": tag, "income": group,
                                 "countries": len(members), "reached": reached,
                                 "pct": 100 * reached / len(members) if members else None})
    last = [r for r in coverage if r["year"] == 2025]
    endpoint = {tag: {"countries": sum(r["countries"] for r in last if r["universe"] == tag),
                      "unreached": sum(r["countries"] - r["reached"] for r in last if r["universe"] == tag)}
                for tag in {r["universe"] for r in last}}
    fig, ax = plt.subplots(figsize=(12, 8), facecolor=BG)
    fig.subplots_adjust(left=.09, right=.96, top=.82, bottom=.27)
    ax.set_facecolor(BG)
    for group in GROUPS:
        for tag, style in [("Website country list", "-"), ("Natural Earth countries, no population floor", "--")]:
            rows = [r for r in coverage if r["income"] == group and r["universe"] == tag]
            ax.plot([r["year"] for r in rows], [r["pct"] for r in rows],
                    color=COLORS[group], ls=style, label=group if style == "-" else None, lw=2)
    ax.set(xlim=(2010, 2025), ylim=(0, 103), ylabel="Countries with at least one study (%)", xlabel="Publication year")
    ax.grid(alpha=.2)
    ax.legend(ncol=2, loc="lower right", frameon=False)
    w, a = endpoint["Website country list"], endpoint["Natural Earth countries, no population floor"]
    fig.text(.09, .89, "Solid: website country list. Dashed: Natural Earth country entities, no population floor.", fontsize=11)
    reach_caption = ("Cumulative reach through each publication year. Countries are grouped by the World Bank "
                     "classification in force on 1 January of that year; the denominator excludes unavailable "
                     "country-year groups. Taiwan uses the recorded high-income override. A country is reached "
                     "once any eligible study has named it by that year, including studies from its earlier income groups. "
                     f"In 2025, solid lines cover {w['countries']} classified countries from the 155-country website list "
                     f"({w['unreached']} unreached); dashed lines cover {a['countries']} classified/overridden Natural Earth "
                     f"Sovereign country/Country entities ({a['unreached']} unreached), with no population floor. "
                     "Denominators vary by year; 197 is not a fixed count of all World Bank economies. "
                     "2026 is partial and omitted, so the Ethiopia/Venezuela 2026 fallback does not affect these lines.")
    fig.text(.09, .035, textwrap.fill(reach_caption, 137), va="bottom", fontsize=9, linespacing=1.5)
    updated_reach = save(fig, "fig_reach_time_checked", "How country coverage changes over time", reach_caption)
    with (OUT / "country_reach_checked.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(coverage[0])); writer.writeheader(); writer.writerows(coverage)

    audit = {"master_sha256": hashlib.sha256(master_path.read_bytes()).hexdigest(),
             "eligible_studies": len(eligible), "counts": totals, "national_gbd_excluded_pairs": excluded,
             "inequality": inequality, "reach_2025": endpoint,
             "deficit_india": {"observed": india["observed"], "expected": india["expected"], "difference": india["deficit"]},
             "country_sets": {"website": sorted(web_ids), "website_burden": sorted(c['iso3'] for c in burden),
                              "national_gbd": sorted(national_ids)}}
    write_json(DATA / "denominator_audit.json", audit)
    content = read_json(DATA / "content.json")
    copy = read_json(DATA / "figure_copy.json")
    updates = read_json(DATA / "figure_updates.json")
    updates["fig_inequality.webp"] = updated_inequality
    updates["fig_reach_time.webp"] = updated_reach
    updates["fig_deficit.webp"] = updated_deficit
    replacements = {
        "fig_inequality.webp": caption, "fig_reach_time.webp": reach_caption,
        "fig_deficit.webp": deficit_caption,
    }
    for section in content["gallery"]:
        for entry in section["figs"]:
            file = entry["file"]
            if file in replacements:
                entry["caption"] = replacements[file]
                copy.setdefault(file, {})["caption"] = replacements[file]
            if file == "fig_worldmap.webp":
                entry["caption"] = entry["caption"].replace("31,774", f"{len(pairs):,}")
                copy.setdefault(file, {})["caption"] = entry["caption"]
    (DATA / "content.json").write_text(json.dumps(content, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    write_json(DATA / "figure_copy.json", copy)
    write_json(DATA / "figure_updates.json", updates)
    print(json.dumps({"counts": totals, "inequality": inequality, "reach_2025": endpoint}, indent=2))


if __name__ == "__main__":
    main()
