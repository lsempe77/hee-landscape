"""Export the Wellcome priority-themes page, with the "added on review" toggle, as one self-contained HTML file.

Version 2 of export_wellcome_standalone.py (kept): reads the v6 build in exports/wellcome_themes_v6_build
(run build_wellcome_analysis_gbd_v6.py first) instead of docs/figures, and embeds both CSVs (GBD definition, and
including studies added on review), each linked from its own view. Writes
exports/wellcome_themes_standalone_<date>/wellcome_priority_themes.html and refuses to overwrite an existing file.
Nothing is written to docs/, so the map is unchanged.
"""
import base64
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "exports" / "wellcome_themes_v6_build"
VENDOR = ROOT / "docs" / "vendor" / "html2canvas-1.4.1.min.js"
FILES = (("wellcome_theme_funders.csv", "text/csv"), ("wellcome_theme_funders_incl_review.csv", "text/csv"),
         ("wellcome_analysis.json", "application/json"))


def data_link(path, mime):
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def main():
    page = (BUILD / "wellcome_analysis.html").read_text(encoding="utf-8")
    for name, mime in FILES:
        old = f'href="{name}" download'
        if old not in page:
            continue  # the single-view page links only one CSV
        # Each link appears in the live <main> and in the view templates; embed the data once and point every link at it.
        page = page.replace(old, f'href="{data_link(BUILD / name, mime)}" download="{name}"')
    renderer = VENDOR.read_text(encoding="utf-8").replace("</script", "<\\/script")
    assert page.count("</head>") == 1
    page = page.replace("</head>", f"<script>{renderer}</script></head>")
    # Never overwrite an earlier export: a second export on the same day goes to a _v2, _v3, ... folder.
    base, n = f"wellcome_themes_standalone_{date.today().isoformat()}", 1
    out = ROOT / "exports" / base
    while (out / "wellcome_priority_themes.html").exists():
        n += 1
        out = ROOT / "exports" / f"{base}_v{n}"
    out.mkdir(parents=True, exist_ok=True)
    path = out / "wellcome_priority_themes.html"
    path.write_text(page, encoding="utf-8")
    print(f"{path} ({path.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
