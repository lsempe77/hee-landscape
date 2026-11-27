"""Export the v3 Wellcome priority-themes page (built by build_wellcome_analysis_gbd_v7.py) as one self-contained HTML file.

Version 3 of export_wellcome_standalone.py (v2 kept): reads exports/wellcome_themes_v7_build, embeds the CSV, JSON and the
site's bundled html2canvas (for PNG download), and writes
exports/wellcome_themes_standalone_2026-11-25_v3/wellcome_priority_themes-v3.html next to v2. Refuses to overwrite an
existing file (pass --out to choose another path). Nothing is written to docs/. Fonts still load from Google Fonts, as in v2;
without a connection the page falls back to system fonts.
"""
import argparse
import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "exports" / "wellcome_themes_v7_build"
VENDOR = ROOT / "docs" / "vendor" / "html2canvas-1.4.1.min.js"
DEFAULT_OUT = ROOT / "exports" / "wellcome_themes_standalone_2026-11-25_v3" / "wellcome_priority_themes-v3.html"
FILES = (("wellcome_funded_publications.csv", "text/csv"), ("wellcome_theme_funders.csv", "text/csv"), ("wellcome_analysis.json", "application/json"))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--build", type=Path, default=BUILD, help="build folder (v8: exports/wellcome_themes_v8_build)")
    args = parser.parse_args()
    out, build = args.out, args.build
    if out.exists():
        raise SystemExit(f"{out} exists; not overwriting. Pass --out with a new name.")
    page = (build / "wellcome_analysis.html").read_text(encoding="utf-8")
    for name, mime in FILES:
        old = f'href="{name}" download'
        if old not in page:
            continue  # builds before v11 do not link wellcome_funded_publications.csv
        assert page.count(old) == 1, name
        page = page.replace(old, f'href="data:{mime};base64,{base64.b64encode((build / name).read_bytes()).decode("ascii")}" download="{name}"')
    renderer = VENDOR.read_text(encoding="utf-8").replace("</script", "<\\/script")
    assert page.count("</head>") == 1
    page = page.replace("</head>", f"<script>{renderer}</script></head>")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(f"{out} ({out.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
