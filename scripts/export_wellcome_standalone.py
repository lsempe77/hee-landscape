"""Export the Wellcome priority-themes page as one self-contained HTML file for internal sharing.

Run: python scripts/export_wellcome_standalone.py
Reads the built page in docs/figures (run build_wellcome_analysis_gbd_v5.py first) and writes
exports/wellcome_themes_standalone_<date>/wellcome_priority_themes.html. The CSV and JSON downloads
are embedded as data links and the bundled html2canvas is inlined, so the file works when opened
from a disk, an email attachment or a shared drive. Only the web fonts need a connection; without
one the page falls back to system fonts. Nothing is written to docs/, so the map is unchanged.
"""
import base64
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "docs" / "figures"
VENDOR = ROOT / "docs" / "vendor" / "html2canvas-1.4.1.min.js"


def data_link(path, mime):
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def main():
    page = (FIG / "wellcome_analysis.html").read_text(encoding="utf-8")
    for name, mime in (("wellcome_theme_funders.csv", "text/csv"), ("wellcome_analysis.json", "application/json")):
        old = f'href="{name}" download'
        assert page.count(old) == 1, name
        page = page.replace(old, f'href="{data_link(FIG / name, mime)}" download="{name}"')
    # Inline the image renderer; the page only fetches it from ../vendor when window.html2canvas is missing.
    renderer = VENDOR.read_text(encoding="utf-8").replace("</script", "<\\/script")
    assert page.count("</head>") == 1
    page = page.replace("</head>", f"<script>{renderer}</script></head>")
    out = ROOT / "exports" / f"wellcome_themes_standalone_{date.today().isoformat()}"
    out.mkdir(parents=True, exist_ok=True)
    path = out / "wellcome_priority_themes.html"
    path.write_text(page, encoding="utf-8")
    print(f"{path} ({path.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
