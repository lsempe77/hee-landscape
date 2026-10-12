"""Improve the dotmap layout while preserving the published map image.

Run from any directory: python scripts/build_dotmap_title.py
The original R renderer lives in hsf/projects/hee/analysis/R/fig-companion-dotmap.R.
This SVG reuses the map and legend from the existing WebP in separate viewports,
with a larger map, consistent margins and newly typeset explanatory text.
No analysis datasets are required: the inputs are the published WebP and
content.json. Both are validated before any output is written. Requires Pillow.
"""
import base64
import html
import json
import io
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TITLE = "Look north for economic evaluation evidence (mostly)"
FIGURES = ROOT / "docs" / "figures"
CONTENT = ROOT / "docs" / "data" / "content.json"


def load_inputs():
    """Fail closed on missing, empty, corrupt or incompatible inputs."""
    source = FIGURES / "fig_dotmap.webp"
    required = (source, CONTENT)
    problems = [str(path) for path in required if not path.is_file() or path.stat().st_size == 0]
    if problems:
        raise ValueError("Required input files are missing or empty: " + ", ".join(problems))
    try:
        from PIL import Image
    except ImportError as exc:
        raise ValueError("Pillow is required to validate the map. Install with: python -m pip install Pillow") from exc
    image_bytes = source.read_bytes()
    with Image.open(io.BytesIO(image_bytes)) as image:
        if image.format != "WEBP" or image.size != (1800, 1080):
            raise ValueError("The map must be a 1800 x 1080 WebP; this title overlay depends on that layout.")
        image.load()
    content = json.loads(CONTENT.read_text(encoding="utf-8"))
    matches = [figure for group in content["gallery"] for figure in group["figs"]
               if figure["file"] in ("fig_dotmap.webp", "fig_dotmap.svg")]
    if len(matches) != 1:
        raise ValueError("content.json must contain exactly one dotmap gallery entry.")
    return image_bytes, content, matches[0]


def atomic_write(path, text):
    """Replace an output only after its complete contents have been written."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         delete=False, suffix=".tmp") as handle:
            temporary = Path(handle.name)
            handle.write(text)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    try:
        image_bytes, content, figure = load_inputs()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise SystemExit(f"Stopped before writing any output: {exc}") from exc
    encoded = base64.b64encode(image_bytes).decode("ascii")
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1800" height="960" viewBox="0 0 1800 960">
  <title>{html.escape(TITLE)}</title>
  <desc>Economic evaluation research is concentrated in higher-income countries. Each bubble represents a country; its size shows the number of studies and its colour shows country income.</desc>
  <defs><image id="published-map" width="1800" height="1080" href="data:image/webp;base64,{encoded}"/></defs>
  <rect width="1800" height="960" fill="#f9f3ee"/>
  <g font-family="Arial, sans-serif" fill="#1a1a1a">
    <text x="40" y="70" font-weight="800" font-size="46">{html.escape(TITLE)}</text>
    <text x="40" y="120" font-size="25" fill="#55534e">Most research is concentrated in North America, Europe and higher-income parts of Asia and the Pacific.</text>
    <text x="40" y="157" font-size="25" fill="#55534e">Larger bubbles mean more studies mention a country. Colours show the country's income group.</text>
  </g>
  <svg x="30" y="195" width="1480" height="662" viewBox="90 280 1430 640" overflow="hidden">
    <use href="#published-map"/>
  </svg>
  <svg x="1545" y="240" width="235" height="566" viewBox="1570 340 220 530" overflow="hidden">
    <use href="#published-map"/>
  </svg>
  <g font-family="Arial, sans-serif" font-size="20" fill="#66635e">
    <text x="40" y="902">54 of the 241 countries and territories shown have no recorded studies; 50 of these have fewer than 1 million people.</text>
    <text x="40" y="932">Among 155 sovereign countries with at least 1 million people, only Mauritius and Eritrea have no recorded studies.</text>
  </g>
</svg>
'''
    figure["file"] = "fig_dotmap.svg"
    figure["title"] = TITLE
    content_text = json.dumps(content, ensure_ascii=False, separators=(",", ":"))
    atomic_write(FIGURES / "fig_dotmap.svg", svg)
    atomic_write(CONTENT, content_text)
    print(f"Success: larger map and improved title/explanation spacing for '{TITLE}'")
    print(f"Figure: {FIGURES / 'fig_dotmap.svg'}")
    print(f"Gallery: {CONTENT}")


if __name__ == "__main__":
    main()
