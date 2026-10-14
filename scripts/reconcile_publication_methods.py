"""Reconcile the publication draft and selection figure with current local data."""
import csv
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw'
OUT=ROOT/'exports/publication_reconciliation'
csv.field_size_limit(10**9)
def read(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def main():
    draft=RAW/'HEE_METHODS_PUBLICATION-updated-Oct-14.md'
    backup=OUT/'manuscript_backups'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup.mkdir(parents=True)
    shutil.copy2(draft,backup/draft.name)
    shutil.copy2(ROOT/'docs/data/figure_updates.json',backup/'figure_updates.json')
    rows=read(RAW/'hee_analysis_master_v2.csv');included=[r for r in rows if r['is_eligible']=='TRUE']
    ids={r['record_id'] for r in included};n=len(ids);assert n==41610
    counts=Counter(r['eligibility'] for r in rows)
    reviews=Counter(r['review_type'] for r in included)
    assert reviews=={'Systematic review':1856,'Review (non-systematic)':796,'Not identified as a review':38958}
    q={r['record_id'] for r in included if r['uses_qaly']=='TRUE'}
    d={r['record_id'] for r in read(RAW/'hee_outcomes_long.csv') if r['family']=='DALYs'}&ids
    gbd=json.loads((ROOT/'docs/data/disease_gbd.json').read_text(encoding='utf-8'))
    language=Counter(r['language'] for r in included)
    lang_known=n-language['NA']-language['ng']
    geo_ids={r['record_id'] for r in read(RAW/'hee_geo_long.csv') if r['record_id'] in ids and r['iso3'] not in ('NA','')}
    topic=[r for r in read(RAW/'topic_map.csv') if r['record_id'] in ids]
    text=draft.read_text(encoding='utf-8')
    assert 'A subsequent publication-family audit' not in text, 'Already reconciled; review a new delta instead of rerunning'
    text=text.replace('every number here is taken from the v2\nanalysis dataset (October 2026).',
        'final descriptive counts use the reconciled v2\nanalysis dataset (14 October 2026); screening and validation results describe their original\nreference samples, and topic-model stability describes the original clustering run.')
    marker='Extraction accuracy was assessed against a human-coded sample:'
    insert='''A subsequent publication-family audit investigated 61 potential excess reports across 57
normalised-title groups containing 118 records, and traced five additional full articles.
Titles, author teams, abstracts, sample sizes, interventions, study periods, results, DOIs,
trial registrations and publisher version statements were compared. We retained the newest
full research article for each duplicated evaluation; later abstracts, translations and
synopses did not displace a full article. Distinct evaluations, substantive companion analyses
and review/HTA updates were retained. The audit excluded 44 redundant reports, two registrations
without results and one retracted paper. Bundled-payments and carpal-tunnel relationships were
adjudicated by the study team from matching study details without an explicit publication link;
the Ginkgo translation was explicitly confirmed by the publisher. Original records were
preserved with exclusion reasons and retained-report links. This was a targeted audit, not a
whole-corpus search for all linked publications.

Review status was subsequently reconciled using titles and abstracts, distinguishing systematic
reviews, non-systematic reviews and records not identified as reviews. Labels were based on
explicit descriptions and reconciled against documented exceptions; targeted published-methods
checks resolved selected ambiguous cases. A separate field recorded whether a review also
contained an original evaluation, so review status did not by itself determine exclusion.
These classifications were not independently validated across the whole corpus.

'''
    assert marker in text;text=text.replace(marker,insert+marker,1)
    start=text.index('Countries were mapped to World Bank income groups')
    end=text.index('Disease areas were coded',start)
    text=text[:start]+'''Study geography was based on the country or setting named in the title and abstract;
author affiliations and publisher locations were not used to infer the patient setting.
Where the title and abstract did not state a sample location, it was recorded as not reported.
For income comparisons over time, countries were mapped to World Bank historical classifications
in force on 1 January of each study's publication year. Missing country-year classifications
were excluded from these comparisons, except for recorded 2026 exceptions: Ethiopia used its
FY2025 low-income classification and Venezuela its last available FY2021 upper-middle-income
classification. Taiwan was coded as high income in every year by recorded override.
Country-level maps and cross-sectional summaries used the July 2026 classification. Populations
were retrieved from the World Bank API [access date]. Studies naming more than 15 countries
were classed as multi-country. '''+text[end:]
    text=text.replace('A GBD cause was\nassigned to 87.6% of studies',f'A GBD analysis group was\nassigned to {len(set(gbd["s"])):,} of {n:,} included records (87.6%)')
    text=text.replace('As checks, a second model', 'In the original coding-validation samples, a second model')
    text=text.replace('giving 73 clusters labelled by', 'giving 73 clusters labelled by')
    text=text.replace('cluster. Clustering was stable',
        'cluster. The model was fitted to 41,661 records eligible at the time of the October 2026\nrun and was not refitted after subsequent eligibility changes, preserving cluster identities.\nOf the final 41,610 included records, 41,583 had topic coordinates; 27 were unmapped.\nClustering was stable')
    start=text.index('Analyses are descriptive.')
    end=text.index('\n## Deviations from the protocol',start)
    text=text[:start]+'''Analyses are descriptive. We report counts and proportions with Wilson 95% confidence
intervals where used; research density per country relative to population, disease burden and
health spending; and, by disease area, the ratio of each area's share of research to its share
of disease burden, separately for high-income and for low-income and middle-income countries.
A ratio of one indicates research proportional to burden; it is a reference point, not a target.
Single-country studies with a known publication-year income group were used for study-level
income comparisons; multi-country studies could contribute once to each named country's
country-level counts and to each relevant income stratum in disease-share analyses.

Country denominator sets were matched to the comparison: national burden analyses used the
204 national GBD 2023 locations, including locations with no studies; website country-density
analyses used the available country list and metric-specific non-missing denominators. Study
locations absent from the national burden export were excluded from that comparison, not
assigned zero burden. Annual reach analyses used each year's income classification and
excluded unclassified country-years; the broader country-universe sensitivity used Natural
Earth country entities without a population floor. Analyses extending through 2026 treated
that final year as partial.

As an exploratory extension of Schmallenbach et al. (Nature Medicine, 2025;
doi:10.1038/s41591-025-03923-0), we measured divergence between disease-burden shares (p) and
research shares (q) using Kullback–Leibler divergence, KLD(p||q) = sum p ln(p/q), with natural
logarithms. Research shares counted study–cause links; a study naming several causes could
contribute to each. DALYs and research were pooled within matching three-year windows from
2010–2012 to 2021–2023. The main comparison used 16 GBD level-2 causes matching the published
analysis. All studies were compared with global DALYs; studies of low- and middle-income
settings were compared with DALYs in those settings, with high-income settings supplementary.
Research setting used publication-year income classification; burden used the classification
in the burden year. Records without a reported country contributed to the global analysis
but not the setting-specific panels. Scores across panels therefore had different burden
references and were interpreted within panels.

To distinguish changes in research from changes in burden, we compared the observed trend with
two scenarios fixed at the 2010–2012 baseline: unchanged research shares with changing burden,
and unchanged burden shares with changing research. Their relative changes through 2017–2019
were descriptive scenarios, not causal effects or additive components. Uncertainty intervals
were based on 1,000 bootstrap resamples of studies within publication year, including the
baseline; DALY uncertainty was not propagated. Main 16-cause point estimates used no smoothing;
if a bootstrap draw left a cause without studies, that cause received 0.5 study. Sensitivities
used 20 causes including mental disorders and additional injury groups, and excluded causes
whose research or burden share was below 1% in any window, using a fixed retained cause set
within each panel. Empty causes in the sparse 20-cause point estimates also received 0.5 study.
Windows reaching 2020–2023 were shown separately as a COVID-affected extension. These analyses
were exploratory. Analyses were done in R (version 4.4.1) and Python.
'''+text[end:]
    text=text.replace('and no full-text stage was conducted.',
        'and no systematic full-text eligibility stage was conducted. Selected publisher pages,\nfull texts and registrations were consulted during subsequent review-classification and\npublication-linkage checks; these did not constitute a full-text stage for the entire corpus.')
    start=text.index('31,188 were excluded')
    end=text.index('\n## Limitations',start)
    text=text[:start]+f'''31,235 were excluded (13,573 partial evaluations, 11,975 not classifiable as full evaluations,
4,965 with non-clinical consequences, 675 duplicates identified by DOI or title/year,
44 additional redundant publications, two trial registrations without results and one
retracted paper), leaving **41,610 included records**. The reconciled review classification
identified 1,856 systematic and 796 non-systematic reviews (2,652 total); the other 38,958 records
were not identified as reviews. This classification does not independently establish that
every remaining record is a primary study. Of included records, {len(q|d):,} (46.9%) reported a
generic outcome measure (QALYs or DALYs). The study selection flow is shown in figure 1.
'''+text[end:]
    start=text.index('The\nevidence base is almost entirely in English')
    text=text[:start]+'''Of the 32,853 records with an interpretable publication-language code,
32,792 (99.8%) were coded as English; language was missing for 8,754 records and three had an
uninterpretable code. A country, region or global scope was recorded for 71.8% of records;
29,104 (69.9%) had a named country, and 87.6% had a GBD analysis group. Methodological quality
was not assessed through a systematic full-text audit; decision-analytic reporting indicators
record what abstracts reported, not necessarily what was done. The publication-family audit
resolved the flagged groups but does not establish that all linked publications in the corpus
have been found. Companion analyses and review updates remain included, so the analysis unit
is an included report rather than necessarily a unique underlying clinical study. Review
classifications remain limited by title/abstract reporting and selective follow-up checks.
There are 806 included records coded as posted content (1.9%); this is a metadata category
that commonly includes preprints and working papers, not a verified preprint count.
[Team decision required: retain standalone preprints and other non-article reports, exclude
them, or present a sensitivity analysis.] Screening and extraction validation describe their
original samples and were not repeated following this reconciliation. Topic assignments were
filtered to the final dataset without refitting the clustering model. The KLD results depend
on the selected cause set and sparse-category treatment and do not measure research quality,
funding amounts or causal responsiveness to burden.
'''
    draft.write_text(text,encoding='utf-8')
    # A standalone selection diagram; retain the old raster as historical.
    fig,ax=plt.subplots(figsize=(14,11),facecolor='#f7f4ee');ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
    ax.text(.04,.97,'Study selection: 41,610 included records',fontsize=21,weight='bold',va='top')
    ax.text(.04,.925,'Health economic evaluations arm · reconciled 14 October 2026',fontsize=12,va='top')
    left=[('Records identified','1,154,050'),('Titles and abstracts screened','1,119,811'),('Advanced to extraction','98,065'),('Records extracted','72,845'),('Included in analysis','41,610')]
    ys=[.81,.65,.49,.33,.13]
    for (label,value),y in zip(left,ys):
        ax.add_patch(FancyBboxPatch((.05,y),.39,.10,boxstyle='round,pad=0.008',facecolor='#e8f1fc',edgecolor='none'))
        ax.text(.245,y+.067,label,ha='center',fontsize=13,weight='bold');ax.text(.245,y+.024,value,ha='center',fontsize=17,color='#2868a4')
    for a,b in zip(ys,ys[1:]):ax.annotate('',xy=(.245,b+.112),xytext=(.245,a-.005),arrowprops={'arrowstyle':'->','color':'#555','lw':1.5})
    notes=[(.80,.10,'No abstract for screening: 34,239'),(.63,.12,'Excluded at screening: 1,021,746\nAdvanced: 45,792 included + 52,273 uncertain'),(.47,.10,'No abstract for extraction: 25,220'),(.25,.19,'Excluded after extraction: 31,235\nPartial evaluations: 13,573\nNot classifiable: 11,975\nNon-clinical consequences: 4,965\nDOI/title-year duplicates: 675\nAdditional redundant reports: 44\nRegistrations without results: 2 · Retracted: 1')]
    for y,h,note in notes:
        ax.add_patch(FancyBboxPatch((.51,y),.44,h,boxstyle='round,pad=0.008',facecolor='#e9e7e1',edgecolor='none'))
        ax.text(.73,y+h/2,note,ha='center',va='center',fontsize=11,linespacing=1.5)
    ax.text(.52,.155,'Review classification within included records:\n1,856 systematic + 796 non-systematic reviews\n38,958 records not identified as reviews',fontsize=11,va='top',linespacing=1.6)
    ax.text(.05,.04,'All stages reconcile. Original records are preserved; exclusions are flags.\nReview labels describe the current classification and are not independent confirmation of primary-study status.',fontsize=10,va='top')
    stem=ROOT/'docs/figures/fig_selection_reconciled'
    fig.savefig(stem.with_suffix('.svg'),facecolor=fig.get_facecolor(),bbox_inches='tight')
    fig.savefig(stem.with_suffix('.png'),facecolor=fig.get_facecolor(),bbox_inches='tight',dpi=150);plt.close(fig)
    caption='Study-selection flow after publication reconciliation: 72,845 extracted; 31,235 excluded; 41,610 included. Review classification: 1,856 systematic reviews, 796 non-systematic reviews and 38,958 records not identified as reviews. Original screening counts are unchanged; the audit adds 44 redundant reports, two registrations without results and one retracted paper to exclusions.'
    path=ROOT/'docs/data/figure_updates.json';updates=json.loads(path.read_text(encoding='utf-8'))
    updates['paper01.webp']={'file':'fig_selection_reconciled.svg','title':'Study selection: 41,610 included records','caption':caption}
    path.write_text(json.dumps(updates,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    summary={'included':n,'excluded_after_extraction':len(rows)-n,'review_counts':dict(reviews),'generic_outcome_records':len(q|d),'gbd_group_records':len(set(gbd['s'])),'named_country_records':len(geo_ids),'interpretable_language_records':lang_known,'english_records':language['en'],'topic_coordinates':len(topic),'posted_content':806,'manuscript_backup':str(backup.relative_to(ROOT)),'remaining_items':['protocol reference','search dates','World Bank access date','standalone preprint/non-article eligibility decision'],'figure1':'docs/figures/fig_selection_reconciled.svg'}
    (OUT/'manuscript_reconciliation.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    assert sum([13573,11975,4965,675,44,2,1])==len(rows)-n
    assert 1154050-34239==1119811 and 1119811-1021746==98065 and 98065-25220==72845
    assert '41,657' not in text and 'about 61 included' not in text
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
