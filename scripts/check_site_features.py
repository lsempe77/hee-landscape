"""Check that the site's recent design features are still in place.

Anything pushed to `main` goes live, and docs/app.js is edited by several
people and AI agents. An edit made on an old copy of the file, or a merge
that keeps the wrong side, can quietly undo a feature someone added on
purpose. This script lists those features and, for each one, a few pieces of
code it depends on. If any piece is missing, the feature has probably been
overwritten, and the script says which one and when it was added.

It also checks that the BUILD token in docs/app.js matches the ?v= token
docs/index.html loads app.js with (a mismatch serves visitors a stale file).

Exit status 1 if anything is missing, so it can gate a push.
The git pre-push hook in .githooks/ runs it; see README "Before you push".

ADDING A FEATURE: when you ship a design change colleagues should not lose,
add an entry to FEATURES below (newest first) and run the script once.
REMOVING A FEATURE ON PURPOSE: delete or edit its entry in the same commit,
and say so in the commit message and README "Latest updates".

Usage:
    python scripts/check_site_features.py
    python scripts/check_site_features.py --docs path/to/other/docs   # check a copy
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
if "--docs" in sys.argv:
    DOCS = sys.argv[sys.argv.index("--docs") + 1]

# Each feature: what it does (in plain words), when and where it was added,
# and the code it needs. "needs" maps a file under docs/ to text that must
# appear in it verbatim.
FEATURES = [
    {
        "name": "Studies Overview card jumps to the cumulative publication trend",
        "added": "2 Nov 2026 (commit c0267d3)",
        "needs": {
            "app.js": [
                "[STUDIES_CARD]: () => {",
                '[data-trend-mode="cumulative"]',
                ": go to cumulative publication trend",
            ],
            "index.html": ["overview-trend-card", "data-trend-mode"],
        },
    },
    {
        "name": "Other Overview cards link to their Thematic analysis page (TILE_THEME)",
        "added": "23 Oct 2026 (commit 9a787f4)",
        "needs": {
            "app.js": [
                "const TILE_THEME = {",
                '[ACCESS_CARD]: "Authorship & access"',
                '[GEO_CARD]: "Geography"',
                '[METRICS_CARD]: "Methods & metrics"',
                '[MEASURE_CARD]: "Methods & metrics"',
                '[FUNDERS_CARD]: "Research funding"',
                "openOverviewTheme(theme)",
                "overview-nav-card",
                ": open related analysis",
            ],
        },
    },
    {
        "name": "Thematic analysis pages open with their Overview card(s)",
        "added": "23 Oct 2026 (commit 9a787f4)",
        "needs": {
            "app.js": ["function renderSectionTiles(title)", "renderSectionTiles(group ? null : sec.title)"],
            "index.html": ['id="gal-sec-tiles"'],
        },
    },
    {
        "name": "Explorer HALY type filter has 'All' and opens on it",
        "added": "23 Oct 2026 (commit f9b82d5)",
        "needs": {
            "app.js": [
                '["All", "No HALY", "Any HALY", "QALY only", "DALY only", "Both QALY and DALY"]',
                'qaly: "All"',
            ],
        },
    },
    {
        "name": "DOI / publication links in Countries study lists",
        "added": "23 Oct 2026 (commit 9a787f4)",
        "needs": {
            "app.js": [
                "export function studyReference(",
                '"https://doi.org/" + doi',
                'label: "Publication link"',
            ],
        },
    },
    {
        "name": "Progress bar for 'Download filtered studies (CSV)'",
        "added": "23 Oct 2026 (commit 9a787f4)",
        "needs": {
            "app.js": ['$("x-download-progress")', "Building the CSV file"],
            "index.html": ['id="x-download-progress"'],
        },
    },
    {
        "name": "Explorer download has every title plus abstracts (docs/data/text/)",
        "added": "22 Oct 2026 (commit c929906)",
        "needs": {
            "app.js": ['fetch("data/text/index.json', "abstract: payload.a[i]"],
        },
    },
]


def read(name):
    path = os.path.join(DOCS, name)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return f.read()


def main():
    texts = {}
    problems = []

    for feature in FEATURES:
        missing = []
        for name, snippets in feature["needs"].items():
            if name not in texts:
                texts[name] = read(name)
            text = texts[name]
            if text is None:
                missing.append(f"docs/{name} is missing")
                continue
            missing += [f"docs/{name}: {s}" for s in snippets if s not in text]
        if missing:
            problems.append((feature, missing))

    app = texts.get("app.js") or read("app.js") or ""
    html = texts.get("index.html") or read("index.html") or ""
    build = re.search(r'const BUILD = "([^"]+)"', app)
    loaded = re.search(r'src="app\.js\?v=([^"]+)"', html)
    build_ok = build and loaded and build.group(1) == loaded.group(1)

    if not problems and build_ok:
        print(f"OK: all {len(FEATURES)} protected design features are in place; "
              f"BUILD token {build.group(1)} matches index.html.")
        return 0

    print("PROTECTED SITE FEATURES CHECK FAILED\n")
    for feature, missing in problems:
        print(f"x {feature['name']}")
        print(f"  added {feature['added']}; missing:")
        for m in missing:
            print(f"    - {m}")
        print()
    if not build_ok:
        print("x BUILD token mismatch: app.js has "
              f"{build.group(1) if build else '(none)'}, index.html loads app.js?v="
              f"{loaded.group(1) if loaded else '(none)'}. Bump both to the same value.\n")
    print("This usually means docs/app.js or docs/index.html was edited from an old copy,\n"
          "or a merge kept the older side. Run `git pull`, compare with `git log -p docs/app.js`,\n"
          "and restore the feature. If you are removing it on purpose, edit FEATURES in\n"
          "scripts/check_site_features.py in the same commit and say so in the commit message.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
