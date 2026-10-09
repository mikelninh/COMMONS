#!/usr/bin/env python3
"""CITY THREAD v0.4 release gate.

This is a real RDFLib/SPARQL + pySHACL validation, and a real geometric
point-in-polygon cross-check using a 90-metre regular grid. No LLMs, mocked
measurements, or calls to live Berlin APIs. Data snapshots remain immutable.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from rdflib import Graph, Namespace, RDF
from pyshacl import validate
from shapely.geometry import Point, shape

ROOT = Path(__file__).resolve().parent.parent / "public" / "city-thread"
CT = Namespace("https://citythread.example/ontology#")
GEO = Namespace("http://www.w3.org/2003/01/geo/wgs84_pos#")
PROV = Namespace("http://www.w3.org/ns/prov#")

def snapshots(prefix: str, record_key: str) -> list:
    pages = [json.loads((ROOT / f"{prefix}-{i}.json").read_text(encoding="utf-8")) for i in range(4)]
    assert [p["page"] for p in pages] == [0, 1, 2, 3], "Page indexes must cover full source pagination"
    return [part for page in pages for part in page[record_key]]

def haversine(a: dict, b: dict) -> float:
    rad = math.pi / 180
    dp = (b["lat"] - a["lat"]) * rad
    dl = (b["lon"] - a["lon"]) * rad
    h = math.sin(dp/2)**2 + math.cos(a["lat"]*rad) * math.cos(b["lat"]*rad) * math.sin(dl/2)**2
    return 2 * 6371008.8 * math.asin(min(1, math.sqrt(h)))

def main() -> None:
    waters = snapshots("fountains-all", "records")
    zones = snapshots("heat", "features")
    assert len(waters) == 242 and len({x["id"] for x in waters}) == 242
    assert len(zones) == 154 and len({x["id"] for x in zones}) == 154
    assert all(-180 <= f["lon"] <= 180 and -90 <= f["lat"] <= 90 for f in waters)
    assert all(z["heat"] in {"sehr ungünstig", "ungünstig", "weniger günstig", "günstig"} for z in zones)

    graph = Graph()
    for filename in ["mission.ttl", "mission-fountains-0.ttl", "mission-fountains-1.ttl"]:
        graph.parse(ROOT / filename, format="turtle")
    shapes = Graph().parse(ROOT / "mission-shapes.ttl", format="turtle")
    water_nodes = set(graph.subjects(RDF.type, CT.DrinkingFountain))
    climate_nodes = set(graph.subjects(RDF.type, CT.HeatAssessmentZone))
    assert len(water_nodes) == 242, f"Expected 242 fountain RDF nodes, found {len(water_nodes)}"
    assert len(climate_nodes) == 154, f"Expected 154 heat RDF nodes, found {len(climate_nodes)}"
    assert all(any(graph.objects(f, PROV.wasDerivedFrom)) for f in water_nodes)
    sparql = """
    PREFIX ct: <https://citythread.example/ontology#>
    SELECT (COUNT(DISTINCT ?f) AS ?total) WHERE { ?f a ct:DrinkingFountain . }
    """
    rdf_water_count = int(list(graph.query(sparql))[0][0])
    assert rdf_water_count == len(waters), "SPARQL must count all paginated fountain records"

    conformity, report_graph, report_text = validate(graph, shacl_graph=shapes, advanced=False)
    if not conformity:
        raise AssertionError("Real SHACL validation failed:\n" + report_text)

    # Deliberately remove the source of one fountain: SHACL must detect this.
    victim = next(iter(water_nodes))
    broken = Graph()
    broken += graph
    for source in list(broken.objects(victim, PROV.wasDerivedFrom)):
        broken.remove((victim, PROV.wasDerivedFrom, source))
    conforms_broken, _, _ = validate(broken, shacl_graph=shapes, advanced=False)
    assert conforms_broken is False, "SHACL must refuse a fountain missing provenance"

    bbox = [13.385, 52.490, 13.407, 52.512]
    lat0 = (bbox[1]+bbox[3])/2
    step_lat = 90/111132
    step_lon = 90/(111320*math.cos(math.radians(lat0)))
    features = [(z["heat"], shape(z["g"])) for z in zones]
    samples = []
    lat = bbox[1]+step_lat/2
    while lat < bbox[3]:
        lon = bbox[0]+step_lon/2
        while lon < bbox[2]:
            point = Point(lon,lat)
            matches = [heat for heat,polygon in features if polygon.contains(point)]
            if matches:
                samples.append({"lon":lon,"lat":lat,"heat":matches[0]})
            lon += step_lon
        lat += step_lat

    heavy = [p for p in samples if p["heat"] in {"ungünstig","sehr ungünstig"}]
    uncovered = [p for p in heavy if min(haversine(p,w) for w in waters) > 300]
    best = max(((sum(haversine(s,q) <= 300 for q in uncovered),s) for s in uncovered), key=lambda t:t[0])
    assert samples and heavy and uncovered and best[0] > 0
    print(f"PASS 4/4 source pages: {len(waters)} unique WFS fountains; {len(zones)} unique 2022 climate polygons")
    print(f"PASS RDF/SPARQL: {rdf_water_count} fountains and {len(climate_nodes)} heat zones")
    print(f"PASS pySHACL valid graph and deliberately invalid provenance fixture")
    print(f"PASS spatial join: {len(samples)} sample points; {len(heavy)} in heat classes; "
          f"{len(uncovered)} >300m from documented fountain; best hypothetical +{best[0]} sample points")
    print("Release note: straight-line coverage proxy only; no population, current operation, or planning approval")

if __name__ == "__main__":
    main()
