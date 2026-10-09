# CITY THREAD v0.5 — Interaction Design Decision Record

**North star:** *Berühre die Stadt. Sie antwortet.*

The user feedback on v0.4 was unambiguous: the approved color palette worked, but the UX felt underwhelming. v0.4 put a large presentation, a tiny evidence-map, scattered numbers, and extensive explanatory sections ahead of the core interaction. We redesigned interaction rather than adding more ornament.

## One-minute experience

1. See the real Berlin study-map and a clear invitation to place a hypothetical fountain — above the fold.
2. Touch the map, drag the coral proposal marker (or use the arrow keys), or select one of three candidate test points.
3. The *same* underlying spatial model updates the newly-in-range **sample-grid point** counter and its 126 → 102 example comparison, at default 300 m. No claim about population, real accessibility, temperature change or build feasibility.
4. Toggle **Vorher** / **Mit deiner Idee** to physically remove/restore the proposal and newly highlighted raster cells on the map, not just change a label.
5. Ask **Warum dieses Ergebnis?** to open a single evidence drawer: source links, RDF triples, methodology, uncertainties and an explicitly gated *local-only* Markdown report.

## Interaction decisions

| v0.4 | v0.5 |
| --- | --- |
| Long hero story above map | Concise heading + immediate canvas |
| Model count separated from gesture | Large live effect number adjacent to map; mobile overlay |
| Buried action / microprint | One obvious place/drag interaction; labeled feedback |
| Colorful but abstract study map | Optional © OpenStreetMap basemap aligned to the **real** WGS84 study geometry, preserved fallback |
| Large multi-section source/explanation scroll | Native modal evidence drawer, one click, dismiss with Escape |
| Three suggestions compete with main controls | Compact three-position choice cards |
| Before/after exclusively numerical | Actual map-state toggle, aria-pressed controls |
| Long desktop report UI | Readable local report in drawer, explicit human-review acknowledgment |

## Quality bar

- **First useful action:** user can click the study area as soon as it appears. No preamble or login.
- **Legibility:** the action outcome appears immediately, even on small screens, with a clear unit (90 m sample-grid points, not people).
- **Responsive:** 390 px mobile screen shows at least part of the working map without scrolling; no sideways overflow.
- **Accessibility:** keyboard-operable marker, labeled controls, focus outlines, reduced motion, native modal handling, clear non-live-data wording.
- **Honesty:** clicking beyond the analyzed boundary explains why the site cannot place the proposal there.
- **User agency:** old views remain reconstructible with Before / After, radius and shareable URL.

## Data semantics (unchanged)

The 242 Berlin WFS fountain records and 154 intersecting official 2022 settlement-climate polygons remain unchanged. The transparent straight-line distance / point-in-polygon 90 m screening algorithm remains unchanged. Real SPARQL / SHACL and the independent Shapely cross-check continue to run in CI, not in the public browser.

## Product hypothesis to test

The redesigned first impression should increase the fraction of testers who complete a **meaningful scenario change without instruction**. Ask 5 people to open the link. Measure: time to first placement, whether they noticed the change, ability to state what +24 *really means*, usage of Compare and Evidence, and confidence that the output is NOT a construction approval. Don't present these as measured outcomes until real testers complete sessions.
