# Rubric audit — 6 October 2026

Authority: Data Visualisation 2 Specifications_v1.1.pdf, pages 4–6, plus the TA's advice to exceed three map idioms and ten visualisations. This is an evidence audit, not a promised grade.

## Current revision

Sixteen panels now answer different questions about Australian media. Four map idioms replace the former three views of the same state score. Each annotation explains a comparison, implication or limitation rather than merely repeating a highlighted value.

Final-feedback pass: the horizon has a discrete signed-band key and visible baseline years; the audio network can trace one format with three percentage readouts; geographic maps have state labels and an ACT leader; the cartogram has a same-scale one-million-residents reference circle. Live resizing preserves all five control types instead of clipping desktop legends on mobile. Headings distinguish evidence from stronger claims the surveys cannot establish.

Abbas confirmed on 6 October: full name Abbas Quettawala; Wednesday 10am studio; TA Bruno; GitHub account AbbasQuettawala, with no assignment repository/Pages site yet; hand-drawn sketch unfinished. The public author credit is complete. Student ID is confined to the private email/submission.

| Criterion | Weight | Evidence and remaining work |
| --- | --- | --- |
| Sketch | 2% | Updated guide follows four chapters. The student must supply an actual hand-drawn A4 sketch, discuss it with the tutor, scan it and publish its PDF. A digital sketch earns zero. |
| Idioms and complexity | 8% | Sixteen Vega-Lite panels, four map idioms, readable JSON, documented data transformations and purpose for every chart. The TA must judge effectiveness and classification. |
| Layout, colour, figure–ground | 3% | Existing vertical editorial layout retained; sequential index colours, proportional symbol areas, linked state highlighting and city views prioritise evidence over decoration. |
| Typography | 2% | Existing hierarchy retained; labels and source notes must pass laptop/mobile browser review. |
| Storytelling, annotations, grammar and metadata | 5% | Seven on-diagram Vega-Lite callouts plus 16 interpretive paragraphs, seven numbered source footnotes, reference periods, respondent bases, transformation notes, asset credits and AI acknowledgement. Full public author credit is present; private submission identity is filled in. |
| Domain / who / what / why / how | 2% | Revised draft explains consumer focus, supporting infrastructure and restrictions on causal interpretation. Complete public URLs and final published-site/sketch screenshots. |
| Interview | 3% | Explain the data, transformations, limitations, marks/channels and choices from Weeks 1–11. Review the available Weeks 1–11 materials before the interview. |

## Counting without padding

- There are 16 rendered chart panels. Treat the two heatmaps as one under the similar-charts rule: 15.
- Exclude the hero waffle from a conservative substantive count: 14.
- A stricter grouping of the news dot plot with the paired comparison, and the slopegraph with the profile family, still leaves 12. These are a safety margin, not an authoritative interpretation of the rubric.
- Do not count city views, age selections, horizon rows, maps' base layers, or individual heatmap cells as additional visualisations.
- Candidate advanced idioms include horizon, heatmap, parallel coordinates, benchmark/bullet, bump, slopegraph, bipartite network, choropleth, Dorling cartogram, proportional-symbol map and dot map. The target is at least eight accepted advanced idioms.
- Ask the TA to confirm the four-map classification and supporting infrastructure's relevance before final polishing.

## Chart-to-question inventory

| Panel | Question | Data / analytical purpose |
| --- | --- | --- |
| Waffle | How widespread is online video? | ACMA QF7, 2025; six-month reach, a single valid whole. |
| Horizon | Which formats changed most? | QF4, percentage-point changes from each first measured wave; compact trend comparison. |
| Connected scatter | How did streaming and FTA move together? | QF4 paired yearly estimates; direction over time, not individual switching. |
| Service heatmap | Which platforms differ by age? | QF7, eight services by seven age groups, six-month use. |
| Parallel coordinates | What does each age group's weekly mix look like? | QF4/QH3, six weekly behaviours; unlike the platform heatmap, spans media types. |
| Benchmark / bullet | Which ages spend more time in a selected format? | QF5 means compared only with that format's national benchmark. |
| Bump | How do ranks change within a consistent service selection? | Same eight QF7 services, 2021–2025; tooltips retain reach. |
| Slopegraph | How did online-video devices change? | QF1, 2021 versus 2025; devices can overlap. |
| Audio heatmap | Which audio formats have different age profiles? | QH3; weekly population percentages, not format-listener percentages. |
| Bipartite network | Where do users of each format listen? | QH16 conditional percentages; overlapping relationships, not conserved flows. |
| News dot plot | Is online news/information access limited to young adults? | QD8, one question and six-month period across all seven age groups. |
| Metro/regional dumbbell | Does the location gap vary by medium? | QF4/QH3 source-defined groups, paired estimates and point gaps. |
| Choropleth | Where are average inclusion conditions stronger? | State ADII, 2024 fieldwork, geographic position and sequential colour. |
| Dorling cartogram | How does population change spatial emphasis? | ABS March 2026 residents determine area; ADII colour shows a separate attribute. |
| Radio proportional symbols | Where are DAB+ facilities and how many records share a site? | Issued ACMA DR records grouped by Site Id; real coordinates. |
| Radio dot map | How dispersed are licensed AM/FM sites? | One point per unique site, not one point per listener or licence. |

## Course material applied

- Weeks 1–2: What–Why–How, data abstraction, truthful marks/channels; aligned position for precise differences and area for proportional populations.
- Week 3: interpretation rather than value repetition; no claim that aggregate trends prove individual switching or causal effects.
- Week 4: ordered lightness for quantitative data, muted basemaps, legible labels and restrained highlighting rather than extra site ornament.
- Week 5: Kirk's heatmap, waffle, slopegraph and bump guidance; percentages that overlap are not a partition. Annual observations do not justify a seasonal spiral.
- Week 6: weighted bipartite relationships with explicit bases. No Sankey/chord migration is invented from separate percentages, and no unsupported hierarchy is imposed.
- Week 7: Australian equal-area projection, standardised choropleth values, shared TopoJSON and documented joins.
- Week 8: true point locations versus symbol magnitudes, avoiding crowding through city views. Dots are facilities, not synthetic population locations.
- Week 9: genuine proportional-area cartogram with collision handling; bound controls and annotations. No contours or shaded relief are invented from state averages.

The supplied folders cover Weeks 1–9. This rationale synthesises the relevant notes, studios and readings; it does not claim later course content has been reviewed.

## Data integrity and verification

Retain the earlier repairs: correct polygon winding, visible horizon layers, ordered profiles, Column n rather than positive-response n, separate per-format hour means, fixed service selection and no invented missing-wave zeroes.

The new geography build deduplicates repeated day/night licence assignments by band, licence, technical specification and Site Id. Different sites sharing a licence remain distinct. The source uses some rounded 60-second coordinates; conversion carries these correctly. Issued AM/FM records produce 1,574 sites; DR produces 29 sites and 63 licence records. GDA94 coordinates are used at display scale, not for coverage analysis.

The cartogram reads the March 2026 persons estimates directly from ABS table 4, released 17 September 2026, the latest release at the 6 October review. Area and colour deliberately have different periods: March 2026 residents versus ADII 2024 fieldwork; they are separate attributes, not a contemporaneous relationship. Radius squared is proportional to population; deterministic relaxation removes circle collisions. Eight jurisdictions exclude Other Territories. All-age residents are not adult media users and must not be multiplied by ADII to manufacture an exclusion count.

Run scripts/check_data.py for known values, source denominators, data joins, provenance, licence aggregation, coordinate conversion, circle geometry, manifest/HTML agreement and footnote links. Run scripts/check_browser.py for actual rendering, controls, labels, proportional areas and collisions at 1366, 1024 and 390 pixels. The browser consumes approximately 235 kB of unique chart data, below the few-megabyte requirement. Compilation alone is not proof of correct rendering.

## Data-vintage review — 6 October

- ACMA audience workbooks: cached files match fresh downloads byte-for-byte. Latest linked waves remain 2025. Corrected the viewing/listening report date to 5 March 2026; its workbook URL contains February, which is not the report release date. The internet report remains February 2026. See the [ACMA release](https://www.acma.gov.au/articles/2026-03/streaming-remains-australias-favourite-way-watch-or-listen-acma-research-shows) and [current research series](https://www.acma.gov.au/communications-and-media-australia).
- ADII: the [report page](https://digitalinclusionindex.org.au/download-reports/) still identifies 2025 as current; retain and clearly label 2024 fieldwork.
- Population: replaced the historical June 2024 snapshot with [March 2026 table 4](https://www.abs.gov.au/statistics/people/population/national-state-and-territory-population/mar-2026/310104.xlsx). The parser selects persons series by header and reference month, not fixed cells or rounded landing-page values. Estimates can be revised.
- Boundaries: updated to [ASGS 2026](https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs/edition-4-july-2026-june-2031/access-and-downloads/digital-boundary-files). The service's NSW polygon-ring ordering initially removed ACT during cleaning. Mapshaper's containment-based rewind fixes this before simplification; tests require eight non-empty state shapes.
- Radio: the [current download page](https://www.acma.gov.au/list-transmitters-licence-broadcast) still lists 13 July 2026, matching the cached source.
- News-trust context: the [University of Canberra landing page](https://www.canberra.edu.au/research/centres/nmrc/digital-news-report-australia) is the 2026 report. It remains separate from ACMA's news-reach chart.
- Repeat this review before submission. Different sources have different reporting schedules; a 2026 publication does not imply 2026 fieldwork. Population area and ADII colour are separately dated contextual attributes, not a same-period comparison or a calculated audience count.

## Verification results

Verification on 6 October: data audit and JavaScript syntax passed; all 16 Vega-Lite specifications compiled to Vega and parsed. All 16 charts rendered at 1366, 1024 and 390 pixels. Seven on-diagram callouts render once each; age/format callouts respond to their selections. Browser checks cover labels, page overflow, eight visible state shapes, four-map highlighting, age/format controls, city views, cartogram area ratios and collisions, and radio mark counts. The final-feedback checks additionally cover all six audio selections, area-key scale, geographic labels and live resizing with preserved selections. Simulated chart-loading failure preserves the narrative and recovers using Retry chart. Chart data total approximately 234 kB. Visual Word pagination and public hosting remain student checks.

## Immediate action: TA feedback

Email the TA as soon as the revised preview is checked. Use the email draft in the separate private submission folder, outside this repository. Include an accessible preview or screenshots, not a localhost address that only works on this computer. Ask about idiom classification, chart counting, infrastructure relevance and whether the annotations explain enough.

## Remaining submission gates

- Public GitHub repository and GitHub Pages URL: mandatory. The brief states inaccessible pages/embedded elements receive zero; localhost is not submission-ready.
- Actual hand sketch, tutor discussion, public sketch PDF and matching final design; date any revised sketch honestly.
- Public links, sketch and published-site screenshots, and Word pagination. Full name, student ID and studio have been supplied and added appropriately.
- Student review of claims and ability to explain all chart and code choices.
- Due Sunday 25 October 2026, 11:55 pm; Week 12 studio interview.
