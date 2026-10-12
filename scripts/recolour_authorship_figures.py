"""Recolour the pre-rendered Authorship & access figures to the site's soft palette.

Run: python scripts/recolour_authorship_figures.py [figure.webp ...]
Run it on the original upstream images; a second pass on recoloured output is not intended.
Requires Pillow, numpy and scipy. These figures were rendered upstream; their
source code and affiliation data are not in this repo, so this swaps colours
pixel by pixel instead of re-plotting. Each pixel is matched to the line between
two known colours (background, white, or a source colour), which keeps
anti-aliased edges and overlaps consistent. Solid bars also get the subtle
top-lit gradient used by figure_style.shade_bars. Originals stay in git history.
fig_map_openaccess.webp is left as is: it already uses a soft diverging palette,
and its pale blue-grey end is too close to the grey no-data countries to swap safely.
"""
from pathlib import Path
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

try:
    from figure_style import INCOME_COLORS, LAVENDER
except ModuleNotFoundError:
    from scripts.figure_style import INCOME_COLORS, LAVENDER

FIGURES = Path(__file__).resolve().parents[1] / "docs" / "figures"
LIC, LMIC, UMIC, HIC = INCOME_COLORS
BACKGROUND, WHITE = "#f8f4ee", "#ffffff"
# Saturated upstream colours and their soft-palette replacements, per figure.
BLUE, TEAL, AMBER, ORANGE = "#2a78d0", "#1aa878", "#e9a000", "#e6642f"
INCOME = {BLUE: HIC, TEAL: UMIC, AMBER: LMIC, ORANGE: LIC, "#eb6835": LIC}
JOBS = {
    "fig_authorship_pattern.webp": ({BLUE: HIC, ORANGE: LIC, TEAL: UMIC, "#4a36a8": HIC,
                                     "#008000": LAVENDER, "#e34848": LIC}, True),
    "fig_forest.webp": ({BLUE: HIC}, False),
    "paper06.webp": (INCOME, False),
    "fig_collab_chord.webp": (INCOME, False),
    "fig_openaccess.webp": ({BLUE: HIC, ORANGE: LIC}, False),
    # Bars here carry a dark edge line and a light-cyan compression halo; both fold into fill and background.
    "fig_map_authorship.webp": ({"#1a56aa": HIC, "#2d598a": HIC, "#d2f0ff": BACKGROUND, "#ecf9ff": BACKGROUND}, True),
}
TOLERANCE = 22.0


def rgb(value):
    return np.array([int(value[i:i + 2], 16) for i in (1, 3, 5)], dtype=float)


def recolour(pixels, mapping, fixed):
    """Return recoloured pixels and a mask of solid (fully coloured) matches."""
    ends = [(rgb(c), rgb(c)) for c in [BACKGROUND, WHITE] + fixed] + [(rgb(s), rgb(t)) for s, t in mapping.items()]
    n_fixed = 2 + len(fixed)
    best = np.full(len(pixels), TOLERANCE)
    out = pixels.copy()
    solid = np.zeros(len(pixels), bool)
    for i in range(len(ends)):
        for j in range(max(i + 1, n_fixed), len(ends)):
            (a_src, a_dst), (b_src, b_dst) = ends[i], ends[j]
            span = b_src - a_src
            t = np.clip((pixels - a_src) @ span / (span @ span), 0, 1.05)
            residual = np.linalg.norm(pixels - (a_src + t[:, None] * span), axis=1)
            hit = (residual < best) & (t > .06)
            best[hit] = residual[hit]
            out[hit] = a_dst + t[hit, None] * (b_dst - a_dst)
            solid[hit] = (t[hit] > .85) | (i >= n_fixed)
    # Leave the background, white and near-neutral pixels exactly as they were.
    keep = np.min([np.linalg.norm(pixels - rgb(c), axis=1) for c in [BACKGROUND, WHITE] + fixed], axis=0) < 12
    out[keep] = pixels[keep]
    solid[keep] = False
    return np.clip(out, 0, 255), solid


def add_gradient(image, solid, changed):
    """Lighten the top of each solid block, matching shade_bars (20% toward white)."""
    labels, count = ndimage.label(solid)
    for index, box in enumerate(ndimage.find_objects(labels), 1):
        rows, cols = box
        height = rows.stop - rows.start
        if height < 25 or cols.stop - cols.start < 12:
            continue
        # Include the recoloured anti-aliased rim so bar edges lighten with the fill.
        region = ndimage.binary_dilation(labels[box] == index, iterations=2) & changed[box]
        lift = .2 * (1 - (np.arange(height) / max(1, height - 1)))[:, None, None]
        block = image[box]
        image[box] = np.where(region[..., None], block * (1 - lift) + 255 * lift, block)


def main():
    names = sys.argv[1:] or list(JOBS)
    for name in names:
        job = JOBS[name]
        mapping, gradient, fixed = (job + ([],))[:3]
        path = FIGURES / name
        source = np.asarray(Image.open(path).convert("RGB"), dtype=float)
        shape = source.shape
        pixels, solid = recolour(source.reshape(-1, 3), mapping, fixed)
        image = pixels.reshape(shape)
        if gradient:
            changed = np.abs(image - source).sum(axis=2) > 0
            add_gradient(image, solid.reshape(shape[:2]), changed)
        Image.fromarray(image.round().astype(np.uint8)).save(path, "WEBP", quality=92, method=6)
        print(f"Recoloured {name}")


if __name__ == "__main__":
    main()
