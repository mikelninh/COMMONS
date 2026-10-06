# COMMONS Semantic City - v0.5

> One reusable semantic foundation for municipal questions - with provenance, validation and explicit human authority.

## What v0.5 proves

Semantic City now has **two municipal adapters** in addition to the deterministic four-scenario fixture:

    Berlin WFS
      -> discover compatible climate layers
      -> select the layer that covers the requested location
      -> preserve exact feature provenance
      -> transform to RDF
      -> validate with SHACL
      -> query with SPARQL
      -> keep consequential authority with a human

The live GitHub Actions proof passed on 6 October 2026 against Berlin's official
Klimaanalysekarten 2022 WFS.

At the proof point (52.5219, 13.4132), four land-use-specific WFS layers were
resolved and joined by the shared ISU5 key `0000000001000265`:

| Metric | Official feature type | Snapshot value |
| --- | --- | ---: |
| PET 14:00 | `pb_ua_pet_str_2022` | 40.56 °C |
| UTCI 14:00 | `rb_ua_utci_str_2022` | 36.31 °C |
| Air temperature 14:00 | `hb_ua_lufttemp_str_t2m_14h_2022` | 32.82 °C |
| Urban heat island | `th_kak_verkehrsfl_2022` | 2.18 K |

These are **structural modeled values from Klimaanalysekarten 2022**, not
weather observations from 6 October 2026. Retrieval time is not observation time.

## Cross-domain heat decision proof

The verified Berlin point is no longer a climate-only demo. The same graph now joins four official source families:

```text
Klimaanalysekarten 2022
        +
Umweltgerechtigkeit 2023/2024
        +
Grünanlagenbestand
        +
Krankenhäuser Berlin
        ↓
RDF / PROV → SHACL → SPARQL
        ↓
explainable recommendation
        ↓
explicit evidence gaps
        ↓
accountable human decision
```

Verified snapshot at **52.5219, 13.4132** on 6 October 2026:

| Evidence | Verified value |
| --- | --- |
| PET 14:00 | 40.56 °C |
| UTCI 14:00 | 36.31 °C |
| Urban heat island | 2.18 K |
| Planning area | Alexanderplatzviertel |
| Multiple burden | dreifach |
| Bioclimate burden | hoch |
| Green provision | mittel |
| Social status index | mittlerer Status-Index |
| Nearest mapped public green | Fernsehturmanlage zw. Fernsehturm u. Spandauer Str. · ~249 m |
| Nearest mapped hospital | St. Hedwig-Krankenhaus · ~1.10 km · 415 reported beds |

The resulting semantic graph contains **281 triples**, passes SHACL, uses **4 official source families**, and contains **0 synthetic values** in this cross-domain path.

The system deliberately does not create a new opaque vulnerability score. Instead it exposes the contributing evidence and four blockers before consequential action:

1. current heat warning / forecast,
2. current distribution of heat-vulnerable people and institutions,
3. usable cooling / shade availability and accessibility,
4. current hospital capacity and relevant service availability.

This means the output can say **“review this area early if a current heat trigger is present”** while refusing to claim **“allocate resources here automatically.”**

## Why this exists

Urban data is separated by departments, systems and formats. A decision often
depends on relationships across them. Semantic City makes those relationships
queryable while keeping evidence, uncertainty and authority inspectable.

    sources -> semantic model -> validation -> query / AI
            -> recommendation -> human authority

## Four scenarios on one graph

1. **Heat resilience** - official Berlin structural heat evidence is now wired end-to-end.
2. **Critical infrastructure cascade** - synthetic dependency traversal via `dependsOn+`.
3. **Energy transition** - synthetic carbon/cost/social trade-off with explicit policy weights.
4. **Heavy rain / flood attention** - synthetic exposure-to-service chain with no autonomous command path.

## Standards and implementation

- **RDF / OWL:** `semantic/semantic-city-ontology.ttl`
- **SHACL:** `semantic/semantic-city-shapes.ttl`
- **SPARQL:** executable queries in `src/commons/semantic_city.py` and municipal adapters
- **GeoSPARQL:** Berlin official records carry CRS84 WKT geometry
- **NGSI-LD:** Berlin heat evidence can be exported as interoperable context entities
- **Source adapters:** `semantic/adapters/berlin.json`, `semantic/adapters/cologne.json`
- **RDF runtime:** RDFLib
- **SHACL runtime:** pySHACL
- **CRS transformation:** pyproj, WGS84 -> EPSG:25833
- **Live proofs:** `.github/workflows/semantic-city-live.yml`, `.github/workflows/semantic-city-portability.yml`

## Important architecture choice: discover, do not hard-code

The first live attempt correctly failed because PET, UTCI, air temperature and
UHI are not exposed as one universal table. Berlin separates climate layers by
land-use family such as traffic, settlement and green/open space.

v0.2 therefore:

1. reads WFS capabilities,
2. inspects feature schemas,
3. finds every layer compatible with each metric,
4. queries candidates at the requested point,
5. selects the layer that actually covers that point,
6. joins records by `schl5` when possible, otherwise records a spatial join,
7. preserves each source feature ID in provenance.

That behaviour is much closer to a reusable municipal adapter than a hard-coded demo.

## Portability proof: Cologne

The second adapter targets the official **Baumkataster - Stadt Köln** WFS.

    Cologne WFS
      -> discover available feature types
      -> choose the tree-cadastre layer by semantic name
      -> parse only fields actually returned
      -> normalize common concepts such as species / street / tree number when present
      -> preserve the raw source properties and exact feature ID
      -> transform to the same RDF / PROV / SHACL contract
      -> query with SPARQL

The adapter deliberately does **not** assume Berlin field names. It also preserves
Cologne's published caveat: the cadastre covers city-managed trees only and is
not a complete inventory of every tree in the city or a substitute for an
official site survey.

## Run it

    pip install -e ".[dev]"
    python scripts/semantic_city_demo.py --scenario heat
    python scripts/fetch_berlin_heat.py --lat 52.5219 --lon 13.4132 --radius-m 25 --strict-point
    python scripts/fetch_berlin_heat_context.py --lat 52.5219 --lon 13.4132
    python scripts/fetch_cologne_tree.py

API:

    GET /semantic-city/scenarios
    GET /semantic-city/scenarios/{heat|resilience|energy|flood}
    GET /semantic-city/berlin/heat?lat=52.5219&lon=13.4132&radius_m=25
    GET /semantic-city/berlin/heat/context?lat=52.5219&lon=13.4132
    GET /semantic-city/cologne/tree
    GET /semantic-city/berlin/heat/ngsi-ld?lat=52.5219&lon=13.4132&radius_m=25

Public interface:

    /semantic-city.html

## Governance contract

- AI may retrieve, connect, compare, explain and recommend.
- Every observation must state whether it is a demo value.
- Official records preserve source layer and feature provenance.
- Budget allocation, emergency routing, closures and public-resource decisions stay with accountable humans.
- Missing evidence stays missing; retrieval time is never presented as observation time.

## Release gates

- [x] one shared graph supports four distinct municipal scenarios
- [x] SPARQL queries execute against the graph
- [x] SHACL validates observations and recommendations
- [x] demo values are explicitly marked
- [x] evidence source metadata and caveats are inspectable
- [x] consequential scenarios expose a human authority gate
- [x] public UI can explain WHY? and show query/provenance
- [x] deterministic tests cover graph, queries and authority behaviour
- [x] one scenario ingests official records end-to-end
- [x] live CI proves the official Berlin WFS path
- [x] second municipal adapter demonstrates portability
- [x] NGSI-LD / GeoSPARQL mapping is implemented
- [x] cross-domain Berlin heat decision joins four official source families
- [x] verified browser snapshot contains zero synthetic values
- [x] missing evidence is modeled explicitly before consequential action

## Next technical step

Turn the verified point proof into a **city-wide prioritisation experiment**:
sample multiple planning areas, compare evidence coverage and test whether the
system can identify useful review candidates without hiding policy choices in a
single score. Keep the current point-level proof as the deterministic reference.
