"""Shared soft palette and restrained shading for generated figures."""

INCOME_COLORS = ["#D98F7A", "#D6B264", "#62A89B", "#6D91BE"]
FUNDER_COLORS = [INCOME_COLORS[3], INCOME_COLORS[0], "#B7BBC5"]
LAVENDER = "#9B87B8"
BACKGROUND = "#FAF9F7"


def shade_bars(ax, bars, color):
    """Add a subtle vertical highlight; bar length continues to encode counts."""
    import numpy as np
    from matplotlib.colors import to_rgb

    base = np.array(to_rgb(color))
    highlight = base * .8 + .2
    shading = np.linspace(highlight, base, 64)[:, None, :]
    xlim, ylim = ax.get_xlim(), ax.get_ylim()
    for bar in bars:
        if bar.get_width() <= 0:
            continue
        x, y = bar.get_x(), bar.get_y()
        ax.imshow(shading, extent=(x, x + bar.get_width(), y, y + bar.get_height()),
                  origin="upper", aspect="auto", interpolation="bilinear",
                  clip_path=bar, clip_on=True, zorder=bar.get_zorder() + .1)
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)


def tidy_svg(path):
    path.write_text("\n".join(line.rstrip() for line in path.read_text(encoding="utf-8").splitlines()) + "\n",
                    encoding="utf-8")
