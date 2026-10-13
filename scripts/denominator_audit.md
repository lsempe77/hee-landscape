# Country and study–country denominator audit

Rebuilt on 13 October 2026 from the current eligible `hee_analysis_master_v2_1.csv`
and `hee_geo_long_v2_1.csv`, website country data, GBD 2023 national all-cause
export and Natural Earth medium-scale geography. A pair is a unique eligible
record ID × ISO3; each multi-country study contributes once per named country.

| Country count | Inclusion rule |
|---:|---|
| 133 | At least 5 studies with known open-access status, full geography |
| 138 | At least 5 eligible studies, full geography |
| 152 | Website countries with positive DALYs and at least 1 study |
| 153 | Website countries with at least 1 study |
| 154 | Website countries with positive DALYs, including zero-study countries |
| 155 | Full website country list |
| 187 | Countries/territories named in eligible study geography |
| 204 | Locations in the national GBD 2023 burden export |

The smaller website burden analysis has **31,471 pairs**. The full website has
**31,616 pairs**, including Hong Kong's 145 pairs without a burden denominator.
The full geography has **31,775 pairs**. The national GBD deficit analysis has
**31,627 pairs** across its 204-location burden denominator: Hong Kong (145),
Cayman Islands (1), French Guiana (1) and Guadeloupe (1) are excluded. Thus
31,471 and 31,627 are both valid; their country sets differ. The earlier suggestion
that 31,627 was stale was incorrect. The world-map caption's 31,774 was corrected
to 31,775; its existing embedded image already displayed 31,775.

The reach chart now uses each year's income classification (in force on 1 January)
for both numerator and denominator. A country is reached if any eligible study
has named it by that year, even if the country has since changed income group.
Taiwan uses the recorded high-income override. Solid lines use the website list;
dashed lines use Natural Earth `Sovereign country`/`Country` entities without a
population floor. Unclassified country-years are excluded. In 2025, these are
**154 classified website countries (2 unreached)** and **197 classified/overridden
Natural Earth entities (21 unreached)**. The geography restriction means 197 is
not the count of all World Bank economies. Denominators change by year, so reach
within a group can fall when its membership changes. 2026 is omitted.

The inequality summary is country-level and uses July 2026 country groups,
consistent with the country views. Its 106 LMIC countries contribute 8,732 pairs.
The five largest study producers (CHN, IND, BRA, THA, ZAF) have 57.8% of evidence
and 43.3% of burden. The five largest-burden countries (IND, CHN, NGA, IDN, PAK)
have 48.1% of evidence and 51.7% of burden. The first 41 countries in ascending
studies-per-DALY order that cross half the burden have 1,455 pairs, 53.9% of
burden and 16.7% of evidence. The plotted marker is at these actual coordinates,
not at 50% burden. Gini is 0.49.

## Rebuild and outputs

```powershell
& 'C:/Program Files/R/R-4.5.0/bin/Rscript.exe' scripts/export_country_audit_sources.R C:/Users/Sawa/hsf/projects/hee
python -B scripts/build_denominator_audit.py
python -B -m unittest discover -s tests -p test_denominator_audit.py
```

The R helper exports the source geography and national GBD rows into the ignored
raw-data directory. It needs countrycode, sf and rnaturalearth. The Python builder
checks unique pairs and agreement with website totals, preserves existing figure
updates, and writes replacement SVG/PNG figures, annual reach counts and
`docs/data/denominator_audit.json` with the source-master hash and country sets.
Captions in content.json, figure_copy.json and figure_updates.json agree.
Historical v1–v3 site snapshots and original WebP images are retained; the current
gallery resolves to the new SVG figures through figure_updates.json.
