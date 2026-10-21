"""Build the Infectious Diseases scope candidate list for manual review.

Run: python scripts/build_infectious_candidates.py [--raw data/raw]
Requires openpyxl. The Wellcome page's Infectious Diseases theme counts studies
coded to a GBD 2023 infectious cause. GBD codes disease burden, so infection-
related work it assigns elsewhere is not counted: chronic hepatitis C goes to
liver disease, HPV vaccination to cervical cancer, maternal Group B strep
vaccination to maternal and neonatal disorders, and antimicrobial stewardship
often has no disease code. Wellcome's Infectious Disease programme is framed
around pathogens, vaccines and drug resistance.

This screens the title and abstract of every eligible study outside the
GBD-coded theme for three sub-areas (viral hepatitis, vaccines and
immunisation, antimicrobial use and resistance) and writes a review workbook to
exports/. Nothing is classified automatically: a reviewer marks each candidate
Include / Exclude / Unsure, as for Climate & Health.
"""
import argparse
from collections import defaultdict
import csv
from datetime import date
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "exports"
GBD_LONG = Path("hee_share_v2_1") / "gbd_disease_long.csv"
# The six GBD groups the theme already counts (as in build_wellcome_analysis_gbd_v3.py).
GBD_INFECTIOUS = {"HIV/AIDS and sexually transmitted infections", "Respiratory infections and tuberculosis", "Enteric infections",
                  "Neglected tropical diseases and malaria", "Other infectious diseases", "Infections, disease not stated"}

# Sub-areas and their terms. A study is a candidate if any term matches its title or abstract
# after the exclusions below are removed from the text.
SUBAREAS = {
    "Viral hepatitis": re.compile(
        r"\bhepatitis [abcde]\b|\bviral hepatitis|\bhepatitis\b|\bhbv\b|\bhcv\b|\bhbsag\b|direct[- ]acting antivirals?|\bdaas?\b|"
        r"sofosbuvir|ledipasvir|velpatasvir|glecaprevir|tenofovir|entecavir", re.I),
    "Vaccines and immunisation": re.compile(
        r"vaccin\w*|immuni[sz]ation|immuni[sz]ed?\b|immuno-?prophylaxis|palivizumab|nirsevimab|monoclonal antibod\w* (for|against) (rsv|respiratory syncytial)", re.I),
    "Antimicrobial use and resistance": re.compile(
        r"antimicrobials?|antibiotics?|antibacterials?|antifungals?|antivirals?|stewardship|drug[- ]resistan\w*|multi-?drug[- ]resistan\w*|"
        r"\bamr\b|\bmrsa\b|\bvre\b|\besbl\b|carbapenem\w*|cephalosporins?|fluoroquinolones?|resistant (bacteria|infections?|organisms?|pathogens?)", re.I),
}
# Non-infectious uses removed before matching, so they never create a candidate.
EXCLUSIONS = re.compile(
    r"(autoimmune|alcoholic|ischa?emic|toxic|drug[- ]induced|non-?alcoholic) hepatitis|"
    r"(cancer|tumou?r|dendritic[- ]cell|therapeutic cancer) vaccines?|(data|environmental) stewardship|"
    r"antibiotic[- ]loaded bone cement|"
    r"(drug|treatment|therapy|medication)[- ]resistant (epilepsy|seizures?|depression|hypertension|schizophrenia|pain|migraine|asthma|overactive bladder)|"
    r"(rh|rhesus|rhd|anti-d) (iso|allo)?immuni[sz]\w*|alloimmuni[sz]\w*|isoimmuni[sz]\w*", re.I)
DECISIONS = ["Include", "Exclude", "Unsure"]
# Team rule (2026-10-21): routine antibiotic prophylaxis around surgery or procedures is outside the themes.
# Candidates whose only sub-area is antimicrobial use and that match this are pre-marked Exclude.
PROPHYLAXIS = re.compile(r"(antibiotic|antimicrobial|antibacterial)s? prophylaxis|prophylactic (antibiotic|antimicrobial)s?|"
                         r"(peri-?operative|pre-?operative|post-?operative|surgical) (antibiotic|antimicrobial)s?|"
                         r"surgical (site infection )?prophylaxis", re.I)
PROCEDURE = re.compile(r"surg\w*|operati\w*|peri-?operative|caesarean|cesarean|arthroplasty|evacuation|"
                       r"appendectom\w*|cholecystectom\w*|hernia repair|dental implant\w*|tooth extraction|biopsy|endoscop\w*", re.I)
# Never pre-exclude studies about resistance, stewardship or long-term (non-surgical) prophylaxis.
AMR_FOCUS = re.compile(r"vesicoureteral|urinary tract infections?|continuous (low-dose )?(antibiotic|antimicrobial)|long-term (antibiotic|antimicrobial)|low-dose (antibiotic|antimicrobial)|stewardship|resistan\w*|\bamr\b|\bmrsa\b|\besbl\b|carbapenem", re.I)
PROPHYLAXIS_NOTE = "Rule (2026-10-21): routine antibiotic prophylaxis around surgery or procedures is outside the Wellcome themes; pre-marked Exclude. Change if the study is about resistance or stewardship."


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


def screen(row, gbd):
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
    if not areas:
        return None
    rule = (areas == ["Antimicrobial use and resistance"] and bool(PROPHYLAXIS.search(text)) and bool(PROCEDURE.search(text))
            and not AMR_FOCUS.search(text))
    return {
        "record_id": row["record_id"], "year": row["year"], "title": title,
        "in_title": "Yes" if any(p.search(clean_title) for p in used) else "No",
        "mentions": sum(len(p.findall(text)) for p in used),
        "suggested_subareas": "; ".join(areas), "matched_terms": "; ".join(sorted(terms)),
        "current_gbd_groups": "; ".join(sorted(gbd)) or "(no disease code)",
        "wellcome_funded": "Yes" if re.search(r"\bwellcome\b", row["funders"], re.I) and not re.search(r"burroughs[ -]+wellcome", row["funders"], re.I) else "No",
        "excerpts": snippets(text, used),
        "url": row["url"] if row["url"].startswith(("http://", "https://")) else "",
        "abstract": abstract,
        "decision": "Exclude" if rule else "", "reviewer_notes": PROPHYLAXIS_NOTE if rule else "",
    }


def write_workbook(candidates, path, n_screened, n_theme):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation

    wb = Workbook()
    ws = wb.active
    ws.title = "Candidates"
    columns = [("record_id", 14), ("year", 7), ("title", 60), ("in_title", 9), ("mentions", 10),
               ("suggested_subareas", 30), ("matched_terms", 30), ("current_gbd_groups", 34), ("wellcome_funded", 10),
               ("excerpts", 70), ("decision", 12), ("subarea", 30), ("reviewer_notes", 40), ("url", 30), ("abstract", 90)]
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
            cell.alignment = Alignment(wrap_text=name in ("title", "excerpts", "suggested_subareas", "current_gbd_groups", "abstract"), vertical="top")
            if name == "url" and cand.get("url"):
                cell.hyperlink = cand["url"]
    last = len(candidates) + 1
    letters = {name: ws.cell(row=1, column=i).column_letter for i, (name, _) in enumerate(columns, 1)}
    decision = DataValidation(type="list", formula1='"' + ",".join(DECISIONS) + '"', allow_blank=True)
    ws.add_data_validation(decision)
    decision.add(f"{letters['decision']}2:{letters['decision']}{last}")
    subarea = DataValidation(type="list", formula1='"' + ",".join(SUBAREAS) + '"', allow_blank=True)
    ws.add_data_validation(subarea)
    subarea.add(f"{letters['subarea']}2:{letters['subarea']}{last}")
    ws.freeze_panes = "D2"
    ws.auto_filter.ref = f"A1:{letters['abstract']}{last}"

    in_title = sum(c["in_title"] == "Yes" for c in candidates)
    wellcome = sum(c["wellcome_funded"] == "Yes" for c in candidates)
    guide = wb.create_sheet("How to review", 0)
    lines = [
        ("Infectious Diseases scope candidates: review guide", True),
        (f"Built {date.today().isoformat()} by scripts/build_infectious_candidates.py. {len(candidates):,} candidates from the "
         f"{n_screened - n_theme:,} eligible studies outside the GBD-coded Infectious Diseases theme ({n_theme:,} studies already in it; "
         f"{n_screened:,} eligible in all). {in_title:,} match in the title; {wellcome:,} report Wellcome Trust funding.", False),
        ("", False),
        ("Why", True),
        ("The theme counts studies coded to a GBD 2023 infectious cause. GBD codes disease burden, so it assigns some infection-related "
         "work elsewhere: chronic hepatitis C to cirrhosis and liver disease, HPV vaccination to cervical cancer, maternal Group B strep "
         "vaccination to maternal and neonatal disorders; stewardship often has no disease code. Wellcome's Infectious Disease programme "
         "is framed around pathogens, vaccines and drug resistance. Included studies would be added to the theme, shown as their own sub-area.", False),
        ("", False),
        ("What to do", True),
        ("For each row on the Candidates sheet, read the title and excerpts (and the abstract if needed), then set:", False),
        ("  decision: Include if the evaluated intervention or question falls in a sub-area below; Exclude if the term is only background, "
         "a comparator detail or a passing mention; Unsure if it needs discussion.", False),
        ("  subarea: for included studies, the best-fitting sub-area. suggested_subareas is only a hint.", False),
        ("  reviewer_notes: anything worth recording, especially for Unsure.", False),
        ("Rows are sorted with title matches first (most likely in scope), then by number of mentions. Sort or filter freely; "
         "record_id links each row back to the dataset. current_gbd_groups shows what the GBD coding assigned.", False),
        ("", False),
        ("Scope (proposed; confirm with the team before review)", True),
        ("Viral hepatitis: prevention, testing, treatment or care of hepatitis A-E infection, including chronic hepatitis B and C coded to "
         "liver disease. Exclude non-viral hepatitis and hepatitis mentioned only as a comorbidity or outcome.", False),
        ("Vaccines and immunisation: evaluations of a vaccine, immunisation programme or passive immunisation against an infection "
         "(e.g. HPV, influenza, pneumococcal, rotavirus, maternal Group B strep, RSV antibodies). Exclude cancer vaccines and immunotherapy, "
         "and studies where vaccination is only mentioned.", False),
        ("Antimicrobial use and resistance: antimicrobial prescribing, choice or duration as the evaluated question; stewardship; "
         "diagnostics to guide antimicrobial use; drug-resistant infections. Exclude studies where an antibiotic is only part of a wider "
         "clinical pathway being evaluated.", False),
        ("Routine antibiotic prophylaxis around surgery or procedures does not count (team rule, 21 October 2026). Rows matching it with no "
         "other sub-area are already marked Exclude, with the rule in reviewer_notes; change any that are really about resistance or stewardship.", False),
        ("", False),
        ("Limits", True),
        ("Keyword screening finds candidates; it can miss relevant studies that use none of the terms. Non-infectious uses such as "
         "autoimmune hepatitis and cancer vaccines were removed before matching. Studies already in the GBD-coded theme are not listed.", False),
    ]
    guide.column_dimensions["A"].width = 150
    for i, (text, bold) in enumerate(lines, 1):
        cell = guide.cell(row=i, column=1, value=text)
        cell.font = Font(bold=bold, size=13 if i == 1 else 11)
        cell.alignment = Alignment(wrap_text=True, vertical="top")

    terms = wb.create_sheet("Keyword list")
    terms.column_dimensions["A"].width = 38
    terms.column_dimensions["B"].width = 140
    terms.append(["Sub-area", "Regular expression (case-insensitive)"])
    for cell in terms[1]:
        cell.font = Font(bold=True)
    for name, pattern in [(n, p.pattern) for n, p in SUBAREAS.items()] + [("Exclusions (removed before matching)", EXCLUSIONS.pattern),
                                                                            ("GBD groups already in the theme", "; ".join(sorted(GBD_INFECTIOUS)))]:
        terms.append([name, pattern])
        terms.cell(row=terms.max_row, column=2).alignment = Alignment(wrap_text=True, vertical="top")
    wb.save(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--raw", type=Path, default=ROOT / "data" / "raw")
    args = parser.parse_args()
    master, long_path = args.raw / "hee_analysis_master_v2_1.csv", args.raw / GBD_LONG
    for path in (master, long_path):
        if not path.is_file():
            raise SystemExit(f"Missing input: {path}")
    csv.field_size_limit(10 ** 9)
    gbd = defaultdict(set)
    with long_path.open(encoding="utf-8", newline="") as handle:
        for g in csv.DictReader(handle):
            gbd[g["record_id"]].add(g["grp"])
    with master.open(encoding="utf-8-sig", newline="") as handle:
        rows = [r for r in csv.DictReader(handle) if r["is_eligible"] == "TRUE"]
    theme = {r["record_id"] for r in rows if gbd[r["record_id"]] & GBD_INFECTIOUS}
    candidates = [c for c in (screen(r, gbd[r["record_id"]]) for r in rows if r["record_id"] not in theme) if c]
    candidates.sort(key=lambda c: (c["in_title"] != "Yes", -c["mentions"], c["record_id"]))
    OUT.mkdir(exist_ok=True)
    path = OUT / f"infectious_scope_candidates_{date.today().isoformat()}.xlsx"
    write_workbook(candidates, path, len(rows), len(theme))
    by_area = defaultdict(lambda: [0, 0])
    for c in candidates:
        for area in c["suggested_subareas"].split("; "):
            by_area[area][0] += 1
            by_area[area][1] += c["in_title"] == "Yes"
    print(f"{sum(c['decision'] == 'Exclude' for c in candidates):,} pre-marked Exclude by the surgical-prophylaxis rule.")
    print(f"{len(candidates):,} candidates outside the {len(theme):,}-study theme ({len(rows):,} eligible); "
          f"{sum(c['in_title'] == 'Yes' for c in candidates):,} with a title match; "
          f"{sum(c['wellcome_funded'] == 'Yes' for c in candidates):,} Wellcome-funded.")
    for area, (n, t) in sorted(by_area.items(), key=lambda x: -x[1][0]):
        print(f"  {area}: {n:,} ({t:,} in title)")
    print(path)


if __name__ == "__main__":
    main()
