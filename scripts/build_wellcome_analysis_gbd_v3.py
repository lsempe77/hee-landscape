"""Build the Wellcome priority-themes view on the GBD 2023 disease coding.

Version 3 of build_wellcome_analysis_gbd.py (v2 kept): reads the final v2.1
analysis master (41,610 eligible studies) and splits HIC/LMIC settings by the
World Bank income group in force at publication year (income_broad_pubyear)
instead of the fixed income_broad. Theme and funder counts are unchanged. The general funder figure's caption in
content.json is left as published: this script does not redraw that figure.

Version 2 of build_wellcome_analysis_gbd.py (kept): same themes; the source
line now names the GBD share and the date the analysis was rebuilt, in place
of the web-data export date. Earlier notes follow.

Copy of build_wellcome_analysis.py (kept) in which the Infectious Diseases and
Mental Health themes use the team share v2.1 GBD 2023 coding
(data/raw/hee_share_v2_1/gbd_disease_long.csv) instead of the 14 MeSH-based
disease groups: Infectious Diseases = any GBD infectious cause (HIV/AIDS & STIs,
respiratory infections & TB, enteric infections, malaria & neglected tropical
diseases, other infectious diseases, or an infection with the type not stated);
Mental Health = GBD mental disorders or substance use disorders. Only the
Wellcome outputs are replaced (fig_wellcome_priorities.*, wellcome_analysis.*,
wellcome_theme_funders.csv, and the section in content.json); the general
funder figures the original script also draws are left as published.

Run: python scripts/build_wellcome_analysis_gbd_v3.py [--raw data/raw]
Requires matplotlib. All inputs are validated and all outputs staged before
replacing published files. Raw records stay in data/raw; public outputs contain
aggregate counts and a title-screen audit of already-public publications.
"""
import argparse
from collections import Counter, defaultdict
import csv
import datetime
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
SECTION = "Wellcome priority themes"
INCOMES = ["High-income setting", "Low- & middle-income setting", "Other scope / income unavailable"]
try:
    from figure_style import BACKGROUND, FUNDER_COLORS, LAVENDER, shade_bars, tidy_svg
except ModuleNotFoundError:
    from scripts.figure_style import BACKGROUND, FUNDER_COLORS, LAVENDER, shade_bars, tidy_svg

COLORS = FUNDER_COLORS
PRIORITIES = {
    "infectious": ("Infectious Diseases", "https://wellcome.org/our-priorities/infectious-disease",
                   "Broad proxy: studies whose title and abstract were coded to a Global Burden of Disease (GBD 2023) infectious cause: HIV/AIDS and sexually transmitted infections, respiratory infections and tuberculosis, enteric infections, malaria and neglected tropical diseases, other infectious diseases, or an infection of unstated type. Studies without a disease code are not treated as evidence of absence."),
    "mental": ("Mental Health", "https://wellcome.org/our-priorities/mental-health",
               "Broad proxy: studies coded to the GBD 2023 causes mental disorders or substance use disorders. It includes substance use and is wider than Wellcome's focus on early intervention in anxiety, depression and psychosis. A separate focus-condition title screen is reported below."),
    "climate": ("Climate & Health", "https://wellcome.org/our-priorities/climate-and-health",
                "Reviewed keyword screen: the titles and abstracts of all eligible studies were searched for climate, extreme heat and weather, air pollution, emissions and related terms, and every candidate was reviewed against Wellcome's Climate & Health framing (health impacts of climate change, climate-sensitive infectious disease, air pollution, and mitigation with health co-benefits). Studies of health care's own emissions are included and shown separately. The GBD cause list has no climate category, so this theme does not use disease codes."),
}
# Reviewed Climate & Health list (scripts/build_climate_candidates.py, then a review of every candidate).
CLIMATE_REVIEW = ROOT / "exports" / "climate_health_review_decisions_2026-10-12.csv"
CLIMATE_SECTOR = "Health-sector emissions"
# Parent funders for the merged treemap view only; the bar chart keeps names as normalised.
# NIHR: its programmes (HTA, PHR, HS&DR, PGfAR, EME, RfPB), BRCs, ARCs/CLAHRCs, schools and fellowships.
NIHR_FAMILY = re.compile(r"\bnihr\b|national institute (for|of) health (and care )?research|health technology assessment|"
                         r"public health research programme|health (services|and social care) (and )?delivery research|"
                         r"programme grants for applied research|efficacy and mechanism evaluation|research for patient benefit|"
                         r"biomedical research centre|applied research collaboration|clahrc|"
                         r"collaboration for leadership in applied health research|school for primary care research", re.I)
# US NIH: the agency and its institutes and centres. Same-named bodies in other countries stay separate.
NIH_FAMILY = re.compile(r"^us nih$|national institutes of health|\bnih\b|national cancer institute|"
                        r"national heart,? lung,? and blood institute|national institute of allergy and infectious disease|"
                        r"national institute (on|of) drug abuse|national center for advancing translational sciences|"
                        r"national institute of mental health|national institute of diabetes and digestive and kidney disease|"
                        r"child health and human development|eunice kennedy shriver|national institute on aging|"
                        r"national institute of general medical sciences|national institute of arthritis and musculoskeletal|"
                        r"national institute on minority health|fogarty international center|national institute on alcohol abuse|"
                        r"national institute of neurologic(al)? disorders|national human genome research institute|"
                        r"national institute of nursing research|national institute of dental and craniofacial|"
                        r"national institute of biomedical imaging|national institute of environmental health sciences|"
                        r"national institute on deafness|national center for complementary and integrative health|"
                        r"national library of medicine|national eye institute", re.I)
NON_US = re.compile(r"\b(korea\w*|french|france|colombia\w*|malaysia\w*|brazil\w*|japan\w*|ital(y|ian)|thai\w*|india\w*|"
                    r"canad\w*|mexic\w*|china|chinese|iran\w*|pakistan\w*|nigeria\w*|vietnam\w*|peru\w*|chile\w*|"
                    r"argentin\w*|taiwan\w*|egypt\w*)\b", re.I)
TREEMAP_N = 15


def parent_funder(name):
    """Parent organisation for the merged view; NIHR and US NIH absorb their programmes and institutes."""
    if NON_US.search(name):
        return name
    if NIHR_FAMILY.search(name):
        return "NIHR"
    if NIH_FAMILY.search(name):
        return "US NIH"
    return name
MENTAL_FOCUS = re.compile(r"\banxiet\w*|\bdepress\w*|\bpsychos\w*|\bpsychoti\w*|\bschizophren\w*", re.I)
# Indicative title-keyword groups for Wellcome-funded studies outside all three themes.
# First match wins; unmatched studies fall into the final catch-all group.
OUTSIDE_GROUPS = [
    ("infectious", "Infection-related studies coded to a non-infectious GBD cause",
     re.compile(r"malaria|tubercul|\bhiv\b|antiretroviral|hepatitis|cryptococc|talaromyc|shigella|strep|sars-cov|coronavirus|covid|dengue|wolbachia|\bhpv\b|sepsis|febrile|antibiotic|cephalosporin|infection", re.I),
     "Infection-related topics (hepatitis, HPV and other vaccines, antibiotic use) that GBD codes to a non-infectious cause, as it prescribes (e.g. chronic hepatitis C to liver disease, HPV vaccination to cervical cancer, maternal Group B strep vaccination to maternal and neonatal disorders), or that have no disease code. The code-based Infectious Diseases theme does not count them."),
    ("mental", "Alcohol, drugs and mental health without a mental-health code",
     re.compile(r"alcohol|\bdrug\b|mindfulness|mental health", re.I),
     "Alcohol and drug use or mental-health outcomes without a GBD mental or substance-use code; these relate to the Mental Health theme's proxy."),
    ("food", "Food systems and diet",
     re.compile(r"food|diet|meals?\b|salt|palm oil|meat|tariff|undernutrition", re.I), None),
    ("cardiometabolic", "Cardiometabolic disease and obesity",
     re.compile(r"diabet|hypertens|cardiovascular|obes|weight management|stroke|retinopathy", re.I), None),
    ("mnch", "Maternal, newborn and child health",
     re.compile(r"maternal|newborn|neonat|caesarean|post-partum|fertility|life-saving practices", re.I), None),
    ("cancer", "Cancer screening and care", re.compile(r"cancer|melanoma", re.I), None),
    ("activity", "Physical activity", re.compile(r"physical activity|walking|dance", re.I), None),
    ("systems", "Health systems, policy and methods",
     re.compile(r"benefits package|development assistance|basic income|tobacco|frailty|falls|life table|childhood policy|non-communicable", re.I), None),
]
OUTSIDE_OTHER = ("other", "Other clinical care", None)
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


def load_climate_review(path):
    """Included record IDs and sub-areas from the reviewed Climate & Health decisions, plus the number reviewed."""
    if not path.is_file():
        raise ValueError(f"Missing reviewed Climate & Health decisions: {path}")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        decisions = list(csv.DictReader(handle))
    if not decisions or any(d["decision"] not in ("Include", "Exclude") for d in decisions):
        raise ValueError("Climate & Health decisions must be complete: every candidate marked Include or Exclude.")
    included = {d["record_id"]: d["subarea"] for d in decisions if d["decision"] == "Include"}
    if any(not subarea for subarea in included.values()):
        raise ValueError("Every included Climate & Health study needs a sub-area.")
    return included, len(decisions)


GBD_LONG = Path("hee_share_v2_1") / "gbd_disease_long.csv"
GBD_INFECTIOUS = {"HIV/AIDS and sexually transmitted infections", "Respiratory infections and tuberculosis", "Enteric infections", "Neglected tropical diseases and malaria", "Other infectious diseases", "Infections, disease not stated"}
GBD_MENTAL = {"Mental disorders", "Substance use disorders"}
GBD_SHARE_RECEIVED = "14 October 2026"


def load_inputs(raw):
    master_path = raw / "hee_analysis_master_v2_1.csv"
    required = [master_path, raw / GBD_LONG, DATA / "dict.json", DATA / "content.json"]
    missing = [str(p) for p in required if not p.is_file() or p.stat().st_size == 0]
    if missing:
        raise ValueError("Missing or empty inputs: " + ", ".join(missing))
    meta = json.loads((DATA / "dict.json").read_text(encoding="utf-8"))["meta"]
    content = json.loads((DATA / "content.json").read_text(encoding="utf-8"))
    with master_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = {"record_id", "is_eligible", "title", "year", "funders", "income_broad_pubyear", "geo_scope", "disease_groups", "url"}
        if not fields.issubset(reader.fieldnames or []):
            raise ValueError("The analysis master lacks required columns: " + ", ".join(sorted(fields - set(reader.fieldnames or []))))
        all_rows = list(reader)
    if len({r["record_id"] for r in all_rows}) != len(all_rows) or any(not r["record_id"] for r in all_rows):
        raise ValueError("Analysis-master record IDs must be present and unique.")
    rows = [r for r in all_rows if r["is_eligible"] == "TRUE"]
    gbd = defaultdict(set)
    with (raw / GBD_LONG).open(encoding="utf-8", newline="") as handle:
        for g in csv.DictReader(handle):
            gbd[g["record_id"]].add(g["grp"])
    climate, reviewed = load_climate_review(CLIMATE_REVIEW)
    unknown = set(climate) - {r["record_id"] for r in rows}
    if unknown:
        raise ValueError(f"{len(unknown)} reviewed Climate & Health studies are not eligible records: " + ", ".join(sorted(unknown)[:5]))
    meta = {**meta, "climate_reviewed": reviewed}
    if len(rows) != meta["n_studies"] or not rows:
        raise ValueError(f"Eligible count {len(rows)} does not match web data {meta['n_studies']}; rebuild the matching dataset first.")
    for r in rows:
        if not r["title"] or not r["year"].isdigit() or not meta["years"][0] <= int(r["year"]) <= meta["years"][1]:
            raise ValueError("Invalid title or publication year for " + r["record_id"])
        if r["income_broad_pubyear"] not in ("NA", "", "High income", "Low & middle income"):
            raise ValueError("Unrecognised income classification for " + r["record_id"])
        r["named_funders"] = funders_of(r["funders"])
        r["wellcome"] = "Wellcome Trust" in r["named_funders"]
        r["setting"] = (0 if r["income_broad_pubyear"] == "High income" else 1) if r["geo_scope"] == "single_country" and r["income_broad_pubyear"] in ("High income", "Low & middle income") else 2
        r["gbd"] = gbd.get(r["record_id"], set())
        r["climate_subarea"] = climate.get(r["record_id"])
        r["themes"] = {k for k, match in [("infectious", bool(r["gbd"] & GBD_INFECTIOUS)),
                                           ("mental", bool(r["gbd"] & GBD_MENTAL)),
                                           ("climate", r["climate_subarea"] is not None)] if match}
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


def parent_donor_counts(rows):
    """Unique studies per parent funder, with the names merged into each parent and the HTA share of NIHR."""
    counts, merged = defaultdict(set), defaultdict(set)
    for r in rows:
        for name in r["named_funders"]:
            parent = parent_funder(name)
            counts[parent].add(r["record_id"])
            merged[parent].add(name)
    hta = sum("NIHR HTA Programme" in r["named_funders"] for r in rows)
    ranked = sorted(counts, key=lambda p: (-len(counts[p]), p.casefold()))
    return [{"funder": p, "n": len(counts[p]), "merged_names": len(merged[p]),
             **({"hta": hta} if p == "NIHR" else {})} for p in ranked[:50]]


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
    climate = [r for r in rows if "climate" in r["themes"]]
    themes["climate"]["reviewed"] = meta.get("climate_reviewed", 0)
    themes["climate"]["subareas"] = [
        {"label": label, "n": n, "wellcome": sum(r["wellcome"] for r in climate if r["climate_subarea"] == label)}
        for label, n in Counter(r["climate_subarea"] for r in climate).most_common()]
    wellcome = [r for r in rows if r["wellcome"]]
    focus = [r for r in rows if MENTAL_FOCUS.search(r["title"])]
    labels = {key: label for key, (label, _, _) in PRIORITIES.items()}

    def overlaps(subset):
        pairs = Counter(" + ".join(labels[k] for k in sorted(r["themes"], key=list(PRIORITIES).index))
                        for r in subset if len(r["themes"]) > 1)
        return {"n": sum(pairs.values()), "combinations": dict(pairs.most_common())}

    groups = {key: [] for key, *_ in OUTSIDE_GROUPS + [OUTSIDE_OTHER]}
    for r in wellcome:
        if not r["themes"]:
            key = next((k for k, _, pattern, _ in OUTSIDE_GROUPS if pattern.search(r["title"])), OUTSIDE_OTHER[0])
            groups[key].append(r)
    outside_groups = []
    for key, label, *rest in OUTSIDE_GROUPS + [OUTSIDE_OTHER]:
        note = rest[-1]
        studies = sorted(groups[key], key=lambda r: (r["year"], r["title"]))
        outside_groups.append({"key": key, "label": label, "note": note, "n": len(studies),
                               "studies": [{"title": r["title"], "year": r["year"], "url": r["url"]} for r in studies]})
    return {"meta": {"years": meta["years"], "data_built": meta["built"], "master_sha256": source_hash,
                      "unit": "Unique eligible studies reporting each funder; no grant amounts or causal attribution.",
                      "theme_overlap": True, "sources_accessed": "2026-10-12",
                      "gbd_share": f"team GBD 2023 coding, share v2.1 (received {GBD_SHARE_RECEIVED})",
                      "analysis_built": f"{datetime.date.today():%d %B %Y}".lstrip("0")},
            "global": stats(rows), "wellcome": stats(wellcome), "themes": themes,
            "mental_focus_title_screen": stats(focus),
            "wellcome_outside_themes": sum(not r["themes"] for r in wellcome),
            "wellcome_outside_groups": sorted((g for g in outside_groups if g["n"]), key=lambda g: (g["key"] == "other", -g["n"])),
            "wellcome_theme_overlap": overlaps(wellcome), "all_theme_overlap": overlaps(rows),
            "disease_tagged": sum(bool(r["gbd"]) for r in rows),
            "donors": donor_counts(rows), "parent_donors": parent_donor_counts(rows),
            "wellcome_by_year": [{"year": y, "n": sum(int(r["year"]) == y for r in wellcome)} for y in range(meta["years"][0], meta["years"][1] + 1)]}


def squarify(sizes, x, y, dx, dy):
    """Squarified treemap layout (Bruls et al.); sizes sorted descending and summing to dx * dy."""
    def worst(row, side):
        total = sum(row)
        return max(max(side * side * r / (total * total), total * total / (side * side * r)) for r in row)
    rects, sizes = [], list(sizes)
    while sizes:
        side = min(dx, dy)
        row = [sizes.pop(0)]
        while sizes and worst(row + [sizes[0]], side) <= worst(row, side):
            row.append(sizes.pop(0))
        total = sum(row)
        if dx >= dy:  # Fill a column down the left edge.
            width, top = total / dy, y
            for r in row:
                rects.append((x, top, width, r / width))
                top += r / width
            x, dx = x + width, dx - width
        else:  # Fill a row along the top edge.
            height, left = total / dx, x
            for r in row:
                rects.append((left, y, r / height, height))
                left += r / height
            y, dy = y + height, dy - height
    return rects


TREEMAP_COLORS = ["#6D91BE", "#62A89B", "#D98F7A", "#D6B264", "#9B87B8", "#8FB3C9", "#B9A58C", "#A7BF8E",
                  "#C99BB0", "#7FA7A0", "#D4A373", "#9AA5C4", "#B8B08A", "#A0B8B0", "#C4A7A0"]


def plot_treemap(analysis, staging, plt, background):
    """Top parent funders as a treemap; NIHR and US NIH absorb their programmes and institutes."""
    import textwrap as tw
    from matplotlib.patches import Rectangle
    donors = analysis["parent_donors"][:TREEMAP_N]
    width, height = 100.0, 58.0
    total = sum(d["n"] for d in donors)
    rects = squarify([d["n"] * width * height / total for d in donors], 0, 0, width, height)
    fig = plt.figure(figsize=(14, 9.6), facecolor=background)
    ax = fig.add_axes([.025, .13, .95, .69])
    ax.set_xlim(0, width)
    ax.set_ylim(height, 0)
    ax.axis("off")
    points_per_unit = .95 * 14 * 72 / width
    for d, (x, y, w, h), color in zip(donors, rects, TREEMAP_COLORS):
        ax.add_patch(Rectangle((x, y), w, h, facecolor=color, edgecolor=background, linewidth=3))
        name = {"NIHR": "NIHR", "US NIH": "US NIH"}.get(d["funder"], d["funder"])
        detail = (f"incl. HTA Programme: {d['hta']:,}" if d["funder"] == "NIHR" else
                  "incl. institutes (e.g. NCI, NIAID, NIDA)" if d["funder"] == "US NIH" else "")
        size = max(8, min(24, (w * h) ** .5 * .95))
        chars = max(8, int((w - 2.4) * points_per_unit / (size * .68)))
        label = tw.fill(name, chars)
        pad = min(1.2, w * .06)
        ax.text(x + pad, y + pad * .9, label, ha="left", va="top", fontsize=size, fontweight="bold", color="#10243e", linespacing=1.05)
        if detail and h > 8:
            lines = label.count("\n") + 1
            ax.text(x + pad, y + pad * .9 + lines * size * 1.25 / points_per_unit, tw.fill(detail, int(chars * 1.6)),
                    ha="left", va="top", fontsize=max(8, size * .5), color="#10243e")
        ax.text(x + pad, y + h - pad * .7, f"{d['n']:,}", ha="left", va="bottom", fontsize=min(34, size * 1.45),
                fontweight="bold", color="#10243e")
    top = donors[0]
    fig.text(.025, .95, "Top funders by organisation: who funds the most studies?", fontsize=22, fontweight="bold", color="#10243e")
    fig.text(.025, .905, f"{top['funder']} is named in {top['n']:,} studies, more than any other funder. Bigger box = more studies.",
             fontsize=13.5, color="#33475f")
    fig.text(.025, .865, "Programmes and institutes are counted under the organisation they belong to, "
             "such as NIHR's HTA Programme or the NIH's National Cancer Institute.", fontsize=11.5, color="#5a564d")
    notes = ("NIHR includes its programmes (HTA, Public Health Research, HS&DR, Programme Grants for Applied Research, EME, Research for Patient Benefit),\n"
             "Biomedical Research Centres, ARCs/CLAHRCs and fellowships. US NIH includes its institutes and centres (e.g. NCI, NIAID, NIDA, NHLBI, NIMH, NCATS).\n"
             "Same-named bodies in other countries stay separate. Each study counts once per funder. Counts describe recorded acknowledgements, not funding amounts.")
    fig.text(.025, .03, notes, fontsize=10, color="#5a564d", linespacing=1.6)
    fig.savefig(staging / "fig_funder_treemap.svg", facecolor=background)
    tidy_svg(staging / "fig_funder_treemap.svg")
    fig.savefig(staging / "fig_funder_treemap.png", dpi=110, facecolor=background)
    plt.close(fig)


def plots(analysis, staging):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator
    background = BACKGROUND
    donors = analysis["donors"][:15]
    fig, ax = plt.subplots(figsize=(14, 9), facecolor=background)
    ax.set_facecolor(background)
    left = [0] * len(donors)
    for i, (label, color) in enumerate(zip(INCOMES, COLORS)):
        values = [d["income_counts"][i] for d in donors]
        bars = ax.barh(range(len(donors)), values, left=left, color=color, height=.7, label=label)
        shade_bars(ax, bars, color)
        left = [a + b for a, b in zip(left, values)]
    ax.set_yticks(range(len(donors)), [textwrap.fill(d["funder"], 38) for d in donors], fontsize=10)
    for y, d in enumerate(donors):
        ax.text(d["n"] + 8, y, f"{d['n']:,}", va="center", fontsize=10)
    ax.invert_yaxis()
    ax.set_xlim(0, max(d["n"] for d in donors) * 1.15)
    ax.set_xlabel("Studies reporting the funder (a study may report several)", fontsize=11, labelpad=12)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.grid(axis="x", alpha=.16)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(axis="y", length=0)
    # Legend sits directly under the subtitle, aligned with the title.
    fig.legend(*ax.get_legend_handles_labels(), loc="upper left", bbox_to_anchor=(.019, .885), ncol=3, frameon=False, fontsize=10)
    fig.subplots_adjust(left=.31, right=.96, top=.83, bottom=.2)
    fig.text(.025, .95, "Top funders: who funds economic evidence, and where?", fontsize=22, fontweight="bold", color="#10243e")
    fig.text(.025, .905, "Top 15 recorded funders, ranked by unique eligible studies", fontsize=14, color="#33475f")
    n = analysis["global"]["n"]
    known = analysis["global"]["named_funder"]
    notes = (f"Base: {n:,} eligible studies, including reviews; {known:,} ({100 * known / n:.1f}%) report a funder. "
             "Counts describe recorded acknowledgements, not funding amounts.\n"
             "Blue and coral: single-country studies with known publication-year income. Grey: other geographic scope or unavailable income.\n"
             "Names are lightly normalised and counted once per study; funding coverage is incomplete.\n"
             f"Publication years {analysis['meta']['years'][0]}–{analysis['meta']['years'][1]} (final year partial).")
    fig.text(.025, .04, notes, fontsize=10, color="#5a564d", linespacing=1.6)
    fig.savefig(staging / "fig_funder_funders.svg", facecolor=background)
    tidy_svg(staging / "fig_funder_funders.svg")
    fig.savefig(staging / "fig_funder_funders.png", dpi=110, facecolor=background)
    plt.close(fig)
    plot_treemap(analysis, staging, plt, background)

    fig, ax = plt.subplots(figsize=(13, 6.6), facecolor=background)
    ax.set_facecolor(background)
    themes = list(analysis["themes"].values())
    total = analysis["wellcome"]["n"]
    outside = analysis["wellcome_outside_themes"]
    # The muted final bar accounts for the rest of the Wellcome cohort.
    values = [t["wellcome"] for t in themes] + [outside]
    labels = ["Infectious Diseases", "Mental Health", "Climate & Health", "Outside these three themes"]
    untagged = next((g["n"] for g in analysis["wellcome_outside_groups"] if g["key"] == "infectious"), 0)
    notes = [f"{pct(t['wellcome'], t['n'])} of {t['n']:,} theme studies · {wellcome_rank(t['donors'])}" for t in themes] + [
        f"Includes {untagged} infection-related studies coded to a non-infectious GBD cause" if untagged else "No theme tag and not on the reviewed climate list"]
    # Explain the small Climate & Health count where readers see it.
    climate = analysis["themes"]["climate"]
    notes[2] += (f"\nSmall because few studies in the map address climate: "
                 f"{climate['n']:,} of {analysis['global']['n']:,} studies ({pct(climate['n'], analysis['global']['n'])})")
    colors = [LAVENDER] * 3 + ["#C9C4BA"]
    bars = ax.barh(range(4), values, color=colors, height=.58)
    for bar, color in zip(bars, colors):
        shade_bars(ax, [bar], color)
    ax.set_yticks(range(4), labels, fontsize=13, color="#10243e")
    ax.get_yticklabels()[-1].set_color("#5a564d")
    ax.invert_yaxis()
    step = max(1, max(values)) * .015
    for y, (value, note) in enumerate(zip(values, notes)):
        ax.text(value + step, y - .1, f"{value} {'study' if value == 1 else 'studies'}", va="center", fontsize=13,
                fontweight="bold", color="#10243e" if y < 3 else "#5a564d")
        ax.text(value + step, y + .1, note, va="top", fontsize=10.5, color="#5a564d", linespacing=1.5)
    ax.set_xlim(0, max(1, max(values)) * 1.75)
    ax.set_xticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(axis="y", length=0, pad=10)
    ax.axhline(2.65, color="#ded9ce", linewidth=1)  # below the two-line Climate & Health note
    fig.subplots_adjust(left=.23, right=.97, top=.76, bottom=.24)
    fig.text(.025, .93, "Wellcome-funded studies: which priority themes do they cover?", fontsize=22, fontweight="bold", color="#10243e")
    fig.text(.025, .85, f"{total:,} eligible studies report Wellcome Trust as a funder; {total - outside} fall in at least one priority theme",
             fontsize=15, color="#705a84")
    fig.text(.025, .035, f"{overlap_text(analysis['wellcome_theme_overlap'], 'Wellcome-funded')}\n"
             "Infectious Diseases and Mental Health use GBD 2023 disease codes, so studies without a matching code fall outside. Climate & Health is a reviewed title-and-abstract screen.\n"
             "Rank compares studies reporting each funder within the theme. Funding is reported for about a quarter of studies, so counts are a lower bound,\n"
             "not grant value, exclusive support or Wellcome programme membership.", fontsize=10, color="#5a564d", linespacing=1.6)
    fig.savefig(staging / "fig_wellcome_priorities.svg", facecolor=background)
    tidy_svg(staging / "fig_wellcome_priorities.svg")
    fig.savefig(staging / "fig_wellcome_priorities.png", dpi=110, facecolor=background)
    plt.close(fig)


def escape(value):
    return html.escape(str(value), quote=True)


def pct(n, total):
    return f"{100 * n / total:.1f}%" if total else "Not estimable"


def overlap_text(overlap, who):
    """One sentence on how many studies sit in more than one theme, and which ones."""
    n = overlap["n"]
    if not n:
        return f"No {who} study falls in more than one theme."
    items = list(overlap["combinations"].items())
    combos = ("all in " + items[0][0].replace(" + ", " and ") if len(items) == 1 else
              "; ".join(f"{count:,} in {combo.replace(' + ', ' and ')}" for combo, count in items))
    return f"{n:,} {who} {'study falls' if n == 1 else 'studies fall'} in more than one theme ({combos})."


def ordinal(n):
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def ranks(donors):
    """Competition ranks: tied counts share a rank, so ties are never broken alphabetically."""
    return [1 + sum(other["n"] > d["n"] for other in donors) for d in donors]


def wellcome_rank(donors):
    w = next((d for d in donors if d["funder"] == "Wellcome Trust"), None)
    if not w:
        return "not named in this theme"
    rank = 1 + sum(d["n"] > w["n"] for d in donors)
    tied = sum(d["n"] == w["n"] for d in donors) > 1
    return f"{'joint ' if tied else ''}{ordinal(rank)} of {len(donors):,} reported funders"


def rounded_shares(counts, total, decimals=0):
    """Percentages rounded so they sum to exactly 100 (largest-remainder method)."""
    scale = 10 ** decimals
    exact = [100 * scale * c / total for c in counts]
    floors = [int(x) for x in exact]
    by_remainder = sorted(range(len(exact)), key=lambda i: exact[i] - floors[i], reverse=True)
    for i in by_remainder[:100 * scale - sum(floors)]:
        floors[i] += 1
    return [f / scale for f in floors]


def stacked_bar(counts, total):
    """Inline 100% bar split by setting, with readable labels on wide segments."""
    if not total:
        return '<div class="stack empty">No studies</div>'
    parts = []
    whole, tenths = rounded_shares(counts, total), rounded_shares(counts, total, 1)
    for count, color, label, label_pct, title_pct in zip(counts, COLORS, INCOMES, whole, tenths):
        share = 100 * count / total
        text = f"{label_pct:.0f}%" if share >= 9 else ""
        parts.append(f'<span style="width:{share:.4f}%;background:{color}" title="{escape(label)}: {count:,} ({title_pct:.1f}%)">{text}</span>')
    return '<div class="stack">' + "".join(parts) + "</div>"


STYLE = '''
*{box-sizing:border-box}
body{margin:0;background:#faf9f6;color:#10243e;font:15px/1.6 Inter,system-ui,sans-serif}
main{padding:24px 28px 40px}
h1,h2{font-family:Newsreader,Georgia,serif;font-weight:600;letter-spacing:-.01em}
h1{font-size:clamp(28px,4vw,40px);line-height:1.1;margin:12px 0 10px}
h2{font-size:26px;margin:0 0 6px}
h3{font-size:16px;margin:34px 0 4px}
a{color:#1f5fa8}
.badge{display:inline-block;background:#ece6f1;color:#594069;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600}
.lede{color:#33475f;margin:0}
.hint{color:#5a564d;font-size:13.5px;margin:2px 0 12px}
.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.summary{display:flex;flex-wrap:wrap;margin:24px 0 32px;border-top:1px solid #e7e3da;border-bottom:1px solid #e7e3da}
.summary div{flex:1 1 200px;padding:16px 20px 16px 0}
.summary div+div{border-left:1px solid #e7e3da;padding-left:20px}
.summary strong{display:block;font:600 30px/1.1 Newsreader,Georgia,serif;color:#705a84}
.summary span{display:block;font-size:13px;color:#33475f;margin-top:4px}
.panel{background:white;border:1px solid #e7e3da;border-radius:10px;padding:20px 22px;margin:14px 0}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th,td{padding:9px 10px;border-bottom:1px solid #eeeae2;text-align:left;vertical-align:middle}
thead th{font-size:12px;font-weight:600;color:#5a564d;border-bottom:1px solid #d9d3c7}
tbody tr:last-child th,tbody tr:last-child td{border-bottom:0}
th[scope=row]{font-weight:500}
.overview td:nth-child(3){width:38%}
h2#outside{margin-top:36px}
.groups{padding:6px 22px}
.group{border:0;border-bottom:1px solid #eeeae2;border-radius:0;margin:0;padding:0;background:none}
.group:last-child{border-bottom:0}
.group summary{display:grid;grid-template-columns:minmax(220px,32%) 1fr 48px;gap:16px;align-items:center;padding:11px 0;font-weight:500;list-style:none}
.group summary::-webkit-details-marker{display:none}
.group summary .g-label::before{content:"\\25B8";display:inline-block;width:16px;color:#8a857b;transition:transform .15s}
.group[open] summary .g-label::before{transform:rotate(90deg)}
.group ol{margin:4px 0 14px;padding-left:40px;font-size:13.5px}
.group .hint{margin:0 0 6px 16px}
.overview button{all:unset;cursor:pointer;color:#1f5fa8;font-weight:600}
.overview button:hover{text-decoration:underline}
.meter{position:relative;height:10px;background:#f1eef4;border-radius:5px;min-width:120px}
.meter i{position:absolute;inset:0 auto 0 0;background:#9B87B8;border-radius:5px}
nav{display:flex;gap:8px;flex-wrap:wrap;margin:36px 0 0;position:sticky;top:0;background:#faf9f6;padding:12px 0;z-index:1;border-bottom:1px solid #e7e3da}
nav button{background:white;color:#594069;border:1px solid #c8b9d2;border-radius:24px;padding:8px 18px;font:600 14px Inter,system-ui,sans-serif;cursor:pointer}
nav button[aria-pressed=true]{background:#705a84;border-color:#705a84;color:white}
button:focus-visible,a:focus-visible,summary:focus-visible{outline:3px solid #1f5fa8;outline-offset:3px}
.theme{padding-top:24px}
.definition{border-left:3px solid #9B87B8;padding:2px 0 2px 14px;color:#33475f;font-size:14px;margin:8px 0 18px}
.metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.metric{padding:16px 18px;background:white;border:1px solid #e7e3da;border-radius:10px}
.metric strong{display:block;font:600 28px/1.1 Newsreader,Georgia,serif}
.metric span{display:block;font-size:13px;color:#33475f;margin-top:4px}
.metric small{display:block;font-size:12.5px;color:#5a564d;margin-top:6px}
.metric.wellcome{background:#f6f2f9;border-color:#d9cde3}
.metric.wellcome strong{color:#705a84}
.metrics+.hint{margin-top:10px}
.legend{display:flex;gap:18px;flex-wrap:wrap;font-size:12.5px;color:#33475f;margin:8px 0 4px}
.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px;vertical-align:-1px}
.table-scroll{overflow-x:auto}
.donors{min-width:760px}
.donors .rank{width:36px;color:#5a564d}
.donors .who{width:30%}
.donors .bars{width:34%}
.donors td.muted{color:#5a564d}
.bar{display:flex;height:14px;background:#f5f3ef;border-radius:3px;overflow:hidden}
.bar span{display:block;height:100%}
tr.wellcome{background:#f6f2f9}
tr.wellcome th{font-weight:700;color:#705a84}
tr.gap td{color:#8a857b;text-align:center;padding:2px;font-size:12px}
.stack{display:flex;height:26px;border-radius:4px;overflow:hidden;background:#f5f3ef;min-width:260px}
.stack span{display:flex;align-items:center;justify-content:center;color:white;font-size:12px;font-weight:600;text-shadow:0 0 2px rgba(0,0,0,.25)}
.stack.empty{color:#5a564d;font-size:12.5px;align-items:center;padding-left:8px}
.geo th[scope=row]{width:26%}
.geo td.num{width:90px;color:#5a564d}
aside{background:#f0ece4;padding:14px 16px;border-radius:8px;font-size:14px;margin:18px 0}
details{border:1px solid #e2dbe6;background:white;padding:14px 18px;border-radius:8px;margin:18px 0}
summary{cursor:pointer;font-weight:600}
li{margin-bottom:8px}
small{color:#5a564d}
.download{display:flex;gap:18px;flex-wrap:wrap;margin:24px 0 8px;font-size:14px}
.method{font-size:13.5px;color:#33475f}
.year-table{max-width:320px}
[hidden]{display:none!important}
@media(max-width:760px){main{padding:16px}.metrics{grid-template-columns:1fr}.summary div+div{border-left:0;padding-left:0;border-top:1px solid #e7e3da}.panel{padding:14px}}
@media print{nav{display:none}.theme[hidden]{display:block!important}.theme{break-before:page}.table-scroll{overflow:visible}}
'''


def report(analysis, rows):
    total = analysis["global"]["n"]
    wellcome = analysis["wellcome"]["n"]
    outside = analysis["wellcome_outside_themes"]
    legend = ''.join(f'<span><i style="background:{color}"></i>{escape(label)}</span>'
                     for color, label in zip(COLORS, ["High-income setting", "Low- & middle-income setting", "Multi-country, regional or income unavailable"]))
    max_w = max([t["wellcome"] for t in analysis["themes"].values()] or [1]) or 1
    overview, buttons, panels = [], [], []
    for index, (key, t) in enumerate(analysis["themes"].items()):
        overview.append(f'<tr><th scope="row"><button type="button" data-go="{key}">{escape(t["label"])}</button></th>'
                        f'<td class="num">{t["n"]:,}</td>'
                        f'<td><div class="meter" aria-hidden="true"><i style="width:{100 * t["wellcome"] / max_w:.4f}%"></i></div></td>'
                        f'<td class="num"><strong>{t["wellcome"]:,}</strong></td>'
                        f'<td class="num">{pct(t["wellcome"], t["n"])}</td>'
                        f'<td>{escape(wellcome_rank(t["donors"]).capitalize())}</td></tr>')
        buttons.append(f'<button type="button" aria-pressed="{str(index == 0).lower()}" aria-controls="theme-{key}" data-theme="{key}">{escape(t["label"])}</button>')
        metrics = (f'<div class="metric"><strong>{t["n"]:,}</strong><span>Eligible studies in this theme</span></div>'
                   f'<div class="metric"><strong>{pct(t["named_funder"], t["n"])}</strong><span>Report at least one funder</span><small>{t["named_funder"]:,} studies</small></div>'
                   f'<div class="metric wellcome"><strong>{t["wellcome"]:,}</strong><span>Wellcome-funded ({pct(t["wellcome"], t["n"])} of theme studies)</span>'
                   f'<small>{escape(wellcome_rank(t["donors"]).capitalize())} · {pct(t["wellcome"], t["named_funder"])} of studies that report a funder</small></div>')
        max_n = max([d["n"] for d in t["donors"]] or [1])
        rank_of = ranks(t["donors"])
        shown = list(range(min(10, len(t["donors"]))))
        w_index = next((i for i, d in enumerate(t["donors"]) if d["funder"] == "Wellcome Trust"), None)
        donor_rows = []
        for i in shown + ([w_index] if w_index is not None and w_index not in shown else []):
            d = t["donors"][i]
            if i == w_index and i not in shown:
                donor_rows.append('<tr class="gap"><td colspan="7">⋯</td></tr>')
            segments = ''.join(f'<span style="width:{100 * count / max_n:.4f}%;background:{color}"></span>' for count, color in zip(d["income_counts"], COLORS))
            tied = rank_of.count(rank_of[i]) > 1
            donor_rows.append(f'<tr class="{"wellcome" if i == w_index else ""}"><td class="num rank">{"=" if tied else ""}{rank_of[i]}</td>'
                              f'<th scope="row">{escape(d["funder"])}</th><td><div class="bar" aria-hidden="true">{segments}</div></td>'
                              f'<td class="num"><strong>{d["n"]:,}</strong></td>' + ''.join(f'<td class="num muted">{c:,}</td>' for c in d["income_counts"]) + '</tr>')
        geo = (f'<tr><th scope="row">All theme studies</th><td>{stacked_bar(t["income_counts"], t["n"])}</td><td class="num">n = {t["n"]:,}</td></tr>'
               f'<tr><th scope="row">Wellcome-funded studies</th><td>{stacked_bar(t["wellcome_income_counts"], t["wellcome"])}</td><td class="num">n = {t["wellcome"]:,}</td></tr>')
        extra = ''
        if key == "mental":
            focus = analysis["mental_focus_title_screen"]
            extra = f'<aside><strong>Narrower check on anxiety, depression and psychosis:</strong> {focus["n"]:,} eligible studies mention these conditions in their title; {focus["named_funder"]:,} report any funder and {focus["wellcome"]:,} report Wellcome funding. This title screen covers all eligible studies, including those without disease tags. It does not establish early-intervention focus or Wellcome programme eligibility.</aside>'
        lead = ''
        if key == "climate":
            lead = (f'<aside><strong>Why so few studies?</strong> This map covers health economic evaluations (cost-effectiveness and related '
                    f'studies of health interventions) and reviews of them. Most climate-and-health research is epidemiology or impact modelling, so it falls outside the map. '
                    f'Only {t["n"]:,} of {total:,} eligible studies ({pct(t["n"], total)}) address climate. '
                    f'The {t["reviewed"]:,} candidates found by the keyword screen were each reviewed, and a broader search for related terms found almost no further studies. '
                    f'The small count reflects how thin this evidence is, not a gap in the search.</aside>')
            max_s = max([s["n"] for s in t["subareas"]] or [1])
            sub_items = []
            for s in t["subareas"]:
                items = []
                for r in rows:
                    if r["climate_subarea"] == s["label"]:
                        title = escape(r["title"])
                        if r["url"].startswith(("https://", "http://")):
                            title = f'<a href="{escape(r["url"])}" target="_blank" rel="noopener">{title}</a>'
                        items.append(f'<li>{title} <small>({escape(r["year"])}){" · Wellcome-funded" if r["wellcome"] else ""}</small></li>')
                tag = ' <small>(shown separately: emissions of health care itself)</small>' if s["label"] == CLIMATE_SECTOR else ''
                sub_items.append(f'<details class="group"><summary><span class="g-label">{escape(s["label"])}{tag}</span>'
                                 f'<span class="meter" aria-hidden="true"><i style="width:{100 * s["n"] / max_s:.4f}%"></i></span>'
                                 f'<span class="num"><strong>{s["n"]}</strong></span></summary><ol>{"".join(items)}</ol></details>')
            extra = (f'<h3>What the {t["n"]:,} studies cover</h3><p class="hint">Sub-areas follow Wellcome\'s Climate &amp; Health framing; each study has one. '
                     f'Select a sub-area to list its studies.</p><div class="panel groups">{"".join(sub_items)}</div>')
        panels.append(f'''<section id="theme-{key}" class="theme" {'hidden' if index else ''}>
<h2>{escape(t['label'])}</h2><p class="definition">{escape(t['definition'])} <a href="{escape(t['url'])}" target="_blank" rel="noopener">Wellcome programme scope&nbsp;↗</a></p>
{lead}<div class="metrics">{metrics}</div>
<p class="hint">Funding is reported for {pct(t['named_funder'], t['n'])} of theme studies, so these are observed shares and a lower bound on support.</p>
<h3>Top funders in this theme</h3><p class="hint">Ranked by the number of studies reporting each funder; = marks a tie. Wellcome is highlighted, and added below the top 10 when it ranks lower.</p>
<div class="legend">{legend}</div>
<div class="panel table-scroll"><table class="donors"><caption hidden>Recorded funders in {escape(t['label'])}</caption><thead><tr><th class="num">#</th><th class="who">Funder</th><th class="bars">Studies by setting</th><th class="num">Total</th><th class="num">HIC</th><th class="num">LMIC</th><th class="num">Other</th></tr></thead><tbody>{''.join(donor_rows) or '<tr><td colspan="7">No named funder available.</td></tr>'}</tbody></table></div>
<h3>Where the studies are set</h3><p class="hint">Share of studies by setting: all theme evidence compared with Wellcome-funded studies.</p>
<div class="panel table-scroll"><table class="geo"><tbody>{geo}</tbody></table><div class="legend">{legend}</div></div>{extra}</section>''')
    groups = analysis["wellcome_outside_groups"]
    max_g = max([g["n"] for g in groups] or [1])
    untagged = sum(g["n"] for g in groups if g["key"] in ("infectious", "mental"))
    group_items = []
    for g in groups:
        studies = ''.join(
            f'<li>{f"""<a href="{escape(s["url"])}" target="_blank" rel="noopener">{escape(s["title"])}</a>""" if s["url"].startswith(("https://", "http://")) else escape(s["title"])} <small>({escape(s["year"])})</small></li>'
            for s in g["studies"])
        note = f'<p class="hint">{escape(g["note"])}</p>' if g["note"] else ''
        group_items.append(f'<details class="group"><summary><span class="g-label">{escape(g["label"])}</span>'
                           f'<span class="meter" aria-hidden="true"><i style="width:{100 * g["n"] / max_g:.4f}%"></i></span>'
                           f'<span class="num"><strong>{g["n"]}</strong></span></summary>{note}<ol>{studies}</ol></details>')
    outside_html = (f'<h2 id="outside">What the {outside:,} studies outside the themes cover</h2>'
                    f'<p class="hint">Wellcome-funded studies with no infectious or mental-health disease code and not on the reviewed Climate &amp; Health list, grouped by keywords in their titles. '
                    f'Groupings are indicative. <strong>{untagged:,} of the {outside:,} are infection-related, substance-use or mental-health studies without a matching theme code</strong>, '
                    f'so the theme counts above understate Wellcome-funded work in those themes. Select a group to list its studies.</p>'
                    f'<div class="panel groups">{"".join(group_items)}</div>')
    years = analysis["meta"]["years"]
    annual = ''.join(f'<tr><th scope="row">{d["year"]}{" (partial)" if d["year"] == years[1] else ""}</th><td class="num">{d["n"]}</td></tr>' for d in analysis["wellcome_by_year"])
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>Wellcome priority themes</title><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
            '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Newsreader:opsz,wght@6..72,600&display=swap" rel="stylesheet">'
            f'<style>{STYLE}</style></head><body><main>' + f'''
<span class="badge">Funder-specific view · Wellcome</span><h1>{escape(SECTION)}</h1>
<p class="lede">How much economic evidence exists in Wellcome's three priority themes, and which of those studies report Wellcome Trust as a funder (Wellcome-funded studies). Theme relevance and recorded support are different measures. This view is separate from the global evidence map and is not an official Wellcome grant-portfolio assessment.</p>
<div class="summary"><div><strong>{wellcome:,}</strong><span>Studies report Wellcome Trust as a funder</span></div><div><strong>{wellcome - outside:,}</strong><span>Of these fall in at least one priority theme</span></div><div><strong>{outside:,}</strong><span>Fall outside the three themes · <a href="#outside">see what they cover</a></span></div><div><strong>{pct(analysis['global']['named_funder'], total)}</strong><span>Of all {total:,} studies ({years[0]}–{years[1]}) report any funder</span></div></div>
<h2>The three themes at a glance</h2><p class="hint">Select a theme to see its top funders and settings. A study can belong to more than one theme: {escape(overlap_text(analysis['wellcome_theme_overlap'], 'Wellcome-funded'))} Across all eligible studies, {analysis['all_theme_overlap']['n']:,} fall in more than one theme.</p>
<div class="panel table-scroll"><table class="overview"><thead><tr><th>Theme</th><th class="num">Theme studies</th><th colspan="2">Wellcome-funded studies</th><th class="num">Share of theme</th><th>Wellcome's rank among funders</th></tr></thead><tbody>{''.join(overview)}</tbody></table></div>
{outside_html}
<nav aria-label="Select a priority theme">{''.join(buttons)}</nav>{''.join(panels)}
<details><summary>Wellcome-funded studies by publication year</summary><p class="hint">Publication counts, not grant-award dates or spending. The final year is partial.</p><table class="year-table"><thead><tr><th>Year</th><th class="num">Studies</th></tr></thead><tbody>{annual}</tbody></table></details>
<details class="method"><summary>Technical details and sources</summary><p>Each funder is counted once per eligible study. A study can name multiple funders and belong to multiple themes, so counts do not sum across funders or themes. Funding is recorded for {pct(analysis['global']['named_funder'], total)} of the evidence base, so absence of a name does not establish absence of support. Burroughs Wellcome Fund is a separate organisation and is excluded from the Wellcome cohort.</p>
<p>Setting comparisons use single-country studies with known income, taking the World Bank group in force on 1 January of each study's publication year; all other studies stay visible in the multi-country, regional or income-unavailable category. Names are lightly normalised (NIHR, HTA, NIH, MRC, Gates and common variants); agencies and their programmes are not comprehensively merged. Rankings count reported funders, not funding amounts, and tied funders share a rank. A programme named in an acknowledgement does not establish membership in a current priority programme.</p>
<p>Infectious Diseases and Mental Health use the Global Burden of Disease (GBD 2023) causes coded from each study's title and abstract (the condition the evaluated intervention targets); {analysis['disease_tagged']:,} of {total:,} eligible studies have a disease code, so studies without one can still contain relevant evidence. Climate &amp; Health uses a keyword screen of all titles and abstracts (scripts/build_climate_candidates.py), after which every candidate was reviewed against Wellcome's Climate &amp; Health framing; decisions and their basis are in exports/climate_health_review_decisions_2026-10-12.csv. A broader recall check found almost no further studies. Classification uses titles and abstracts, not full texts. The anxiety, depression and psychosis title screen is a separate sensitivity view. Wellcome-funded studies outside all three themes are grouped by keywords in their titles (first matching group wins) to describe what they cover; this grouping does not change any theme count. These definitions do not establish current Wellcome grant eligibility or early-intervention status.</p>
<p>Source: the map's eligible analysis master, v2.1 ({total:,} studies) and the {escape(analysis['meta']['gbd_share'])}; analysis rebuilt {escape(analysis['meta']['analysis_built'])}. Publication years {years[0]}–{years[1]} (final year partial). Programme scope checked 12 October 2026: <a href="https://wellcome.org/our-priorities/infectious-disease">Infectious Disease</a>, <a href="https://wellcome.org/our-priorities/mental-health">Mental Health</a>, <a href="https://wellcome.org/our-priorities/climate-and-health">Climate and Health</a>.</p></details>
<div class="download"><a href="wellcome_theme_funders.csv" download>Download funder counts by theme (CSV)</a><a href="wellcome_analysis.json" download>Download aggregate analysis (JSON)</a></div>
</main><script>
function show(key) {{
 document.querySelectorAll('[data-theme]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.theme === key)));
 document.querySelectorAll('.theme').forEach(panel => {{ panel.hidden = panel.id !== 'theme-' + key; }});
}}
document.querySelectorAll('[data-theme]').forEach(button => button.addEventListener('click', () => show(button.dataset.theme)));
document.querySelectorAll('[data-go]').forEach(button => button.addEventListener('click', () => {{
 show(button.dataset.go);
 document.querySelector('nav').scrollIntoView({{behavior: 'smooth', block: 'start'}});
}}));
</script></body></html>''')


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--raw", type=Path, default=ROOT / "data" / "raw")
    args = parser.parse_args()
    try:
        rows, meta, content, general_entries, source_hash = load_inputs(args.raw)
        analysis = build_analysis(rows, meta, source_hash)
        if not analysis["wellcome"]["n"] or not analysis["donors"]:
            raise ValueError("No Wellcome records or reported funders; refusing to build an empty analysis.")
        for entry in general_entries:
            entry.update(file="fig_funder_funders.svg", title="Top funders: who funds economic evidence, and where?",
                         caption=f"Top 15 recorded funders by unique eligible studies. {analysis['global']['named_funder']:,} of {len(rows):,} studies report a funder. Blue/coral identify single-country studies by the income group of the country studied; grey retains other scope or unavailable income. Names are lightly normalised; counts describe acknowledgements, not funding amounts.")
            nihr = next(d for d in analysis["parent_donors"] if d["funder"] == "NIHR")
            # Alternative views shown as tabs in the figure pop-up; the bar chart stays the default.
            entry["views"] = [
                {"label": "Funders as named", "file": "fig_funder_funders.svg"},
                {"label": "Grouped by organisation", "file": "fig_funder_treemap.svg",
                 "title": "Top funders by organisation: who funds the most studies?",
                 "summary": (f"The same funders, with programmes and institutes counted under the organisation they belong to. NIHR (incl. HTA Programme: {nihr['hta']:,}) "
                             f"is named in {nihr['n']:,} studies, and the US NIH including its institutes in "
                             f"{next(d['n'] for d in analysis['parent_donors'] if d['funder'] == 'US NIH'):,}. Bigger box = more studies. "
                             "Counts are studies that name a funder, not amounts of money."),
                 "caption": ("NIHR includes its programmes (HTA, Public Health Research, HS&DR, Programme Grants for Applied Research, EME, "
                             "Research for Patient Benefit), Biomedical Research Centres, ARCs/CLAHRCs and fellowships. US NIH includes its "
                             "institutes and centres (e.g. NCI, NIAID, NIDA, NHLBI, NIMH, NCATS). Same-named bodies in other countries stay "
                             "separate. Each study counts once per funder; other funders are counted as in the bar chart.")}]
        section = {"title": SECTION, "blurb": "Economic evidence by Wellcome's three priority themes: Infectious Diseases, Mental Health and Climate & Health. It separates all evidence in each theme from studies that report Wellcome Trust funding, ranks the funders reported within each theme, and sets out how each theme was defined.",
                   "figs": [{"file": "fig_wellcome_priorities.svg", "title": "Wellcome-funded studies: which priority themes do they cover?", "caption": "Studies reporting Wellcome Trust as a funder in each priority theme, with Wellcome's share of theme studies and rank among reported funders. Uses GBD 2023 disease codes from titles and abstracts and a reviewed Climate & Health title-and-abstract screen; Climate & Health is small because few economic evaluations address climate. Themes can overlap; this is not a grant-portfolio assessment."},
                            {"file": "wellcome_analysis.html", "html": True, "title": "Theme explorer: who funds each priority theme, and where?", "caption": "Compare the three themes, then explore each theme's evidence, funding coverage, top funders and study settings. Definitions and denominators are provided within the view; Climate & Health is a reviewed title-and-abstract screen and is small because few economic evaluations address climate."}]}
        # Also drop the section under its earlier name so a rename never leaves a duplicate.
        content["gallery"] = [s for s in content["gallery"] if s["title"] not in (SECTION, "Wellcome-specific analysis")] + [section]
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
            # Wellcome outputs only; the general funder figures stay as published.
            for path in staging.iterdir():
                if path.name.startswith(("wellcome_", "fig_wellcome_priorities")):
                    os.replace(path, OUT / path.name)
            os.replace(staging / "content.json", DATA / "content.json")
    except (OSError, ValueError, KeyError, TypeError, ImportError) as exc:
        raise SystemExit(f"Build stopped: {exc}. Required input checks and staging protect existing outputs from invalid inputs or rendering failures.") from exc
    print(f"Success: {len(rows):,} eligible studies; {analysis['global']['named_funder']:,} report a funder; {analysis['wellcome']['n']:,} report Wellcome Trust.")
    for t in analysis["themes"].values():
        print(f"{t['label']}: {t['n']:,} theme studies; {t['named_funder']:,} report a funder; {t['wellcome']:,} report Wellcome.")
    print(OUT / "wellcome_analysis.html")


if __name__ == "__main__":
    main()
