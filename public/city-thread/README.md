# CITY THREAD v0.3 — Die Stadt zwischen den Zeilen

An independent, educational civic Knowledge Graph prototype. **Dawn edition (v0.3):** a warm, editorial, mobile-first redesign that guides a visitor from a real location to a meaningful relationship and then to its evidence.

**Public page:** https://mikelninh.github.io/COMMONS/city-thread/

## v0.3 product and UX improvements
- A completely renewed visual identity: **warm ivory, expressive ink, indigo and peach**, bespoke hand-drawn Berlin scene, editorial typography and calm depth.
- Horizontal five-chapter navigation replaces the heavy sidebar. Discover → Verbindungen → Fragen → Vertrauen → Lernen.
- Clear landing journey with optional quick introduction and a direct path to real water-fountain data.
- Filter and search 120 points across 12 districts. The list progressively reveals eight at a time, while the coordinate plot retains all filtered points.
- Selected place persists across the atlas, RDF relationship graph and learning example.
- SPARQL syntax is an optional disclosure in the question interface, rather than an intimidating initial editor.
- Trust and evidence shows limitations, provenance and small deliberately falsifiable browser checks.
- Keyboard-operable SVG nodes, reduced-motion support and a mobile layout.
- Playwright regression suite: `node scripts/city-thread-smoke.mjs`, exercised in GitHub Pages CI before and after deployment. Desktop/mobile screenshots saved as CI artifacts.

**Important:** Visualising an RDF graph does not mean an AI model or query engine has executed. The public UI uses fixed question evaluators. The exported `data.ttl` and `shapes.ttl` provide real RDF and SHACL definitions for independent execution.

## What is real
- Berlin water-fountain WFS records: **120 of 242** at snapshot time, collected **9 October 2026**.
- Berlin district names, locations (WGS84 lat/lon), fountain type, reported restriction and build years, if supplied.
- Official Berlin source: https://daten.berlin.de/datensaetze/trinkwasserbrunnen-wfs-47dba2c3
- License: **Datenlizenz Deutschland – Zero – Version 2.0**.
- Published record snapshot: [fountains.json](./fountains.json).

## What is genuinely semantic
- [data.ttl](./data.ttl): 1000+ **actual RDF assertions** derived from the WFS extract.
- [shapes.ttl](./shapes.ttl): a declarative **SHACL constraint model** for points, provenance, districts and geodata.
- The site explains subject–predicate–object and renders the relations for chosen real objects.
- Query Lab displays **real SPARQL query text** paired with fixed local JavaScript evaluations that implement those same specific patterns on the snapshot. It is **not an arbitrary SPARQL engine**. Run actual SPARQL against the TTL file with RDFLib or another SPARQL processor, e.g.:

~~~python
from rdflib import Graph
g = Graph().parse("data.ttl", format="turtle")
rows = g.query("""PREFIX ct: <https://citythread.example/ontology#>
  SELECT (COUNT(?f) AS ?n) WHERE { ?f a ct:DrinkingFountain }""")
print(list(rows)[0][0])
~~~

For full SHACL:
~~~python
from rdflib import Graph
from pyshacl import validate
g = Graph().parse("data.ttl", format="turtle")
shapes = Graph().parse("shapes.ttl", format="turtle")
conforms, report, _ = validate(g, shacl_graph=shapes, inference="rdfs")
print(conforms, report)
~~~

Dependencies: python 3.11+, rdflib, pyshacl. To examine and develop the Python server-side real SPARQL workflow locally, see CITY THREAD v0.1 (the separate FastAPI training prototype).

## What is not established
- This extract covers **only the first 120 out of 242 reported entries**, not a complete or representative city inventory.
- It is **not a live fountain availability status**. Reported restrictions are source text at snapshot time.
- This prototype has **not joined** the official Berlin 2022 climate polygons. It cannot responsibly rank locations by heat vulnerability or justify a new fountain.
- Browser “Trust & evidence” checks are **simple client-side range/provenance checks, not a SHACL execution environment**; the real SHACL definition is in shapes.ttl above.
- City Thread is **not an official service of Berlin, DKSR or CIVORA**.

## Interview demonstration in 90 seconds
1. **Discover:** select a real place and show its official WFS origin. Explain the sample-boundary banner.
2. **Connect:** open "Verbindungen"; click the district node and explain `fountain:f24 ct:inDistrict district:friedrichshain-kreuzberg`.
3. **Ask:** run a fixed SPARQL-style example, reveal the source query, explain which claims cannot yet be made.
4. **Verify:** inject a broken coordinate and demonstrate the quality gate. Explain why full SHACL execution is separate.

## Product hypothesis for DKSR interview
A modular semantic layer could make municipal assets queryable and traceable across heterogeneous data sources, with quality gates before AI outputs.

Next release gate: verified spatial join (2022 heat polygons + drinking fountain geodata), explicit spatial predicates, validation tests, municipality adapter, and permissions.

## License, rights and attribution
Data from the Berlin geodata service (WFS Trinkwasserbrunnen), catalog as above; dl-de-zero-2.0. Independent learning code/prototype.
