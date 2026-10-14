"""Render manually assessed publication relationships; never changes the master."""
import csv
import itertools
import json
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'exports/publication_version_check'
rows = list(csv.DictReader((ROOT / 'exports/potential_publication_versions_61_records.csv').open(encoding='utf-8-sig')))
groups = defaultdict(list)
for row in rows:
    groups[int(row['candidate_group'])].append(row)

assessments = {}
def add(group, category, relationship, evidence, handling, strength='strong', sources=()):
    assessments[group] = dict(candidate_group=group, category=category, relationship=relationship,
        evidence_strength=strength, evidence=evidence, suggested_handling=handling,
        additional_sources=list(sources))

LINK = 'linked_reports'
UPDATE = 'review_update'
DISTINCT = 'distinct_evaluations'
REGISTRY = 'registry_and_results'

add(1, DISTINCT, 'Different economic evaluations',
    'Different author teams: Sathianathen et al. versus Sung et al. The earlier analysis compares three treatment strategies; the later compares five and reaches a different preferred-treatment result. The later paper cites the earlier as previous research.',
    'Retain both as separate evaluations.', sources=['https://www.frontiersin.org/journals/oncology/articles/10.3389/fonc.2021.627083/full'])
add(2, LINK, 'Conference abstract and full article',
    'Overlapping Schuetz/Sulo/Walzer author team; same EFFORT trial, 2,028 participants (1,015/1,013), 30-day model, CHF214 saving and CHF19.56 after dietitian costs. Crossref identifies MON-LB676 as the conference report.',
    'Link as one evaluation; full article is the preferred report.')
add(3, UPDATE, 'Cochrane review update',
    'Same Cochrane review identifier CD009261. Publisher update metadata links pub5 to pub4. Searches advance from June 2019 to January 2021; RCT count rises from 44 to 62 and economic studies from five to six.',
    'Link review lineage; decide whether the map counts each update or only the latest review.')
add(4, LINK, 'ATTILA trial conference report and HTA',
    'Same named trial, 495 participants, 248/247 allocation and assistive-technology comparison. Crossref identifies the earlier record as P4-628 and overlapping Gathercole/Howard authors. HTA adds fuller economic and caregiver reporting.',
    'Link study family; use the HTA for economic details.')
add(5, DISTINCT, 'Country-specific economic analyses using the same trial',
    'Both use CRYSTAL-AF, with some overlapping authors, but the 2016 model uses a UK NHS perspective and the later model uses US costs and adds immediate versus delayed monitoring strategies.',
    'Retain both evaluations; a common trial does not make the economic analyses duplicates.', sources=['https://pubmed.ncbi.nlm.nih.gov/26763916/', 'https://pubmed.ncbi.nlm.nih.gov/33300381/'])
add(6, DISTINCT, 'Separate evaluations of the Shanghai screening programme',
    'Li et al. model annual screening of a hypothetical population of 100,000 using 3.5% discounting; Jiang et al. use 2014-2016 real-world programme data (1,097,656 residents) and 3% discounting. Different author lists, cohort definitions and cost-effectiveness estimates.',
    'Retain both economic analyses; optionally link the shared programme.', sources=['https://www.frontiersin.org/journals/public-health/articles/10.3389/fpubh.2022.986728/full'])
add(7, UPDATE, 'Cochrane review update',
    'Same identifier CD001800, publisher new-version link from pub4 to pub3, and the 2021 abstract explicitly updates the 2016 review with searches through 2020/2021.',
    'Link review lineage; apply an explicit review-update counting policy.')
add(8, LINK, 'NBER working paper and published article',
    'Same Goodman-Bacon author and Medicaid implementation design. NBER explicitly lists the 2021 American Economic Review article as the published version of working paper 22899.',
    'Link as one evaluation; prefer the journal version.', sources=['https://www.nber.org/papers/w22899'])
add(9, LINK, 'NBER working paper and published article',
    'Identical five-author team and 18-month Malawi chlorine-coupon experiment. NBER explicitly lists the 2023 journal article as the published version of working paper 27570.',
    'Link as one evaluation; prefer the journal version.', sources=['https://www.nber.org/papers/w27570'])
add(10, 'unresolved_overlap', 'Possible shared trial/protocol; conflicting reported cohorts',
    'Full texts share Shenglong Li, the Liaoning institution, protocol CMU/CL/12/15 and recruitment starting January 2015. However, the 2019 paper reports 250 patients recruited through January 2016; the 2022 paper reports 160 recruited through January 2018 with broader eligibility and different results. Neither supplies an explicit version link to the other. The 2019 paper is retracted.',
    'Do not merge automatically. Resolve whether these are revised/subset data or separate cohorts; consider the retracted record separately under a retraction policy.',
    strength='unresolved', sources=['https://pmc.ncbi.nlm.nih.gov/articles/PMC6357891/', 'https://pmc.ncbi.nlm.nih.gov/articles/PMC9254448/', 'https://pubmed.ncbi.nlm.nih.gov/30740297/'])
add(11, LINK, 'Early-online and issue-publication records of the same article',
    'RIS provides the same four Liu/Zhan/Liu/Chen authors and journal. Abstracts describe the identical 92 patients recruited January 2017-August 2021, the same 46/46 comparison and outcomes. The earlier abstract labels itself ahead of print; PubMed identifies the 2024 issue record, PMID 38064624.',
    'Treat as duplicate records of one article; prefer the complete issue citation.', sources=['https://pubmed.ncbi.nlm.nih.gov/38064624/'])
add(12, UPDATE, 'Updated Ontario health technology assessment',
    'Same HTA subject but 2016 searches end in 2014 and find insufficient evidence; the 2024 assessment contains updated evidence, a new model (ICER CAD57,314/QALY) and new budget/equity analyses. RIS confirms distinct Ontario HTA volumes 16(1) and 24(2).',
    'Link assessment lineage; retain as separate assessment editions unless latest-only is the chosen policy.')
add(13, LINK, 'Conference/full-article metadata mixed with a later journal synopsis',
    'Both corpus abstracts reproduce the same BRCA1 model: 1,429,074 pregnancies, 3,716 carriers, 1,394 prevented cancers, 1,084 prevented deaths and ICER USD86,001/QALY. Crossref says the 2025 Survey report is abstracted from the 2024 full article. Record 131462474 instead stores a conference DOI (10.1016/j.ajog.2023.11.454); its full-article abstract matches 10.1016/j.ajog.2024.04.014.',
    'Link the same evaluation, flag the synopsis as secondary reporting, and repair DOI/report provenance before choosing the canonical record.', sources=['https://pubmed.ncbi.nlm.nih.gov/38621481/'])
add(14, UPDATE, 'Cochrane review update',
    'Same identifier CD007491 and explicit publisher pub3-to-pub2 update. Searches change from 2016 to 2022; included trials increase from 16 (1,814 participants) to 20 (3,100).',
    'Link review lineage; apply a review-update counting policy.')
add(15, LINK, 'NBER working paper and published article',
    'Same Ganimian/Muralidharan/Walters team and ICDS staffing experiment. NBER explicitly lists the 2024 Journal of Political Economy article as the published version of paper 28780.',
    'Link as one evaluation; prefer the journal version.', sources=['https://www.nber.org/papers/w28780'])
add(16, REGISTRY, 'Likely trial registration and results article',
    'RIS identifies record 132884066 as TCTR20221219005. The registry abstract has planned interventions and outcomes but no results. Its distinctive title, tissue-adhesive/suture comparison, 2/6-week outcomes and cost endpoint match the 120-patient article. The accessible article does not explicitly state this registry number.',
    'Probable trial-family link; verify the registration-to-paper identity before consolidation. The registry record is not a second completed evaluation.', strength='probable', sources=['https://trialsearch.who.int/Trial2.aspx?TrialID=TCTR20221219005', 'https://pmc.ncbi.nlm.nih.gov/articles/PMC11315953/'])
add(17, LINK, 'medRxiv preprint and published article',
    'Same five authors, 11 Colombian cities, 10-year model, Cali saving USD4.95/person, 369 DALYs averted/100,000, and benefit-cost ratios 5.50/4.68. The article and preprint describe the same economic analysis.',
    'Link as one evaluation; prefer the published article.')
add(18, LINK, 'Conference abstract and revised full economic analysis',
    'Identical eight-author team and pooled GAIN/GAP70/INTEGERATE/5C model, Canadian payer perspective, six-month horizon and trial-specific scenarios. Conference INMB CAD1,117 (70.7% probability) changes to CAD599 (60.9%) in the article.',
    'Link as the same evaluation with revised results; use the final article rather than pooling estimates.')
add(19, LINK, 'Conference abstract and revised results article',
    '2023 DOI identifies a CUA meeting poster collection containing this MV140 analysis. Both abstracts have the same Canadian 1.25-year, four-state model versus prophylactic antibiotics. Base-case implementation and savings change between reports.',
    'Link the evaluation; retain final results and the exact poster citation.', sources=['https://pmc.ncbi.nlm.nih.gov/articles/PMC10266804/'])
add(20, DISTINCT, 'Separate Korean and US economic models',
    '2019 model uses Korean insurance claims and gives ICER USD9,707/QALY; the 2012 model uses US payer/Medicare costs and ROCKET-AF inputs, giving USD27,498/QALY. Different populations, data and costs.',
    'Retain both as separate evaluations.')
add(21, LINK, 'Chilean working paper and journal article',
    'RIS identifies the earlier report as Chilean Economics working paper 382 by Dominguez/Harrison/Atal, matching journal authors. Both have a 20-year Markov model, USD28,000 direct savings and USD102,000 including quality of life.',
    'Link as one evaluation; prefer the journal article.')
add(22, LINK, 'English and Italian reports of the same NICE appraisal',
    'Identical eight authors in Crossref. The 2013 publisher title is Italian, although the corpus uses an English translation. Abstracts describe the same ERG reanalysis and identical GBP2,500-6,200 and GBP19,000 ICERs.',
    'Link as translated/republished appraisal reporting; use one economic evaluation.')
add(23, LINK, 'Parallel reports of the same valve-replacement evaluation',
    'RIS Iranian-journal authors overlap the international article. Both describe 30 patients per arm at Imam-Khomeini hospital in 2000-2005, identical SF-36 scores 66.06/57.85 and 0.67 QALY difference. Savings are expressed in different currencies. Crossref also distinguishes 2009 online publication from the 2011 issue year.',
    'Link as one evaluation; verify language/citation details and apply a consistent year rule.')
add(24, LINK, 'Republication/abstract of an Argentine study in a Chilean journal',
    'Same Lenz/Vassallo team and identical Garrahan trial results. The 2012 publisher page explicitly describes regional republication of selected pediatric papers and cites the original 2010 Argentine journal report.',
    'Link as one evaluation; prefer the original full report.', sources=['https://scielo.cl/scielo.php?pid=S0370-41062012000100011&script=sci_arttext'])
add(25, UPDATE, 'Cochrane review update with no new included trial',
    'Same identifier CD001917; publisher new-version link from pub4 to pub3. Search moves from 2011 to 2015, but both abstracts retain the same single trial. A rerun search is still a new review edition, not a conference/full-paper pair.',
    'Link review lineage; latest-only policy could consolidate these editions.')
add(26, UPDATE, 'Cochrane review update',
    'Same identifier CD007293 and publisher pub4-to-pub3 update. Search dates move from December 2011 to June 2018 and certainty/reporting is updated.',
    'Link review lineage; apply a review-update counting policy.')
add(27, LINK, 'Probable secondary reproduction of the same Ginkgo economic analysis',
    'Both corpus abstracts report the same 1,201-patient meta-analysis, 22.3-month delay, EUR3,692-29,577 savings and EUR530.88 per additional success. Crossref identifies different author attribution (Rainer/Mucke/Schlaefke versus Klement) and different German-language publication venues. These support overlap but do not establish an authorized translation or exact republication.',
    'Probable same-evaluation link; inspect the German secondary article before treating it as a duplicate version.', strength='probable')
add(28, UPDATE, 'Cochrane review update',
    'Same CD004305 identifier and publisher pub5-to-pub4 update. Search moves from April 2012 to September 2016 and the cost-effectiveness synthesis is refreshed.',
    'Link review lineage; apply a review-update counting policy.')
add(29, LINK, 'Same Cochrane review reproduced in another journal',
    'Overlapping Gomes/Calanzani/Curiale/McCrone/Higginson/de Brito author team. Both abstracts use the same November 2012 search, seven-trial home-death pooled result and six-study inconclusive economic evidence. Later DOI is in Sao Paulo Medical Journal rather than a new Cochrane edition.',
    'Link as secondary reporting of one review; use the original Cochrane report.')
add(30, LINK, 'Conference abstract and full Li-Tho trial report',
    'Same four authors; 100 lobectomy patients, identical LigaSure versus stapler randomization, Pareto analysis and postoperative findings. Crossref identifies earlier B-006 conference abstract.',
    'Link as one evaluation; prefer the full article.')
add(31, LINK, 'Chilean working paper and journal article',
    'RIS identifies working paper 383 with the same four Dominguez/Harrison/Atal/Larrain authors. Both estimate Chilean organ-donation policies with identical six-extra-donor savings (USD1.9 million direct; USD15 million including quality of life) and four-donor break-even point.',
    'Link as one evaluation; prefer the journal article. This is separate from the transplant valuation in group 21.')
add(32, LINK, 'SSRN working paper and journal article',
    'Matching six-author team (order changes), food-tax demand/health uncertainty method, sugar-tax effects and distributional conclusions. Later article is the expanded publication of this analysis.',
    'Link as one evaluation; prefer the journal article.')
add(33, LINK, 'Conference abstract and revised full article',
    'Overlapping Coyle/Grunfeld team and identical 408-patient breast-cancer survivorship RCT, two-year societal analysis and QALYs 1.42/1.41. Costs and cost-effectiveness probability change slightly in the full report.',
    'Link the same evaluation; use final article estimates.')
add(34, LINK, 'Full article and later conference presentation',
    'Identical seven authors, Irish hospital RCT 361/376 participants, EUR807 saving, 0.064 fewer ADRs and the same cost-effectiveness probabilities. Conference publication occurs after the full article.',
    'Link as one evaluation; retain the full article. Do not assume the later year is the preferred report.')
add(35, UPDATE, 'Cochrane review update',
    'Same CD004242 identifier and publisher pub5-to-pub4 update. Search advances from 2011 to 2015; this is an updated synthesis of day-case versus inpatient cataract surgery.',
    'Link review lineage; apply a review-update counting policy.')
add(36, LINK, 'Conference abstract and full trial-based evaluation',
    'Overlapping Moojen/Peul/Vleggeert-Lankamp authors, same 159-patient Dutch trial, first-year societal costs, EUR3,030 healthcare difference and EUR2,762 societal difference. Utility tariff details differ between preliminary and final reports.',
    'Link the evaluation; prefer the full article and preserve the version-specific utility assumptions.')
add(37, LINK, 'Repeated conference reporting of the same transplant evaluation',
    'Overlapping Gheith/Halim/Al-Otaibi team; identical 201 recipients, 100/101 groups, doses 450/900 mg, six-month prophylaxis and one-year follow-up. Costs and leukopenia results match. However, the first record combines the 2017 full-paper abstract with a 2015 conference DOI; the matching full paper is 10.6002/ect.mesot2016.P34.',
    'Link the evaluation and flag mixed DOI/abstract/year provenance; identify the intended report before consolidation.', sources=['https://pubmed.ncbi.nlm.nih.gov/28260458/'])
add(38, LINK, 'Conference abstract and full RIVUR economic analysis',
    'Same Palmer/Seideman/Lotan team and decision-tree analysis. Both report costs USD3,092/2,932, 12.7 fewer infections per 100, and identical USD386, 32%, 63% and 48% sensitivity thresholds.',
    'Link as one evaluation; prefer the full article.')
add(39, LINK, 'Withdrawn article record and surviving publication of the same analysis',
    'Same eight authors and virtually identical abstracts: MISCAN-Colon, 76 screening strategies, 79% prevented colorectal-cancer deaths and the same recommended starting ages. Crossref marks DOI 10.1053/j.gastro.2017.12.011 as WITHDRAWN and records publisher withdrawal metadata; the other DOI identifies the complete 2018 article.',
    'Link as one evaluation and flag the withdrawn record; prefer 10.1053/j.gastro.2017.10.036.')
add(40, LINK, 'Conference abstract and full helmet-ventilation cost analysis',
    'Overlapping Kyeremanteng/Gagnon team and same Patel trial. Both report ICU/hospital savings USD2,527/3,103, 43.3% intubation reduction and identical annual projections.',
    'Link as one evaluation; prefer the full article.')
add(41, LINK, 'Conference abstract and revised full nivolumab evaluation',
    'Overlapping Raphael/Sun/Bjarnason/Sander/Naimark authors; same CheckMate-025 model, Canadian payer and Ontario costs. Annual discount rate changes from 5% to 3%, explaining why QALMs, costs and ICERs differ.',
    'Link the same evaluation; use final article estimates and note the revised assumptions.')
add(42, LINK, 'NBER working paper and published article',
    'Same Chan/Chen authors and Veterans Health Administration emergency-department design. NBER explicitly lists the 2026 American Economic Review article as the published version of paper 30608.',
    'Link as one evaluation; prefer the journal version.', sources=['https://www.nber.org/papers/w30608'])
add(43, LINK, 'NBER working paper and published article',
    'Same Zeltzer/Einav/Rashba/Balicer team and Israeli telemedicine study. NBER explicitly lists the 2024 journal article as the published version of paper 28978.',
    'Link as one evaluation; prefer the journal version.', sources=['https://www.nber.org/papers/w28978'])
add(44, LINK, 'Two preprint platforms reporting the same analysis',
    'Overlapping Dorn/Khailaie team and essentially identical German COVID-19 integrated model abstracts, including reproduction-number optimum 0.75. Crossref also links the medRxiv report to journal DOI 10.1007/s10198-022-01452-y, outside this title group.',
    'Link the preprint reports; check for the final journal version when selecting a canonical publication.')
add(45, DISTINCT, 'Unrelated dissertations with a generic title',
    'RIS identifies the 2016 Wisconsin dissertation as Ryne William Marksteiner, covering grant aid, faculty demographics and spousal substance-use spillovers. The other record describes Medicaid/Medicare dynamics and flexible work/study; Crossref attributes its DOI to Ferrell and titles it Three Essays in Public Economics. It is not the same thesis.',
    'Retain as separate records; verify the second dissertation DOI/year because its metadata is sparse.')
add(46, LINK, 'Working paper and conference report of the same evaluation',
    'RIS identifies a 2015 CERDI working paper by Yakhelef/Audibert/Pereira/Mons/Chabert; later DOI is a EUROSPINE abstract collection. Both abstracts describe 99 randomized patients with identical cost totals, QALY difference 0.01 and three perspective-specific ICERs.',
    'Link as one evaluation; locate the individual abstract within the proceedings citation.')
add(47, LINK, 'Two working-paper/preprint platforms for one NHS analysis',
    'Same Gaynor/Moreno-Serra/Propper authors and English 2006 competition reform analysis. NBER also identifies a 2013 journal version, whereas the 2013 included candidate uses an SSRN DOI.',
    'Link the working-paper records; do not label the SSRN record as the journal article.', sources=['https://www.nber.org/papers/w16164'])
add(48, LINK, 'Conference abstract and full LIGRO trial economic analysis',
    'Overlapping Hasselgren/Henriksson team, same 100-patient ALPPS/TSH trial and two-year Swedish economic analysis. Cost difference 12,662, QALY difference 0.1285 and ICER 93,186 match exactly.',
    'Link as one evaluation; prefer the full article.')
add(49, LINK, 'Conference abstract and full Hungarian boceprevir model',
    'Identical five-author team, payer model and trials. QALY gains 0.59/1.13 and both HUF ICERs are identical; a few clinical-event figures differ slightly in the final article.',
    'Link the same evaluation; prefer final article estimates.')
add(50, LINK, 'Two conference reports of the SARAH trial evaluation',
    'Overlapping Heine/Williams/Lamb team and same 17-trust English hand-exercise trial and 12-month economic evaluation. Later report changes intervention costing and ICER; this is repeated/revised trial reporting, not a second independent RCT. The full HTA is separately included as record 131941353, DOI 10.3310/hta19190, with the same 490 patients and trial design.',
    'Link the study family and existing HTA; retain report-specific economic estimates rather than treating both abstracts as independent studies.', sources=['https://www.journalslibrary.nihr.ac.uk/hta/HTA19190'])
add(51, LINK, 'Repeated conference reporting, with one incorrect DOI',
    'Both candidate abstracts describe the same 1,180-woman Swedish equivalence trial and identical EUR44/58 direct costs, EUR11 complication saving and EUR-9/-18 ICERs. RIS supplies the Sjostrom/Kopp-Kallner/Simeonova/Madestam/Gemzell-Danielsson team for the 2015 abstract. The 2016 candidate DOI actually identifies an unrelated conscientious-objection article. The full economic paper is separately included as record 131977666 (PLOS DOI 10.1371/journal.pone.0158645), with revised final estimates.',
    'Link by study evidence, flag the incorrect DOI, and include the existing full paper in the study family. Do not replace the conference DOI with the full-paper DOI without deciding which report this record represents.', sources=['https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0158645'])
add(52, LINK, 'Repeated conference reporting of the same droxidopa model',
    '2015 DOI is a poster collection and 2016 DOI is a specific Neurology conference poster. Both use NOH306 trial data and report exactly USD30,112 drug costs, USD14,574 savings, ICER USD47,001/QALY and identical fall-specific ICERs.',
    'Link as one evaluation; retain exact individual-poster provenance.')
add(53, LINK, 'Repeated conference reporting of the same RxEACH economic model',
    'Both DOIs identify conference collections, rather than individual full articles. Abstracts report the same Canadian 30-year model, 1.5% discounting, USD/CAD4.6-billion saving, 592,049 QALYs and nine-million avoided events. A full revised economic paper is separately included as record 131121257, DOI 10.1177/1715163519851822.',
    'Link both conference reports and the existing full article; use the final article for estimates.')
add(54, REGISTRY, 'Confirmed trial registration and results conference abstract',
    'RIS identifies TCTR20220720007 and the results abstract explicitly repeats that identifier. It reports 98 kidney recipients randomized 49/49. The registry only states planned outcomes. A separately included full article, record 132297933, repeats the same trial and exact infection counts and testing costs.',
    'Link the registry, abstract and full article; assess the registry as a registration record rather than a completed economic evaluation.', sources=['https://trialsearch.who.int/Trial2.aspx?TrialID=TCTR20220720007', 'https://doi.org/10.1016/j.ijid.2025.108311'])
add(55, 'mixed_generic_title', 'Six records cover five trials, including one related pair',
    'Crossref supplies specific titles despite the corpus title Public Health. Records describe MYB in Australia (132885538/132928004), DelpHi-MV in Germany (132885614), J-MINT in Japan (132885799), SMART4MD in Sweden/Spain (132889729) and AGELESS in Malaysia (132889811). Only the MYB pair is linked within this group: economic evaluation versus broader trial overview, with the same three-year intervention and cognitive effect 0.18. DelpHi-MV also links across groups to 132885613.',
    'Split the generic-title group into five study families. Link MYB companion reports, restore specific titles and preserve distinct economic analyses.')
add(56, DISTINCT, 'Different dementia trials sharing a conference section heading',
    'Crossref resolves actual titles. Record 132885613 is the German DelpHi-MV collaborative-care trial (428 economic-analysis participants; 36 months). Record 132889609 is UK NIDUS-Family (302 dyads; 12 months; ISRCTN11425138). They are unrelated evaluations.',
    'Retain both; restore individual titles. Link DelpHi-MV to the subgroup report in group 55.')
add(57, LINK, 'Probable revised/repeated conference analysis',
    'Both abstracts use 2010-2017 Medicare claims, the same ten BPCI episode groups and factorial-style comparison with identical non-BPCI count 1,268,933. Participating physician counts and effect estimates change materially, so exact duplication is not established. Public conference programmes show the same presentation topic in 2021/2022. A related final paper is included as 131377387 but extends claims to 2018 and reports medical/surgical effects separately.',
    'Link as a probable study family, retain version-specific estimates, and verify the extent of reanalysis before collapsing publications.', strength='probable', sources=['https://jamanetwork.com/journals/jama-health-forum/fullarticle/2799960', 'https://higherlogicdownload.s3.amazonaws.com/SGIM/bb0affd7-3de8-4514-b673-feab46845626/UploadedImages/SGIM22/Poster_Session_2.pdf'])

assert set(assessments) == set(groups) == set(range(1, 58))
assert len(rows) == 118
assert sum(len(v) - 1 for v in groups.values()) == 61

def metadata(row):
    p = OUT / (row['record_id'] + '_crossref.json')
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}

def doi_link(doi):
    return 'https://doi.org/' + doi if doi not in ('', 'NA') else ''

pair_rows = []
for group, members in sorted(groups.items()):
    assessment = assessments[group]
    for a, b in itertools.combinations(members, 2):
        result = dict(assessment)
        if group == 55:
            myb = {a['record_id'], b['record_id']} == {'132885538', '132928004'}
            result.update(category=LINK if myb else DISTINCT,
                relationship='Same MYB trial; economic report and companion overview' if myb else 'Different dementia studies under a generic heading',
                evidence_strength='strong')
        pair_rows.append({**result, 'record_id_a': a['record_id'], 'record_id_b': b['record_id'],
            'doi_a': a['doi'], 'doi_b': b['doi'], 'year_a': a['year'], 'year_b': b['year']})

extra_links = [
    dict(record_id_a='132885614', record_id_b='132885613', category=LINK, evidence_strength='strong',
         relationship='DelpHi-MV overall and living-arrangement subgroup reports',
         evidence='Same author team, 428 participants, 36-month follow-up and identical subgroup QALY gains 0.224/0.079 and costs -3815/+3283. These are companion analyses; not exact duplicate abstracts.'),
    dict(record_id_a='132866653', record_id_b='131977666', category=LINK, evidence_strength='strong',
         relationship='Abortion conference abstract and separately included full economic article',
         evidence='Same Sjostrom author team and 1180-woman Swedish equivalence-trial evaluation; final estimates revised.'),
    dict(record_id_a='132877525', record_id_b='131121257', category=LINK, evidence_strength='strong',
         relationship='RxEACH conference evaluation and separately included full article',
         evidence='Same trial, 30-year economic model, 1.5% discounting and Canadian population extrapolation; final figures revised.'),
    dict(record_id_a='132891161', record_id_b='132297933', category=LINK, evidence_strength='strong',
         relationship='CMV trial results abstract and separately included full article',
         evidence='Same TCTR20220720007 trial, 98 participants (49/49), 13 versus 12 infections and costs USD2320 versus USD10014.'),
    dict(record_id_a='132914275', record_id_b='131377387', category=LINK, evidence_strength='probable',
         relationship='BPCI conference analysis and related final journal analysis',
         evidence='Same PGP/hospital BPCI comparison and outcome framework; journal analysis expands dates to 2018 and changes sample definitions and estimates. Verify version history before merging.'),
    dict(record_id_a='132865649', record_id_b='131941353', category=LINK, evidence_strength='strong',
         relationship='SARAH conference report and separately included full HTA',
         evidence='Same Heine/Williams/Lamb team, 490 participants (244/246), 17 English trusts, hand-exercise comparison and 12-month economic evaluation. HTA reports additional economic analyses and different imputed ICERs.'),
]

# Original "61" is excess records, not number of pairwise edges or removals.
extra_counts = Counter()
for group, members in groups.items():
    if group == 55:
        extra_counts['linked_reports_strong'] += 1
        extra_counts[DISTINCT] += 4
    else:
        result = assessments[group]
        key = result['category']
        if key in (LINK, REGISTRY):
            key += '_' + result['evidence_strength']
        extra_counts[key] += len(members) - 1
assert sum(extra_counts.values()) == 61
assert len(pair_rows) == 71

record_fields = ['candidate_group', 'record_id', 'year', 'title', 'doi', 'publication_type', 'journal', 'url']
record_rows = []
for row in rows:
    data = metadata(row)
    record_rows.append({**{k: row[k] for k in record_fields},
        'crossref_title': ' | '.join(data.get('title', [])),
        'crossref_container': ' | '.join(data.get('container-title', [])),
        'crossref_authors': '; '.join(' '.join([a.get('given', ''), a.get('family', '')]).strip() for a in data.get('author', [])),
        'crossref_updates': json.dumps(data.get('update-to', []), ensure_ascii=False),
        'crossref_relations': json.dumps(data.get('relation', {}), ensure_ascii=False),
        'crossref_source': 'https://api.crossref.org/works/' + quote(row['doi'], safe='') if data else '',
        'metadata_retrieved': bool(data)})

def write_csv(name, values):
    fields = list(dict.fromkeys(k for row in values for k in row))
    with (OUT / name).open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in values:
            writer.writerow({k: ' | '.join(v) if isinstance(v, list) else v for k, v in row.items()})

write_csv('group_decisions.csv', list(assessments.values()))
write_csv('pair_decisions.csv', pair_rows)
write_csv('additional_links.csv', extra_links)
write_csv('record_metadata.csv', record_rows)
summary = dict(date='2026-10-14', original_groups=57, original_records=118, original_excess_records=61,
    pairwise_comparisons=71, crossref_records_retrieved=sum(r['metadata_retrieved'] for r in record_rows),
    original_excess_record_breakdown=dict(extra_counts), additional_links=6,
    additional_included_records=5, total_records_examined=123, master_changed=False,
    caveat='Linked study reporting is not automatically a duplicate economic evaluation. Counts are analyst assessments, not an independent dual-review adjudication.')
(OUT / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')

lines = ['# Close check of potential linked publications', '', 'Reviewed 14 October 2026.', '',
    '## Scope and method', '',
    'All 118 included records in the 57 original title-match groups were assessed. This creates 71 within-group pairwise comparisons (the six-record Public Health group creates 15 pairs). The number 61 is the number of records beyond one per title group, not a list of 61 uniquely identified duplicates.', '',
    'Evidence compared: complete corpus abstracts, study/trial identifiers, sample sizes, countries, interventions, model horizons, numerical results, author lists and publisher-deposited Crossref titles/types/relations/updates. Crossref metadata was retrieved for ' + str(summary['crossref_records_retrieved']) + ' records. RIS was checked for records without DOI; publisher/PubMed/NBER sources were inspected for ambiguities. Both giant-cell tumour full texts were retrieved as Europe PMC XML. Five additional included full articles/HTAs were examined when traced from the candidate reports.', '',
    'A strong link means explicit publisher/version/trial evidence or multiple distinctive matching study facts supported by abstracts and available author metadata. It does not mean every full text was inspected, or that two reports have identical economic analyses. Probable links remain flagged. One author/protocol overlap with incompatible reported cohorts is unresolved. This was one analyst assessment, not independent duplicate human review.', '',
    '## Reconciliation of the original 61', '', '| Assessment | Excess records |', '|---|---:|']
labels = {'linked_reports_strong':'Strong evidence of linked reporting of the same evaluation/study',
    'linked_reports_probable':'Probable linked reporting; do not automatically merge',
    'registry_and_results_strong':'Confirmed registry/results relationship',
    'registry_and_results_probable':'Probable registry/results relationship',
    UPDATE:'Updated reviews/HTAs; counting policy required',
    DISTINCT:'Title matches that do not establish one evaluation',
    'unresolved_overlap':'Shared trial protocol but conflicting cohorts; unresolved'}
for key, value in sorted(extra_counts.items()):
    lines.append(f'| {labels[key]} | {value} |')
lines += ['| **Total** | **61** |', '',
    'These are counts against the original title-group baseline, not a recommended removal total. In particular, the five excess Public Health records resolve to one related MYB report plus four different-study records. Links to newly traced full articles and the cross-group DelpHi-MV link are reported separately below.', '',
    '## Material findings', '',
    '- The 2019 giant-cell tumour paper (131733131) is retracted. Full texts share author/institution/protocol with the 2022 paper but report conflicting sample sizes and recruitment periods. Treat this relationship as unresolved, not as a proven independent cohort or automatic duplicate.',
    '- The 2017 cystic-fibrosis screening record (132530207) is a publisher-marked withdrawn article record. It has the same authors and analysis as the surviving 2018 article (132054884). Withdrawal of this record does not establish that the surviving economic analysis is retracted.',
    '- Eight pairs are review/HTA editions. Some add substantial new evidence; a same-review identifier does not make an update an accidental bibliographic duplicate.',
    '- Two earlier records are trial registrations, with planned outcomes rather than completed cost-effectiveness findings. One registry link is explicit in the results report; the other is probable.',
    '- Generic conference headings hide actual study titles. Public Health includes five trial families, and Dementia Care Research and Psychosocial Factors matches unrelated DelpHi-MV and NIDUS-Family studies.',
    '- Three records need report-level identifier/provenance repair: 131462474 mixes the BRCA1 full-article abstract with a conference DOI; 132018093 mixes a 2017 valganciclovir full-article abstract with a 2015 conference DOI; 132866626 carries a DOI for an unrelated conscientious-objection article. Do not silently replace conference identifiers with full-article identifiers.', '',
    '## Links beyond the original title groups', '',
    'The close check found one relationship between existing title groups and five separately included full articles/HTAs whose titles differed enough to evade the original match. These make the original 61 an incomplete candidate screen, not a validated total of remaining duplicate studies.', '']
for link in extra_links:
    lines += [f"- **{link['record_id_a']} ↔ {link['record_id_b']}** ({link['evidence_strength']}): {link['relationship']}. {link['evidence']}"]
lines += ['', '## Suggested methods wording', '',
    '> A post hoc publication-linkage check assessed 57 groups of matching normalised titles, containing 118 included records. The 61 records beyond one per title group comprised 40 strongly or probably linked study reports, two trial-registration/results relationships, eight review or assessment updates, ten records representing distinct evaluations, and one unresolved overlapping-trial relationship. Additional links were identified where titles differed. Linked reporting was distinguished from duplicate economic analyses; no records were removed by this audit.', '',
    'The 40 linked reports comprise 38 with strong evidence and two probable links. The two registry/results relationships comprise one confirmed and one probable link. Avoid saying that all 61 are preprint/article or abstract/full-paper duplicates.', '',
    '## Group-by-group decisions', '',
    '| Group | Topic | Decision | Evidence strength |', '|---:|---|---|---|']
for group, assessment in sorted(assessments.items()):
    title = groups[group][0]['title'].replace('|', '/')
    lines.append(f"| [{group}](#group-{group}) | {title} | {assessment['relationship']} | {assessment['evidence_strength']} |")
for group, assessment in sorted(assessments.items()):
    lines += ['', f'<a id="group-{group}"></a>', f"### {group}. {groups[group][0]['title']}", '',
        f"**Decision:** {assessment['relationship']}. **Evidence strength:** {assessment['evidence_strength']}.", '',
        assessment['evidence'], '', '**Suggested handling:** ' + assessment['suggested_handling'], '', 'Records and source metadata:', '']
    for row in groups[group]:
        data = metadata(row)
        link = doi_link(row['doi']) or row['url']
        citation = f"- **{row['record_id']}**, recorded year {row['year']}: {row['title']}"
        if link not in ('', 'NA'):
            citation += f'; [recorded publication link]({link})'
        lines.append(citation + '.')
        if data:
            authors = '; '.join(' '.join([a.get('given',''), a.get('family','')]).strip() for a in data.get('author', []))
            lines.append('  - Publisher title: ' + ' | '.join(data.get('title', [])) + '. Venue: ' + ' | '.join(data.get('container-title', [])) + '. Authors: ' + (authors or 'not deposited for this collection') + '.')
            lines.append('  - [Crossref publisher metadata](https://api.crossref.org/works/' + quote(row['doi'], safe='') + '); cached file `' + row['record_id'] + '_crossref.json`.')
        else:
            lines.append('  - No cached Crossref record; decision uses corpus abstract, available RIS metadata and supplementary sources below.')
    for source in assessment['additional_sources']:
        lines.append(f'- [Additional source]({source})')
    if group == 55:
        lines += ['', 'Within-group pair decisions: only 132885538 ↔ 132928004 is linked (MYB companion reports); the other 14 combinations describe different trial families. DelpHi-MV record 132885614 links to 132885613 in group 56.']

lines += ['', '## Artifacts and limits', '',
    '- `group_decisions.csv`: all 57 group decisions and reasons.',
    '- `pair_decisions.csv`: all 71 within-group pairwise relationships.',
    '- `additional_links.csv`: six extra relationships, five to additional included full reports.',
    '- `record_metadata.csv`: recorded and publisher-deposited titles, authors and metadata links.',
    '- `summary.json`: reconciled counts and scope.',
    '- `ris_missing_doi_metadata.json`: original RIS metadata used for no-DOI and registry records.',
    '- `additional_included_reports.json`: five additional included records examined.',
    '- `PMC6357891.xml` / `PMC9254448.xml`: full texts for the unresolved giant-cell tumour pair.', '',
    'The master datasets, eligibility flags, website counts and manuscript were not changed. Before implementing exclusions, choose the unit of counting (publication, economic evaluation, underlying clinical study or review edition), resolve the flagged probable/unresolved cases, and repair mixed report metadata. A common clinical trial can support multiple legitimate economic analyses. This audit examined the named candidate groups and traced reports; it is not a whole-corpus fuzzy-match audit.', '']
(OUT / 'REPORT.md').write_text('\n'.join(lines), encoding='utf-8')
print(json.dumps(summary, indent=2))
