from urllib.parse import parse_qs, urlparse

from commons.berlin_heat_wfs import (
    build_graph,
    discover_feature_type,
    fetch_record,
    run_official_heat,
)
from commons.semantic_city import CITY

CAPABILITIES = b'''<wfs:WFS_Capabilities xmlns:wfs="http://www.opengis.net/wfs/2.0">
<wfs:FeatureTypeList><wfs:FeatureType><wfs:Name>fis:wind</wfs:Name></wfs:FeatureType>
<wfs:FeatureType><wfs:Name>fis:klima_isu5</wfs:Name></wfs:FeatureType></wfs:FeatureTypeList>
</wfs:WFS_Capabilities>'''
SCHEMA_WIND = b'''<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema"><xsd:element name="wg"/></xsd:schema>'''
SCHEMA_CLIMATE = b'''<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
<xsd:element name="schl5"/><xsd:element name="typklar"/><xsd:element name="pet14h"/>
<xsd:element name="utci14h"/><xsd:element name="t2m14h"/><xsd:element name="uhi"/></xsd:schema>'''
FEATURE = b'''<wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs/2.0" xmlns:gml="http://www.opengis.net/gml/3.2" xmlns:fis="https://example.test/fis">
<wfs:member><fis:klima_isu5 gml:id="klima.123"><fis:schl5>110000123456</fis:schl5>
<fis:typklar>dense residential</fis:typklar><fis:pet14h>41.7</fis:pet14h>
<fis:utci14h>38.6</fis:utci14h><fis:t2m14h>31.4</fis:t2m14h><fis:uhi>3.2</fis:uhi>
</fis:klima_isu5></wfs:member></wfs:FeatureCollection>'''


def fake_wfs(url: str) -> bytes:
    q = {k.upper(): v for k, v in parse_qs(urlparse(url).query).items()}
    request = q["REQUEST"][0].lower()
    if request == "getcapabilities":
        return CAPABILITIES
    if request == "describefeaturetype":
        return SCHEMA_CLIMATE if q["TYPENAMES"][0] == "fis:klima_isu5" else SCHEMA_WIND
    if request == "getfeature":
        return FEATURE
    raise AssertionError(url)


def test_discovers_climate_feature_type_from_schema() -> None:
    feature_type, fields = discover_feature_type(fake_wfs)
    assert feature_type == "fis:klima_isu5"
    assert {"pet14h", "utci14h", "t2m14h"}.issubset(fields)


def test_official_record_flows_wfs_to_rdf_shacl_sparql_and_human_gate() -> None:
    record = fetch_record(fetch=fake_wfs, allow_fallback=False)
    assert record.match_mode == "point_bbox"
    assert record.feature_id == "klima.123"
    assert record.properties["pet14h"] == 41.7

    graph = build_graph(record)
    flags = [graph.value(obs, CITY.isDemoValue).toPython() for obs in graph.subjects(CITY.metric, None)]
    assert flags and all(flag is False for flag in flags)

    result = run_official_heat(record)
    assert result["validation"]["conforms"] is True
    assert float(result["rows"][0]["pet"]) == 41.7
    assert float(result["rows"][0]["utci"]) == 38.6
    assert result["authority"] == "human_decision_required"
    assert "not observation time" in result["caveat"].lower()
