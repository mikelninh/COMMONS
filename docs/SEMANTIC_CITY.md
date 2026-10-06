# COMMONS Semantic City - v0.1

> One reusable semantic foundation for municipal questions - with provenance, validation and explicit human authority.

## Why this exists

Urban data is usually separated by department, system and file format. A map can show layers, but a decision often depends on relationships across them: a vulnerable population lives in an area; the area has heat exposure; a care service depends on a route; the route depends on infrastructure; a recommendation is supported by evidence but controlled by a human authority.

Semantic City makes those relationships queryable.

    sources -> semantic model -> validation -> query / AI
            -> recommendation -> human authority

The prototype deliberately avoids claiming operational accuracy. Relationships are representative and all numeric fixture values are marked city:isDemoValue true.

## Four scenarios on one graph

1. **Heat resilience** - connect heat, social burden, green access and modeled weather without hiding them inside one opaque score.
2. **Critical infrastructure cascade** - traverse dependsOn+ from one asset to affected mobility and care services.
3. **Energy transition** - compare carbon benefit, cost and social context while leaving policy weights explicit.
4. **Heavy rain / flood attention** - connect modeled exposure to critical services and escalate attention without issuing operational commands.

## Standards used

- **RDF / OWL:** semantic/semantic-city-ontology.ttl
- **SHACL:** semantic/semantic-city-shapes.ttl
- **SPARQL:** executable queries in src/commons/semantic_city.py
- **Source adapter:** semantic/adapters/berlin.json
- **Python graph runtime:** RDFLib
- **SHACL runtime:** pySHACL, with a structural fallback for constrained environments

## Core ontology

    City
    Area
    PopulationGroup
    InfrastructureAsset
    Building
    Service
    Observation
    EvidenceSource
    Action
    Recommendation
    HumanAuthority

Important relationships:

    locatedIn
    livesIn
    containsPopulation
    dependsOn
    hasObservation
    about
    evidenceSource
    controlledBy
    requiresHumanApproval

The important design choice is that **authority is part of the model**, not an afterthought in the UI.

## Berlin adapter

The first adapter maps graph concepts to source families already used by Berlin Deep City:

- Umweltatlas Berlin climate analysis
- Umweltatlas Berlin environmental-justice context
- Geoportal Berlin green spaces
- Geoportal Berlin hospitals
- Open-Meteo modeled weather
- VBB transit movement

The adapter stores mapping metadata, not copied live facts. Replacing Berlin with another municipality should primarily mean replacing the source adapter and transformations, while preserving the ontology and scenario logic where appropriate.

## Run it

    pip install -e ".[dev]"
    python scripts/semantic_city_demo.py --scenario heat
    python scripts/semantic_city_demo.py --scenario resilience
    python scripts/semantic_city_demo.py --scenario energy
    python scripts/semantic_city_demo.py --scenario flood

Export the RDF fixture:

    python scripts/semantic_city_demo.py --format turtle

API:

    GET /semantic-city/scenarios
    GET /semantic-city/scenarios/{heat|resilience|energy|flood}

Public interface:

    /semantic-city.html

## Governance contract

Semantic City distinguishes **decision support** from **decision authority**.

- AI may retrieve, connect, compare, explain and recommend.
- High-impact operational actions are never executed from this prototype.
- Budget allocation, emergency routing, closures and public-resource decisions remain with accountable humans.
- Missing or stale evidence should remain visible rather than being filled with invented certainty.

## Release gates

v0.1 is ready when:

- [x] one shared graph supports four distinct municipal scenarios
- [x] SPARQL queries execute against the graph
- [x] SHACL constraints cover observations and recommendations
- [x] demo values are explicitly marked as demo values
- [x] evidence source metadata and caveats are inspectable
- [x] consequential scenarios expose a human authority gate
- [x] public UI can explain WHY? and show query/provenance
- [x] deterministic tests cover graph, queries and authority behavior
- [ ] one scenario ingests live official records end-to-end
- [ ] second municipal adapter demonstrates portability with real source mappings
- [ ] NGSI-LD / GeoSPARQL mapping is implemented rather than documented only

## Next technical step

The highest-value next step is **not more scenarios**. It is replacing one demo fixture - heat is the best candidate - with a reproducible official-data ingestion path while retaining the same RDF model, SHACL validation, SPARQL query and human-gate behavior.
