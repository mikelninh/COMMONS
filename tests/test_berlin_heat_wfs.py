from urllib.parse import parse_qs, urlparse

from commons.berlin_heat_wfs import (
    METRICS,
    build_graph,
    discover_metric_layers,
    fetch_record,
    run_official_heat,
)
from commons.semantic_city import CITY

CAPABILITIES = b'''<wfs:WFS_Capabilities xmlns:wfs="http://www.opengis.net/wfs/2.0">
<wfs:FeatureTypeList>
<wfs:FeatureType><wfs:Name>fis:pet</wfs:Name></wfs:FeatureType>
<wfs:FeatureType><wfs:Name>fis:utci</wfs:Name></wfs:FeatureType>
<wfs:FeatureType><wfs:Name>fis:temp</wfs:Name></wfs:FeatureType>
<wfs:FeatureType><wfs:Name>fis:uhi</wfs:Name></wfs:FeatureType>
</wfs:FeatureTypeList>
</wfs:WFS_Capabilities>'''

SCHEMAS = {
    "fis:pet": b'''<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <xsd:element name="schl5"/><xsd:element name="typklar"/><xsd:element name="pet14h"/>
    </xsd:schema>''',
    "fis:utci": b'''<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <xsd:element name="schl5"/><xsd:element name="utci14h"/>
    </xsd:schema>''',
    "fis:temp": b'''<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <xsd:element name="schl5"/><xsd:element name="t2m14h"/>
    </xsd:schema>''',
    "fis:uhi": b'''<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <xsd:element name="schl5"/><xsd:element name="uhi"/>
    </xsd:schema>''',
}

VALUES = {
    "fis:pet": ("pet14h", "41.7"),
    "fis:utci": ("utci14h", "38.6"),
    "fis:temp": ("t2m14h", "31.4"),
    "fis:uhi": ("uhi", "3.2"),
}


def _feature(feature_type: str) -> bytes:
    field, value = VALUES[feature_type]
    local = feature_type.split(":")[-1]
    return f'''<wfs:FeatureCollection
      xmlns:wfs="http://www.opengis.net/wfs/2.0"
      xmlns:gml="http://www.opengis.net/gml/3.2"
      xmlns:fis="https://example.test/fis">
      <wfs:member>
        <fis:{local} gml:id="{local}.123">
          <fis:schl5>110000123456</fis:schl5>
          <fis:typklar>dense residential</fis:typklar>
          <fis:{field}>{value}</fis:{field}>
        </fis:{local}>
      </wfs:member>
    </wfs:FeatureCollection>'''.encode()


def fake_wfs(url: str) -> bytes:
    q = {
        k.upper(): v
        for k, v in parse_qs(urlparse(url).query).items()
    }
    request = q["REQUEST"][0].lower()
    if request == "getcapabilities":
        return CAPABILITIES
    feature_type = q.get("TYPENAMES", [""])[0]
    if request == "describefeaturetype":
        return SCHEMAS[feature_type]
    if request == "getfeature":
        return _feature(feature_type)
    raise AssertionError(url)


def test_discovers_each_metric_from_realistic_split_layers() -> None:
    layers = discover_metric_layers(fake_wfs)
    assert set(layers) == set(METRICS)
    assert layers["pet14h"][0].feature_type == "fis:pet"
    assert layers["utci14h"][0].feature_type == "fis:utci"
    assert layers["t2m14h"][0].feature_type == "fis:temp"
    assert layers["uhi"][0].feature_type == "fis:uhi"


def test_official_multilayer_record_flows_to_rdf_shacl_sparql() -> None:
    record = fetch_record(
        fetch=fake_wfs,
        allow_fallback=False,
    )
    assert record.match_mode == "point_bbox"
    assert record.join_mode == "shared_schl5"
    assert record.feature_id == "110000123456"
    assert record.properties == {
        "pet14h": 41.7,
        "schl5": "110000123456",
        "typklar": "dense residential",
        "utci14h": 38.6,
        "t2m14h": 31.4,
        "uhi": 3.2,
    }
    assert {
        layer["feature_type"]
        for layer in record.layers.values()
    } == {"fis:pet", "fis:utci", "fis:temp", "fis:uhi"}

    graph = build_graph(record)
    observations = list(
        graph.subjects(CITY.metric, None)
    )
    flags = [
        graph.value(obs, CITY.isDemoValue).toPython()
        for obs in observations
    ]
    assert len(observations) == 4
    assert all(flag is False for flag in flags)

    result = run_official_heat(record)
    assert result["validation"]["conforms"] is True
    row = result["rows"][0]
    assert float(row["pet"]) == 41.7
    assert float(row["utci"]) == 38.6
    assert float(row["temp"]) == 31.4
    assert float(row["uhi"]) == 3.2
    assert result["authority"] == "human_decision_required"
    assert "not observation time" in result["caveat"].lower()
