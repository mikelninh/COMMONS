# CITY THREAD v0.2 — Semantic City Lab

An independent, educational civic Knowledge Graph prototype.

**Public page:** https://mikelninh.github.io/COMMONS/city-thread/

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

## Product hypothesis for DKSR interview
A modular semantic layer could make municipal assets queryable and traceable across heterogeneous data sources, with quality gates before AI outputs.

Next release gate: verified spatial join (2022 heat polygons + drinking fountain geodata), explicit spatial predicates, validation tests, municipality adapter, and permissions.

## License, rights and attribution
Data from the Berlin geodata service (WFS Trinkwasserbrunnen), catalog as above; dl-de-zero-2.0. Independent learning code/prototype.
