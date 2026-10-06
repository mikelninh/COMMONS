from rdflib import Graph, URIRef

from commons.berlin_heat_wfs import BerlinHeatRecord
from commons.semantic_interop import (
    GEO,
    attach_geosparql_point,
    berlin_heat_ngsi_ld,
)


def sample_record() -> BerlinHeatRecord:
    return BerlinHeatRecord(
        feature_type="multi-layer-wfs",
        feature_id="0000000001000265",
        retrieved_at="2026-10-06T09:01:57Z",
        longitude=13.4132,
        latitude=52.5219,
        radius_m=25.0,
        match_mode="point_bbox",
        join_mode="shared_schl5",
        properties={
            "pet14h": 40.56,
            "utci14h": 36.31,
            "t2m14h": 32.82,
            "uhi": 2.18,
        },
        layers={},
    )


def test_geosparql_point_uses_crs84_wkt() -> None:
    graph = Graph()
    subject = URIRef(
        "https://example.test/area/1"
    )
    geometry = attach_geosparql_point(
        graph,
        subject,
        13.4132,
        52.5219,
    )
    assert (
        graph.value(subject, GEO.hasGeometry)
        == geometry
    )
    wkt = str(
        graph.value(geometry, GEO.asWKT)
    )
    assert "CRS84" in wkt
    assert "POINT(13.4132 52.5219)" in wkt


def test_ngsi_ld_preserves_structural_truth_boundary() -> None:
    entities = berlin_heat_ngsi_ld(
        sample_record()
    )
    source, area = entities
    assert source["type"] == "EvidenceSource"
    assert area["type"] == "Area"
    assert (
        area["location"]["type"]
        == "GeoProperty"
    )
    assert (
        area["location"]["value"]["coordinates"]
        == [13.4132, 52.5219]
    )
    assert area["pet14h"]["value"] == 40.56
    assert area["pet14h"]["unitCode"] == "CEL"
    assert "observedAt" not in area["pet14h"]
    assert (
        area["retrievedAt"]["value"]
        == "2026-10-06T09:01:57Z"
    )
    assert (
        area["datasetModelYear"]["value"]
        == "2022"
    )
