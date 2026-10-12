"""Update the dotmap title while preserving the published map image.

Run from any directory: python scripts/build_dotmap_title.py
The original R renderer lives in hsf/projects/hee/analysis/R/fig-companion-dotmap.R.
This SVG embeds the existing WebP unchanged and replaces only its title strip.
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
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1800" height="1080" viewBox="0 0 1800 1080">
  <title>{html.escape(TITLE)}</title>
  <image width="1800" height="1080" href="data:image/webp;base64,{encoded}"/>
  <rect x="14" y="96" width="1772" height="52" fill="#f8f4ee"/>
  <text x="20" y="140" font-family="Franklin Gothic Heavy, Arial, sans-serif" font-weight="900" font-size="46" fill="#1a1a1a">{html.escape(TITLE)}</text>
</svg>
'''
    figure["file"] = "fig_dotmap.svg"
    figure["title"] = TITLE
    content_text = json.dumps(content, ensure_ascii=False, separators=(",", ":"))
    atomic_write(FIGURES / "fig_dotmap.svg", svg)
    atomic_write(CONTENT, content_text)
    print(f"Success: figure title updated to '{TITLE}'")
    print(f"Figure: {FIGURES / 'fig_dotmap.svg'}")
    print(f"Gallery: {CONTENT}")


if __name__ == "__main__":
    main()
