"""Research-disease divergence in health economic evaluations, version 2.

Revision of build_kld_replication.py (kept), shaped to answer one question:
does research shift with disease burden once high-income studies are removed?

  - Main comparison, two panels: all studies vs global DALYs ("with high-income
    studies") and studies of low- and middle-income countries vs LMIC DALYs
    ("without"). Studies of high-income countries vs HIC DALYs are supplementary.
  - Pooled 3-year rolling windows (labelled by their middle year), so small
    yearly counts do not drown the trend. Main period: windows within 2010-2019,
    as the paper stops at 2019; windows reaching 2020-2023 are shown dashed as a
    COVID-affected extension.
  - A decomposition with 95% intervals: the change in divergence from 2010-12
    to 2017-19 split into a research part and a burden part. Each part is the
    average of the two orderings (fix research first, or burden first), so the
    two parts add up exactly to the observed change.
  - The paper's Fig. 4: each cause's contribution to that change, split into its
    research and burden parts, to show which diseases moved.

KLD, cause sets, geography and data are as in version 1 (see its docstring):
KLD(p || q) = sum p ln(p/q), p = DALY shares, q = research shares (study-cause
links); 16 causes as in the paper (main) and 20 with mental disorders and
injuries (supplementary).

Revised after a cross-check (14 October 2026):
  - no smoothing in the point estimates, as in the paper's main analysis (no cause
    has zero studies in any 3-year window); in a resampling draw where a cause
    gets no study, that cause alone gets 0.5, and such draws are counted;
  - the paper's rare-cause sensitivity: KLD without causes whose research or DALY
    share is below 1% (supplementary figure);
  - the Fig. 3 box reports the same changes as the plotted lines (fixed-research
    and fixed-DALY scenarios), so the box and the lines agree;
  - panels share one y-axis.

Writes exports/kld_replication_v2_<date>/.

Usage:
    python scripts/build_kld_replication_v2.py [--raw data/raw] [--draws 1000]
"""
import argparse
import csv
import datetime
import os
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import build_kld_replication as v1

ROOT = v1.ROOT
WINDOWS = [(y, y + 2) for y in range(2010, 2022)]  # 2010-12 ... 2021-23
MAIN_END = 2019
BASE_W, END_W = (2010, 2012), (2017, 2019)
GROUPS = {"all": ("With high-income studies", "All studies vs global DALYs", "#1d1d1d"),
          "lmic": ("Without high-income studies", "Studies of low- and middle-income countries vs LMIC DALYs", "#D98F7A"),
          "hic": ("High-income studies only", "Studies of high-income countries vs HIC DALYs", "#6D91BE")}
BG = v1.BG
C_OBS, C_RES_FIXED, C_DAL_FIXED = "#3f6fb5", "#3f8f80", "#c2412d"
C_RESEARCH, C_BURDEN = "#c2412d", "#3f8f80"
SHORT = {"HIV/AIDS and sexually transmitted infections": "HIV/AIDS & STIs",
         "Respiratory infections and tuberculosis": "Respiratory infections & TB",
         "Neglected tropical diseases and malaria": "NTDs & malaria",
         "Maternal and neonatal disorders": "Maternal & neonatal",
         "Self-harm and interpersonal violence": "Self-harm & violence",
         "Skin and subcutaneous diseases": "Skin diseases", "Diabetes and kidney diseases": "Diabetes & kidney"}


def label(w):
    return f"{w[0]}–{str(w[1])[2:]}"


def mid(w):
    return (w[0] + w[1]) / 2


def matrix(studies, key, causes):
    """Per year: a studies x causes 0/1 matrix for one group."""
    idx = {c: i for i, c in enumerate(causes)}
    out = {}
    for y in range(2010, 2024):
        rows = [[1 if c in s["causes"] else 0 for c in causes] for s in studies
                if s["year"] == y and key in s["groups"] and s["causes"] & set(idx)]
        out[y] = np.array(rows, dtype=np.int32).reshape(-1, len(causes))
    return out


ZERO_DRAWS = {"n": 0, "total": 0}
ZERO_POINT = set()
CAUSES_NOW = []


def q_of(mats, w, rng=None):
    """Research shares for a window; with rng, studies are resampled within each year.
    No smoothing: the observed windows have no empty cause. A resampling draw that leaves
    a cause with no study gives that cause 0.5 (counted in ZERO_DRAWS)."""
    total = np.zeros(next(iter(mats.values())).shape[1])
    n = 0
    for y in range(w[0], w[1] + 1):
        m = mats[y]
        if rng is not None and len(m):
            m = m[rng.integers(0, len(m), len(m))]
        total += m.sum(axis=0)
        n += len(m)
    if (total == 0).any():
        if rng is None:
            # Only in the 20-cause sensitivity set (an injury cause in a thin window); disclosed.
            ZERO_POINT.add(f"{label(w)}: " + ", ".join(CAUSES_NOW[i] for i in np.flatnonzero(total == 0)))
        else:
            ZERO_DRAWS["n"] += 1
        total = np.where(total == 0, .5, total)
    if rng is not None:
        ZERO_DRAWS["total"] += 1
    return total / total.sum(), n


def p_of(dalys, key, causes, w):
    v = np.array([sum(dalys[y][key].get(c, 0) for y in range(w[0], w[1] + 1)) for c in causes])
    return v / v.sum()


def terms(p, q):
    return p * np.log(p / q)


def kld_rare_excluded(p, q, keep):
    """The paper's sensitivity check (causes with a DALY or research share below 1% left out), with one
    fixed set of causes per group, so the line does not jump when a cause crosses 1% in some window."""
    return float(np.sum(terms(p[keep], q[keep])))


def shapley(p0, q0, p1, q1):
    """Per-cause research and burden parts of the change in KLD terms (they sum to the change)."""
    t00, t01, t10, t11 = terms(p0, q0), terms(p0, q1), terms(p1, q0), terms(p1, q1)
    research = ((t01 - t00) + (t11 - t10)) / 2
    burden = ((t10 - t00) + (t11 - t01)) / 2
    return research, burden


def ci(a):
    return np.percentile(a, 2.5), np.percentile(a, 97.5)


def analyse(studies, dalys, causes, draws, seed):
    rng = np.random.default_rng(seed)
    CAUSES_NOW[:] = causes
    ZERO_DRAWS.update(n=0, total=0)
    ZERO_POINT.clear()
    res = {}
    for key in GROUPS:
        mats = matrix(studies, key, causes)
        p = {w: p_of(dalys, key, causes, w) for w in WINDOWS}
        q = {w: q_of(mats, w)[0] for w in WINDOWS}
        n = {w: q_of(mats, w)[1] for w in WINDOWS}
        boot_q = {w: [q_of(mats, w, rng)[0] for _ in range(draws)] for w in WINDOWS}
        keep = np.logical_and.reduce([(p[w] >= .01) & (q[w] >= .01) for w in WINDOWS])
        line = []
        for w in WINDOWS:
            obs = [np.sum(terms(p[w], qb)) for qb in boot_q[w]]
            excl = [kld_rare_excluded(p[w], qb, keep) for qb in boot_q[w]]
            dal_fixed = [np.sum(terms(p[BASE_W], qb)) for qb in boot_q[w]]
            res_fixed = [np.sum(terms(p[w], qb)) for qb in boot_q[BASE_W]]
            line.append({"window": label(w), "mid": mid(w), "end": w[1], "n_studies": n[w],
                         "observed": float(np.sum(terms(p[w], q[w]))), "observed_ci": ci(obs),
                         "dalys_fixed": float(np.sum(terms(p[BASE_W], q[w]))), "dalys_fixed_ci": ci(dal_fixed),
                         "research_fixed": float(np.sum(terms(p[w], q[BASE_W]))), "research_fixed_ci": ci(res_fixed),
                         "rare_excluded": kld_rare_excluded(p[w], q[w], keep), "rare_excluded_ci": ci(excl),
                         "n_causes_excluded": int((~keep).sum()),
                         "causes_excluded": "; ".join(c for c, k in zip(causes, keep) if not k)})
        # Change from the base to the end window, as % of base KLD, for the three plotted lines.
        p0, p1 = p[BASE_W], p[END_W]
        k0 = float(np.sum(terms(p0, q[BASE_W])))
        r_c, b_c = shapley(p0, q[BASE_W], p1, q[END_W])

        def changes(q0, q1):
            base = np.sum(terms(p0, q0))
            return (100 * (np.sum(terms(p1, q1)) / base - 1),   # observed
                    100 * (np.sum(terms(p1, q0)) / base - 1),   # research fixed: only DALYs change
                    100 * (np.sum(terms(p0, q1)) / base - 1))   # DALYs fixed: only research changes
        point = changes(q[BASE_W], q[END_W])
        boots = np.array([changes(qb0, qb1) for qb0, qb1 in zip(boot_q[BASE_W], boot_q[END_W])])
        res[key] = {
            "line": line, "kld_base": k0,
            "decomp": {"observed": point[0], "observed_ci": ci(boots[:, 0]),
                       "burden": point[1], "burden_ci": ci(boots[:, 1]),
                       "research": point[2], "research_ci": ci(boots[:, 2])},
            "causes": [{"cause": c, "research": 100 * r / k0, "burden": 100 * b / k0,
                        "research_share_0": q[BASE_W][i], "research_share_1": q[END_W][i],
                        "daly_share_0": p0[i], "daly_share_1": p1[i]}
                       for i, (c, r, b) in enumerate(zip(causes, r_c, b_c))],
        }
    return res


def style(ax):
    ax.set_facecolor(BG)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#b9b2a6")
    ax.tick_params(colors="#3b3832", labelsize=9.5)
    ax.grid(axis="y", color="#e6e1d8", linewidth=.8)
    ax.axvspan(MAIN_END - 1 + .5, 2022.5, color="#efeae1", zorder=0)
    ax.text(2021, 1.0, "windows reaching\n2020–23 (COVID)", transform=ax.get_xaxis_transform(), ha="center",
            va="top", fontsize=8, color="#8a8378")
    ticks = [mid(w) for w in WINDOWS][::2]
    ax.set_xticks(ticks, [label(w) for w in WINDOWS][::2], fontsize=8.5)


def plot_series(ax, line, col, colour, lab=None, lw=2.2):
    main = [r for r in line if r["end"] <= MAIN_END]
    ext = [r for r in line if r["end"] >= MAIN_END]
    for part, ls in ((main, "-"), (ext, "--")):
        x = [r["mid"] for r in part]
        ax.fill_between(x, [r[col + "_ci"][0] for r in part], [r[col + "_ci"][1] for r in part],
                        color=colour, alpha=.13, linewidth=0)
        ax.plot(x, [r[col] for r in part], color=colour, linewidth=lw, linestyle=ls,
                marker="o" if ls == "-" else None, markersize=3.5, label=lab if ls == "-" else None)


def fig2a(res, keys, causes_label, path, col="observed", title=None, note=None):
    fig, axes = plt.subplots(1, len(keys), figsize=(6.2 * len(keys), 5.2), facecolor=BG)
    top = max(r[col + "_ci"][1] for key in keys for r in res[key]["line"]) * 1.15
    for ax, key in zip(np.atleast_1d(axes), keys):
        style(ax)
        head, sub, colour = GROUPS[key]
        line = res[key]["line"]
        plot_series(ax, line, col, colour)
        end = next(r for r in line if r["end"] == MAIN_END)
        chg = 100 * (end[col] / line[0][col] - 1)
        ax.text(.02, .95, f"2010–12 → 2017–19: {chg:+.0f}%", transform=ax.transAxes, fontsize=9.5,
                fontweight="bold", color=colour, va="top")
        ax.set_ylim(0, top)
        ax.set_title(f"{head}\n", loc="left", fontsize=12, fontweight="bold", color="#1d1d1d")
        ax.text(0, 1.02, sub, transform=ax.transAxes, fontsize=9, color="#5d574e")
        ax.text(.01, .02, f"n = {line[0]['n_studies']:,} studies in 2010–12, {end['n_studies']:,} in 2017–19",
                transform=ax.transAxes, fontsize=8, color="#6b665d")
    np.atleast_1d(axes)[0].set_ylabel("Research–disease divergence (KLD)", fontsize=10.5)
    fig.suptitle(title or "Evolution of research–disease divergence, 2010–2023", x=.03, ha="left",
                 fontsize=14, fontweight="bold")
    fig.text(.03, .925, textwrap.fill(note or (f"KLD across {causes_label}, 3-year rolling windows. Solid: 2010–2019; dashed: windows "
             "reaching 2020–23. Shaded: 95% intervals from resampling studies. Same y-axis in both panels; levels are "
             "not comparable across panels (different burden references), trends are."), 175),
             fontsize=9.3, color="#5d574e", va="top")
    fig.tight_layout(rect=(0, 0, 1, .85))
    fig.savefig(path, dpi=150, facecolor=BG)
    plt.close(fig)


def fig3(res, keys, causes_label, path):
    fig, axes = plt.subplots(1, len(keys), figsize=(6.2 * len(keys), 5.8), facecolor=BG)
    top = max(r[c + "_ci"][1] for key in keys for r in res[key]["line"]
              for c in ("observed", "research_fixed", "dalys_fixed")) * 1.12
    for i, (ax, key) in enumerate(zip(np.atleast_1d(axes), keys)):
        style(ax)
        head, sub, _ = GROUPS[key]
        line = res[key]["line"]
        plot_series(ax, line, "observed", C_OBS, "Observed")
        plot_series(ax, line, "research_fixed", C_RES_FIXED, "Research fixed to 2010–12 (only burden changes)", 1.8)
        plot_series(ax, line, "dalys_fixed", C_DAL_FIXED, "DALYs fixed to 2010–12 (only research changes)", 1.8)
        ax.set_ylim(0, top)
        d = res[key]["decomp"]
        box = (f"Change 2010–12 → 2017–19 (95% interval)\n"
               f"  observed:            {d['observed']:+.0f}% ({d['observed_ci'][0]:+.0f} to {d['observed_ci'][1]:+.0f})\n"
               f"  only DALYs change:   {d['burden']:+.0f}% ({d['burden_ci'][0]:+.0f} to {d['burden_ci'][1]:+.0f})\n"
               f"  only research changes: {d['research']:+.0f}% ({d['research_ci'][0]:+.0f} to {d['research_ci'][1]:+.0f})")
        ax.text(.02, .03, box, transform=ax.transAxes, fontsize=8.3, color="#1d1d1d", family="monospace",
                bbox={"facecolor": "white", "edgecolor": "#d9d3c7", "boxstyle": "round,pad=.4"})
        ax.set_title(f"{head}\n", loc="left", fontsize=12, fontweight="bold", color="#1d1d1d")
        ax.text(0, 1.02, sub, transform=ax.transAxes, fontsize=9, color="#5d574e")
        if i == 0:
            ax.legend(frameon=False, fontsize=8.3, loc="upper left")
    np.atleast_1d(axes)[0].set_ylabel("Research–disease divergence (KLD)", fontsize=10.5)
    fig.suptitle("Contributions of research and disease burden to changes in divergence", x=.03, ha="left", fontsize=14, fontweight="bold")
    fig.text(.03, .92, textwrap.fill(
        f"KLD across {causes_label}, 3-year rolling windows. If the observed line follows the green line, changing burden "
        "explains the trend; if it follows the red line, research has shifted. Box: each line's change from 2010–12 to "
        "2017–19 as % of 2010–12 divergence, with 95% intervals. Same y-axis in both panels.",
        175), fontsize=9.3, color="#5d574e", va="top")
    fig.tight_layout(rect=(0, 0, 1, .85))
    fig.savefig(path, dpi=150, facecolor=BG)
    plt.close(fig)


def fig4(res, keys, causes_label, path):
    # Shares, not per-cause KLD terms: those terms can be negative, so a cause whose research
    # moves towards its burden can still score as adding divergence (kept in the CSV only).
    fig, axes = plt.subplots(1, len(keys), figsize=(7.2 * len(keys), 7.6), facecolor=BG)
    for ax, key in zip(np.atleast_1d(axes), keys):
        ax.set_facecolor(BG)
        cs = sorted(res[key]["causes"], key=lambda c: c["daly_share_1"])
        y = np.arange(len(cs))
        xmax = 100 * max(max(c["research_share_0"], c["research_share_1"], c["daly_share_0"], c["daly_share_1"]) for c in cs)
        for i, c in enumerate(cs):
            for (a, b, colour, dy) in ((c["research_share_0"], c["research_share_1"], C_RESEARCH, .17),
                                       (c["daly_share_0"], c["daly_share_1"], C_BURDEN, -.17)):
                ax.scatter(100 * a, i + dy, s=18, color=colour, zorder=3)
                ax.annotate("", (100 * b, i + dy), (100 * a, i + dy),
                            arrowprops={"arrowstyle": "-|>", "color": colour, "lw": 1.6, "mutation_scale": 10})
            gap = 100 * (abs(c["research_share_1"] - c["daly_share_1"]) - abs(c["research_share_0"] - c["daly_share_0"]))
            ax.text(xmax * 1.05, i, f"{'closer' if gap < 0 else 'further'} {abs(gap):.1f} pts", va="center", fontsize=8.3,
                    color=C_BURDEN if gap < 0 else C_RESEARCH, fontweight="bold")
        ax.set_xlim(0, xmax * 1.32)
        ax.set_yticks(y, [SHORT.get(c["cause"], c["cause"]) for c in cs], fontsize=9)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.grid(axis="x", color="#e6e1d8", linewidth=.8)
        ax.set_xlabel("Share (%), 2010–12 (dot) → 2017–19 (arrowhead)", fontsize=9.5)
        head, sub, _ = GROUPS[key]
        ax.set_title(f"{head}\n", loc="left", fontsize=12, fontweight="bold")
        ax.text(0, 1.01, sub, transform=ax.transAxes, fontsize=9, color="#5d574e")
    from matplotlib.lines import Line2D
    fig.legend(handles=[Line2D([], [], color=C_RESEARCH, lw=2, label="Share of research"),
                        Line2D([], [], color=C_BURDEN, lw=2, label="Share of DALYs")],
               frameon=False, fontsize=9.5, loc="upper right", ncol=2, bbox_to_anchor=(.98, .975))
    fig.suptitle("Which diseases moved, 2010–12 to 2017–19?", x=.03, ha="left", fontsize=14, fontweight="bold")
    fig.text(.03, .93, textwrap.fill(
        f"Share of research and share of DALYs for each of {causes_label}, ordered by 2017–19 burden. Right: whether the "
        "gap between a cause's research share and burden share narrowed (closer) or widened (further), in percentage points.",
        170), fontsize=9.3, color="#5d574e", va="top")
    fig.tight_layout(rect=(0, 0, 1, .88))
    fig.savefig(path, dpi=150, facecolor=BG)
    plt.close(fig)


# Decomposition CSV columns: change 2010-12 -> 2017-19 in each plotted line, % of 2010-12 KLD.
DECOMP_COLS = [("observed", "observed_change"), ("burden", "only_dalys_change_research_fixed"),
               ("research", "only_research_changes_dalys_fixed")]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--raw", default=os.path.join(ROOT, "data", "raw"))
    ap.add_argument("--draws", type=int, default=1000)
    args = ap.parse_args()
    out = os.path.join(ROOT, "exports", f"kld_replication_v2_{datetime.date.today():%Y-%m-%d}")
    os.makedirs(out, exist_ok=True)
    studies = v1.load_studies(args.raw)
    dalys, _ = v1.load_dalys(args.raw)
    line_rows, decomp_rows, cause_rows = [], [], []
    for tag, causes, lab in [("16causes", v1.CAUSES_16, "the paper's 16 GBD level-2 causes"),
                             ("20causes", v1.CAUSES_20, "20 GBD level-2 causes (the paper's 16 plus mental disorders and injuries)")]:
        res = analyse(studies, dalys, causes, args.draws, 20261014)
        print(f"[{tag}] resampling draws (per window and group) with a cause left empty: "
              f"{ZERO_DRAWS['n']:,} of {ZERO_DRAWS['total']:,}; observed windows with an empty cause: "
              f"{sorted(ZERO_POINT) or 'none'}")
        prefix = "main" if tag == "16causes" else "supp"
        fig2a(res, ["all", "lmic"], lab, os.path.join(out, f"{prefix}_fig2a_{tag}.png"))
        fig3(res, ["all", "lmic"], lab, os.path.join(out, f"{prefix}_fig3_{tag}.png"))
        fig4(res, ["all", "lmic"], lab, os.path.join(out, f"{prefix}_fig4_{tag}.png"))
        if tag == "16causes":
            fig2a(res, ["all", "lmic"], lab, os.path.join(out, "supp_fig2a_rare_causes_excluded_16causes.png"),
                  col="rare_excluded", title="Sensitivity: divergence without rare causes",
                  note="The paper's sensitivity check: KLD leaving out causes whose research or DALY share is below 1%. Here one "
                       "fixed set per panel (below 1% in any window), so the line does not jump as causes cross 1%. Shaded: 95% intervals.")
        fig2a(res, ["hic"], lab, os.path.join(out, f"supp_fig2a_hic_{tag}.png"))
        fig3(res, ["hic"], lab, os.path.join(out, f"supp_fig3_hic_{tag}.png"))
        fig4(res, ["hic"], lab, os.path.join(out, f"supp_fig4_hic_{tag}.png"))
        print(f"== {tag}: change in KLD 2010-12 -> 2017-19 (% of base), 95% CI")
        for key in GROUPS:
            d = res[key]["decomp"]
            print(f"  {key:5s} base KLD {res[key]['kld_base']:.3f} | observed {d['observed']:+.0f}% {tuple(round(x) for x in d['observed_ci'])}"
                  f" | only DALYs change {d['burden']:+.0f}% {tuple(round(x) for x in d['burden_ci'])}"
                  f" | only research changes {d['research']:+.0f}% {tuple(round(x) for x in d['research_ci'])}")
            ex = res[key]["line"]
            print(f"        rare causes excluded ({ex[0]['causes_excluded']}): "
                  + ", ".join(f"{r['rare_excluded']:.3f}" for r in ex))
            decomp_rows.append({"cause_set": tag, "group": key, "kld_2010_12": round(res[key]["kld_base"], 4),
                                **{f"{name}_pct": round(d[k], 1) for k, name in DECOMP_COLS},
                                **{f"{name}_lo": round(d[k + "_ci"][0], 1) for k, name in DECOMP_COLS},
                                **{f"{name}_hi": round(d[k + "_ci"][1], 1) for k, name in DECOMP_COLS}})
            for r in res[key]["line"]:
                line_rows.append({"cause_set": tag, "group": key, "window": r["window"], "n_studies": r["n_studies"],
                                  **{c: round(r[c], 4) for c in ("observed", "research_fixed", "dalys_fixed", "rare_excluded")},
                                  **{f"{c}_lo": round(r[c + "_ci"][0], 4) for c in ("observed", "research_fixed", "dalys_fixed", "rare_excluded")},
                                  **{f"{c}_hi": round(r[c + "_ci"][1], 4) for c in ("observed", "research_fixed", "dalys_fixed", "rare_excluded")},
                                  "n_causes_excluded": r["n_causes_excluded"], "causes_excluded": r["causes_excluded"]})
            for c in res[key]["causes"]:
                cause_rows.append({"cause_set": tag, "group": key, **{k: (round(v, 4) if isinstance(v, float) else v)
                                                                       for k, v in c.items()}})
    for name, rows in (("kld_windows.csv", line_rows), ("kld_decomposition.csv", decomp_rows),
                       ("kld_cause_contributions.csv", cause_rows)):
        with open(os.path.join(out, name), "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    print("wrote", out)


if __name__ == "__main__":
    main()
