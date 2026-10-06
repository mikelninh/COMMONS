from __future__ import annotations

from typing import Any

from rdflib import Graph, Literal, Namespace, RDF, URIRef

GEO = Namespace("http://www.opengis.net/ont/geosparql#")
NGSI_CONTEXT = (
    "https://uri.etsi.org/ngsi-ld/v1/"
    "ngsi-ld-core-context.jsonld"
)


def attach_geosparql_point(
    graph: Graph,
    subject: URIRef,
    longitude: float,
    latitude: float,
) -> URIRef:
    """Attach a WGS84 point using the GeoSPARQL vocabulary."""
    graph.bind("geo", GEO)
    geometry = URIRef(f"{subject}/geometry")
    graph.add((subject, GEO.hasGeometry, geometry))
    graph.add((geometry, RDF.type, GEO.Geometry))
    graph.add(
        (
            geometry,
            GEO.asWKT,
            Literal(
                (
                    "<http://www.opengis.net/def/crs/"
                    "OGC/1.3/CRS84> "
                    f"POINT({longitude} {latitude})"
                ),
                datatype=GEO.wktLiteral,
            ),
        )
    )
    return geometry


def berlin_heat_ngsi_ld(
    record: Any,
) -> list[dict[str, Any]]:
    """Map official Berlin heat evidence to NGSI-LD.

    Retrieval time is metadata, not an observation timestamp,
    because the climate-map values model structural 2022 conditions.
    """
    safe_id = str(record.feature_id).replace(" ", "-")
    source_id = (
        "urn:ngsi-ld:EvidenceSource:"
        "BerlinKlimaanalyse2022"
    )
    area_id = (
        f"urn:ngsi-ld:Area:BerlinHeat:{safe_id}"
    )

    source: dict[str, Any] = {
        "id": source_id,
        "type": "EvidenceSource",
        "name": {
            "type": "Property",
            "value": "Klimaanalysekarten 2022",
        },
        "publisher": {
            "type": "Property",
            "value": (
                "Senatsverwaltung für Stadtentwicklung, "
                "Bauen und Wohnen Berlin"
            ),
        },
        "endpoint": {
            "type": "Property",
            "value": record.source_endpoint,
        },
        "evidenceClass": {
            "type": "Property",
            "value": "official-structural-modeled",
        },
        "@context": [NGSI_CONTEXT],
    }

    area: dict[str, Any] = {
        "id": area_id,
        "type": "Area",
        "location": {
            "type": "GeoProperty",
            "value": {
                "type": "Point",
                "coordinates": [
                    record.longitude,
                    record.latitude,
                ],
            },
        },
        "retrievedAt": {
            "type": "Property",
            "value": record.retrieved_at,
        },
        "datasetModelYear": {
            "type": "Property",
            "value": record.dataset_model_year,
        },
        "providedBy": {
            "type": "Relationship",
            "object": source_id,
        },
        "@context": [NGSI_CONTEXT],
    }

    units = {
        "pet14h": "CEL",
        "utci14h": "CEL",
        "t2m14h": "CEL",
        "uhi": "KEL",
    }
    for metric, unit_code in units.items():
        value = record.properties.get(metric)
        if not isinstance(value, (int, float)):
            continue
        area[metric] = {
            "type": "Property",
            "value": value,
            "unitCode": unit_code,
            "datasetModelYear": {
                "type": "Property",
                "value": record.dataset_model_year,
            },
        }

    return [source, area]
