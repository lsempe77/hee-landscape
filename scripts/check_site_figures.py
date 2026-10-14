"""Check that every figure the site shows exists and opens.

Collects the figure files the site refers to: the gallery in
docs/data/content.json (with the redrawn replacements from
docs/data/figure_updates.json swapped in, as docs/app.js does), plus every
figure file named in docs/app.js, docs/index.html and docs/data/figure_copy.json.
Each must exist in docs/figures; images must open, and HTML figures must be
non-empty. Also lists files in docs/figures that nothing refers to.

Exit status 1 if anything is missing or broken, so it can gate a sync.

Usage:
    python scripts/check_site_figures.py
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
FIGS = os.path.join(DOCS, "figures")
# Quoted file names only, so code such as `f.html` is not taken for a file.
NAME = re.compile(r"""["']([\w\-]+\.(?:webp|svg|png|jpg|html))["']""")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def main():
    content = json.loads(read(os.path.join(DOCS, "data", "content.json")))
    updates_path = os.path.join(DOCS, "data", "figure_updates.json")
    updates = json.loads(read(updates_path)) if os.path.exists(updates_path) else {}

    def files(node):
        """Every "file" value in the gallery, including figures' alternative views."""
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "file" and isinstance(v, str):
                    yield v
                else:
                    yield from files(v)
        elif isinstance(node, list):
            for v in node:
                yield from files(v)

    referenced = set(files(content["gallery"]))
    for path in ("app.js", "index.html", os.path.join("data", "figure_copy.json")):
        referenced |= set(NAME.findall(read(os.path.join(DOCS, path))))
    # Some gallery paths concatenate a fixed subdirectory with an image name.
    # Resolve those expressions instead of checking the basename at figures/.
    app = read(os.path.join(DOCS, "app.js"))
    for variable, directory in re.findall(r'''const\s+(\w+)\s*=\s*["']([^"']+/)["'];''', app):
        pattern = re.compile(r'\b' + re.escape(variable) + r'\s*\+\s*' + NAME.pattern)
        for name in pattern.findall(app):
            referenced.discard(name)
            referenced.add(directory + name)
    referenced -= {"index.html"}
    # The site shows the redrawn file in place of the original; both are kept.
    shown = {updates.get(f, {}).get("file", f) for f in referenced} | set(referenced)

    problems = []
    for name in sorted(shown):
        path = os.path.join(FIGS, name)
        if not os.path.exists(path):
            # Names in app.js that are not figures (e.g. pages) are only reported
            # when they look like figure files the gallery would load.
            problems.append(f"missing: figures/{name}")
            continue
        if name.endswith((".webp", ".png", ".jpg")):
            try:
                from PIL import Image
                with Image.open(path) as im:
                    im.verify()
            except Exception as e:  # noqa: BLE001 - report any unreadable image
                problems.append(f"unreadable: figures/{name} ({e})")
        elif os.path.getsize(path) == 0:
            problems.append(f"empty: figures/{name}")

    for old, new in updates.items():
        if old not in referenced:
            problems.append(f"figure_updates.json replaces {old}, which the site does not show")

    unused = sorted(set(os.listdir(FIGS)) - shown)
    print(f"{len(shown)} figure files referenced; {len(problems)} problem(s).")
    for p in problems:
        print("  " + p)
    print(f"{len(unused)} file(s) in docs/figures not referenced (kept, e.g. archived originals):")
    for u in unused:
        print("  " + u)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
