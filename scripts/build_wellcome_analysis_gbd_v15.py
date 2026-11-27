"""Build the Wellcome priority-themes page, v3 design (exports/.../wellcome_dashboard_v3_spec.md): v3.2 scope.

Version 15 (v14 kept; v14 built v3.9): builds v3.10. Only change: the "About the thematic mapping" link is removed
from the top banner (user request, 27 Nov 2026). The technical note is still reachable from the overview's footnote
link and from each theme's "Definition and matching criteria".

Version 14 (v13 kept; v13 built v3.8): builds v3.9. Counts and wording of findings unchanged. Visual refresh:
cooler page background with each section on a white card; violet gradient header band; headline figures as tinted
tiles; thicker rounded bars; cool greys instead of beige; violet accents on section headings; light fill under the
trend line; short theme summaries (the detail stays in "Definition and matching criteria").

Version 13 (v12 kept; v12 built v3.6): builds v3.8 (v3.7 was an intermediate draft of the same changes). Counts unchanged. Tone review of the technical note, crosswalk
and theme "Definition and matching criteria" (user request, 27 Nov 2026): the mapping is presented as the closest match
available with GBD codes, with known limitations stated openly, not as errors. Facts are unchanged; wording such as
"overly broad proxy", "partial fit", "flagged for a coding fix" and "not reviewed publication by publication" is
replaced. The spec-required introduction and interpretive note are unchanged.

Version 12 (v11 kept; v11 built v3.5): builds v3.6. Counts unchanged. The "Other Wellcome-funded HEE publications"
list, grouped by title keywords, is removed from the page and from the JSON (user decision, 27 Nov 2026): the keyword
groups read as if those publications belonged in the themes, without explaining the comparability reasons for not
mapping them. The coverage bar still shows how many are not captured; the CSV still lists every Wellcome-funded
publication with its GBD code and a captured yes/no flag, ungrouped.

Version 11 (v10 kept; v10 built v3.4): builds v3.5. Counts unchanged.
- Colours: refreshed palette, validated with the dataviz palette checker (lightness, chroma, colour-vision separation):
  Wellcome #5530C8, other funders #B9A6F2, not identified #E2DFE8; income groups #0B7FA3 / #E5793A / #D8D2C6.
- New download: wellcome_funded_publications.csv (all Wellcome-funded publications, captured or not, with theme and GBD
  code), alongside the funder-count CSV and JSON.
- Publication titles link to their DOI (the master's url field is empty for most records).
- Technical note rewritten to be shorter (user's draft wording, checked against the final codes). The crosswalk table's
  GBD codes are verified at build time against the codes that actually define the themes.

Version 10 (v9 kept; v9 built v3.3): layout only, counts and wording of findings unchanged. The crosswalk table
cites short source names (full quotes stay in "Sources for Wellcome's priorities") with fixed column widths, so columns
no longer collapse; overview column headers and headline labels shortened; "1 is in both" grammar. Writes
exports/wellcome_themes_v10_build/.

Version 9 (v8 kept; v8 built v3.2): text only, counts unchanged. The vector-borne list is evidenced by the WHO
fact sheet "Vector-borne diseases" (26 Sep 2024; PDF saved 27 Nov 2026 20:21): all ten included GBD causes are in its
table. WHO-listed diseases without their own GBD cause (e.g. Japanese and tick-borne encephalitis, chikungunya, Lyme
disease) sit in mixed GBD codes and stay excluded; stated as a limitation. Writes exports/wellcome_themes_v9_build/.

Version 8 (v7 kept; v7 built v3.1): Infectious Diseases now covers all four focus areas on Wellcome's Infectious Disease
page ("Our focus includes": tuberculosis; cholera; vector-borne diseases such as schistosomiasis, leishmaniasis and
dengue; drug-resistant infections; PDF saved 27 Nov 2026 20:05). Vector-borne diseases is read as a category (all GBD
level-3 causes transmitted by vectors; encephalitis excluded as mixed), chosen by the user on 27 Nov 2026 for
consistency with "all forms of psychotic disorders". Crosswalk rationale quotes Wellcome's wording. PTSD/OCD coding
inconsistency is noted, not recoded. Writes exports/wellcome_themes_v8_build/.

Version 7 notes follow.

Version 7 of build_wellcome_analysis_gbd.py (v6 kept, and imported here for its validated input loading and funder
normalisation, so funding identification rules are unchanged). Changes from v6, as required by the v3 specification:

- Only two themes are analysed, each restricted to the previously agreed GBD criteria for Wellcome's specified priority
  areas. Infectious Diseases = Wellcome's named areas (tuberculosis, cholera, drug-resistant infections; wellcome.org,
  checked 27 Nov 2026) = GBD level-3 Tuberculosis + Diarrheal diseases (a broad proxy for cholera, which has no GBD code;
  scope chosen by the user on 27 Nov 2026); drug-resistant infection has no GBD code. Mental Health = Wellcome's stated
  focus, anxiety, depression and psychosis = GBD level-3 depressive disorders, anxiety disorders, schizophrenia, bipolar
  disorder (MENTAL_GROUPS, sourced in v5/v6). Other mental disorders and substance use disorders are no longer counted.
- Climate & Health (keyword screen, not comparable with the GBD approach) is excluded from every displayed analysis.
- The 17 publications added on review (REVIEW_ADDED in v6) are excluded: they were identified only by supplementary
  screening. No toggle, no ◆ markers.
- New page: one overview (headline counts, combined funding bar, two theme rows on a shared absolute scale), two theme
  tabs, a full-map Wellcome section (coverage bar, interpretive note, other Wellcome-funded publications, annual and
  cumulative line charts with a fixed 0-100 annual axis), and a collapsible methodology with the crosswalk.

Writes only to exports/wellcome_themes_v8_build/ (git-ignored by the exports/*_build rule if present); pack it with
export_wellcome_standalone_v3.py. Nothing in docs/ is written.

Run: python scripts/build_wellcome_analysis_gbd_v8.py [--raw data/raw]
"""
import argparse
from collections import defaultdict
import csv
import datetime
import json
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_wellcome_analysis_gbd_v6 as v6  # noqa: E402  (kept unchanged; reused for inputs and funder rules)

ROOT = v6.ROOT
BUILD_OUT = ROOT / "exports" / "wellcome_themes_v15_build"
TITLE = "Wellcome priority themes"
INF_URL = "https://wellcome.org/our-priorities/infectious-disease"
MH_URL = v6.MENTAL_SOURCE
BIPOLAR_URL = v6.MENTAL_BIPOLAR_SOURCE
INFECTIOUS_GROUPS = v6.INFECTIOUS_GROUPS
MENTAL_GROUPS = v6.MENTAL_GROUPS
# GBD 2023 level-3 causes. Every vector-borne cause below is in the table of the WHO fact sheet "Vector-borne diseases" (26 Sep 2024).
VECTOR_BORNE = ["Malaria", "Dengue", "Leishmaniasis", "Schistosomiasis", "Chagas disease", "Lymphatic filariasis",
                "Onchocerciasis", "Zika virus", "Yellow fever", "African trypanosomiasis"]
INFECTIOUS_CODES = ["Tuberculosis", "Diarrheal diseases"] + VECTOR_BORNE
# Wellcome wording, quoted from the saved pages (27 Nov 2026).
Q_ID = ("“Our focus includes: Tuberculosis (TB)…; Cholera…; Vector-borne diseases such as schistosomiasis, leishmaniasis "
        "and dengue…; Drug-resistant infections…” (Wellcome, Infectious Disease, accessed 27 Nov 2026)")
Q_MH = ("“Our mission is to enable a step change in early interventions for anxiety, depression and psychosis.” "
        "(Wellcome, Mental Health, accessed 27 Nov 2026)")
WHO_URL = "https://www.who.int/news-room/fact-sheets/detail/vector-borne-diseases"
Q_WHO = ("WHO fact sheet “Vector-borne diseases” (26 September 2024), table of vector-borne diseases by vector "
         "(described by WHO as non-exhaustive)")
WHO_MIXED = ("Some diseases WHO lists as vector-borne, such as Japanese and tick-borne encephalitis, chikungunya and Lyme "
             "disease, have no GBD code of their own. They sit within broader codes (encephalitis, other neglected tropical "
             "diseases, other infectious diseases) that also cover other conditions, so these codes are not included, to keep "
             "the mapping specific.")
Q_CALL = ("Mental Health Award call: “all types of anxiety (including obsessive-compulsive disorder and post-traumatic stress "
          "disorder); all types of depressive disorders (including post-natal depression); all forms of psychotic disorders "
          "(including schizophrenia, postpartum psychosis and bipolar disorder)”")
THEMES = {"infectious": "Infectious Diseases", "mental": "Mental Health"}

# Funding categories (section 5 of the spec): dark purple, light purple, neutral grey.
FUND = [("wellcome", "Wellcome-funded", "#5530C8", "#ffffff"),
        ("other", "Other reported funders only", "#B9A6F2", "#21124d"),
        ("none", "Funder not identified", "#E3E4EC", "#3a3644")]
# Income groups: kept distinct from the funding purples so the two encodings are never confused.
SETTING_COLORS = ["#0B7FA3", "#E5793A", "#CDD3DD"]
SETTING_INK = ["#ffffff", "#2b1d05", "#2a3140"]
SETTING_LABELS = ["High-income setting", "Low- & middle-income setting", "Multi-country, regional or income unavailable"]
CAPTURED, NOT_CAPTURED = "#5530C8", "#DCD5F5"

INTRO = ("This analysis uses existing GBD classifications as a proxy for alignment with Wellcome's specified research "
         "priorities within Infectious Diseases and Mental Health. The findings provide an indicative rather than "
         "comprehensive characterisation of thematic alignment.")
NOTE_1 = ("The thematic analysis provides an indicative characterisation of the HEE evidence base using existing GBD "
          "classifications as a proxy for Wellcome's specified research priorities. Differences in the scope and granularity "
          "of these classification systems limit the extent to which thematic alignment can be captured.")
NOTE_2 = ("Wellcome-funded publications not captured by this mapping may nevertheless contribute to Wellcome's research "
          "priorities, including through cross-cutting research and areas not represented by the selected GBD categories. "
          "The results should therefore not be interpreted as a comprehensive assessment of Wellcome's research portfolio "
          "or its alignment with strategic priorities.")

DESCRIPTION = {
    "infectious": ("Wellcome's infectious disease focus areas (tuberculosis, cholera, vector-borne diseases and drug-resistant "
                   "infections), matched with the closest GBD 2023 codes. See “Definition and matching criteria” below for the codes used."),
    "mental": ("Wellcome's mental health focus (anxiety, depression and psychosis), matched with the GBD 2023 codes for anxiety "
               "disorders, depressive disorders, schizophrenia and bipolar disorder. See “Definition and matching criteria” below for details."),
}

# Crosswalk: specified priority area -> eligible GBD codes. Fixed before any funding result was inspected; the same rule
# applies to every publication whoever funds it. status: confirmed / agreed judgement / flagged / not representable.
SRC_ID = "Wellcome, Infectious Disease page (“Our focus includes”), saved 27 Nov 2026."
SRC_MH = "Wellcome, Mental Health page (mission), saved 27 Nov 2026; Mental Health Award call."
SRC_CALL = "Wellcome Mental Health Award call: “all forms of psychotic disorders (including schizophrenia, postpartum psychosis and bipolar disorder)”."
CROSSWALK = [
    ("Infectious Diseases", "Tuberculosis", "Tuberculosis (GBD 2023 level 3)", SRC_ID, "GBD has a specific tuberculosis code.", "confirmed"),
    ("Infectious Diseases", "Cholera", "Diarrheal diseases (GBD 2023 level 3)", SRC_ID + " GBD has no separate cholera code.",
     "It also includes other diarrhoeal infections, such as rotavirus and Shigella.", "flagged"),
    ("Infectious Diseases", "Vector-borne diseases (named: schistosomiasis, leishmaniasis, dengue)",
     "Schistosomiasis; Leishmaniasis; Dengue (GBD 2023 level 3)", SRC_ID, "Each has its own GBD code.", "confirmed"),
    ("Infectious Diseases", "Vector-borne diseases (rest of the category)",
     "Malaria; Chagas disease; Lymphatic filariasis; Onchocerciasis; Zika virus; Yellow fever; African trypanosomiasis (GBD 2023 level 3)",
     "Wellcome names examples (“such as”), so the whole category is included, consistent with “all forms of psychotic "
     "disorders”. Every code listed is in the table of the WHO fact sheet “Vector-borne diseases” (26 Sep 2024).",
     "Mapped using WHO's list. " + WHO_MIXED, "judgement"),
    ("Infectious Diseases", "Drug-resistant infections", "None", SRC_ID,
     "GBD classifies conditions rather than resistance. Drug-resistant tuberculosis, for example, is included under "
     "tuberculosis.", "absent"),
    ("Mental Health", "Depression (incl. post-natal depression)", "Depressive disorders (GBD 2023 level 3)", SRC_MH + " The call includes “post-natal depression”.",
     "Includes post-natal depression.", "confirmed"),
    ("Mental Health", "Anxiety (incl. OCD and PTSD)", "Anxiety disorders (GBD 2023 level 3)", SRC_MH + " The call includes “obsessive-compulsive disorder and post-traumatic stress disorder”.",
     "OCD and PTSD studies coded to anxiety disorders are included; those coded to other mental disorders "
     "are outside the codes used.", "confirmed"),
    ("Mental Health", "Psychosis (incl. schizophrenia, postpartum psychosis, bipolar disorder)", "Schizophrenia; Bipolar disorder (GBD 2023 level 3)",
     SRC_CALL,
     "GBD has no single psychosis code; these follow Wellcome's own list of psychotic disorders. GBD has no separate "
     "code for postpartum psychosis; no publication in the map addresses it.", "flagged"),
    ("Mental Health", "Early intervention", "None", "Wellcome's mission is early intervention.",
     "GBD codes conditions, not the stage of intervention. Publications on these conditions are included at every "
     "stage and age.", "absent"),
]
NOT_IN_SCOPE = [
    ("Other infectious causes (e.g. HIV/AIDS, lower respiratory infections, COVID-19, rabies, intestinal nematodes)", "Counted in the broad Infectious Diseases theme in v5/v6; outside Wellcome's focus areas, so not eligible here."),
    ("Infections coded only at a broad level ('Respiratory infections and tuberculosis', 'Enteric infections', 'Neglected tropical diseases and malaria', 'Infections, disease not stated')", "Cannot be assigned to a specific eligible cause; not eligible. Flagged for review."),
    ("Other mental disorders and substance use disorders", "Previously counted in the broad Mental Health theme (v5/v6); outside Wellcome's specified focus, so not eligible here."),
    ("'Mental disorders' with no level-3 condition coded", "Cannot be assigned to anxiety, depression or psychosis; not eligible. Flagged for review."),
    ("Climate & Health", "Identified by a reviewed keyword screen, not GBD codes; excluded from every displayed analysis and aggregate."),
    ("17 Wellcome-funded publications added on title-and-abstract review (v6)", "Identified only by supplementary screening of Wellcome-funded publications; excluded."),
]

# Wellcome-funded publications not captured by the mapping: a GBD-based group first, then indicative title-keyword groups (v6).
UNMATCHED_NOTES = {
    "infectious": ("GBD 2023 classifies each study under the condition its intervention prevents or treats, shown beside each title: "
                   "HPV vaccination under cervical cancer, hepatitis C treatment under cirrhosis and other chronic liver diseases, maternal "
                   "Group B strep vaccination under neonatal disorders, antibiotic prophylaxis in miscarriage surgery under maternal disorders, "
                   "and an antibiotic stewardship programme under no single disease. These are not GBD infectious causes, so these "
                   "publications are not captured by the GBD-based Infectious Diseases mapping."),
    "mental": ("These publications address alcohol policy, such as minimum pricing and taxation, or include mental health among the outcomes "
               "of a wider programme. They are coded to a risk factor or to another condition, not to the GBD causes used for the Mental "
               "Health mapping."),
}
INFECTIOUS_OTHER = ("infectious_other", "Other infectious diseases",
                    "GBD 2023 codes these publications to infectious causes other than tuberculosis, diarrhoeal diseases and vector-borne "
                    "diseases, for example HIV/AIDS, lower respiratory infections or COVID-19. The Infectious Diseases mapping is restricted "
                    "to Wellcome's focus areas, so they are not captured.")
MENTAL_OTHER = ("mental_other", "Other mental health conditions and substance use",
                "GBD 2023 codes these publications to mental or substance use disorders other than the specified focus conditions "
                "(depressive and anxiety disorders, schizophrenia, bipolar disorder), for example alcohol or drug use disorders. "
                "The Mental Health mapping is restricted to Wellcome's specified focus, so they are not captured.")


def link_of(r):
    """Publication link: the master's url if present, else its DOI (the url field is empty for most records)."""
    url = (r.get("url") or "").strip()
    if url.startswith(("https://", "http://")):
        return url
    doi = (r.get("doi") or "").strip()
    if doi and doi.upper() != "NA":
        return doi if doi.startswith("http") else "https://doi.org/" + doi
    return ""


def crosswalk_codes():
    """GBD codes named in the crosswalk table, parsed back out, so the table cannot drift from the code lists used."""
    codes = set()
    for row in CROSSWALK:
        if row[2] != "None":
            codes |= {c.strip() for c in row[2].replace("(GBD 2023 level 3)", "").split(";") if c.strip()}
    return codes


def pct(n, d, digits=1):
    """Percentage with an explicit not-applicable for a zero denominator."""
    return f"{100 * n / d:.{digits}f}%" if d else "n/a"


esc = v6.escape


def analyse(rows, meta, source_hash):
    by_id = {r["record_id"]: r for r in rows}
    H = set(by_id)
    F = {i for i in H if by_id[i]["named_funders"]}
    W = {i for i in H if by_id[i]["wellcome"]}
    if not W <= F:
        raise ValueError(f"{len(W - F)} Wellcome-funded publications have no identified funder; check the funder rules.")
    sets = {"infectious": {i for i in H if by_id[i]["gbd_l3"] & set(INFECTIOUS_CODES)},
            "mental": {i for i in H if by_id[i]["gbd_l3"] & set(MENTAL_GROUPS)}}
    T = sets["infectious"] | sets["mental"]
    for i in T:  # eligibility never depends on supplementary screening or the climate list
        assert not (by_id[i]["review"] and not by_id[i]["themes_gbd"])

    def measures(S):
        m = {"n": len(S), "funded": len(S & F), "wellcome": len(S & W), "other": len(S & (F - W)), "none": len(S - F)}
        assert m["wellcome"] + m["other"] + m["none"] == m["n"], "funding segments must sum to the theme total"
        return m

    def subgroups(S, groups_of, order):
        members = defaultdict(list)
        for i in S:
            for g in groups_of(by_id[i]):
                members[g].append(by_id[i])
        out = []
        for g in sorted(members, key=lambda g: (-len(members[g]), order.index(g))):
            rs = members[g]
            out.append({"label": g, "n": len(rs), "wellcome": sum(r["wellcome"] for r in rs),
                        "studies": [{"title": r["title"], "year": r["year"], "url": link_of(r)}
                                    for r in sorted((r for r in rs if r["wellcome"]), key=lambda r: (r["year"], r["title"]))]})
        return out

    themes = {}
    for key, S in sets.items():
        subset = [by_id[i] for i in S]
        themes[key] = {"label": THEMES[key], **measures(S), "donors": v6.donor_counts(subset),
                       "income_counts": [sum(r["setting"] == k for r in subset) for k in range(3)],
                       "wellcome_income_counts": [sum(r["wellcome"] and r["setting"] == k for r in subset) for k in range(3)]}
        themes[key]["wellcome_rank"] = v6.wellcome_rank(themes[key]["donors"])
    themes["infectious"]["subgroups"] = subgroups(sets["infectious"], lambda r: r["gbd_l3"] & set(INFECTIOUS_CODES), INFECTIOUS_CODES)
    themes["mental"]["subgroups"] = subgroups(sets["mental"], lambda r: r["gbd_l3"] & set(MENTAL_GROUPS), MENTAL_GROUPS)
    other_inf = {i for i in H - sets["infectious"] if by_id[i]["gbd"] & set(INFECTIOUS_GROUPS)}
    broad_labels = {"Respiratory infections and tuberculosis", "Enteric infections", "Other infectious diseases",
                    "Neglected tropical diseases and malaria",
                    "Communicable, maternal, neonatal, and nutritional diseases"}
    broad_only = {i for i in other_inf if not by_id[i]["gbd_l3"] - broad_labels}
    mental_unspecified = {i for i in H if "Mental disorders" in by_id[i]["gbd_l3"] and not by_id[i]["gbd_l3"] & set(MENTAL_GROUPS)}

    # Wellcome-funded publications not captured: GBD-coded other mental/substance use first, then v6's title-keyword groups.
    groups = defaultdict(list)
    for i in sorted(W - T):
        r = by_id[i]
        key = (INFECTIOUS_OTHER[0] if r["gbd"] & set(INFECTIOUS_GROUPS) else MENTAL_OTHER[0] if r["mental_broad"] else
               next((k for k, _, pattern, _ in v6.OUTSIDE_GROUPS if pattern.search(r["title"])), v6.OUTSIDE_OTHER[0]))
        groups[key].append(r)
    specs = [INFECTIOUS_OTHER, MENTAL_OTHER] + [(k, label, UNMATCHED_NOTES.get(k)) for k, label, _, _ in v6.OUTSIDE_GROUPS] + [(v6.OUTSIDE_OTHER[0], v6.OUTSIDE_OTHER[1], None)]
    unmatched = [{"key": k, "label": label, "note": note, "n": len(groups[k]),
                  "studies": [{"title": r["title"], "year": r["year"], "url": link_of(r), "gbd": r["gbd_label"]}
                              for r in sorted(groups[k], key=lambda r: (r["year"], r["title"]))]}
                 for k, label, note in specs if groups[k]]
    unmatched.sort(key=lambda g: (g["key"] == "other", -g["n"]))
    wellcome_list = []
    for i in sorted(W, key=lambda i: (by_id[i]["year"], by_id[i]["title"])):
        r = by_id[i]
        themes_of = [THEMES[k] for k in sets if i in sets[k]]
        wellcome_list.append({"year": r["year"], "title": r["title"], "link": link_of(r),
                              "captured_by_mapping": "Yes" if themes_of else "No", "themes": "; ".join(themes_of),
                              "gbd_causes": r["gbd_label"],
                              "other_funders_identified": "; ".join(sorted(f for f in r["named_funders"] if f != "Wellcome Trust"))})

    years = meta["years"]
    by_year = [{"year": y, "n": sum(int(by_id[i]["year"]) == y for i in W)} for y in range(years[0], years[1] + 1)]
    overlap = sets["infectious"] & sets["mental"]
    union = measures(T)
    checks = {
        "W_subset_F": W <= F,
        "theme_segments_sum": all(t["wellcome"] + t["other"] + t["none"] == t["n"] for t in themes.values()),
        "union_segments_sum": union["wellcome"] + union["other"] + union["none"] == union["n"],
        "captured_plus_not_captured_equals_W": len(W & T) + len(W - T) == len(W),
        "union_equals_sum_minus_overlap": len(T) == len(sets["infectious"]) + len(sets["mental"]) - len(overlap),
        "trend_sums_to_W": sum(y["n"] for y in by_year) == len(W),
        "unmatched_lists_sum_to_W_minus_T": sum(g["n"] for g in unmatched) == len(W - T),
        "unique_record_ids": len(H) == len(rows),
        "wellcome_list_equals_W": True,  # set below once the list is built
    }
    checks["wellcome_list_equals_W"] = len(wellcome_list) == len(W) and sum(x["captured_by_mapping"] == "Yes" for x in wellcome_list) == len(W & T)
    if not all(checks.values()):
        raise ValueError("Reconciliation failed: " + ", ".join(k for k, ok in checks.items() if not ok))
    return {
        "meta": {"years": years, "data_built": meta["built"], "master_sha256": source_hash, "n_eligible": len(H),
                 "gbd_share": f"team GBD 2023 coding, share v2.1 (received {v6.GBD_SHARE_RECEIVED})",
                 "search_end": v6.SEARCH_END, "analysis_built": f"{datetime.date.today():%d %B %Y}".lstrip("0"),
                 "unit": "Unique eligible publication (record_id). Funders counted once per publication; not grants or amounts."},
        "H": len(H), "F": len(F), "W": len(W), "union": union, "overlap": len(overlap),
        "overlap_wellcome": len(overlap & W), "themes": themes,
        "wellcome_captured": len(W & T), "wellcome_not_captured": len(W - T),
        "infectious_other_excluded": {"n": len(other_inf), "wellcome": len(other_inf & W)},
        "infectious_broad_level_only_excluded": {"n": len(broad_only), "wellcome": len(broad_only & W)},
        "mental_unspecified_excluded": {"n": len(mental_unspecified), "wellcome": len(mental_unspecified & W)},
        "unmatched_groups": unmatched, "wellcome_by_year": by_year, "checks": checks, "wellcome_publications": wellcome_list,
        "crosswalk": [dict(zip(["theme", "priority_area", "gbd_codes", "rationale_source", "limitation", "status"], c)) for c in CROSSWALK],
        "not_in_scope": [{"category": a, "reason": b} for a, b in NOT_IN_SCOPE],
    }


STYLE = '''
:root{--ink:#1d1a2e;--muted:#5d5870;--soft:#7d778f;--line:#e8e3ef;--paper:#f5f5fa;--card:#fff;--violet:#5530C8;--violet-2:#8C72E6;
--lav:#efeafd;--lav-2:#f7f4fe;--focus:#1f5fa8}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.6 Inter,system-ui,sans-serif}
main{padding:24px 28px 40px;max-width:1120px;overflow-wrap:anywhere}
.embedded main{padding-top:4px}.embedded .page-head{display:none}
h1,h2{font-family:Newsreader,Georgia,serif;font-weight:600;letter-spacing:-.01em}
h1{font-size:clamp(28px,4vw,40px);line-height:1.1;margin:8px 0 10px}
h2{font-size:26px;line-height:1.2;margin:0 0 6px}
h3{font-size:16px;margin:0 0 4px}
a{color:var(--violet)}
button:focus-visible,a:focus-visible,summary:focus-visible,[tabindex]:focus-visible{outline:3px solid var(--focus);outline-offset:3px}
.lede{color:var(--muted);margin:0 0 8px;max-width:820px}
.hint{color:var(--muted);font-size:13.5px;margin:2px 0 12px;max-width:860px}
.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.linkbtn{all:unset;cursor:pointer;color:var(--violet);font-weight:600;font-size:14px}.linkbtn:hover{text-decoration:underline}
section.block{margin:44px 0 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:22px 24px}
/* Section A */
.heads{display:grid;grid-template-columns:repeat(3,1fr);gap:0;margin:18px 0 22px}
.head{padding:0 22px}.head:first-child{padding-left:0}.head+.head{border-left:1px solid var(--line)}
.head strong{display:block;font:600 44px/1 Newsreader,Georgia,serif}
.head.w strong{color:var(--violet)}
.head .lab{display:block;font-weight:600;margin-top:6px}
.head .den{display:block;font-size:13px;color:var(--muted)}
.fbar{display:flex;height:30px;border-radius:7px;overflow:hidden;background:#fff}
.fbar span{display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:600;white-space:nowrap;overflow:hidden;min-width:0}
.fbar span+span{box-shadow:inset 2px 0 0 #fff}
.frow{display:grid;grid-template-columns:minmax(150px,190px) 1fr 120px 140px 120px;gap:14px;align-items:center;padding:12px 0;border-top:1px solid var(--line);font-size:13.5px}
.frow.total{border-top:0;padding-top:0}
.frow .name{font-weight:600}.frow .name small{display:block;font-weight:500;color:var(--muted);font-size:12.5px}
.frow .track{background:transparent}
.frow .stat{font-variant-numeric:tabular-nums}.frow .stat b{display:block;font-size:15px}.frow .stat small{color:var(--muted);font-size:12px}
.frow .stat.w b{color:var(--violet)}
.explore{all:unset;cursor:pointer;justify-self:end;color:var(--violet);font-weight:600;font-size:13.5px;border:1px solid #d8cdea;border-radius:999px;padding:5px 12px;white-space:nowrap}
.explore:hover{background:var(--lav)}
.colhead{display:grid;grid-template-columns:minmax(150px,190px) 1fr 120px 140px 120px;gap:14px;align-items:end;font-size:11.5px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:var(--soft);padding:16px 0 6px;line-height:1.35}.colhead small{display:block;font-size:11px;font-weight:500;letter-spacing:0;text-transform:none;color:var(--soft)}
.legend{display:flex;gap:6px 18px;flex-wrap:wrap;font-size:12.5px;color:var(--muted);margin:12px 0 0}
.legend i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:6px;vertical-align:-1px}
.foot{font-size:12.5px;color:var(--muted);margin:10px 0 0}
/* Section B */
nav.tabs{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0 0;position:sticky;top:0;background:var(--paper);padding:12px 0;z-index:2;border-bottom:1px solid var(--line)}
nav.tabs button{background:#fff;color:var(--ink);border:1px solid var(--line);border-radius:999px;padding:8px 16px;font:600 14px Inter,system-ui,sans-serif;cursor:pointer}
nav.tabs button[aria-selected=true]{background:var(--violet);border-color:var(--violet);color:#fff}
.theme{padding-top:18px}
.theme>.desc{max-width:860px;margin:0 0 6px}
.sub{font-size:12px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--soft);margin:26px 0 8px}
.rankline{font-size:14px;margin:0 0 10px}.rankline b{color:var(--violet)}
.donors{display:grid;grid-template-columns:34px minmax(150px,260px) 1fr 56px;gap:7px 14px;align-items:center;font-size:13.5px}
.donors .rank{color:var(--soft);text-align:right;font-variant-numeric:tabular-nums}
.donors .bar{display:flex;height:16px;border-radius:4px;overflow:hidden}
.donors .bar span{display:block;height:100%}
.donors .wl{font-weight:700;color:var(--violet)}
.donors .gap{grid-column:1/-1;text-align:center;color:var(--soft);font-size:12px;line-height:1}
.compare{display:grid;grid-template-columns:200px 1fr 80px;gap:10px 14px;align-items:center;font-size:13.5px}
.stack{display:flex;height:26px;border-radius:6px;overflow:hidden;background:var(--lav);min-width:160px}
.stack span{display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:600}.stack span+span{box-shadow:inset 2px 0 0 #fff}
.stack.empty{color:var(--muted);font-size:12.5px;align-items:center;padding-left:8px}
.groups{border-top:1px solid var(--line)}
.group{border-bottom:1px solid var(--line)}
.group summary{display:grid;grid-template-columns:minmax(220px,40%) 1fr 96px;gap:16px;align-items:center;padding:8px 0;list-style:none;cursor:pointer}
.group summary::-webkit-details-marker{display:none}
.group summary .g-label::before{content:"\\25B8";display:inline-block;width:16px;color:var(--soft);transition:transform .15s}
.group[open] summary .g-label::before{transform:rotate(90deg)}
.group ol{margin:4px 0 14px;padding-left:40px;font-size:13.5px}
.group .hint{margin:0 0 6px 16px}
.meter{position:relative;height:8px;background:var(--lav);border-radius:4px;min-width:80px}
.meter i{position:absolute;inset:0 auto 0 0;border-radius:4px;background:var(--violet-2)}
.meter b{position:absolute;inset:0 auto 0 0;border-radius:4px;background:var(--violet)}
.num small.wn{display:block;font-size:11.5px;font-weight:500;color:var(--muted)}
details.def{margin:22px 0 0;border:1px solid var(--line);border-radius:10px;background:var(--card);padding:10px 16px}
details.def summary{cursor:pointer;color:var(--violet);font-weight:600;font-size:14px}
details.def ul{margin:8px 0 4px;padding-left:20px;font-size:13.5px}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin:6px 0 0}
.gbd{background:var(--lav-2);border:1px solid #e2d9f0;border-radius:999px;padding:2px 10px;font-size:12.5px;color:#3b2b63}
/* Section C */
.wtop{display:grid;grid-template-columns:minmax(180px,240px) 1fr;gap:28px;align-items:center;margin-top:14px}
.wtop .big strong{display:block;font:600 64px/1 Newsreader,Georgia,serif;color:var(--violet)}
.wtop .big span{display:block;color:var(--muted);font-size:13.5px;margin-top:6px}
.cov h3{font-size:14px;font-weight:600;color:var(--muted);margin:0 0 8px}
.cov .fbar{height:24px}
.note{margin:16px 0 0;background:var(--lav-2);border-left:3px solid var(--violet-2);border-radius:6px;padding:10px 14px;font-size:13.5px;max-width:900px}
.note p{margin:0}.note p+p{margin-top:8px}
details.list{margin:16px 0 0;border:1px solid var(--line);border-radius:10px;background:var(--card);padding:10px 16px}
details.list>summary{cursor:pointer;font-weight:600;color:var(--violet)}
details.list .group summary{grid-template-columns:minmax(220px,45%) 1fr 44px}
.trend-head{display:flex;justify-content:space-between;align-items:flex-end;gap:12px;flex-wrap:wrap;margin-top:30px}
.toggle{display:inline-flex;border:1px solid var(--line);border-radius:999px;overflow:hidden;background:#fff}
.toggle button{all:unset;cursor:pointer;padding:6px 14px;font-size:13px;font-weight:600;color:var(--muted)}
.toggle button[aria-pressed=true]{background:var(--violet);color:#fff}
#trend{position:relative;margin-top:10px}
#trend svg{display:block;width:100%;height:auto;overflow:visible}
#trend svg:focus{outline:none}#trend svg:focus-visible{outline:3px solid var(--focus);outline-offset:4px}
#trend .tip{position:absolute;pointer-events:none;background:#fff;border:1px solid var(--line);border-radius:8px;padding:6px 10px;font-size:12.5px;box-shadow:0 4px 14px rgba(40,30,70,.12);white-space:nowrap;transform:translate(-50%,-120%)}
.trend-note{font-size:12.5px;color:var(--muted);margin:8px 0 0;max-width:900px}
/* tooltips for ? marks */
.qmark{display:inline-flex;align-items:center;justify-content:center;width:15px;height:15px;border-radius:50%;background:var(--lav);border:1px solid #d8cdea;color:#5b4691;font:700 10px/1 Inter,system-ui,sans-serif;cursor:help;vertical-align:1px;margin-left:3px}
.qtip{position:fixed;z-index:50;max-width:320px;background:#2d2840;color:#fff;font:500 12px/1.45 Inter,system-ui,sans-serif;padding:7px 10px;border-radius:8px;box-shadow:0 6px 18px rgba(30,20,60,.25)}
/* Methodology */
details.method{border:1px solid var(--line);background:var(--card);padding:14px 18px;border-radius:12px;margin:44px 0 0;font-size:13.5px;color:var(--ink)}
details.method>summary{cursor:pointer;font-weight:600;font-size:15px}
details.method h4{margin:18px 0 4px;font-size:13.5px}
details.method p{margin:4px 0 8px;color:#38344a}
.xw-wrap{overflow-x:auto;max-width:100%}.xw{min-width:760px;width:100%;table-layout:fixed;border-collapse:collapse;font-size:12.5px;line-height:1.5;margin:6px 0}.xw th:nth-child(1){width:11%}.xw th:nth-child(2){width:17%}.xw th:nth-child(3){width:19%}.xw th:nth-child(4){width:23%}.xw th:nth-child(5){width:30%}.xw td{overflow-wrap:break-word;hyphens:auto}.xw .st{display:inline-block;margin:0 0 4px}
.xw th,.xw td{border-top:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}
.xw th{font-size:11.5px;text-transform:uppercase;letter-spacing:.04em;color:var(--soft)}
.st{display:inline-block;border-radius:999px;padding:0 8px;font-size:11.5px;font-weight:600;white-space:nowrap}
.st.confirmed{background:#e3f4f8;color:#0b5a73}.st.judgement{background:#efeafd;color:#4a2fa8}.st.flagged{background:#efeafd;color:#4a2fa8}.st.absent{background:#efedf3;color:#4a4658}
.download{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:22px 0 8px;font-size:13.5px}.download a{color:var(--violet);font-weight:600;text-decoration:none;border:1px solid #d9cff7;background:#fff;border-radius:999px;padding:6px 14px}.download a:hover{background:var(--lav)}
.png-status{font-size:13px;color:var(--muted)}
[hidden]{display:none!important}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}

/* v3.9 visual refresh */
body{background:var(--paper)}
main{max-width:1160px}
.page-head{background:linear-gradient(120deg,#ece5ff 0%,#f4f0ff 45%,#ffffff 100%);border:1px solid #e3daff;border-radius:20px;padding:30px 34px 26px;margin:6px 0 0;box-shadow:0 10px 30px rgba(85,48,200,.08)}
.page-head h1{margin:0 0 10px;color:#1b1340}
.page-head .eyebrow{display:inline-block;font:700 11.5px/1 Inter,system-ui,sans-serif;letter-spacing:.08em;text-transform:uppercase;color:var(--violet);background:#fff;border:1px solid #e3daff;border-radius:999px;padding:6px 10px;margin-bottom:12px}
.page-head .lede{color:#4b4565;max-width:860px}
section.block{background:#fff;border:1px solid #ebe8f3;border-radius:18px;padding:26px 28px 24px;box-shadow:0 1px 2px rgba(30,20,60,.04),0 10px 28px rgba(30,20,60,.05);margin:22px 0 0}
section.block>h2{display:flex;align-items:center;gap:12px}
section.block>h2::before{content:"";flex:0 0 auto;width:6px;height:24px;border-radius:3px;background:linear-gradient(180deg,#8C72E6,#5530C8)}
.heads{gap:14px}
.head{padding:18px 20px;border-radius:14px;background:#f6f4fc;border:1px solid #ece7fa}
.head:first-child{padding-left:20px}
.head+.head{border-left:1px solid #ece7fa}
.head:nth-child(2){background:#f1ecfd}
.head.w{background:linear-gradient(135deg,#ebe3ff,#f4efff);border-color:#ddd2fb}
.head strong{color:#1b1340}
.head.w strong{color:var(--violet)}
.fbar{height:34px;border-radius:10px}
.frow .fbar{height:28px;border-radius:8px}
.cov .fbar{height:30px}
.stack{height:28px;border-radius:8px}
.donors .bar{height:18px;border-radius:6px}
.explore{background:#f3effe;border-color:#e0d6fb}
.explore:hover{background:#e9e2fd}
nav.tabs{background:#fff}
.note{background:#f6f3ff;border-left:4px solid #8C72E6;border-radius:10px}
.meter{height:9px;background:#f0edf8}
details.method,details.def{border-color:#ebe8f3;border-radius:14px}
details.method{background:#fff;box-shadow:0 1px 2px rgba(30,20,60,.04)}
.sub{color:#6c5fa0}
@media(max-width:820px){section.block{padding:20px 16px 18px;border-radius:14px}.page-head{padding:22px 18px 18px;border-radius:16px}}
@media(max-width:820px){main{padding:16px}
.heads{grid-template-columns:1fr;gap:14px}.head{padding:0}.head+.head{border-left:0;border-top:1px solid var(--line);padding-top:12px}
.colhead{display:none}.frow{grid-template-columns:1fr 1fr;gap:8px 12px}.frow .name,.frow .track{grid-column:1/-1}.frow .explore{grid-column:1/-1;justify-self:start}
.wtop{grid-template-columns:1fr;gap:12px}.compare{grid-template-columns:1fr 64px}.compare .lab{grid-column:1/-1;margin-bottom:-6px}
.donors{grid-template-columns:22px minmax(0,1fr) minmax(70px,32%) 40px;gap:6px 8px;font-size:12.5px}
.group summary{grid-template-columns:1fr 110px}details.list .group summary{grid-template-columns:1fr 44px}.group summary .meter{display:none}
}
@media print{body{background:#fff}nav.tabs,.explore,.toggle,.download,.qtip{display:none!important}
.theme[hidden]{display:block!important}.theme{break-before:page}#trend .tip{display:none}}
'''

SCRIPT = r'''
if (window.self !== window.top) document.documentElement.classList.add('embedded');
const DATA = JSON.parse(document.getElementById('data').textContent);
// '?' tooltips: hover or keyboard focus.
const qtip = document.createElement('div'); qtip.className = 'qtip'; qtip.hidden = true; qtip.setAttribute('role', 'tooltip'); document.body.appendChild(qtip);
function showTip(el) {
  qtip.textContent = el.dataset.tip; qtip.hidden = false;
  const r = el.getBoundingClientRect(), w = qtip.offsetWidth, h = qtip.offsetHeight, vw = document.documentElement.clientWidth;
  qtip.style.left = Math.max(8, Math.min(vw - w - 8, r.left + r.width / 2 - w / 2)) + 'px';
  qtip.style.top = (r.top - h - 8 >= 8 ? r.top - h - 8 : r.bottom + 8) + 'px';
}
function bindTip(el) {
  el.addEventListener('mouseenter', () => showTip(el)); el.addEventListener('focus', () => showTip(el));
  el.addEventListener('mouseleave', () => { qtip.hidden = true; }); el.addEventListener('blur', () => { qtip.hidden = true; });
}
document.querySelectorAll('.qmark').forEach(bindTip);
window.addEventListener('scroll', () => { qtip.hidden = true; }, {passive: true});
// Theme tabs (two only) and the overview's "Explore theme" actions.
const tabs = [...document.querySelectorAll('nav.tabs [role=tab]')];
function show(key, scroll) {
  tabs.forEach(b => { const on = b.dataset.theme === key; b.setAttribute('aria-selected', String(on)); b.tabIndex = on ? 0 : -1; });
  document.querySelectorAll('.theme').forEach(p => { p.hidden = p.id !== 'theme-' + key; });
  if (scroll) document.getElementById('explore').scrollIntoView({behavior: 'smooth', block: 'start'});
}
tabs.forEach((b, i) => {
  b.addEventListener('click', () => show(b.dataset.theme, false));
  b.addEventListener('keydown', e => {
    if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
    const n = tabs[(i + (e.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length]; n.focus(); show(n.dataset.theme, false);
  });
});
document.querySelectorAll('[data-explore]').forEach(b => b.addEventListener('click', () => { show(b.dataset.explore, true); }));
document.querySelectorAll('[data-open-method]').forEach(b => b.addEventListener('click', e => {
  e.preventDefault(); const d = document.getElementById('method'); d.open = true; d.scrollIntoView({behavior: 'smooth', block: 'start'});
}));
// Print: open the methodology so it is included; restore afterwards.
let wasOpen = null;
window.addEventListener('beforeprint', () => { const d = document.getElementById('method'); wasOpen = d.open; d.open = true; });
window.addEventListener('afterprint', () => { if (wasOpen !== null) document.getElementById('method').open = wasOpen; });
// PNG of the page as shown (current theme tab).
document.querySelectorAll('[data-png]').forEach(link => link.addEventListener('click', async e => {
  e.preventDefault();
  const status = document.querySelector('.png-status'); status.textContent = 'Preparing image…';
  try {
    if (!window.html2canvas) await new Promise((resolve, reject) => {
      const sc = document.createElement('script'); sc.src = '../vendor/html2canvas-1.4.1.min.js';
      sc.onload = resolve; sc.onerror = () => reject(new Error('Image renderer could not load.')); document.head.appendChild(sc);
    });
    await document.fonts.ready;
    const canvas = await window.html2canvas(document.querySelector('main'), {scale: 2, backgroundColor: '#f5f5fa', windowWidth: 1200, logging: false,
      onclone(clone) { clone.querySelectorAll('.qtip, .download, details.method, nav.tabs, .explore, .toggle, #trend .tip').forEach(n => n.remove()); }});
    const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'));
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'wellcome_priority_themes.png';
    document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 10000);
    status.textContent = '';
  } catch (err) { status.textContent = 'Image download failed: ' + err.message; }
}));
// Publication-year trend: line charts for both views, straight segments, no smoothing.
// Annual: fixed 0-100 axis, ticks every 30 (raised in steps of 30 only if a count exceeds 100).
// Cumulative: its own zero-based rounded axis. Final (partial) year: dashed segment and hollow point.
const NS = 'http://www.w3.org/2000/svg';
function node(tag, attrs, parent) { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; }
function niceStep(v) { const s = Math.pow(10, Math.floor(Math.log10(v))); for (const m of [1, 2, 2.5, 5, 10]) if (m * s >= v) return m * s; return v; }
let mode = 'annual', cur = null;
function drawTrend() {
  const host = document.getElementById('trend'); host.textContent = '';
  const years = DATA.years.map(d => d.year), annual = DATA.years.map(d => d.n);
  let run = 0; const vals = mode === 'cumulative' ? annual.map(n => (run += n)) : annual;
  const wide = host.clientWidth === 0 || host.clientWidth >= 640;
  // Plot area about 3:1 on desktop (870 x 290), about 1.8:1 on narrow screens.
  const W = wide ? 940 : 600, H = wide ? 340 : 370, L = 46, R = 24, T = 14, B = 36, last = years.length - 1;
  const top = Math.max(...vals);
  let ymax, ticks = [];
  if (mode === 'annual') { ymax = top <= 100 ? 100 : 30 * Math.ceil(top / 30); for (let v = 0; v < ymax || (ymax % 30 === 0 && v === ymax); v += 30) ticks.push(v); }
  else { const st = niceStep(top / 4); ymax = st * Math.ceil(top / st); for (let v = 0; v <= ymax + 1e-9; v += st) ticks.push(v); }
  const x = i => L + i * (W - L - R) / last, y = v => T + (H - T - B) * (1 - v / ymax);
  const label = `Wellcome-funded publications by publication year, ${mode === 'cumulative' ? 'cumulative' : 'per year'}, ${years[0]} to ${years[last]}. Use the left and right arrow keys to read each year.`;
  const svg = node('svg', {viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': label, tabindex: 0}, host);
  ticks.forEach(v => {
    node('line', {x1: L, x2: W - R, y1: y(v), y2: y(v), stroke: v ? '#ece8f1' : '#c9c1d6', 'stroke-width': 1}, svg);
    node('text', {x: L - 8, y: y(v) + 4, 'text-anchor': 'end', 'font-size': 11.5, fill: '#7d778f'}, svg).textContent = v.toLocaleString();
  });
  const every = wide ? 2 : 3;
  years.forEach((yr, i) => { if ((i % every === 0 && last - i >= every) || i === last) node('text', {x: x(i), y: H - 12, 'text-anchor': 'middle', 'font-size': 11.5, fill: '#7d778f'}, svg).textContent = yr; });
  const pts = vals.map((v, i) => [x(i), y(v)]);
  node('polygon', {points: `${x(0)},${y(0)} ` + pts.map(p => p.join(',')).join(' ') + ` ${x(last)},${y(0)}`, fill: '#5530C8', 'fill-opacity': .07}, svg);
  node('polyline', {points: pts.slice(0, last).map(p => p.join(',')).join(' '), fill: 'none', stroke: '#5530C8', 'stroke-width': 2.25, 'stroke-linejoin': 'round', 'stroke-linecap': 'round'}, svg);
  node('line', {x1: pts[last - 1][0], y1: pts[last - 1][1], x2: pts[last][0], y2: pts[last][1], stroke: '#5530C8', 'stroke-width': 2.25, 'stroke-dasharray': '5 5'}, svg);
  pts.forEach(([px, py], i) => node('circle', {cx: px, cy: py, r: i === last ? 4.5 : 3.25, fill: i === last ? '#fff' : '#5530C8', stroke: i === last ? '#5530C8' : '#fff', 'stroke-width': i === last ? 2 : 1}, svg));
  const tip = document.createElement('div'); tip.className = 'tip'; tip.hidden = true; host.appendChild(tip);
  const guide = node('line', {y1: T, y2: H - B, stroke: '#cfc7dc', 'stroke-dasharray': '3 3', visibility: 'hidden'}, svg);
  function at(i) {
    cur = i; const box = svg.getBoundingClientRect();
    guide.setAttribute('x1', x(i)); guide.setAttribute('x2', x(i)); guide.setAttribute('visibility', 'visible');
    tip.hidden = false; tip.style.left = (x(i) * box.width / W) + 'px'; tip.style.top = (y(vals[i]) * box.height / H) + 'px';
    tip.innerHTML = `<strong>${mode === 'cumulative' ? 'By end of ' : ''}${years[i]}</strong>: ${vals[i].toLocaleString()} ${vals[i] === 1 ? 'publication' : 'publications'}${i === last ? ` (partial year, searches ended ${DATA.searchEnd})` : ''}`;
  }
  function hide() { tip.hidden = true; guide.setAttribute('visibility', 'hidden'); }
  const hit = node('rect', {x: L - 10, y: T, width: W - L - R + 20, height: H - T - B, fill: 'transparent'}, svg);
  hit.addEventListener('mousemove', ev => { const box = svg.getBoundingClientRect(), sx = (ev.clientX - box.left) * W / box.width;
    at(Math.max(0, Math.min(last, Math.round((sx - L) / ((W - L - R) / last))))); });
  hit.addEventListener('mouseleave', hide);
  svg.addEventListener('focus', () => at(cur === null ? last : cur)); svg.addEventListener('blur', hide);
  svg.addEventListener('keydown', e => { if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') { e.preventDefault(); at(Math.max(0, Math.min(last, (cur === null ? last : cur) + (e.key === 'ArrowRight' ? 1 : -1)))); } });
}
document.querySelectorAll('[data-trend]').forEach(b => b.addEventListener('click', () => {
  document.querySelectorAll('[data-trend]').forEach(o => o.setAttribute('aria-pressed', String(o === b)));
  mode = b.dataset.trend; cur = null; drawTrend();
}));
let lastWide = null;
window.addEventListener('resize', () => { const w = document.getElementById('trend').clientWidth >= 640; if (w !== lastWide) { lastWide = w; drawTrend(); } });
drawTrend(); lastWide = document.getElementById('trend').clientWidth >= 640;
'''


def report(a):
    H, union, themes = a["H"], a["union"], a["themes"]
    W, cap, notcap = a["W"], a["wellcome_captured"], a["wellcome_not_captured"]
    years = a["meta"]["years"]
    scale = max(1, union["n"])  # one absolute scale: the combined bar and both theme rows

    def tip(text):
        return f'<span class="qmark" tabindex="0" role="note" aria-label="{esc(text)}" data-tip="{esc(text)}">?</span>'

    def link(x):
        t = esc(x["title"])
        return f'<a href="{esc(x["url"])}" target="_blank" rel="noopener">{t}</a>' if x["url"].startswith(("https://", "http://")) else t

    def fund_bar(m, width_pct, label):
        parts = []
        for key, name, color, ink in FUND:
            n = m[key]
            if not n:
                continue
            share = 100 * n / m["n"]
            text = f"{share:.0f}%" if share * width_pct / 100 >= 7 else ""
            parts.append(f'<span style="flex:{n};background:{color};color:{ink}" title="{esc(name)}: {n:,} of {m["n"]:,} ({share:.1f}%)">{text}</span>')
        summary = "; ".join(f"{name} {m[key]:,} ({pct(m[key], m['n'])})" for key, name, _, _ in FUND)
        return (f'<div class="track"><div class="fbar" role="img" aria-label="{esc(label)}: {esc(summary)}" '
                f'style="width:{width_pct:.3f}%">{"".join(parts)}</div></div>')

    def frow(m, name, sub, key=None, cls=""):
        explore = (f'<button type="button" class="explore" data-explore="{key}" aria-controls="theme-{key}">Explore theme →</button>'
                   if key else '<span></span>')
        return (f'<div class="frow{cls}"><span class="name">{esc(name)}<small>{sub}</small></span>'
                f'{fund_bar(m, 100 * m["n"] / scale, name)}'
                f'<span class="stat"><b>{m["funded"]:,}</b><small>{pct(m["funded"], m["n"])} of {m["n"]:,}</small></span>'
                f'<span class="stat w"><b>{m["wellcome"]:,}</b><small>{pct(m["wellcome"], m["funded"])} of {m["funded"]:,}</small></span>{explore}</div>')

    legend = '<div class="legend">' + ''.join(f'<span><i style="background:{c}"></i>{esc(n)}</span>' for _, n, c, _ in FUND) + '</div>'
    sec_a = f'''<section class="block" id="overview" aria-labelledby="overview-h"><h2 id="overview-h">Evidence coverage and funding across mapped priority areas</h2>
<p class="hint">Publications in the map captured by the GBD-based mapping of Wellcome's specified priority areas within Infectious Diseases and Mental Health, and whether a funder, and Wellcome, is identified.</p>
<div class="heads">
<div class="head"><strong>{union["n"]:,}</strong><span class="lab">Publications captured by the mapping</span><span class="den">{pct(union["n"], H)} of all {H:,} publications in the map</span></div>
<div class="head"><strong>{union["funded"]:,}</strong><span class="lab">Funder identified {tip("A funder is named in the publication's Crossref metadata. For the rest none was found there; they may still report funding in the full text, which was not screened. Missing funder information is not evidence of no funding.")}</span><span class="den">{pct(union["funded"], union["n"])} of the {union["n"]:,} mapped publications</span></div>
<div class="head w"><strong>{union["wellcome"]:,}</strong><span class="lab">Wellcome-funded {tip("Wellcome identified as a funder, alone or with other funders.")}</span><span class="den">{pct(union["wellcome"], union["funded"])} of the {union["funded"]:,} with a funder identified</span><span class="den">{pct(union["wellcome"], union["n"], 1)} of all {union["n"]:,} mapped (the share in the bar)</span></div>
</div>
<div class="colhead" aria-hidden="true"><span></span><span>Funding composition<small>Shared scale: bar length = publications</small></span><span>Funder identified<small>% of row total</small></span><span>Wellcome-funded<small>% of funder identified</small></span><span></span></div>
{frow(union, "All mapped publications", f"{union['n']:,} unique", cls=" total")}
{''.join(frow(themes[k], THEMES[k], f"{themes[k]['n']:,} publications", k) for k in THEMES)}
{legend}
<p class="foot">Publications may be captured under more than one theme ({a["overlap"]:,} {"is" if a["overlap"] == 1 else "are"} in both). Combined figures count unique publications. All bars use the same scale: bar length is the number of publications; segments within each bar are shares of that row's total. <a href="#method" data-open-method>About the thematic mapping</a></p>
</section>'''

    tablist, panels = [], []
    for i, (key, t) in enumerate(themes.items()):
        tablist.append(f'<button type="button" role="tab" id="tab-{key}" data-theme="{key}" aria-controls="theme-{key}" aria-selected="{str(i == 0).lower()}" tabindex="{0 if i == 0 else -1}">{esc(t["label"])}</button>')
        donors, rank_of = t["donors"], v6.ranks(t["donors"])
        max_n = max([d["n"] for d in donors] or [1])
        shown = list(range(min(10, len(donors))))
        wi = next((j for j, d in enumerate(donors) if d["funder"] == "Wellcome Trust"), None)
        rows_html, wl_cls = [], ' class="wl"'
        for j in shown + ([wi] if wi is not None and wi not in shown else []):
            d = donors[j]
            if j == wi and j not in shown:
                rows_html.append('<div class="gap">⋯</div>')
            hover = " · ".join(f"{lab}: {c:,}" for lab, c in zip(["High income", "Low & middle income", "Other / unavailable"], d["income_counts"]))
            seg = ''.join(f'<span style="width:{100 * c / max_n:.4f}%;background:{col}"></span>' for c, col in zip(d["income_counts"], SETTING_COLORS))
            tied = rank_of.count(rank_of[j]) > 1
            rows_html.append(f'<span class="rank">{"=" if tied else ""}{rank_of[j]}</span><span{wl_cls if j == wi else ""}>{esc(d["funder"])}</span>'
                             f'<span class="bar" title="{esc(d["funder"])}: {d["n"]:,} publications. {esc(hover)}" style="background:linear-gradient(90deg,transparent {100 * d["n"] / max_n:.2f}%,#f4f1f8 0)">{seg}</span>'
                             f'<span class="num"><strong>{d["n"]:,}</strong></span>')
        set_legend = '<div class="legend" style="margin:0 0 10px">' + ''.join(f'<span><i style="background:{c}"></i>{esc(l)}</span>' for c, l in zip(SETTING_COLORS, SETTING_LABELS)) + '</div>'

        def stack(counts, total):
            if not total:
                return '<div class="stack empty">No publications</div>'
            whole, tenths = v6.rounded_shares(counts, total), v6.rounded_shares(counts, total, 1)
            return '<div class="stack">' + ''.join(
                f'<span style="width:{100 * c / total:.4f}%;background:{col};color:{ink}" title="{esc(lab)}: {c:,} of {total:,} ({tp:.1f}%)">{f"{wp:.0f}%" if 100 * c / total >= 9 else ""}</span>'
                for c, col, ink, lab, wp, tp in zip(counts, SETTING_COLORS, SETTING_INK, SETTING_LABELS, whole, tenths)) + '</div>'

        max_g = max(g["n"] for g in t["subgroups"])
        items = []
        for g in t["subgroups"]:
            lis = ''.join(f'<li>{link(x)} <small>({esc(x["year"])})</small></li>' for x in g["studies"])
            body = f'<ol>{lis}</ol>' if lis else '<p class="hint">No Wellcome-funded publications in this group.</p>'
            items.append(f'<details class="group"><summary><span class="g-label">{esc(g["label"])}</span>'
                         f'<span class="meter" aria-hidden="true"><i style="width:{100 * g["n"] / max_g:.4f}%"></i><b style="width:{100 * g["wellcome"] / max_g:.4f}%"></b></span>'
                         f'<span class="num"><strong>{g["n"]:,}</strong><small class="wn">{g["wellcome"]:,} Wellcome-funded</small></span></summary>{body}</details>')
        group_sum = sum(g["n"] for g in t["subgroups"])
        overlap_note = (f" A publication can be coded to more than one group, so the group counts ({group_sum:,} in total) sum to more than the {t['n']:,} publications in the theme."
                        if group_sum > t["n"] else " Each publication is in one group.")
        if key == "infectious":
            oi, bo = a["infectious_other_excluded"], a["infectious_broad_level_only_excluded"]
            criteria = (f'<li>Eligible GBD 2023 level-3 causes:<div class="chips">{"".join(f"<span class=gbd>{esc(g)}</span>" for g in INFECTIOUS_CODES)}</div></li>'
                        f'<li>Rationale: Wellcome\'s <a href="{INF_URL}" target="_blank" rel="noopener">Infectious Disease</a> page: {esc(Q_ID)}. Diarrhoeal diseases is the closest GBD code for cholera. Vector-borne diseases is mapped as a whole category, using the <a href="{WHO_URL}" target="_blank" rel="noopener">WHO list of vector-borne diseases</a>, because Wellcome names examples (“such as”).</li>'
                        f'<li>Points to note: diarrhoeal diseases also includes other diarrhoeal infections, such as rotavirus and Shigella. {esc(WHO_MIXED)} Drug-resistant infection is not a separate GBD category; drug-resistant tuberculosis, for example, is included under tuberculosis. '
                        f'Publications on other infectious diseases ({oi["n"]:,}, {oi["wellcome"]:,} of them Wellcome-funded) are outside these priority areas.</li>')
        else:
            criteria = (f'<li>Eligible GBD 2023 level-3 causes:<div class="chips">{"".join(f"<span class=gbd>{esc(g)}</span>" for g in MENTAL_GROUPS)}</div></li>'
                        f'<li>Rationale: <a href="{MH_URL}" target="_blank" rel="noopener">Wellcome: Mental Health</a>: {esc(Q_MH)} <a href="{BIPOLAR_URL}" target="_blank" rel="noopener">{esc(Q_CALL)}</a>. GBD has no psychosis cause; schizophrenia and bipolar disorder represent it.</li>'
                        f'<li>Points to note: other mental disorders and substance use disorders are outside this focus, as are publications coded to mental disorders without a specific condition. '
                        f'OCD and PTSD studies coded to anxiety disorders are included; those coded to other mental disorders are outside the codes used. GBD has no separate code for postpartum psychosis, and early intervention is not a GBD category, so publications on these conditions are included whatever the stage or age group.</li>')
        panels.append(f'''<section id="theme-{key}" class="theme" role="tabpanel" aria-labelledby="tab-{key}"{' hidden' if i else ''}>
<p class="desc">{esc(DESCRIPTION[key])}</p>
<div class="sub">Funding landscape</div>
<p class="rankline">Wellcome ranks <b>{esc(t["wellcome_rank"])}</b> by number of publications. {tip(f"Ranked among the {t['funded']:,} publications in this theme with a funder identified. A publication may report several funders, so it can count towards more than one; = marks a tie (tied funders share a rank). Rankings reflect publication counts, not funding amounts. Wellcome is shown below the top 10 when it ranks lower.")}</p>
{set_legend}<div class="donors">{''.join(rows_html) or '<span></span><span>No funder identified.</span>'}</div>
<p class="foot">Bar colours show the setting of each funder's publications (hover a bar for counts).</p>
<div class="sub">Country income group comparison</div>
<p class="hint">Unit: publications. Single-country publications are grouped by the World Bank income group of the country studied in the publication year; multi-country and regional publications, and those whose income group is unavailable, form the third group.</p>
<div class="compare"><span class="lab">All publications in this theme</span>{stack(t["income_counts"], t["n"])}<span class="num">n = {t["n"]:,}</span>
<span class="lab"><strong>Wellcome-funded</strong></span>{stack(t["wellcome_income_counts"], t["wellcome"])}<span class="num">n = {t["wellcome"]:,}</span></div>
<div class="sub">Disease and subarea breakdown</div>
<p class="hint">Publications per eligible GBD condition; the darker part of each bar is Wellcome-funded.{overlap_note} Select a group to list its Wellcome-funded publications.</p>
<div class="groups">{"".join(items)}</div>
<details class="def"><summary>Definition and matching criteria</summary><ul>{criteria}
<li>GBD codes were assigned from titles and abstracts under the team's coding rules and checked against a second coder and MeSH headings. <a href="#method" data-open-method>Technical note</a></li></ul></details>
</section>''')

    sec_b = (f'<section class="block" id="explore" aria-labelledby="explore-h"><h2 id="explore-h">Explore individual themes</h2>'
             f'<nav class="tabs" role="tablist" aria-label="Select a theme">{"".join(tablist)}</nav>{"".join(panels)}</section>')

    groups = a["unmatched_groups"]
    max_u = max([g["n"] for g in groups] or [1])
    gitems = []
    for g in groups:
        lis = ''.join(f'<li>{link(s)} <small>({esc(s["year"])}) · GBD: {esc(s["gbd"])}</small></li>' for s in g["studies"])
        note = f'<p class="hint">{esc(g["note"])}</p>' if g["note"] else ''
        gitems.append(f'<details class="group"><summary><span class="g-label">{esc(g["label"])}</span>'
                      f'<span class="meter" aria-hidden="true"><i style="width:{100 * g["n"] / max_u:.4f}%"></i></span>'
                      f'<span class="num"><strong>{g["n"]}</strong></span></summary>{note}<ol>{lis}</ol></details>')
    cov = {"n": W, "cap": cap, "not": notcap}
    cov_bar = (f'<div class="fbar" role="img" aria-label="Captured by thematic mapping {cap:,} ({pct(cap, W)}); not captured by thematic mapping {notcap:,} ({pct(notcap, W)})">'
               f'<span style="flex:{cap};background:{CAPTURED};color:#fff" title="Captured by thematic mapping: {cap:,} of {W:,} ({pct(cap, W)})">{pct(cap, W, 0)}</span>'
               f'<span style="flex:{notcap};background:{NOT_CAPTURED};color:#2d2840" title="Not captured by thematic mapping: {notcap:,} of {W:,} ({pct(notcap, W)})">{pct(notcap, W, 0)}</span></div>')
    sec_c = f'''<section class="block" id="wellcome" aria-labelledby="wellcome-h"><h2 id="wellcome-h">Wellcome-funded evidence across the HEE map</h2>
<p class="hint">This section covers every publication in the map, whatever its topic.</p>
<div class="wtop"><div class="big"><strong>{W:,}</strong><span>publications with Wellcome identified as a funder, of {H:,} in the map ({years[0]}–{years[1]})</span></div>
<div class="cov"><h3>Coverage of the GBD-based thematic mapping</h3>{cov_bar}
<div class="legend"><span><i style="background:{CAPTURED}"></i>Captured by thematic mapping: <b>{cap:,}</b> ({pct(cap, W)} of {W:,})</span><span><i style="background:{NOT_CAPTURED}"></i>Not captured by thematic mapping: <b>{notcap:,}</b> ({pct(notcap, W)} of {W:,})</span></div></div></div>
<div class="note"><p>{esc(NOTE_1)}</p><p>{esc(NOTE_2)}</p></div>

<div class="trend-head"><div><h3 style="font-size:18px">Wellcome-funded publications by publication year</h3>
<p class="hint" style="margin:0">All {W:,} Wellcome-funded publications. Publication counts, not grant-award dates or spending.</p></div>
<div class="toggle" role="group" aria-label="Trend view"><button type="button" data-trend="annual" aria-pressed="true">Annual</button><button type="button" data-trend="cumulative" aria-pressed="false">Cumulative</button></div></div>
<div id="trend"></div>
<p class="trend-note">The annual view uses a fixed 0–100 scale with gridlines every 30 publications; the cumulative view has its own scale. Hover the chart, or focus it and use the arrow keys, for exact counts. {years[1]} is a partial year (searches ended {esc(v6.SEARCH_END)}), shown with a dashed final segment and hollow point; its lower count does not indicate a decline.</p>
</section>'''

    xw_rows = ''.join(f'<tr><td>{esc(c[0])}</td><td>{esc(c[1])}</td><td>{esc(c[2])}</td><td>{esc(c[3])}</td><td><span class="st {c[5]}">{ {"confirmed": "Direct match", "judgement": "Full category", "flagged": "Closest code", "absent": "Not a GBD category"}[c[5]] }</span> {esc(c[4])}</td></tr>' for c in CROSSWALK)
    mu, oi = a["mental_unspecified_excluded"], a["infectious_other_excluded"]
    ov = a["overlap"]
    method = f'''<details class="method" id="method"><summary>Technical note: how publications were matched to Wellcome's priorities</summary>
<h4>How were publications matched to Wellcome's priorities?</h4>
<p>We matched publications to Wellcome's specified priorities using GBD 2023 disease codes, the classification used across the HEE evidence map. Within Infectious Diseases, the priorities are tuberculosis, cholera, vector-borne diseases and drug-resistant infections; within Mental Health, anxiety, depression and psychosis. The same criteria are applied to every publication, whoever funds it, so results are comparable across funders.</p>
<p>For each priority we used the closest available GBD codes:</p>
<ul>
<li>Most priorities have a direct GBD code: tuberculosis, anxiety, depression, and the vector-borne diseases on WHO's list.</li>
<li>Where GBD has no specific code, we used the nearest category: diarrhoeal diseases for cholera, and schizophrenia and bipolar disorder for psychosis, following Wellcome's own list of psychotic disorders.</li>
<li>Drug-resistant infections and early intervention are not disease categories in GBD, so they are covered through the underlying conditions rather than identified separately.</li>
</ul>
<p>Because GBD classifies diseases rather than research areas, the mapping is an indicative guide to Wellcome's priorities rather than an exact match. We set out its known limitations below and in the table.</p>
<h4>Codes used</h4>
<p>The GBD codes used for each priority. The table is checked automatically against the codes behind every count on this page.</p>
<div class="xw-wrap"><table class="xw"><thead><tr><th>Theme</th><th>Wellcome priority</th><th>GBD 2023 code(s)</th><th>Source</th><th>How it is matched</th></tr></thead><tbody>{xw_rows}</tbody></table></div>
<h4>Scope of the mapping</h4>
<ul>
<li>Publications on other conditions are outside these priorities. Examples are other infectious diseases, such as HIV/AIDS, lower respiratory infections and COVID-19 ({oi["n"]:,} publications, {oi["wellcome"]:,} Wellcome-funded), and other mental health conditions, including substance use.</li>
<li>Some GBD codes combine eligible and other conditions: encephalitis, other neglected tropical diseases, broad infection groups, and mental disorders with no specific condition ({mu["n"]:,} publications). These are not included, to keep the mapping specific.</li>
<li>Climate &amp; Health, which was identified by keywords rather than GBD codes, is not included, and neither are publications identified through additional screening. This keeps every funder's publications identified in the same way.</li>
</ul>
<p>A publication outside the mapping may still contribute to Wellcome's priorities, for example through cross-cutting research.</p>
<h4>Counting and funding</h4>
<ul>
<li>Each publication is counted once, even when it is in both themes ({ov:,} {"publication is" if ov == 1 else "publications are"}).</li>
<li>Funders are taken from Crossref publication metadata. A funder is identified for {pct(a["F"], H)} of all {H:,} publications; “funder not identified” does not mean unfunded.</li>
<li>Wellcome-funded means Wellcome Trust is among the identified funders, alone or with others (Burroughs Wellcome Fund is separate).</li>
<li>Publications can report several funders, so funder counts do not add up to theme totals. Tied funders share a rank.</li>
<li>Single-country publications are grouped by the World Bank income group in their publication year; multi-country, regional and unclassified publications form a third group.</li>
<li>Publications from {years[0]} to {esc(v6.SEARCH_END)}; {years[1]} is partial.</li>
<li>Counts describe economic evidence (including reviews) and the funders it acknowledges. They do not measure funding amounts, grant portfolios or strategic performance.</li>
</ul>
<h4>Sources</h4>
<ul>
<li>Wellcome, <a href="{INF_URL}">Infectious Disease</a> (saved 27 Nov 2026): {esc(Q_ID.split(" (Wellcome")[0])}.</li>
<li>Wellcome, <a href="{MH_URL}">Mental Health</a> (saved 27 Nov 2026): {esc(Q_MH.split(" (Wellcome")[0])}</li>
<li>Wellcome, <a href="{BIPOLAR_URL}">Mental Health Award call</a>: {esc(Q_CALL)}.</li>
<li>WHO, <a href="{WHO_URL}">Vector-borne diseases</a> fact sheet (26 Sep 2024): the list of vector-borne diseases.</li>
<li>Data: HEE analysis master v2.1 ({H:,} publications; SHA-256 {a["meta"]["master_sha256"][:12]}…), {esc(a["meta"]["gbd_share"])}. Built {esc(a["meta"]["analysis_built"])} by scripts/build_wellcome_analysis_gbd_v15.py.</li>
</ul>
</details>'''

    data = json.dumps({"years": a["wellcome_by_year"], "searchEnd": v6.SEARCH_END}).replace("</", "<\\/")
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{esc(TITLE)}</title><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
            '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Newsreader:opsz,wght@6..72,600&display=swap" rel="stylesheet">'
            f'<style>{STYLE}</style></head><body><main>'
            f'<header class="page-head"><span class="eyebrow">HEE evidence map</span><h1>{esc(TITLE)}</h1><p class="lede">{esc(INTRO)}</p></header>'
            f'{sec_a}{sec_b}{sec_c}{method}'
            '<div class="download"><a href="wellcome_funded_publications.csv" download>Wellcome-funded publications (CSV)</a>'
            '<a href="wellcome_theme_funders.csv" download>Funder counts by theme (CSV)</a>'
            '<a href="wellcome_analysis.json" download>All figures (JSON)</a><a href="#" data-png>Page as image (PNG)</a>'
            '<span class="png-status" role="status"></span></div>'
            f'</main><script type="application/json" id="data">{data}</script><script>{SCRIPT}</script></body></html>')


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--raw", type=Path, default=ROOT / "data" / "raw")
    args = parser.parse_args()
    try:
        rows, meta, *_rest, source_hash = v6.load_inputs(args.raw)
        if crosswalk_codes() != set(INFECTIOUS_CODES) | set(MENTAL_GROUPS):
            raise ValueError("Crosswalk table and theme code lists disagree: "
                             f"{sorted(crosswalk_codes() ^ (set(INFECTIOUS_CODES) | set(MENTAL_GROUPS)))}")
        a = analyse(rows, meta, source_hash)
        page = report(a)
        for banned in ("Climate", "◆", "added on review", "Added on review", "outside Wellcome", "non-priority"):
            # Climate & Health may appear only in the methodology's exclusion notes; nothing else from v6 may survive.
            visible = page.split('<details class="method"')[0]
            if banned in visible:
                raise ValueError(f"Obsolete or excluded label {banned!r} found outside the methodology.")
        BUILD_OUT.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=BUILD_OUT) as tmp:
            staging = Path(tmp)
            (staging / "wellcome_analysis.html").write_text(page, encoding="utf-8")
            (staging / "wellcome_analysis.json").write_text(json.dumps({k: v for k, v in a.items() if k != "unmatched_groups"}, indent=2, ensure_ascii=False), encoding="utf-8")
            with (staging / "wellcome_funded_publications.csv").open("w", encoding="utf-8-sig", newline="") as handle:
                cols = ["year", "title", "link", "captured_by_mapping", "themes", "gbd_causes", "other_funders_identified"]
                w = csv.DictWriter(handle, fieldnames=cols)
                w.writeheader()
                w.writerows(a["wellcome_publications"])
            with (staging / "wellcome_theme_funders.csv").open("w", encoding="utf-8", newline="") as handle:
                w = csv.writer(handle)
                w.writerow(["theme", "theme_publications", "theme_publications_funder_identified", "funder", "publications",
                            "single_country_hic", "single_country_lmic", "other_scope_or_unknown_income"])
                for t in a["themes"].values():
                    for d in t["donors"]:
                        w.writerow([t["label"], t["n"], t["funded"], d["funder"], d["n"], *d["income_counts"]])
            for p in staging.iterdir():
                os.replace(p, BUILD_OUT / p.name)
    except (OSError, ValueError, KeyError, TypeError, ImportError, AssertionError) as exc:
        raise SystemExit(f"Build stopped: {exc}") from exc
    u = a["union"]
    print(f"H={a['H']:,} F={a['F']:,} W={a['W']:,}")
    for name, m in [("Union", u)] + [(t["label"], t) for t in a["themes"].values()]:
        print(f"{name}: n={m['n']:,} funded={m['funded']:,} wellcome={m['wellcome']:,} other_only={m['other']:,} none={m['none']:,}")
    print(f"Wellcome captured {a['wellcome_captured']} / not captured {a['wellcome_not_captured']}; overlap I&M {a['overlap']}")
    print("Checks:", ", ".join(f"{k}={v}" for k, v in a["checks"].items()))
    print(BUILD_OUT / "wellcome_analysis.html")


if __name__ == "__main__":
    main()
