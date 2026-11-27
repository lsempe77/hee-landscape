# Wellcome priority themes dashboard — v3 implementation specification

**Input:** `wellcome_priority_themes-v2.html`, underlying HEE publication and funding data, and previously agreed Wellcome priority specifications and GBD mapping documentation.

**Output:** `wellcome_priority_themes-v3.html` and a concise implementation and validation summary. Preserve v2 and all source data unchanged.

## 1. Objective and requirement hierarchy

Simplify the dashboard into a coherent analytical narrative while improving methodological consistency. Present an indicative characterisation of Wellcome's specified research priorities using existing GBD classifications, not a comprehensive assessment of Wellcome's strategic funding alignment.

Sections 2–3 define mandatory analytical requirements; section 4 defines the required page structure; section 5 provides design preferences; sections 6–7 define technical and acceptance requirements. Analytical validity takes precedence over visual preferences. Do not invent missing data or resolve substantive methodological ambiguity without approval.

## 2. Analytical scope and mapping (mandatory)

### 2.1 Establish eligibility before analysing funding

- Restrict the displayed thematic analysis to the previously specified Wellcome priority areas within Infectious Diseases and Mental Health, not the entirety of either overarching theme.
- Retrieve the exact previously agreed priority specifications and GBD matching criteria from the project documentation. Establish the eligible GBD code sets before calculating or inspecting funding results for the revised mapping. Apply the same eligibility criteria regardless of funding status.
- Do not broaden the scope to adjacent diseases, research areas or GBD codes to capture additional Wellcome-funded publications. Do not use the presence or absence of Wellcome funding to determine thematic eligibility.
- Document a crosswalk of specified priority area, eligible GBD code(s), rationale, source and classification limitations. Distinguish confirmed matches from ambiguous or overly broad categories and priorities not representable by the available codes. If an ambiguous category requires substantive judgement, flag it for review rather than automatically including it or presenting an unapproved mapping as final. If the agreed specifications cannot be located, do not infer replacements.
- Exclude Climate & Health from all displayed thematic analyses and associated aggregates because its keyword-based identification method is not directly comparable with the GBD-based approach. Preserve original data and code in the source materials; it need not remain in the v3 interface.
- Exclude publications identified solely through supplementary searches or manual screening. Retain publications independently meeting the approved GBD criteria, including those manually verified. Verification of existing GBD matches is distinct from expanding eligibility through supplementary identification.
- Retain one GBD-based analytical view only. Remove the expanded-view toggle, supplementary inclusion markers and obsolete interface elements.
- A consistent matching method improves comparability but does not guarantee equal mapping coverage or accuracy across themes. Document differences in scope and granularity; do not claim comprehensive coverage.

### 2.2 Data prerequisites and statistical definitions

Inspect the existing HTML and available source datasets before implementation. The HTML may contain precomputed aggregates rather than all publication-level records needed for recalculation. Do not estimate intersections, funder counts or rankings from visual summaries.

Use stable, deduplicated publication identifiers and the existing funding identification rules. The unit is a publication, not a grant, funding amount or funder mention.

Define:

- H: all unique eligible HEE publications in the selected dataset version.
- I and M: unique publications meeting the approved Infectious Diseases and Mental Health GBD criteria, respectively.
- T = I ∪ M: unique publications captured by either thematic mapping.
- F: publications with at least one identified funder under the existing funding identification rules.
- W: publications with Wellcome identified as a funder, including co-funded publications. W must be a subset of F; investigate any inconsistency rather than silently changing source data.

For T and each individual theme S, calculate:

| Measure | Count | Percentage denominator |
|---|---|---|
| Mapped publications | \|S\| | \|H\| where shown |
| Funder identified | \|S ∩ F\| | \|S\| |
| Wellcome-funded | \|S ∩ W\| | \|S ∩ F\| |
| Wellcome-funded segment | \|S ∩ W\| | \|S\| |
| Other reported funders only | \|S ∩ (F \\ W)\| | \|S\| |
| Funder not identified | \|S \\ F\| | \|S\| |

Use the same definitions throughout. Label percentages with explicit denominators, especially where the headline Wellcome percentage differs from its share in the stacked bar. Handle zero denominators as not applicable, not as an observed zero percentage.

For the entire HEE evidence base, calculate \|W\|, \|W ∩ T\| and \|W \\ T\|; both thematic coverage percentages use \|W\| as denominator. Recalculate theme-specific funder rankings, country income group distributions, subarea counts and all associated lists from the approved scope. Preserve existing country and funder classification rules and document the unit of analysis for multi-country studies and multi-funder publications. Do not infer funding absence from missing funder information.

The full-map Wellcome count and publication-year trend should not change solely because the thematic scope changes. Document the dataset version and any genuine source-data updates separately.

If required source data or the approved crosswalk are unavailable, identify the specific missing inputs. Implement independently supportable layout changes if feasible, but do not present obsolete or estimated aggregates as final revised results.

## 3. Donor-facing interpretation (mandatory)

Use neutral terminology that distinguishes thematic alignment from coverage of the proxy mapping. Avoid “outside Wellcome's priority themes”, “non-priority publications”, or statements implying a funding allocation or strategic performance assessment.

**Introductory text**

> This analysis uses existing GBD classifications as a proxy for alignment with Wellcome's specified research priorities within Infectious Diseases and Mental Health. The findings provide an indicative rather than comprehensive characterisation of thematic alignment.

**Interpretive note adjacent to the full-map thematic coverage visual**

> The thematic analysis provides an indicative characterisation of the HEE evidence base using existing GBD classifications as a proxy for Wellcome's specified research priorities. Differences in the scope and granularity of these classification systems limit the extent to which thematic alignment can be captured.
>
> Wellcome-funded publications not captured by this mapping may nevertheless contribute to Wellcome's research priorities, including through cross-cutting research and areas not represented by the selected GBD categories. The results should therefore not be interpreted as a comprehensive assessment of Wellcome's research portfolio or its alignment with strategic priorities.

In the detailed methodology, explain that non-matching may reflect GBD classification limitations, cross-cutting research, the exclusion of Climate & Health, supplementary-only identification excluded from this analysis, or research in other areas. The reasons have not been systematically assessed; do not attribute all non-matches to classification limitations or infer that they lack thematic relevance.

## 4. Required page structure

### Section A — Evidence coverage and funding across mapped priority areas

Remove the separate introductory hero, “The three themes at a glance” section, individual theme cards and miniature thematic composition bars. Replace them with one integrated overview:

1. Three aligned headline statistics: publications captured by the thematic mapping, funder identified and Wellcome-funded. Show counts and the headline percentage denominators defined in section 2.
2. One combined horizontal stacked bar showing Wellcome-funded, other reported funders only and funder not identified. Use the mapped total as the denominator for all three segments.
3. Immediately below, two theme rows using the same funding categories and legend. Each row contains the theme name, total publications, absolute-scale stacked bar, funder-identified count and percentage, Wellcome-funded count and percentage, and an “Explore theme” action activating the corresponding detail tab and scrolling to it.

Use a common absolute bar scale for the two theme rows; do not normalise each independently. Add: “Publications may be captured under more than one theme. Combined figures count unique publications.”

### Section B — Explore individual themes

Retain two tabs only: Infectious Diseases and Mental Health. For the selected theme, show:

- A concise description of the specific Wellcome priority areas represented by the approved GBD mapping.
- Funding landscape: existing funder ranking visualisation, with Wellcome highlighted and its rank shown, including ties under the existing ranking convention. Avoid repeating the overview counts unnecessarily. Explain that publications may report multiple funders and rankings reflect publication counts, not funding amounts.
- Country income group comparison: retain the existing analytical definitions, relevant comparison subsets, counts and percentages, recalculated for the revised scope. Clearly label units and denominators; use consistent income group colours.
- Disease/subarea breakdown: retain eligible categories, total and Wellcome-funded publication counts, proportional bars and existing expandable publication lists where supported. Do not include ineligible broader categories. If subareas overlap, make this clear rather than implying their counts sum to the theme total.
- Collapsible definition and matching details: approved priorities, exact GBD codes, matching rationale and limitations. Link to the full methodology rather than duplicating long explanations.

### Section C — Wellcome-funded evidence across the HEE map

This section covers the full HEE map, independently of thematic scope.

- Display the total number of publications with Wellcome identified as a funder as the principal headline statistic.
- Provide a visually secondary stacked bar titled “Coverage of the GBD-based thematic mapping”, with counts and percentages for “Captured by thematic mapping” and “Not captured by thematic mapping”. Use dark purple and a neutral grey/lavender, respectively. Do not present these categories as a performance measure.
- Place the interpretive note in section 3 directly below the coverage bar. Retain access to the existing publication lists, updated for the revised mapping; label the unmatched list “Other Wellcome-funded HEE publications”. Where appropriate, use “Wellcome-funded publications not captured by the GBD-based priority mapping”.
- Retain the annual/cumulative full-map Wellcome publication trend, using **line charts for both views; do not use a bar chart**. Address Lucas's feedback on visually exaggerated annual fluctuations by revising the axis and chart proportions, as follows:
  - Annual view: use a fixed Y-axis domain of 0–100, with major tick labels and gridlines at 0, 30, 60 and 90 (100 is the upper plot boundary, not an additional regular tick). Do not automatically rescale. If any actual annual count exceeds 100, increase the ceiling to prevent clipping while retaining 30-publication tick intervals, and document the change. Apply the same scale across comparable annual views and exports. Retain exact counts in tooltips; the wider scale reduces the visual prominence of fluctuations without changing the observations.
  - Use a wide, relatively shallow plot (approximately 3:1 plot width to height on desktop, adapting responsively on smaller screens) to reduce visually exaggerated slopes. Use a clean purple line with subtle point markers, light horizontal gridlines and exact-count tooltips. Connect observed annual values with straight segments; do not smooth or interpolate the data.
  - Cumulative view: retain a line chart with its own fixed, zero-based, rounded Y-axis appropriate to the cumulative maximum. Do not reuse the annual axis range.
  - Preserve the actual annual counts, full publication-year range, annual/cumulative toggle, tooltips and partial-year indicator and explanation. Visually distinguish the incomplete final year (e.g., a dashed final segment and hollow point); do not treat it as evidence of decline.
  - Inspect the rendered annual and cumulative charts at desktop and mobile sizes. The objective is a less visually volatile but still accurate presentation, not suppression of genuine variation. Record the chosen axis limits and chart proportions in the implementation report.

### Methodology and limitations

At the bottom, retain a collapsible methodology section accessible from an introductory “About the thematic mapping” link. Include the approved crosswalk and source, matching limitations, scope exclusions (including Climate & Health and supplementary-only records), manual verification distinction, deduplication, funding identification and missingness, multiple funders, income groups, publication-year coverage, and limits of publication counts as indicators of funding activity. Use concise contextual notes beside relevant visuals rather than repeating this full explanation.

## 5. Design preferences

- Retain existing typography and purple-based identity. Use dark purple for identified Wellcome funding, light purple for other reported funders only and neutral grey for funder not identified, with context-specific legends.
- Use whitespace and alignment rather than multiple decorative cards, badges or repeated legends. Avoid redundant summary visuals.
- Preserve clear numbers and denominator labels; use shared scales for like-for-like comparisons, readable contrast, keyboard access and responsive layout. Small stacked segments must remain identifiable via labels/tooltips without artificially increasing their widths.
- Use line charts for both annual and cumulative publication trends (mandatory). A wider, shallower plot and restrained styling are design preferences; the specified fixed annual axis, separate cumulative axis and accurate data are requirements.

Schematic hierarchy (not data):

```text
Wellcome priority themes
  Short introduction · About the thematic mapping

Evidence coverage and funding
  [Mapped publications] [Funder identified] [Wellcome-funded]
  Combined funding composition ━━━━━━━━━━━━━━━━━━━
  Infectious Diseases          ━━━━━━━━━━━━━━━  Explore
  Mental Health                ━━━━━━━          Explore
  Shared legend · Overlap note

Explore individual themes
  [Infectious Diseases] [Mental Health]
  Specified priority areas
  Funding landscape / ranked funders
  Country income group comparison
  Disease and subarea breakdown
  ▸ Definition and matching criteria

Wellcome-funded evidence across the HEE map
  Total Wellcome-funded publications
  Coverage of the GBD-based thematic mapping
  ━━━━━━━━━━━ Captured | Not captured ━━━━━━━━━━━
  Interpretive note
  ▸ Other Wellcome-funded HEE publications
  Publication-year trend [Annual | Cumulative]

▸ Methodology and limitations
```

## 6. Technical implementation

Preserve retained theme navigation, tooltips, expandable lists and pop-ups, annual/cumulative toggle, partial-year indicator, PNG download, embedding, responsive behaviour and print/export. Remove obsolete handlers, references and CSS as appropriate. Ensure hidden/excluded Climate & Health and expanded-view content cannot reappear in print or export. The existing print stylesheet deserves particular attention because it explicitly reveals hidden theme panels.

Keep original source files unchanged. Preserve excluded data in those sources or a documented separate source, not necessarily in the v3 HTML. Follow the existing packaging approach; do not introduce new network dependencies. If offline operation is required, identify and address existing external assets separately rather than silently claiming full offline support.

## 7. Acceptance criteria and deliverables

- [ ] Approved, documented funding-independent crosswalk; only the two specified GBD-based themes displayed; supplementary-only publications excluded; verified valid matches retained.
- [ ] Publication-level deduplication and all count identities verified: S funding segments sum to S; captured plus not captured Wellcome publications sum to W; W is a subset of F. Overlaps and missingness handled correctly.
- [ ] All recalculated counts, percentages, rankings and lists reconcile with source data; clear denominators and analytical units; full-map funding totals and trend unchanged unless a documented source update occurred.
- [ ] Neutral terminology and donor-facing caveats are visible; no implication that unmatched publications are non-priority or that publication counts measure expenditure.
- [ ] Three-section layout implemented without duplicate summaries; annual and cumulative line charts (no bars), fixed annual scale of 0–100 with major ticks every 30 (unless a higher ceiling is required to prevent clipping), and separate cumulative scaling; chart proportions reviewed and partial year retained.
- [ ] Theme switching, links, tooltips, lists, trend toggle, responsive layout, keyboard interaction, embedding, PNG export and print checked; no excluded panels or obsolete labels visible.
- [ ] Original files preserved; no fabricated counts or unsupported methodological decisions.

Deliver v3 HTML and a short implementation report specifying source files and dataset version, the approved crosswalk and exclusions, recalculated totals and reconciliation checks, chosen annual/cumulative axis limits and chart proportions, technical tests actually performed and their outcomes, and unresolved data or methodological requirements. Distinguish verified results from untested functionality. If final results are blocked, label the output as provisional and explain what is needed to complete it.
