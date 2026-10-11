"""Build the "(Un)equal weight" at-a-glance infographic for the HEE evidence map.

Reads the web build in docs/data plus scripts/wb_regions.csv (World Bank
regions) and writes one self-contained interactive page,
docs/figures/fig_glance_regions.html, which the site embeds in the
"Maps & regional charts" Thematic analysis section.

Values the web data cannot supply are shown as "xx"; every "xx" (and every
figure that needs a caveat) carries a "?" button explaining why.

Usage:
    python scripts/build_glance_regions.py [--start 2010] [--end 2026]
"""
import argparse
import csv
import html
import json
import math
import os
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "docs", "data")
OUT = os.path.join(ROOT, "docs", "figures", "fig_glance_regions.html")
REGIONS_CSV = os.path.join(ROOT, "scripts", "wb_regions.csv")

REGION_ORDER = ["EAS", "ECS", "LCN", "MEA", "NAC", "SAS", "SSF"]
# Approximate label positions (lon, lat) for the black region tags on the map.
REGION_TAG_POS = {
    "NAC": (-100, 45), "LCN": (-62, -12), "ECS": (62, 56), "MEA": (30, 24),
    "SSF": (20, -6), "SAS": (78, 22), "EAS": (110, 32),
}
# Shape-only additions for the card silhouettes: World Bank members missing
# from the map's country data, so the outlines have no holes. Not counted.
SILHOUETTE_EXTRA = {
    "EAS": ["FJI", "BRN", "SLB", "VUT"],
    "ECS": ["KAZ", "ISL", "LUX", "MNE"],
    "LCN": ["CUB", "GUY", "SUR", "BLZ", "BHS"],
    "MEA": ["ISR", "PSE", "MLT"],
    "NAC": [],
    "SAS": ["BTN"],
    "SSF": ["CPV", "COM"],
}
# Fixed (lon, lat) windows for the silhouettes; fitting to the countries
# misbehaves where Russia and the Pacific cross the 180° meridian.
SILHOUETTE_VIEW = {
    "EAS": ((70, 180), (-48, 55)), "ECS": ((-25, 180), (34, 78)), "LCN": ((-118, -34), (-56, 33)),
    "MEA": ((-18, 63), (11, 40)), "NAC": ((-170, -52), (18, 72)), "SAS": ((60, 93), (5, 39)),
    "SSF": ((-26, 58), (-35, 26)),
}
# 14 harmonised disease groups -> GBD level-1 cause groups.
DISEASE_CATEGORY = {
    "Infectious": "Communicable", "Maternal & neonatal": "Communicable",
    "Injuries": "Injuries",
}  # every other group is non-communicable
CATEGORIES = ["Communicable", "Non-communicable", "Injuries"]
CAT_COLOURS = {"Communicable": "#3f8f80", "Non-communicable": "#8a63a8", "Injuries": "#d8a03c"}
# Diverging map ramp: under-represented (red) -> median (sand) -> high (blue).
MAP_COLOURS = [[0, "#c2412d"], [0.25, "#e58c6c"], [0.5, "#efe4d6"], [0.75, "#8d9fd3"], [1, "#4b64b4"]]
PLOTLY_SRC = "https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/plotly.min.js"
PLOTLY_SRI = "sha384-cCVCZkAjYNxaYKbM8lsArLznDF/SvMFr1jcZrvOpSTCa0W40ZAdLzHCEulnUa5i7"

# Explanations behind the "?" buttons.
NOTES = {
    "countries": "Countries in the map's country data named by at least one study in the period.",
    "model": "Share of studies with a clear label that are model-based (decision-analytic model) rather than measured in patients. "
             "Studies whose approach is unclear (about 4%) are left out of the base, as on the site's Overview.",
    "utility": "Share of studies that report QALYs.",
    "open_access": "Share of studies with a known open-access status (from OpenAlex, matched by DOI). Studies whose status could not be found are left out of the base.",
    "lmic": "Share of studies naming at least one country that name at least one low- or middle-income country (World Bank income groups). Studies naming no country are left out of the base.",
    "intensity": "Studies naming at least one country in the region, divided by the region's total disease burden (GBD 2023 all-cause DALYs, summed over its countries), per 100,000 DALYs. "
                 "The marker sits on the same colour scale as the map.",
    "disease": "Share of the region's disease-coded studies, split into communicable (infectious, maternal and neonatal), non-communicable and injuries. "
               "A study in several groups is split equally between them. Caveats: only about half of all studies have a disease group; "
               "asthma, allergies and autoimmune conditions are also coded as infectious, which overstates the communicable share; "
               "'metabolic & nutritional' (diabetes and malnutrition together) is counted as non-communicable because the data cannot separate them.",
    "top_diseases": "Not available yet. Each study's disease is recorded only as one or more of 14 broad groups "
                    "(e.g. cardiovascular, neoplasms, infectious, mental & substance use), so the data can say a study is about "
                    "'cardiovascular disease' but not whether it is about stroke, heart failure or hypertension. "
                    "The detailed disease terms (MeSH headings) that these groups were built from are not included in the map's data. "
                    "To fill this row, the source data needs either those MeSH headings mapped to specific GBD causes, "
                    "or the study-level research themes from the topic model (which name diseases such as malaria, HIV and dementia). "
                    "Until then, the top three of the 14 broad groups could be shown instead.",
    "utility_region": "Share of the region's studies that report QALYs. The red line is the share across all studies.",
    "trend": "Cumulative share of the region's countries (the 155 countries in the map's country data) "
             "named by at least one study, or by two or more, by each year. The grey line is the same for all regions combined. "
             "The final, partial year of data is left out.",
    "search_dates": "Search dates are not in the web data; they need to come from the review protocol.",
}


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def fmt_int(n):
    return f"{n:,}"


def pct(x):
    return f"{round(100 * x)}%"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--start", type=int, default=None, help="first publication year (default: first in data)")
    ap.add_argument("--end", type=int, default=None, help="last publication year (default: last in data)")
    args = ap.parse_args()

    dic = load("dict.json"); lv = dic["levels"]; meta = dic["meta"]
    st = load("studies.json"); geo = load("geo.json"); dis = load("disease.json")
    countries = load("countries.json")
    first_year, last_year = meta["years"]
    start = args.start or first_year
    end = args.end or last_year
    full_range = (start, end) == (first_year, last_year)

    with open(REGIONS_CSV, encoding="utf-8") as f:
        wb = {r["iso3"]: r for r in csv.DictReader(f)}
    region_name = {r["wb_region_code"]: r["wb_region"] for r in wb.values()}
    iso_of = lv["iso3"]
    cinfo = {c["iso3"]: c for c in countries}
    missing = [c["iso3"] for c in countries if c["iso3"] not in wb]
    if missing:
        raise SystemExit("No World Bank region for: " + ", ".join(missing))

    years = st["year"]
    in_range = [start <= y <= end for y in years]
    studies = [s for s in range(len(years)) if in_range[s]]
    n_studies = len(studies)

    # Study -> countries, restricted to the year range.
    s_isos = defaultdict(set)
    for s, c in zip(geo["s"], geo["c"]):
        if in_range[s]:
            s_isos[s].add(iso_of[c])
    s_groups = defaultdict(set)
    for s, g in zip(dis["s"], dis["g"]):
        if in_range[s]:
            s_groups[s].add(lv["disease_grp"][g])

    def share(col, label, pool, base_labels=None):
        code = lv[col].index(label)
        if base_labels:
            base_codes = {lv[col].index(b) for b in base_labels}
            pool = [s for s in pool if st[col][s] in base_codes]
        return (sum(1 for s in pool if st[col][s] == code) / len(pool)) if pool else None

    qaly_all = share("qaly_label", "Uses QALY", studies)
    # Same base as the site's Overview: studies with a clear model/measured label.
    model_all = share("model_label", "Model-based", studies, ["Model-based", "Measured"])
    oa_known = share("oa_label", "Open access", studies, ["Open access", "Not open"])
    linked = [s for s in studies if s_isos[s]]
    lmic = sum(1 for s in linked if any(cinfo[i]["income"] != "High income" for i in s_isos[s])) / len(linked)

    # ---- Map: studies per 100k DALYs per country ----
    per_country = defaultdict(int)
    for s in linked:
        for i in s_isos[s]:
            per_country[i] += 1
    map_rows = []
    for c in countries:
        if not c["dalys"]:
            continue
        n = per_country.get(c["iso3"], 0)
        map_rows.append({"iso3": c["iso3"], "country": c["country"], "n": n,
                         "rate": 1e5 * n / c["dalys"] if n else 0})
    rated = sorted(r["rate"] for r in map_rows if r["rate"] > 0)
    median = rated[len(rated) // 2]
    logs = [math.log10(r) for r in rated]
    half = max(abs(math.log10(median) - logs[int(0.05 * len(logs))]),
               abs(logs[int(0.95 * len(logs)) - 1] - math.log10(median)))
    zmin, zmax = math.log10(median) - half, math.log10(median) + half

    def scale_pos(rate):
        if not rate:
            return 0.0
        return min(1.0, max(0.0, (math.log10(rate) - zmin) / (zmax - zmin)))

    # ---- Regions ----
    reg_countries = defaultdict(list)
    for c in countries:
        reg_countries[wb[c["iso3"]]["wb_region_code"]].append(c["iso3"])
    trend_end = min(end, last_year - 1)  # final data year is partial
    trend_years = list(range(start, trend_end + 1))
    pairs_by_year = defaultdict(lambda: defaultdict(int))  # iso3 -> year -> new studies
    for s in linked:
        for i in s_isos[s]:
            pairs_by_year[i][years[s]] += 1

    def coverage(isos, min_n):
        out = []
        for y in trend_years:
            k = sum(1 for i in isos if sum(v for yy, v in pairs_by_year[i].items() if yy <= y) >= min_n)
            out.append(100 * k / len(isos))
        return out

    all_isos = [c["iso3"] for c in countries]
    trend_all = coverage(all_isos, 1)
    regions = []
    for code in REGION_ORDER:
        isos = set(reg_countries[code])
        rs = [s for s in linked if s_isos[s] & isos]
        dalys = sum(cinfo[i]["dalys"] or 0 for i in isos)
        rate = 1e5 * len(rs) / dalys if dalys else None
        cat = defaultdict(float)
        coded = [s for s in rs if s_groups[s]]
        for s in coded:
            cats = [DISEASE_CATEGORY.get(g, "Non-communicable") for g in s_groups[s]]
            for c in cats:
                cat[c] += 1 / len(cats)
        dshare = {c: (cat[c] / len(coded) if coded else None) for c in CATEGORIES}
        regions.append({
            "code": code, "name": region_name[code], "n": len(rs), "rate": rate,
            "pos": scale_pos(rate), "disease": dshare, "n_coded": len(coded),
            "qaly": share("qaly_label", "Uses QALY", rs),
            "trend1": coverage(sorted(isos), 1), "trend2": coverage(sorted(isos), 2),
        })

    page = render(locals())
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(page)
    print(f"wrote {OUT}: {n_studies:,} studies {start}-{end}")
    for r in regions:
        print(f"  {r['code']} n={r['n']:,} rate={r['rate']:.2f} qaly={r['qaly']:.0%} "
              + " ".join(f"{c[:4]}={v:.0%}" for c, v in r["disease"].items() if v is not None))


def help_btn(key):
    return (f'<button class="q" type="button" aria-label="What does this mean?" '
            f'data-note="{html.escape(NOTES[key], quote=True)}">?</button>')


def waffle(dshare):
    if dshare["Communicable"] is None:
        return '<div class="waffle-empty">xx</div>'
    raw = {c: 100 * dshare[c] for c in CATEGORIES}
    counts = {c: int(raw[c]) for c in CATEGORIES}
    for c in sorted(CATEGORIES, key=lambda c: raw[c] - counts[c], reverse=True)[:100 - sum(counts.values())]:
        counts[c] += 1
    dots = "".join(f'<i style="background:{CAT_COLOURS[c]}"></i>' for c in CATEGORIES for _ in range(counts[c]))
    labels = "".join(f'<span style="color:{CAT_COLOURS[c]}">{counts[c]}%</span>' for c in CATEGORIES)
    return f'<div class="waffle">{dots}</div><div class="waffle-labels">{labels}</div>'


def sparkline(years, r1, r2, rall):
    w, h, pad = 150, 74, 4
    def path(vals):
        n = len(vals)
        pts = [(pad + (w - 2 * pad) * i / max(1, n - 1), h - pad - (h - 2 * pad) * v / 100) for i, v in enumerate(vals)]
        return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts), pts[-1]
    pa, _ = path(rall)
    p1, e1 = path(r1)
    p2, e2 = path(r2)
    return (f'<svg class="spark" viewBox="0 0 {w + 34} {h + 14}" role="img" aria-label="Coverage trend">'
            f'<line x1="{pad}" x2="{w - pad}" y1="{h - pad}" y2="{h - pad}" stroke="#d9d3c7"/>'
            f'<line x1="{pad}" x2="{w - pad}" y1="{pad}" y2="{pad}" stroke="#ece6da"/>'
            f'<path d="{pa}" fill="none" stroke="#b3ada3" stroke-width="2"/>'
            f'<path d="{p2}" fill="none" stroke="#1d1d1d" stroke-width="1.6" stroke-dasharray="4 3"/>'
            f'<path d="{p1}" fill="none" stroke="#1d1d1d" stroke-width="1.8"/>'
            f'<text x="{e1[0] + 4:.1f}" y="{e1[1] + 3:.1f}">{round(r1[-1])}%</text>'
            f'<text x="{e2[0] + 4:.1f}" y="{e2[1] + 9:.1f}">{round(r2[-1])}%</text>'
            f'<text x="{pad}" y="{h + 12}">{years[0]}</text>'
            f'<text x="{w - pad}" y="{h + 12}" text-anchor="end">{years[-1]}</text></svg>')


def render(v):
    start, end, regions = v["start"], v["end"], v["regions"]
    period = f"{start}–{end}"
    kpis = [
        (fmt_int(v["n_studies"]), f"health economic evaluations, {period}", None),
        (fmt_int(sum(1 for i in v["per_country"] if v["per_country"][i] > 0)),
         "countries profiled in the map with at least one", "countries"),
        (pct(v["qaly_all"]), "report a utility measure such as the QALY", "utility"),
        (pct(v["model_all"]), "are model-based", "model"),
        (pct(v["oa_known"]), "are open access", "open_access"),
        (pct(v["lmic"]), "focus on low- and middle-income countries", "lmic"),
    ]
    kpi_html = "".join(
        f'<div class="kpi"><div class="kpi-v">{html.escape(val)}{help_btn(k) if k else ""}</div>'
        f'<div class="kpi-l">{html.escape(lab)}</div></div>' for val, lab, k in kpis)

    qaly_global = v["qaly_all"]
    cards = []
    for r in regions:
        top3 = "".join(
            '<div class="dz"><span class="dz-icon"></span><span class="dz-name">xx</span>'
            '<span class="dz-v">xx%</span><div class="dz-bar"><b style="width:0"></b></div></div>' for _ in range(3))
        qaly = r["qaly"]
        cards.append(f"""
      <div class="card" style="--accent:{_accent(r['pos'])}">
        <div class="sil" id="sil-{r['code']}" aria-hidden="true"></div>
        <h3>{html.escape(r['name'])}</h3>
        <div class="tagline"><span class="tag">{r['code']}</span> n = {fmt_int(r['n'])}</div>
        <div class="row row-scale">
          <div class="scale"><span class="marker" style="left:{100 * r['pos']:.1f}%"></span></div>
          <div class="scale-v">{r['rate']:.2f} per 100,000 DALYs</div>
        </div>
        <div class="row row-waffle">{waffle(r['disease'])}</div>
        <div class="row row-top3">{top3}</div>
        <div class="row row-utility">
          <div class="big">{pct(qaly)}</div>
          <div class="ubar"><b style="width:{100 * qaly:.1f}%"></b><span class="avg" style="left:{100 * qaly_global:.1f}%"></span></div>
        </div>
        <div class="row row-trend">{sparkline(v['trend_years'], r['trend1'], r['trend2'], v['trend_all'])}</div>
      </div>""")

    map_data = {
        "rows": v["map_rows"], "zmin": v["zmin"], "zmax": v["zmax"], "median": v["median"],
        "colours": MAP_COLOURS,
        "tags": [{"code": c, "lon": REGION_TAG_POS[c][0], "lat": REGION_TAG_POS[c][1]} for c in REGION_ORDER],
        "silhouettes": {c: {"isos": sorted(v["reg_countries"][c]) + SILHOUETTE_EXTRA[c],
                            "lon": SILHOUETTE_VIEW[c][0], "lat": SILHOUETTE_VIEW[c][1]} for c in REGION_ORDER},
    }
    built = v["meta"]["built"]
    return TEMPLATE.format(
        period=period, kpis=kpi_html, cards="".join(cards), built=built,
        median=f"{v['median']:.2f}",
        map_json=json.dumps(map_data, separators=(",", ":")),
        plotly_src=PLOTLY_SRC, plotly_sri=PLOTLY_SRI,
        q_intensity=help_btn("intensity"), q_disease=help_btn("disease"),
        q_top=help_btn("top_diseases"), q_utility=help_btn("utility_region"),
        q_trend=help_btn("trend"), q_search=help_btn("search_dates"),
        n_countries=len(v["countries"]), trend_end=v["trend_end"],
    )


def _accent(pos):
    # Card top border follows the region's place on the map scale.
    stops = MAP_COLOURS
    for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
        if pos <= p1:
            t = (pos - p0) / (p1 - p0) if p1 > p0 else 0
            a = [int(c0[i:i + 2], 16) for i in (1, 3, 5)]
            b = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
            return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))
    return stops[-1][1]


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>(Un)equal weight at a glance</title>
<style>
:root {{ --ink:#1d1d1d; --muted:#6b665d; --line:#d9d3c7; --bg:#f7f3ec; --card:#ece6dc; --red:#c2412d; }}
* {{ box-sizing: border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink); font:14px/1.45 Inter, "Segoe UI", Arial, sans-serif; }}
.wrap {{ max-width:1200px; margin:0 auto; padding:28px 24px 32px; }}
.eyebrow {{ display:flex; justify-content:space-between; align-items:center; font-size:11px; letter-spacing:.12em; text-transform:uppercase; color:var(--red); font-weight:700; }}
.badge {{ background:#f2dc9b; color:#5c4a12; padding:4px 10px; border-radius:4px; letter-spacing:.04em; }}
h1 {{ font:800 34px/1.12 "Arial Narrow", "Roboto Condensed", Inter, sans-serif; font-stretch:condensed; margin:14px 0 10px; }}
.lede {{ color:#3b3832; font-size:16px; max-width:820px; margin:0 0 26px; }}
.sec {{ display:flex; align-items:center; gap:10px; margin:22px 0 6px; }}
.sec b {{ background:var(--ink); color:#fff; font-size:11px; width:20px; height:20px; display:inline-flex; align-items:center; justify-content:center; border-radius:3px; }}
.sec h2 {{ font:800 20px/1 "Arial Narrow", "Roboto Condensed", Inter, sans-serif; font-stretch:condensed; text-transform:uppercase; margin:0; }}
.sec span {{ color:var(--muted); font-size:12px; }}
#map {{ height:520px; }}
.kpis {{ display:grid; grid-template-columns:repeat(6, minmax(0, 1fr)); border-top:1.5px solid var(--ink); border-bottom:1px solid var(--line); margin-top:8px; }}
.kpi {{ padding:16px 14px 14px; border-left:1px solid var(--line); }}
.kpi:first-child {{ border-left:0; padding-left:0; }}
.kpi-v {{ font:800 36px/1 "Arial Narrow", "Roboto Condensed", Inter, sans-serif; font-stretch:condensed; display:flex; align-items:flex-start; gap:4px; }}
.kpi-l {{ color:var(--muted); font-size:12px; margin-top:8px; }}
.regions {{ display:grid; grid-template-columns:150px repeat(7, minmax(118px, 1fr)); gap:10px; overflow-x:auto; padding-bottom:6px; }}
.labels {{ display:grid; grid-template-rows:var(--rows); padding-top:17px; }}
.lab {{ font-size:11px; color:var(--muted); padding-right:6px; }}
.lab strong {{ display:block; color:var(--ink); font:800 15px/1.1 "Arial Narrow", "Roboto Condensed", Inter, sans-serif; text-transform:uppercase; margin-bottom:4px; }}
.lab .key {{ display:flex; align-items:center; gap:5px; }}
.lab .key i {{ width:9px; height:9px; border-radius:2px; display:inline-block; }}
.wrap {{ --rows: 62px 40px 24px 58px 150px 140px 92px 104px; }}
.sil {{ height:58px; }}
.card {{ display:grid; grid-template-rows:var(--rows); background:var(--card); border-radius:10px; border-top:5px solid var(--accent); padding:12px 10px; min-width:0; }}
.card h3 {{ font:800 14px/1.15 "Arial Narrow", "Roboto Condensed", Inter, sans-serif; text-transform:uppercase; text-align:center; margin:0; align-self:center; }}
.tag {{ background:var(--ink); color:#fff; font-size:10px; font-weight:700; padding:2px 5px; border-radius:3px; }}
.row-scale, .tagline {{ font-size:11px; text-align:center; color:#3b3832; }}
.scale {{ position:relative; height:6px; margin:10px 6px 6px; border-radius:3px; background:linear-gradient(90deg,#c2412d,#e58c6c,#efe4d6,#8d9fd3,#4b64b4); }}
.marker {{ position:absolute; top:-4px; width:9px; height:14px; margin-left:-4.5px; background:var(--ink); border-radius:4px; border:1.5px solid #fff; }}
.scale-v {{ font-size:10.5px; color:var(--muted); }}
.waffle {{ display:grid; grid-template-columns:repeat(10, 1fr); gap:2px; width:100%; max-width:112px; margin:6px auto 0; }}
.waffle i {{ display:block; aspect-ratio:1; border-radius:50%; }}
.waffle-labels {{ display:flex; justify-content:space-around; font-size:11px; font-weight:700; margin-top:5px; }}
.waffle-empty, .xx {{ font-weight:700; color:var(--muted); text-align:center; }}
.dz {{ display:grid; grid-template-columns:22px 1fr auto; gap:2px 6px; align-items:center; font-size:11px; margin-bottom:6px; }}
.dz-icon {{ width:20px; height:20px; border-radius:50%; background:#d6d0c5; grid-row:span 2; }}
.dz-name, .dz-v {{ color:var(--muted); font-weight:700; }}
.dz-bar {{ grid-column:2 / 4; height:4px; background:#d6d0c5; border-radius:2px; }}
.big {{ font:800 26px/1 "Arial Narrow", "Roboto Condensed", Inter, sans-serif; text-align:center; margin:8px 0 8px; }}
.ubar {{ position:relative; height:16px; border-radius:8px; background:#cbc5ba; overflow:visible; }}
.ubar b {{ display:block; height:100%; border-radius:8px; background:var(--ink); }}
.ubar .avg {{ position:absolute; top:-3px; width:2.5px; height:22px; margin-left:-1.25px; background:var(--red); }}
.spark {{ width:100%; height:auto; overflow:visible; }}
.spark text {{ font-size:9px; fill:#3b3832; }}
.foot {{ display:flex; justify-content:space-between; gap:24px; border-top:1px solid var(--line); margin-top:22px; padding-top:12px; font-size:11px; color:var(--muted); }}
.foot p {{ margin:0 0 4px; }}
.q {{ display:inline-flex; align-items:center; justify-content:center; width:16px; height:16px; flex:0 0 16px; padding:0; border:1px solid #8a8378; border-radius:50%; background:#fff; color:#5d574e; font:700 10px/1 Inter, Arial, sans-serif; cursor:pointer; vertical-align:middle; }}
.q:hover, .q[aria-expanded="true"] {{ background:var(--ink); color:#fff; border-color:var(--ink); }}
#pop {{ position:absolute; z-index:10; max-width:300px; padding:10px 12px; background:#fff; border:1px solid var(--line); border-radius:8px; box-shadow:0 8px 24px rgba(0,0,0,.14); font-size:12px; line-height:1.45; color:#2e2b26; display:none; }}
@media (max-width: 900px) {{ .kpis {{ grid-template-columns:repeat(3, minmax(0, 1fr)); }} .kpi {{ border-top:1px solid var(--line); }} #map {{ height:360px; }} h1 {{ font-size:26px; }} }}
</style>
</head>
<body>
<div class="wrap">
  <div class="eyebrow"><span>HEE evidence map</span><span class="badge">Draft · data as of {built}</span></div>
  <h1>(Un)equal weight: Health economic research output compared to disease burden</h1>
  <p class="lede">Research intensity is concentrated in high-income countries, where systems are more likely to be in place to evaluate evidence and use it to inform benefit decisions.</p>

  <div class="sec"><b>A</b><h2>Research intensity by country</h2><span>Evaluations per 100,000 DALYs · median {median}</span>{q_intensity}</div>
  <div id="map"></div>

  <div class="kpis">{kpis}</div>

  <div class="sec"><b>B</b><h2>Profile of evaluations by region</h2><span>Each card matches the black region tag on the map</span></div>
  <div class="regions">
    <div class="labels">
      <div></div><div></div><div></div>
      <div class="lab">Marker shows where each region falls on the map's colour scale {q_intensity}</div>
      <div class="lab"><strong>Disease focus {q_disease}</strong>Share of disease-coded evaluations. 1 dot = 1%
        <span class="key"><i style="background:#3f8f80"></i>Communicable</span>
        <span class="key"><i style="background:#8a63a8"></i>Non-communicable</span>
        <span class="key"><i style="background:#d8a03c"></i>Injuries</span></div>
      <div class="lab"><strong>Top three diseases {q_top}</strong>Bar = share of evaluations</div>
      <div class="lab"><strong>Utility measure as an outcome {q_utility}</strong>Black = QALY reported; red line = all-study average</div>
      <div class="lab"><strong>Trend over time {q_trend}</strong>% of the region's countries with an evaluation: solid = at least 1, dashed = 2 or more, grey = all regions (at least 1)</div>
    </div>
    {cards}
  </div>

  <div class="foot">
    <div>
      <p>Data: HEE evidence map web build ({built}); {period} publication years. Search dates: xx {q_search}</p>
      <p>Regions: World Bank (EAS East Asia &amp; Pacific, ECS Europe &amp; Central Asia, LCN Latin America &amp; Caribbean, MEA Middle East &amp; North Africa, NAC North America, SAS South Asia, SSF Sub-Saharan Africa). Map and trend lines cover the {n_countries} countries in the map's country data; trends run to {trend_end}.</p>
      <p>Burden: GBD 2023 all-cause DALYs. Utility measure: QALY reported. Disease groups: 14 harmonised groups from MeSH, grouped into GBD level-1 causes. Map: Robinson projection; grey = no eligible evaluation or no country data.</p>
    </div>
  </div>
</div>
<div id="pop" role="dialog"></div>
<script src="{plotly_src}" integrity="{plotly_sri}" crossorigin="anonymous"></script>
<script>
const MAP = {map_json};
(function () {{
  const rows = MAP.rows;
  const z = rows.map(r => r.rate > 0 ? Math.log10(r.rate) : null);
  const text = rows.map(r => r.country + "<br>" + r.n.toLocaleString("en-GB") + " studies" +
    (r.rate > 0 ? "<br>" + r.rate.toFixed(2) + " per 100,000 DALYs" : "<br>no eligible evaluation"));
  const none = rows.filter(r => r.rate === 0);
  window.Plotly.newPlot("map", [
    {{ type: "choropleth", locations: rows.filter(r => r.rate > 0).map(r => r.iso3),
       z: z.filter(v => v !== null), text: text.filter((t, i) => rows[i].rate > 0), hoverinfo: "text",
       zmin: MAP.zmin, zmax: MAP.zmax, colorscale: MAP.colours,
       marker: {{ line: {{ color: "#ffffff", width: 0.4 }} }},
       colorbar: {{ title: {{ text: "per 100,000<br>DALYs", font: {{ size: 11 }} }}, thickness: 10, len: 0.55, x: 0.02, y: 0.3,
         tickvals: [MAP.zmin, Math.log10(MAP.median), MAP.zmax], ticktext: ["low", "median", "high"] }} }},
    {{ type: "choropleth", locations: none.map(r => r.iso3), z: none.map(() => 0), showscale: false,
       text: none.map(r => r.country + "<br>no eligible evaluation"), hoverinfo: "text",
       colorscale: [[0, "#dcd6cc"], [1, "#dcd6cc"]], marker: {{ line: {{ color: "#ffffff", width: 0.4 }} }} }},
    // Region tags: black boxes, then their white codes on top.
    {{ type: "scattergeo", lon: MAP.tags.map(t => t.lon), lat: MAP.tags.map(t => t.lat), mode: "markers",
       marker: {{ symbol: "square", size: 30, color: "#1d1d1d" }}, hoverinfo: "skip" }},
    {{ type: "scattergeo", lon: MAP.tags.map(t => t.lon), lat: MAP.tags.map(t => t.lat), mode: "text",
       text: MAP.tags.map(t => "<b>" + t.code + "</b>"), hoverinfo: "skip",
       textfont: {{ color: "#ffffff", size: 11 }} }}
  ], {{
    margin: {{ t: 0, b: 0, l: 0, r: 0 }}, showlegend: false, paper_bgcolor: "rgba(0,0,0,0)",
    font: {{ family: "Inter, Segoe UI, Arial, sans-serif" }},
    geo: {{ projection: {{ type: "robinson" }}, showframe: false, showcoastlines: false, showland: true,
           landcolor: "#e6e1d8", showcountries: true, countrycolor: "#ffffff", bgcolor: "rgba(0,0,0,0)",
           lataxis: {{ range: [-58, 85] }} }}
  }}, {{ responsive: true, displayModeBar: false }});
}})();
// Region silhouettes above each card: the region's countries filled black
// in a fixed window (same country outlines as the main map).
for (const [code, sil] of Object.entries(MAP.silhouettes)) {{
  window.Plotly.newPlot("sil-" + code, [{{
    type: "choropleth", locations: sil.isos, z: sil.isos.map(() => 1), showscale: false, hoverinfo: "skip",
    colorscale: [[0, "#1d1d1d"], [1, "#1d1d1d"]], marker: {{ line: {{ color: "#1d1d1d", width: 0.4 }} }}
  }}], {{
    margin: {{ t: 0, b: 0, l: 0, r: 0 }}, paper_bgcolor: "rgba(0,0,0,0)",
    geo: {{ visible: false, projection: {{ type: "mercator" }}, bgcolor: "rgba(0,0,0,0)",
           lonaxis: {{ range: sil.lon }}, lataxis: {{ range: sil.lat }} }}
  }}, {{ staticPlot: true, responsive: true }});
}}
// "?" notes: click to open, click elsewhere or Esc to close.
(function () {{
  const pop = document.getElementById("pop");
  let open = null;
  const close = () => {{ pop.style.display = "none"; if (open) open.setAttribute("aria-expanded", "false"); open = null; }};
  document.addEventListener("click", e => {{
    const b = e.target.closest(".q");
    if (!b) {{ if (!pop.contains(e.target)) close(); return; }}
    if (open === b) {{ close(); return; }}
    close();
    pop.textContent = b.dataset.note;
    pop.style.display = "block";
    const r = b.getBoundingClientRect();
    const left = Math.min(window.scrollX + r.left, window.scrollX + document.documentElement.clientWidth - pop.offsetWidth - 12);
    pop.style.left = Math.max(8, left) + "px";
    pop.style.top = (window.scrollY + r.bottom + 6) + "px";
    b.setAttribute("aria-expanded", "true");
    open = b;
  }});
  document.addEventListener("keydown", e => {{ if (e.key === "Escape") close(); }});
}})();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
