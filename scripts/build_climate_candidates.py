"""Build the Climate & Health candidate list for manual review.

Run: python scripts/build_climate_candidates.py [--raw data/raw]
Requires openpyxl. Screens the title and abstract of every eligible study with a
keyword list that follows Wellcome's Climate & Health framing, then writes a
review workbook to exports/. Nothing is classified automatically: a reviewer
marks each candidate Include / Exclude / Unsure.

Scope (Wellcome's framing, checked 12 October 2026): health impacts of climate
change (including extreme heat and weather), climate-sensitive infectious
diseases, air pollution, and climate mitigation with health co-benefits.
Studies of health-sector emissions are included but tagged separately.
"""
import argparse
import csv
from datetime import date
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "exports"

# Sub-areas and their terms. A study is a candidate if any term matches its
# title or abstract after the exclusions below are removed from the text.
SUBAREAS = {
    "Health impacts of climate change": re.compile(
        r"climate change|global warming|climatic change|changing climate|climate crisis|climate[ -]related|"
        r"climate[ -]sensitive|climate adaptation|climate resilien|extreme heat|heat[ -]?waves?|heat[ -]related|"
        r"heat stress|heat[ -]health|heat illness|hot weather|high ambient temperature|extreme weather|"
        r"\bfloods?\b|flooding|drought|wildfires?|bushfires?|cyclones?|hurricanes?|sea[ -]level rise|"
        r"natural disasters?|disaster funds?", re.I),
    "Air pollution": re.compile(
        r"\bair pollution|\bair pollutants?|\bair quality|particulate matter|\bpm ?2\.5|\bpm ?10\b|black carbon|"
        r"household air|indoor air|cookstoves?|solid fuels?|biomass fuel", re.I),
    "Mitigation with health co-benefits": re.compile(
        r"greenhouse gas|\bghg\b|carbon emissions?|co2 emissions?|carbon dioxide emissions?|co2[ -]?e(q)?\b|"
        r"carbon footprint|carbon tax|carbon pric|decarboni[sz]|net[ -]zero|low[ -]carbon|sustainable diets?|"
        r"planetary health|environmental impacts?|environmental(ly)? sustainab|active travel|"
        r"clean energy|renewable energy", re.I),
}
# Climate-sensitive infectious diseases: a climate or weather term together with a sensitive disease.
CLIMATE_CONTEXT = re.compile(r"\bclimat(e|ic)\b|\bweather\b|rainfall|seasonal(ity)? temperature|temperature and (rainfall|humidity)", re.I)
SENSITIVE_DISEASE = re.compile(r"dengue|malaria|cholera|vector[ -]borne|zika|chikungunya|leishmania|schistosom|diarrho?eal", re.I)
SENSITIVE = "Climate-sensitive infectious disease"
# Health-sector emissions: an emissions term together with a health-care setting.
EMISSIONS = re.compile(r"greenhouse gas|\bghg\b|carbon emissions?|co2|carbon footprint|carbon dioxide emissions?", re.I)
HEALTH_CARE = re.compile(r"hospitals?|surg|operating (room|theat)|inhalers?|anaesthe|anesthe|health ?care|dialysis|"
                         r"telemedicine|telehealth|virtual care|clinic\b|clinics\b|pharmaceutical", re.I)
HEALTH_SECTOR = "Health-sector emissions (tag)"
# Non-environmental uses removed before matching, so they never create a candidate.
EXCLUSIONS = re.compile(
    r"(organi[sz]ational|safety|school|economic|political|investment|financial|social|work|working|team|ethical|"
    r"regulatory|policy|business|funding|fiscal|reimbursement|current|present|today'?s|health ?care|healthcare|"
    r"research|market|commercial) climate|climate schools|climate of\b|"
    r"(positron|otoacoustic|photon|light) emissions?|emission tomography|\bflood(ing)? (of|with) (fluid|blood)", re.I)
# The page's earlier title-only screen, for comparison.
OLD_TITLE_SCREEN = re.compile(r"\bclimat(?:e|ic)\b|global warming|greenhouse gas|carbon (?:footprint|tax)|decarbon|heat[ -]?wave|"
                              r"heat[ -]related|heat mitigation|heat[ -]health|heat stress|heat risks|heat warning|wildfire|"
                              r"cold weather plan|representative concentration pathways", re.I)
DECISIONS = ["Include", "Exclude", "Unsure"]
REVIEW_SUBAREAS = list(SUBAREAS) + [SENSITIVE, "Health-sector emissions"]


def snippets(text, patterns, width=90, limit=3):
    """Short excerpts around the first few matched terms."""
    found = []
    for pattern in patterns:
        for match in pattern.finditer(text):
            start, end = max(0, match.start() - width), min(len(text), match.end() + width)
            if any(start < e and end > s for s, e, _ in found):
                continue
            found.append((start, end, "…" + text[start:end].replace("\n", " ") + "…"))
            if len(found) >= limit:
                break
        if len(found) >= limit:
            break
    return "\n".join(s for _, _, s in sorted(found))


def screen(row):
    title, abstract = row["title"], "" if row["abstract"] in ("", "NA") else row["abstract"]
    text = EXCLUSIONS.sub(" ", f"{title}\n{abstract}")
    clean_title = EXCLUSIONS.sub(" ", title)
    areas, terms, used = [], set(), []
    for name, pattern in SUBAREAS.items():
        hits = [m.group(0).lower() for m in pattern.finditer(text)]
        if hits:
            areas.append(name)
            terms.update(hits)
            used.append(pattern)
    if CLIMATE_CONTEXT.search(text) and SENSITIVE_DISEASE.search(text):
        areas.append(SENSITIVE)
        terms.update(m.group(0).lower() for m in CLIMATE_CONTEXT.finditer(text))
        used.append(CLIMATE_CONTEXT)
    if not areas:
        return None
    sector = bool(EMISSIONS.search(text) and HEALTH_CARE.search(text))
    mentions = sum(len(p.findall(text)) for p in used)
    return {
        "record_id": row["record_id"], "year": row["year"], "title": title,
        "in_title": "Yes" if any(p.search(clean_title) for p in used) else "No",
        "mentions": mentions, "suggested_subareas": "; ".join(areas + ([HEALTH_SECTOR] if sector else [])),
        "matched_terms": "; ".join(sorted(terms)), "excerpts": snippets(text, used),
        "in_previous_title_screen": "Yes" if OLD_TITLE_SCREEN.search(title) else "No",
        "url": row["url"] if row["url"].startswith(("http://", "https://")) else "",
        "abstract": abstract,
    }


def write_workbook(candidates, path, n_screened):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation

    wb = Workbook()
    ws = wb.active
    ws.title = "Candidates"
    columns = [("record_id", 14), ("year", 7), ("title", 60), ("in_title", 9), ("mentions", 10),
               ("suggested_subareas", 34), ("matched_terms", 30), ("excerpts", 70), ("in_previous_title_screen", 12),
               ("decision", 12), ("subarea", 34), ("reviewer_notes", 40), ("url", 30), ("abstract", 90)]
    header_fill = PatternFill("solid", fgColor="E9E2EE")
    review_fill = PatternFill("solid", fgColor="FFF6DC")
    for col, (name, width) in enumerate(columns, 1):
        cell = ws.cell(row=1, column=col, value=name)
        cell.font = Font(bold=True)
        cell.fill = review_fill if name in ("decision", "subarea", "reviewer_notes") else header_fill
        ws.column_dimensions[cell.column_letter].width = width
    for r, cand in enumerate(candidates, 2):
        for col, (name, _) in enumerate(columns, 1):
            cell = ws.cell(row=r, column=col, value=cand.get(name, ""))
            cell.alignment = Alignment(wrap_text=name in ("title", "excerpts", "suggested_subareas", "abstract"), vertical="top")
            if name == "url" and cand.get("url"):
                cell.hyperlink = cand["url"]
    last = len(candidates) + 1
    letters = {name: ws.cell(row=1, column=i).column_letter for i, (name, _) in enumerate(columns, 1)}
    decision = DataValidation(type="list", formula1='"' + ",".join(DECISIONS) + '"', allow_blank=True)
    ws.add_data_validation(decision)
    decision.add(f"{letters['decision']}2:{letters['decision']}{last}")
    # A Lists sheet holds the sub-area options; a quoted list would exceed Excel's 255-character limit.
    lists = wb.create_sheet("Lists")
    for i, name in enumerate(REVIEW_SUBAREAS, 1):
        lists.cell(row=i, column=1, value=name)
    subarea = DataValidation(type="list", formula1=f"=Lists!$A$1:$A${len(REVIEW_SUBAREAS)}", allow_blank=True)
    ws.add_data_validation(subarea)
    subarea.add(f"{letters['subarea']}2:{letters['subarea']}{last}")
    ws.freeze_panes = "D2"
    ws.auto_filter.ref = f"A1:{letters['abstract']}{last}"

    guide = wb.create_sheet("How to review", 0)
    lines = [
        ("Climate & Health candidates: review guide", True),
        (f"Built {date.today().isoformat()} by scripts/build_climate_candidates.py. "
         f"{len(candidates):,} candidates from {n_screened:,} eligible studies (title and abstract keyword screen).", False),
        ("", False),
        ("What to do", True),
        ("For each row on the Candidates sheet, read the title and excerpts (and the abstract if needed), then set:", False),
        ("  decision: Include if the study's main subject falls in the scope below; Exclude if climate, heat, pollution or emissions are only mentioned in passing; Unsure if it needs discussion.", False),
        ("  subarea: for included studies, pick the best-fitting sub-area. suggested_subareas is only a hint.", False),
        ("  reviewer_notes: anything worth recording, especially for Unsure.", False),
        ("Sort or filter freely; record_id links each row back to the dataset.", False),
        ("", False),
        ("Scope (follows Wellcome's Climate & Health framing)", True),
        ("Health impacts of climate change: effects of climate change, extreme heat and extreme weather on health or health systems.", False),
        ("Climate-sensitive infectious disease: studies where climate or weather is part of the question (e.g. dengue or malaria under changing climate). A malaria study with no climate angle is Exclude here.", False),
        ("Air pollution: outdoor or household air pollution and its health effects or interventions (Wellcome names air pollution as a climate-and-health focus area).", False),
        ("Mitigation with health co-benefits: emissions reduction in food systems, transport, energy or housing with health outcomes (e.g. sustainable diets, carbon taxes on food, active travel).", False),
        ("Health-sector emissions: the carbon footprint or emissions of health care itself (e.g. surgery, inhalers, telemedicine). Included, but kept as its own sub-area so it can be shown or left out.", False),
        ("", False),
        ("Columns", True),
        ("in_title: whether a scope term appears in the title. mentions: number of matched terms in title and abstract.", False),
        ("in_previous_title_screen: whether the page's earlier title-only screen already counted the study.", False),
        ("Rows are sorted with title matches first, then by number of mentions.", False),
        ("", False),
        ("Limits", True),
        ("Keyword screening finds candidates; it can miss relevant studies that use none of the terms. "
         "Non-environmental uses such as 'organisational climate' or 'current climate' were removed before matching.", False),
    ]
    guide.column_dimensions["A"].width = 150
    for i, (text, bold) in enumerate(lines, 1):
        cell = guide.cell(row=i, column=1, value=text)
        cell.font = Font(bold=bold, size=13 if i == 1 else 11)
        cell.alignment = Alignment(wrap_text=True, vertical="top")

    terms = wb.create_sheet("Keyword list")
    terms.column_dimensions["A"].width = 38
    terms.column_dimensions["B"].width = 140
    rows = [(name, p.pattern) for name, p in SUBAREAS.items()] + [
        (SENSITIVE, f"climate context: {CLIMATE_CONTEXT.pattern}  AND  disease: {SENSITIVE_DISEASE.pattern}"),
        (HEALTH_SECTOR, f"emissions: {EMISSIONS.pattern}  AND  setting: {HEALTH_CARE.pattern}"),
        ("Exclusions (removed before matching)", EXCLUSIONS.pattern)]
    terms.append(["Sub-area", "Regular expression (case-insensitive)"])
    for cell in terms[1]:
        cell.font = Font(bold=True)
    for name, pattern in rows:
        terms.append([name, pattern])
        terms.cell(row=terms.max_row, column=2).alignment = Alignment(wrap_text=True, vertical="top")
    wb.save(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--raw", type=Path, default=ROOT / "data" / "raw")
    args = parser.parse_args()
    master = args.raw / "hee_analysis_master_v2.csv"
    if not master.is_file():
        raise SystemExit(f"Missing input: {master}")
    with master.open(encoding="utf-8-sig", newline="") as handle:
        rows = [r for r in csv.DictReader(handle) if r["is_eligible"] == "TRUE"]
    candidates = [c for c in map(screen, rows) if c]
    candidates.sort(key=lambda c: (c["in_title"] != "Yes", -c["mentions"], c["record_id"]))
    OUT.mkdir(exist_ok=True)
    path = OUT / f"climate_health_candidates_{date.today().isoformat()}.xlsx"
    write_workbook(candidates, path, len(rows))
    by_area = {}
    for c in candidates:
        for area in c["suggested_subareas"].split("; "):
            by_area[area] = by_area.get(area, 0) + 1
    print(f"{len(candidates):,} candidates from {len(rows):,} eligible studies; "
          f"{sum(c['in_title'] == 'Yes' for c in candidates):,} with a title match.")
    for area, n in sorted(by_area.items(), key=lambda x: -x[1]):
        print(f"  {area}: {n:,}")
    print(path)


if __name__ == "__main__":
    main()
