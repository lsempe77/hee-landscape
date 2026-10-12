"""Build neutral global funder figures and a separate Wellcome-specific view.

Run: python scripts/build_wellcome_analysis.py [--raw data/raw]
Requires matplotlib. All inputs are validated and all outputs staged before
replacing published files. Raw records stay in data/raw; public outputs contain
aggregate counts and a title-screen audit of already-public publications.
"""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import html
import json
import os
from pathlib import Path
import re
import tempfile
import textwrap

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data"
OUT = ROOT / "docs" / "figures"
SECTION = "Wellcome-specific analysis"
INCOMES = ["High-income setting", "Low- & middle-income setting", "Other scope / income unavailable"]
COLORS = ["#2a78d6", "#eb6834", "#b3aea5"]
PRIORITIES = {
    "infectious": ("Infectious Diseases", "https://wellcome.org/our-priorities/infectious-disease",
                   "Broad proxy: studies tagged Infectious in the map's harmonised disease groups. Missing disease tags are not treated as evidence of absence."),
    "mental": ("Mental Health", "https://wellcome.org/our-priorities/mental-health",
               "Broad proxy: the map's Mental & substance use group. It includes substance use and is wider than Wellcome's focus on early intervention in anxiety, depression and psychosis. A separate focus-condition title screen is reported below."),
    "climate": ("Climate & Health", "https://wellcome.org/our-priorities/climate-and-health",
                "Provisional title screen: explicit climate, greenhouse gas, carbon footprint/tax, heat-health, wildfire or cold-weather-plan terms. This includes health-sector emissions studies. It is not a validated climate-change attribution or programme-eligibility classification; relevant studies may be missed."),
}
CLIMATE = re.compile(r"\bclimat(?:e|ic)\b|global warming|greenhouse gas|carbon (?:footprint|tax)|decarbon|heat[ -]?wave|heat[ -]related|heat mitigation|heat[ -]health|heat stress|heat risks|heat warning|wildfire|cold weather plan|representative concentration pathways", re.I)
CLIMATE_EXCLUSIONS = re.compile(r"climate schools|tropical and subtropical climate settings", re.I)
MENTAL_FOCUS = re.compile(r"\banxiet\w*|\bdepress\w*|\bpsychos\w*|\bpsychoti\w*|\bschizophren\w*", re.I)
PLACEHOLDERS = re.compile(r"^(?:na|n/a|none\.?|unknown|not (?:reported|available|applicable|stated)|no (?:funding|funder|external funding)|self[ -]funded|self[ -]funding)[.!]?$", re.I)


def clean(value):
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def normalize_funder(value):
    value = clean(value)
    if not value or PLACEHOLDERS.fullmatch(value):
        return None
    low = value.casefold()
    if re.match(r"^(?:none\b|no (?:specific |external )?funding\b|self[ -]funded\b|not funded\b|not available\b)", low):
        return None
    # This is a separate US foundation, not Wellcome Trust.
    if re.search(r"burroughs[ -]+wellcome", low):
        return "Burroughs Wellcome Fund"
    if re.search(r"\bwellcome\b", low):
        return "Wellcome Trust"
    rules = [
        (r"health technology assessment", "NIHR HTA Programme"),
        (r"national institute for health(?: and care)? research|^nihr$", "NIHR"),
        (r"national institutes of health|^nih$", "US NIH"),
        (r"gates foundation", "Gates Foundation"),
        (r"^medical research council$|medical research council.*(?:uk|united kingdom)", "UK MRC"),
        (r"national natural science foundation of china", "NSFC (China)"),
        (r"national health and medical research council|^nhmrc$", "NHMRC (Australia)"),
        (r"health research council of new zealand", "HRC (New Zealand)"),
        (r"^pfizer(?: inc\.?)?$", "Pfizer"),
        (r"^astrazeneca(?: ab| uk| plc)?$", "AstraZeneca"),
        (r"^zonmw$", "ZonMw"),
    ]
    for pattern, name in rules:
        if re.search(pattern, low):
            return name
    return value


def funders_of(value):
    names = set()
    for item in value.split(";"):
        normalized = normalize_funder(item)
        if normalized:
            names.add(normalized)
        # Keep explicitly named cofunders in joint Wellcome strings.
        if normalized == "Wellcome Trust":
            for pattern, name in [(r"\broyal society\b", "Royal Society"),
                                  (r"\bmedical research council\b", "UK MRC"),
                                  (r"\bnihr\b|national institute for health", "NIHR")]:
                if re.search(pattern, item, re.I):
                    names.add(name)
    return names


def load_inputs(raw):
    master_path = raw / "hee_analysis_master.csv"
    required = [master_path, DATA / "dict.json", DATA / "content.json"]
    missing = [str(p) for p in required if not p.is_file() or p.stat().st_size == 0]
    if missing:
        raise ValueError("Missing or empty inputs: " + ", ".join(missing))
    meta = json.loads((DATA / "dict.json").read_text(encoding="utf-8"))["meta"]
    content = json.loads((DATA / "content.json").read_text(encoding="utf-8"))
    with master_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = {"record_id", "is_eligible", "title", "year", "funders", "income_broad", "geo_scope", "disease_groups", "url"}
        if not fields.issubset(reader.fieldnames or []):
            raise ValueError("The analysis master lacks required columns: " + ", ".join(sorted(fields - set(reader.fieldnames or []))))
        all_rows = list(reader)
    if len({r["record_id"] for r in all_rows}) != len(all_rows) or any(not r["record_id"] for r in all_rows):
        raise ValueError("Analysis-master record IDs must be present and unique.")
    rows = [r for r in all_rows if r["is_eligible"] == "TRUE"]
    if len(rows) != meta["n_studies"] or not rows:
        raise ValueError(f"Eligible count {len(rows)} does not match web data {meta['n_studies']}; rebuild the matching dataset first.")
    for r in rows:
        if not r["title"] or not r["year"].isdigit() or not meta["years"][0] <= int(r["year"]) <= meta["years"][1]:
            raise ValueError("Invalid title or publication year for " + r["record_id"])
        if r["income_broad"] not in ("NA", "", "High income", "Low & middle income"):
            raise ValueError("Unrecognised income classification for " + r["record_id"])
        r["named_funders"] = funders_of(r["funders"])
        r["wellcome"] = "Wellcome Trust" in r["named_funders"]
        r["setting"] = (0 if r["income_broad"] == "High income" else 1) if r["geo_scope"] == "single_country" and r["income_broad"] in ("High income", "Low & middle income") else 2
        disease = set(r["disease_groups"].split(";"))
        r["themes"] = {k for k, match in [("infectious", "Infectious" in disease),
                                           ("mental", "Mental & substance use" in disease),
                                           ("climate", bool(CLIMATE.search(r["title"])) and not CLIMATE_EXCLUSIONS.search(r["title"]))] if match}
    entries = [f for s in content["gallery"] for f in s["figs"] if f["file"] in ("fig_funder_funders.webp", "fig_funder_funders.svg")]
    if not entries:
        raise ValueError("The gallery has no general funder figure to update.")
    return rows, meta, content, entries, hashlib.sha256(master_path.read_bytes()).hexdigest()


def donor_counts(rows):
    counts = defaultdict(lambda: [0, 0, 0])
    for r in rows:
        for name in r["named_funders"]:
            counts[name][r["setting"]] += 1
    return sorted(({"funder": name, "n": sum(values), "income_counts": values} for name, values in counts.items()), key=lambda d: (-d["n"], d["funder"].casefold()))


def stats(rows):
    return {"n": len(rows), "named_funder": sum(bool(r["named_funders"]) for r in rows),
            "wellcome": sum(r["wellcome"] for r in rows),
            "income_counts": [sum(r["setting"] == i for r in rows) for i in range(3)],
            "wellcome_income_counts": [sum(r["wellcome"] and r["setting"] == i for r in rows) for i in range(3)]}


def build_analysis(rows, meta, source_hash):
    themes = {}
    for key, (label, url, definition) in PRIORITIES.items():
        subset = [r for r in rows if key in r["themes"]]
        themes[key] = {"label": label, "url": url, "definition": definition, **stats(subset), "donors": donor_counts(subset)}
    wellcome = [r for r in rows if r["wellcome"]]
    focus = [r for r in rows if MENTAL_FOCUS.search(r["title"])]
    return {"meta": {"years": meta["years"], "data_built": meta["built"], "master_sha256": source_hash,
                      "unit": "Unique eligible studies naming each funder; no grant amounts or causal attribution.",
                      "theme_overlap": True, "sources_accessed": "2026-10-12"},
            "global": stats(rows), "wellcome": stats(wellcome), "themes": themes,
            "mental_focus_title_screen": stats(focus),
            "wellcome_outside_themes": sum(not r["themes"] for r in wellcome),
            "disease_tagged": sum(r["disease_groups"] not in ("", "NA") for r in rows),
            "donors": donor_counts(rows),
            "wellcome_by_year": [{"year": y, "n": sum(int(r["year"]) == y for r in wellcome)} for y in range(meta["years"][0], meta["years"][1] + 1)]}


def plots(analysis, staging):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator
    background = "#f7f4ee"
    donors = analysis["donors"][:15]
    fig, ax = plt.subplots(figsize=(14, 9), facecolor=background)
    ax.set_facecolor(background)
    left = [0] * len(donors)
    for i, (label, color) in enumerate(zip(INCOMES, COLORS)):
        values = [d["income_counts"][i] for d in donors]
        ax.barh(range(len(donors)), values, left=left, color=color, height=.7, label=label)
        left = [a + b for a, b in zip(left, values)]
    ax.set_yticks(range(len(donors)), [textwrap.fill(d["funder"], 38) for d in donors], fontsize=10)
    for y, d in enumerate(donors):
        ax.text(d["n"] + 8, y, f"{d['n']:,}", va="center", fontsize=10)
    ax.invert_yaxis()
    ax.set_xlim(0, max(d["n"] for d in donors) * 1.15)
    ax.set_xlabel("Studies naming the funder (a study may name several)", fontsize=11, labelpad=12)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.grid(axis="x", alpha=.16)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.legend(loc="lower left", bbox_to_anchor=(-.38, 1.02), ncol=3, frameon=False, fontsize=9)
    fig.subplots_adjust(left=.31, right=.96, top=.79, bottom=.2)
    fig.text(.025, .95, "Top dollar: who funds economic evaluations, and where?", fontsize=22, fontweight="bold", color="#10243e")
    fig.text(.025, .905, "Top 15 recorded funders, ranked by unique eligible studies", fontsize=14, color="#33475f")
    n = analysis["global"]["n"]
    known = analysis["global"]["named_funder"]
    notes = (f"Base: {n:,} eligible evaluations; {known:,} ({100 * known / n:.1f}%) name a funder. "
             "Counts describe recorded acknowledgements, not funding amounts.\n"
             "Blue and orange: single-country studies with known income. Grey: other geographic scope or unavailable income.\n"
             "Names are lightly normalised and counted once per study; funding coverage is incomplete.\n"
             f"Publication years {analysis['meta']['years'][0]}–{analysis['meta']['years'][1]} (final year partial).")
    fig.text(.025, .04, notes, fontsize=10, color="#5a564d", linespacing=1.6)
    fig.savefig(staging / "fig_funder_funders.svg", facecolor=background)
    fig.savefig(staging / "fig_funder_funders.png", dpi=110, facecolor=background)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(12, 6), facecolor=background)
    ax.set_facecolor(background)
    themes = list(analysis["themes"].values())
    values = [t["wellcome"] for t in themes]
    labels = ["Infectious Diseases\n(mapped disease group)", "Mental Health\n(mental & substance use proxy)", "Climate & Health\n(provisional title screen)"]
    ax.barh(range(3), values, color="#705a84", height=.55)
    ax.set_yticks(range(3), labels, fontsize=11)
    ax.invert_yaxis()
    total = analysis["wellcome"]["n"]
    for y, value in enumerate(values):
        ax.text(value + 1, y, f"{value} {'study' if value == 1 else 'studies'} ({100 * value / total:.1f}%)", va="center", fontsize=11)
    ax.set_xlim(0, max(1, max(values)) * 1.55)
    ax.set_xlabel("Studies naming Wellcome Trust", fontsize=11)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.grid(axis="x", alpha=.15)
    ax.set_axisbelow(True)
    fig.subplots_adjust(left=.31, right=.97, top=.74, bottom=.25)
    fig.text(.025, .93, "Wellcome-specific analysis: priority themes", fontsize=22, fontweight="bold", color="#10243e")
    fig.text(.025, .84, f"{total:,} eligible evaluations name Wellcome Trust as a funder", fontsize=16, color="#705a84")
    fig.text(.025, .05, "Shares use all studies naming Wellcome as the denominator. Themes can overlap.\n"
             "Theme matches are proxies, not confirmed Wellcome programme membership; missing tags can hide relevant studies.\n"
             "Recorded funder names are incomplete and do not establish exclusive support, grant value or impact.", fontsize=10, color="#5a564d", linespacing=1.6)
    fig.savefig(staging / "fig_wellcome_priorities.svg", facecolor=background)
    fig.savefig(staging / "fig_wellcome_priorities.png", dpi=110, facecolor=background)
    plt.close(fig)


def escape(value):
    return html.escape(str(value), quote=True)


def pct(n, total):
    return f"{100 * n / total:.1f}%" if total else "Not estimable"


def report(analysis, rows):
    total = analysis["global"]["n"]
    wellcome = analysis["wellcome"]["n"]
    buttons, panels = [], []
    for index, (key, t) in enumerate(analysis["themes"].items()):
        buttons.append(f'<button type="button" aria-pressed="{str(index == 0).lower()}" aria-controls="theme-{key}" data-theme="{key}">{escape(t["label"])}</button>')
        metrics = ''.join(f'<div class="metric"><strong>{value}</strong><span>{escape(label)}</span></div>' for value, label in [
            (f"{t['n']:,}", "Eligible theme studies"),
            (f"{t['named_funder']:,} · {pct(t['named_funder'], t['n'])}", "Theme studies naming any funder"),
            (f"{t['wellcome']:,}", "Theme studies naming Wellcome"),
            (pct(t['wellcome'], t['named_funder']), "Wellcome share among theme studies naming a funder")])
        max_n = max([d["n"] for d in t["donors"]] or [1])
        top = t["donors"][:10]
        donor_rows = []
        for d in top:
            segments = ''.join(f'<span style="width:{100 * count / max_n:.4f}%;background:{color}"></span>' for count, color in zip(d["income_counts"], COLORS))
            donor_rows.append(f'<tr class="{"wellcome" if d["funder"] == "Wellcome Trust" else ""}"><th scope="row">{escape(d["funder"])}</th><td><div class="bar" aria-hidden="true">{segments}</div></td><td>{d["n"]:,}</td><td>{d["income_counts"][0]:,}</td><td>{d["income_counts"][1]:,}</td><td>{d["income_counts"][2]:,}</td></tr>')
        rank = next((i for i, d in enumerate(t["donors"], 1) if d["funder"] == "Wellcome Trust"), None)
        rank_text = (f"Rank {rank} by count (ties ordered alphabetically)." if rank else "No Wellcome acknowledgement identified in this theme subset.")
        income_rows = ''.join(f'<tr><th scope="row">{escape(label)}</th><td>{t["income_counts"][i]:,} ({pct(t["income_counts"][i], t["n"])})</td><td>{t["wellcome_income_counts"][i]:,} ({pct(t["wellcome_income_counts"][i], t["wellcome"])})</td></tr>' for i, label in enumerate(INCOMES))
        extra = ''
        if key == "mental":
            focus = analysis["mental_focus_title_screen"]
            extra = f'<aside><strong>Focus-condition title screen:</strong> {focus["n"]:,} eligible studies mention anxiety, depression or psychosis/schizophrenia; {focus["named_funder"]:,} name any funder and {focus["wellcome"]:,} name Wellcome. This separate screen covers all eligible studies, including those without disease tags. It does not establish early intervention or Wellcome programme eligibility.</aside>'
        if key == "climate":
            items = []
            for r in rows:
                if "climate" in r["themes"]:
                    title = escape(r["title"])
                    if r["url"].startswith(("https://", "http://")):
                        title = f'<a href="{escape(r["url"])}" target="_blank" rel="noopener">{title}</a>'
                    items.append(f'<li>{title} <small>({escape(r["year"])}){" · Wellcome named" if r["wellcome"] else ""}</small></li>')
            extra = '<details><summary>Review the provisional Climate &amp; Health title matches</summary><p>Title inspection only; full-text confirmation is still needed. No climate-topic label alone was used because some topic labels are unrelated to the study title.</p><ol>' + ''.join(items) + '</ol></details>'
        panels.append(f'''<section id="theme-{key}" class="theme" {'hidden' if index else ''}>
<h2>{escape(t['label'])}</h2><p class="definition">{escape(t['definition'])} <a href="{escape(t['url'])}" target="_blank" rel="noopener">Wellcome programme scope ↗</a></p>
<div class="metrics">{metrics}</div>
<p>Wellcome is named by <strong>{pct(t['wellcome'], t['n'])}</strong> of all identified theme studies, including those without a named funder. Missing acknowledgements mean this is an observed share, not an estimate of total support.</p>
<h3>Top donors within this priority-theme evidence</h3><p>Top 10 by unique studies naming the funder. All eligible theme studies are retained; grey includes multi-country, regional and unspecified geography.</p>
<div class="legend"><span><i style="background:{COLORS[0]}"></i>High-income setting</span><span><i style="background:{COLORS[1]}"></i>Low- &amp; middle-income setting</span><span><i style="background:{COLORS[2]}"></i>Other / unavailable</span></div>
<div class="table-scroll"><table class="donors"><caption>Recorded funders in {escape(t['label'])}</caption><thead><tr><th>Funder</th><th>Study counts by setting</th><th>Total</th><th>HIC</th><th>LMIC</th><th>Other</th></tr></thead><tbody>{''.join(donor_rows) or '<tr><td colspan="6">No named funder available.</td></tr>'}</tbody></table></div>
<aside><strong>Wellcome within this theme:</strong> {t['wellcome']:,} studies. {rank_text} Wellcome emphasis appears only in this funder-specific view.</aside>
<h3>Geographic focus: all theme evidence and studies naming Wellcome</h3><div class="table-scroll"><table><thead><tr><th>Setting</th><th>All theme studies</th><th>Studies naming Wellcome</th></tr></thead><tbody>{income_rows}</tbody></table></div>{extra}</section>''')
    years = analysis["meta"]["years"]
    annual = ''.join(f'<tr><th scope="row">{d["year"]}{" (partial)" if d["year"] == years[1] else ""}</th><td>{d["n"]}</td></tr>' for d in analysis["wellcome_by_year"])
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Wellcome-specific analysis</title><style>
*{box-sizing:border-box}body{margin:0;background:#faf9f6;color:#10243e;font:15px/1.55 system-ui,sans-serif}main{max-width:1200px;margin:auto;padding:28px}h1{font:600 clamp(25px,4vw,38px)/1.15 Georgia,serif;margin:12px 0}h2{font:600 28px Georgia,serif}h3{margin-top:30px}a{color:#1f5fa8}.badge{display:inline-block;background:#e9e2ee;color:#594069;padding:5px 12px;border-radius:20px;font-size:12px;font-weight:700}.lede{max-width:950px;color:#33475f}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:22px 0}.metric{padding:18px;background:white;border:1px solid #e7e3da;border-radius:9px}.metric strong{display:block;font-size:25px;color:#705a84}.metric span{display:block;font-size:13px;margin-top:6px}.theme{border-top:1px solid #e7e3da;padding-top:16px}.definition,aside{background:#f0ece4;padding:16px;border-radius:7px}nav{display:flex;gap:8px;flex-wrap:wrap;margin:28px 0}button{background:white;color:#594069;border:1px solid #c8b9d2;border-radius:24px;padding:10px 18px;font:600 15px system-ui;cursor:pointer}button[aria-pressed=true]{background:#705a84;color:white}button:focus-visible,a:focus-visible,summary:focus-visible{outline:3px solid #1f5fa8;outline-offset:3px}.legend{display:flex;gap:18px;flex-wrap:wrap;font-size:12px;margin:14px 0}.legend i{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px}.table-scroll{overflow-x:auto}table{width:100%;border-collapse:collapse;background:white;margin:10px 0 20px;font-size:13px}caption{text-align:left;font-size:14px;font-weight:600;margin-bottom:8px}th,td{padding:10px;border-bottom:1px solid #e7e3da;text-align:left}thead th{background:#eeeae2}th[scope=row]{font-weight:500}.donors{min-width:720px}.donors th:first-child{width:28%}.donors td:nth-child(2){width:32%}.bar{display:flex;height:16px;background:#f5f3ef;min-width:180px}.wellcome th:first-child{font-weight:700;color:#705a84}.wellcome{background:#f4eef7}.download{display:flex;gap:18px;flex-wrap:wrap;margin:20px 0}details{border:1px solid #ded6e3;padding:16px;border-radius:8px;margin:20px 0}summary{cursor:pointer;font-weight:600}li{margin-bottom:10px}small{color:#5a564d}.method{border-top:1px solid #e7e3da;margin-top:30px;padding-top:12px;font-size:13px;color:#33475f}[hidden]{display:none!important}@media(max-width:700px){main{padding:16px}.metrics{grid-template-columns:repeat(2,1fr)}.metric strong{font-size:22px}}@media print{nav{display:none}.theme[hidden]{display:block!important}.theme{break-before:page}.table-scroll{overflow:visible}}
</style></head><body><main>''' + f'''
<span class="badge">Funder-specific view · Wellcome</span><h1>Wellcome-specific analysis</h1>
<p class="lede">Explore the global economic evaluation landscape in Wellcome's three priority themes, then see which studies name Wellcome. Theme relevance and recorded support are different measures. This view is separate from the general global evidence map and is not an official Wellcome grant-portfolio assessment.</p>
<div class="metrics"><div class="metric"><strong>{total:,}</strong><span>Eligible evaluations, {years[0]}–{years[1]}</span></div><div class="metric"><strong>{analysis['global']['named_funder']:,}</strong><span>Studies naming any funder ({pct(analysis['global']['named_funder'], total)})</span></div><div class="metric"><strong>{wellcome:,}</strong><span>Studies naming Wellcome Trust</span></div><div class="metric"><strong>{analysis['wellcome_outside_themes']:,}</strong><span>Wellcome-named studies outside these theme tags / screens</span></div></div>
<p>Burroughs Wellcome Fund is a separate organisation and is excluded from the Wellcome cohort. Themes may overlap. Only {analysis['disease_tagged']:,} of {total:,} eligible studies have a harmonised disease tag; untagged studies can contain relevant evidence.</p>
<nav aria-label="Select a priority theme">{''.join(buttons)}</nav>{''.join(panels)}
<details><summary>Studies naming Wellcome by publication year</summary><p>Publication counts, not grant-award dates or spending. The final year is partial.</p><table><thead><tr><th>Year</th><th>Studies</th></tr></thead><tbody>{annual}</tbody></table></details>
<div class="download"><a href="wellcome_theme_funders.csv" download>Download donor counts by theme (CSV)</a><a href="wellcome_analysis.json" download>Download aggregate analysis (JSON)</a></div>
<section class="method"><h2>How to read these results</h2><p>Each funder is counted once per eligible study. A study can name multiple funders and belong to multiple themes. Counts do not sum to unique study totals across funders or themes. Funding is recorded for {pct(analysis['global']['named_funder'],total)} of the evidence base, so absence of a name does not establish absence of support.</p>
<p>Income comparisons use single-country studies with known income. All other studies remain visible in the other / unavailable category. Names are lightly normalised (NIHR, HTA, NIH, MRC, Gates and common variants); agencies and their programmes are not comprehensively merged. Rankings are counts of named acknowledgements, not funding amounts. A programme named in an acknowledgement does not establish membership in a current priority programme.</p>
<p>Infectious Diseases and Mental Health use broad existing MeSH-derived disease groups. Climate &amp; Health is a reproducible provisional title screen; full-text validation is outstanding. The focus-condition mental-health title screen is a separate sensitivity view. These definitions do not establish current Wellcome grant eligibility or early-intervention status.</p>
<p>Source: the map's eligible analysis master; web data built {escape(analysis['meta']['data_built'])}. Publication years {years[0]}–{years[1]} (final year partial). Programme scope checked 12 October 2026: <a href="https://wellcome.org/our-priorities/infectious-disease">Infectious Disease</a>, <a href="https://wellcome.org/our-priorities/mental-health">Mental Health</a>, <a href="https://wellcome.org/our-priorities/climate-and-health">Climate and Health</a>.</p></section>
</main><script>
document.querySelectorAll('[data-theme]').forEach(button => button.addEventListener('click', () => {{
 document.querySelectorAll('[data-theme]').forEach(b => b.setAttribute('aria-pressed', String(b === button)));
 document.querySelectorAll('.theme').forEach(panel => {{ panel.hidden = panel.id !== 'theme-' + button.dataset.theme; }});
}}));
</script></body></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--raw", type=Path, default=ROOT / "data" / "raw")
    args = parser.parse_args()
    try:
        rows, meta, content, general_entries, source_hash = load_inputs(args.raw)
        analysis = build_analysis(rows, meta, source_hash)
        if not analysis["wellcome"]["n"] or not analysis["donors"]:
            raise ValueError("No Wellcome records or named funders; refusing to build an empty analysis.")
        for entry in general_entries:
            entry.update(file="fig_funder_funders.svg", title="Top dollar: who funds economic evaluations, and where?",
                         caption=f"Top 15 recorded funders by unique eligible studies. {analysis['global']['named_funder']:,} of {len(rows):,} evaluations name a funder. Blue/orange identify single-country studies with known income; grey retains other scope or unavailable income. Names are lightly normalised; counts describe acknowledgements, not funding amounts.")
        section = {"title": SECTION, "blurb": "Funder-specific view of Wellcome's priority themes: Infectious Diseases, Mental Health and Climate & Health. Distinguishes the global theme landscape from studies naming Wellcome; includes donor rankings by theme and transparent screening definitions.",
                   "figs": [{"file": "fig_wellcome_priorities.svg", "title": "Wellcome-specific analysis: recorded support across priority themes", "caption": "Studies naming Wellcome Trust, using broad disease-group proxies and a provisional Climate & Health title screen. Themes can overlap; this is not a grant-portfolio assessment."},
                            {"file": "wellcome_analysis.html", "html": True, "title": "Wellcome priority themes: evidence landscape and top donors", "caption": "Explore theme evidence, funding coverage, Wellcome acknowledgements, geographic focus and donor rankings. Definitions and denominators are provided within the view; Climate & Health classification is provisional."}]}
        content["gallery"] = [s for s in content["gallery"] if s["title"] != SECTION] + [section]
        with tempfile.TemporaryDirectory(dir=OUT) as temporary:
            staging = Path(temporary)
            plots(analysis, staging)
            (staging / "wellcome_analysis.html").write_text(report(analysis, rows), encoding="utf-8")
            (staging / "wellcome_analysis.json").write_text(json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8")
            with (staging / "wellcome_theme_funders.csv").open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["theme", "theme_studies", "theme_studies_naming_funder", "funder", "studies", "single_country_hic", "single_country_lmic", "other_scope_or_unknown_income"])
                for key, t in analysis["themes"].items():
                    for d in t["donors"]:
                        writer.writerow([t["label"], t["n"], t["named_funder"], d["funder"], d["n"], *d["income_counts"]])
            (staging / "content.json").write_text(json.dumps(content, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            for path in staging.iterdir():
                if path.name != "content.json":
                    os.replace(path, OUT / path.name)
            os.replace(staging / "content.json", DATA / "content.json")
    except (OSError, ValueError, KeyError, TypeError, ImportError) as exc:
        raise SystemExit(f"Build stopped: {exc}. Required input checks and staging protect existing outputs from invalid inputs or rendering failures.") from exc
    print(f"Success: {len(rows):,} eligible studies; {analysis['global']['named_funder']:,} name a funder; {analysis['wellcome']['n']:,} name Wellcome Trust.")
    for t in analysis["themes"].values():
        print(f"{t['label']}: {t['n']:,} theme studies; {t['named_funder']:,} name a funder; {t['wellcome']:,} name Wellcome.")
    print(OUT / "wellcome_analysis.html")


if __name__ == "__main__":
    main()
