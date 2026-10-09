from urllib.parse import parse_qs, urlparse

from rdflib import RDF

from commons.cologne_tree_wfs import (
    build_graph,
    choose_tree_feature_type,
    fetch_record,
    normalize_properties,
    run_official_tree,
)
from commons.semantic_city import CITY

CAPABILITIES = b'''<wfs:WFS_Capabilities xmlns:wfs="http://www.opengis.net/wfs/2.0">
<wfs:FeatureTypeList>
<wfs:FeatureType><wfs:Name>koeln:stadtbezirke</wfs:Name></wfs:FeatureType>
<wfs:FeatureType><wfs:Name>koeln:baumkataster_extern</wfs:Name></wfs:FeatureType>
</wfs:FeatureTypeList></wfs:WFS_Capabilities>'''

FEATURE = b'''<wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs/2.0" xmlns:gml="http://www.opengis.net/gml/3.2" xmlns:k="https://example.test/koeln">
<wfs:member><k:baumkataster_extern gml:id="baum.4711">
<k:BAUMNUMMER>K-4711</k:BAUMNUMMER>
<k:BAUMART>Winter-Linde</k:BAUMART>
<k:STRASSE>Teststrasse</k:STRASSE>
<k:STATUS>Bestand</k:STATUS>
</k:baumkataster_extern></wfs:member></wfs:FeatureCollection>'''


def fake_wfs(url: str) -> bytes:
    q = {
        k.upper(): v
        for k, v in parse_qs(urlparse(url).query).items()
    }
    request = q["REQUEST"][0].lower()
    if request == "getcapabilities":
        return CAPABILITIES
    if request == "getfeature":
        return FEATURE
    raise AssertionError(url)


def test_feature_type_discovery_prefers_tree_layer() -> None:
    assert choose_tree_feature_type(
        [
            "koeln:stadtbezirke",
            "koeln:baumkataster_extern",
        ]
    ) == "koeln:baumkataster_extern"


def test_normalization_is_schema_tolerant() -> None:
    normalized = normalize_properties(
        {
            "BAUMART": "Linde",
            "STRASSE": "Domstrasse",
            "BAUMNUMMER": "12",
        }
    )
    assert normalized["species"] == "Linde"
    assert normalized["street"] == "Domstrasse"
    assert normalized["tree_number"] == "12"


def test_official_cologne_record_flows_to_shared_rdf_contract() -> None:
    record = fetch_record(fetch=fake_wfs)
    assert record.feature_type == "koeln:baumkataster_extern"
    assert record.feature_id == "baum.4711"
    assert record.normalized["species"] == "Winter-Linde"

    graph = build_graph(record)
    trees = list(
        graph.subjects(RDF.type, CITY.UrbanTree)
    )
    assert trees
    assert (
        graph.value(trees[0], CITY.species).toPython()
        == "Winter-Linde"
    )

    result = run_official_tree(record)
    assert result["validation"]["conforms"] is True
    assert result["rows"][0]["species"] == "Winter-Linde"
    assert result["authority"] == "inform"
    assert "not every tree" in result["caveat"].lower()
