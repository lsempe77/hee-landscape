"""Standalone theme_hee figure: Wellcome-funded studies by publication year. Never writes docs/."""
import json
import sys
sys.dont_write_bytecode = True
import matplotlib.pyplot as plt
import pandas as pd
import create_manuscript_figures_oct19 as h

SRC = h.ROOT / 'docs/figures/wellcome_analysis.json'
OUT = h.ROOT / 'exports/wellcome_by_year_2026-10-20'

def main():
    OUT.mkdir(exist_ok=True)
    a = json.loads(SRC.read_text(encoding='utf-8'))
    df = pd.DataFrame(a['wellcome_by_year']).set_index('year')
    n, last = int(df.n.sum()), int(df.index.max())
    assert n == a['wellcome']['n'] == 174
    df.to_csv(OUT/'wellcome_by_year.csv')
    since = int(df.loc[2020:, 'n'].sum())

    fig = plt.figure(figsize=(9, 5.2))
    h.title(fig, 'Wellcome-funded health economic studies by publication year, 2010–2026')
    fig.text(.035, .905, f'{n} studies name Wellcome as a funder; {since} ({since/n:.0%}) were published from 2020 onwards',
             fontsize=9.5, color=h.SECONDARY, va='top')
    ax = fig.add_axes([.06, .19, .9, .66]); h.style(ax, None)
    for y, v in df.n.items():
        partial = y == last
        ax.bar(y, v, width=.72, lw=0, color=h.BLUE, alpha=.55 if partial else 1,
               hatch='////' if partial else None, edgecolor=h.BG if partial else None)
        ax.text(y, v + .5, f'{v}', ha='center', va='bottom', fontsize=8.5,
                weight='bold' if v == df.n.max() else 'normal', color=h.INK)
    ax.set_ylim(0, df.n.max() * 1.15); ax.set_yticks([])
    ax.set_xticks(list(df.index), [*map(str, df.index[:-1]), f'{last}*'])
    ax.axhline(0, color=h.MUTED, lw=.6)

    caption = (f"Eligible studies, 2010–{last}, including reviews (n = {n}). A study counts as Wellcome-funded when its recorded funders name the "
               "Wellcome Trust; the Burroughs Wellcome Fund, a separate US foundation, is excluded. Counts describe acknowledged funding, not grant amounts. "
               f"*{last} is incomplete (searches ran to August {last}), so its bar is hatched. Source: docs/figures/wellcome_analysis.json (built 14 October 2026).")
    h.foot(fig, caption, 150)
    for ext in ['png', 'pdf', 'svg']:
        fig.savefig(OUT/f'wellcome_by_year.{ext}', dpi=300)
    (OUT/'caption.txt').write_text(caption + '\n', encoding='utf-8')
    print('Saved', OUT)

if __name__ == '__main__': main()
