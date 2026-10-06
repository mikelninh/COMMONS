from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import re
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from rdflib import Graph, Literal, RDF, RDFS, URIRef, XSD

from commons.semantic_city import Authority, CITY, PROV, validate_graph

ENDPOINT = "https://gdi.berlin.de/services/wfs/ua_klimaanalyse_2022"
FIELDS = ("schl5", "typklar", "pet14h", "utci14h", "t2m14h", "uhi")
NUMERIC_FIELDS = {"pet14h", "utci14h", "t2m14h", "uhi"}
OFFICIAL_HEAT_QUERY = """
PREFIX city: <https://commons.local/semantic-city/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?area ?label ?pet ?utci ?temp ?uhi WHERE {
  ?area a city:Area ; rdfs:label ?label .
  OPTIONAL { ?p city:about ?area ; city:metric "pet14h" ; city:value ?pet . }
  OPTIONAL { ?u city:about ?area ; city:metric "utci14h" ; city:value ?utci . }
  OPTIONAL { ?t city:about ?area ; city:metric "t2m14h" ; city:value ?temp . }
  OPTIONAL { ?h city:about ?area ; city:metric "uhi" ; city:value ?uhi . }
  FILTER(BOUND(?pet) || BOUND(?utci) || BOUND(?temp) || BOUND(?uhi))
}
"""


class WFSFetchError(RuntimeError):
    pass


@dataclass(frozen=True)
class BerlinHeatRecord:
    feature_type: str
    feature_id: str
    retrieved_at: str
    longitude: float
    latitude: float
    radius_m: float
    match_mode: str
    properties: dict[str, Any]
    source_endpoint: str = ENDPOINT
    source_crs: str = "EPSG:25833"
    dataset_model_year: str = "2022"
    dataset_release_date: str = "2024-06-01"
    license: str = "Datenlizenz Deutschland – Zero – Version 2.0"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].split(":")[-1]


def _url(params: dict[str, Any]) -> str:
    return f"{ENDPOINT}?{urlencode(params, doseq=True)}"


def _default_fetch(url: str) -> bytes:
    request = Request(
        url,
        headers={
            "User-Agent": "COMMONS-Semantic-City/0.2 (+https://github.com/mikelninh/COMMONS)",
            "Accept": "application/xml,text/xml,*/*;q=0.8",
        },
    )
    with urlopen(request, timeout=30) as response:
        return response.read()


def _xml(payload: bytes, context: str) -> ET.Element:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise WFSFetchError(f"Invalid XML from Berlin WFS during {context}: {exc}") from exc
    if "exception" in _local_name(root.tag).lower():
        detail = " ".join(text.strip() for text in root.itertext() if text.strip())
        raise WFSFetchError(f"Berlin WFS error during {context}: {detail[:500]}")
    return root


def discover_feature_type(fetch: Callable[[str], bytes] = _default_fetch) -> tuple[str, set[str]]:
    """Discover the ISU5 climate layer and verify its documented schema."""
    root = _xml(fetch(_url({
        "SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetCapabilities"
    })), "GetCapabilities")
    feature_types: list[str] = []
    for feature in root.iter():
        if _local_name(feature.tag) != "FeatureType":
            continue
        for child in feature:
            if _local_name(child.tag) == "Name" and child.text:
                feature_types.append(child.text.strip())
                break
    if not feature_types:
        raise WFSFetchError("Berlin WFS advertised no FeatureType names")

    required = {"pet14h", "utci14h", "t2m14h"}
    nearest: tuple[str, set[str]] | None = None
    score = -1
    for feature_type in feature_types:
        try:
            schema = _xml(fetch(_url({
                "SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "DescribeFeatureType",
                "TYPENAMES": feature_type,
            })), f"DescribeFeatureType {feature_type}")
        except WFSFetchError:
            continue
        fields = {
            str(el.attrib.get("name", "")).lower()
            for el in schema.iter()
            if _local_name(el.tag) == "element" and el.attrib.get("name")
        }
        overlap = len(set(FIELDS) & fields)
        if overlap > score:
            nearest, score = (feature_type, fields), overlap
        if required.issubset(fields):
            return feature_type, fields
    if nearest:
        raise WFSFetchError(
            "No FeatureType exposes PET/UTCI/air-temperature fields; closest was "
            f"{nearest[0]} with {sorted(set(FIELDS) & nearest[1])}"
        )
    raise WFSFetchError("Could not inspect a Berlin climate FeatureType schema")


def _coerce(name: str, value: str) -> Any:
    value = value.strip()
    if name in NUMERIC_FIELDS:
        try:
            return float(value.replace(",", "."))
        except ValueError:
            return value
    return value


def _records(payload: bytes) -> list[tuple[str, dict[str, Any]]]:
    root = _xml(payload, "GetFeature")
    records: list[tuple[str, dict[str, Any]]] = []
    for member in root.iter():
        if _local_name(member.tag) not in {"member", "featureMember"}:
            continue
        children = list(member)
        if not children:
            continue
        feature = children[0]
        feature_id = next(
            (value for key, value in feature.attrib.items() if _local_name(key) == "id"), ""
        )
        props: dict[str, Any] = {}
        for el in feature.iter():
            if list(el) or el.text is None:
                continue
            key = _local_name(el.tag).lower()
            text = el.text.strip()
            if key in FIELDS and text:
                props[key] = _coerce(key, text)
        if props:
            records.append((feature_id or str(props.get("schl5", "record")), props))
    return records


def _project(longitude: float, latitude: float) -> tuple[float, float]:
    try:
        from pyproj import Transformer
    except ImportError as exc:
        raise WFSFetchError("pyproj is required for Berlin point queries") from exc
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:25833", always_xy=True)
    return transformer.transform(longitude, latitude)


def fetch_record(
    longitude: float = 13.4132,
    latitude: float = 52.5219,
    radius_m: float = 20.0,
    fetch: Callable[[str], bytes] = _default_fetch,
    *,
    allow_fallback: bool = True,
) -> BerlinHeatRecord:
    feature_type, fields = discover_feature_type(fetch)
    x, y = _project(longitude, latitude)
    properties = [field for field in FIELDS if field in fields]
    base = {
        "SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature",
        "TYPENAMES": feature_type, "COUNT": 8, "SRSNAME": "EPSG:25833",
    }
    if properties:
        base["PROPERTYNAME"] = ",".join(properties)
    point = dict(base)
    point["BBOX"] = f"{x-radius_m},{y-radius_m},{x+radius_m},{y+radius_m},EPSG:25833"

    try:
        found = _records(fetch(_url(point)))
    except WFSFetchError:
        point.pop("PROPERTYNAME", None)
        found = _records(fetch(_url(point)))

    match_mode = "point_bbox"
    if not found and allow_fallback:
        fallback = dict(base)
        fallback.pop("PROPERTYNAME", None)
        found = _records(fetch(_url(fallback)))
        match_mode = "fallback_first_feature"
    if not found:
        raise WFSFetchError(f"No Berlin climate feature near {latitude:.5f},{longitude:.5f}")

    feature_id, props = max(found, key=lambda item: sum(f in item[1] for f in NUMERIC_FIELDS))
    if not (set(props) & NUMERIC_FIELDS):
        raise WFSFetchError("Feature had none of the documented numeric heat fields")
    return BerlinHeatRecord(
        feature_type=feature_type,
        feature_id=feature_id,
        retrieved_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        longitude=longitude,
        latitude=latitude,
        radius_m=radius_m,
        match_mode=match_mode,
        properties=props,
    )


def _safe(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-") or "record"


def build_graph(record: BerlinHeatRecord) -> Graph:
    """Transform one official record to the shared Semantic City vocabulary."""
    graph = Graph()
    graph.bind("city", CITY)
    graph.bind("prov", PROV)

    berlin = CITY["city/berlin"]
    graph.add((berlin, RDF.type, CITY.City))
    graph.add((berlin, RDFS.label, Literal("Berlin")))

    source = CITY["source/berlin-klimaanalyse-2022"]
    graph.add((source, RDF.type, CITY.EvidenceSource))
    graph.add((source, RDFS.label, Literal("Klimaanalysekarten 2022")))
    graph.add((source, CITY.publisher, Literal("Senatsverwaltung für Stadtentwicklung, Bauen und Wohnen Berlin")))
    graph.add((source, CITY.endpoint, Literal(ENDPOINT, datatype=XSD.anyURI)))
    graph.add((source, CITY.evidenceClass, Literal("official-structural-modeled")))
    graph.add((source, CITY.caveat, Literal("Representative 2022 climate-model evidence; not current weather.")))

    key = _safe(record.feature_id)
    area = CITY[f"area/berlin-heat/{key}"]
    label = str(record.properties.get("schl5") or record.feature_id)
    graph.add((area, RDF.type, CITY.Area))
    graph.add((area, RDFS.label, Literal(f"Berlin climate feature {label}")))
    graph.add((area, CITY.locatedIn, berlin))
    if "typklar" in record.properties:
        graph.add((area, CITY.structureType, Literal(str(record.properties["typklar"]))))

    evidence = CITY[f"evidence-record/berlin-heat/{key}"]
    graph.add((evidence, RDF.type, CITY.EvidenceRecord))
    graph.add((evidence, RDFS.label, Literal(f"Berlin WFS feature {record.feature_id}")))
    graph.add((evidence, CITY.evidenceSource, source))
    graph.add((evidence, CITY.sourceFeatureType, Literal(record.feature_type)))
    graph.add((evidence, CITY.sourceFeatureId, Literal(record.feature_id)))
    graph.add((evidence, CITY.matchMode, Literal(record.match_mode)))
    graph.add((evidence, PROV.generatedAtTime, Literal(record.retrieved_at, datatype=XSD.dateTime)))

    units = {"pet14h": "degC", "utci14h": "degC", "t2m14h": "degC", "uhi": "K"}
    for field in ("pet14h", "utci14h", "t2m14h", "uhi"):
        value = record.properties.get(field)
        if not isinstance(value, (int, float)):
            continue
        obs = CITY[f"observation/official-{field}-{key}"]
        graph.add((obs, RDF.type, CITY.Observation))
        graph.add((obs, RDFS.label, Literal(f"{field}: {value}")))
        graph.add((obs, CITY.about, area))
        graph.add((obs, CITY.metric, Literal(field)))
        graph.add((obs, CITY.value, Literal(float(value), datatype=XSD.decimal)))
        graph.add((obs, CITY.unit, Literal(units[field])))
        graph.add((obs, CITY.evidenceSource, source))
        graph.add((obs, CITY.evidenceClass, Literal("official-structural-modeled")))
        graph.add((obs, CITY.isDemoValue, Literal(False, datatype=XSD.boolean)))
        graph.add((obs, CITY.rawField, Literal(field)))
        graph.add((obs, PROV.wasDerivedFrom, evidence))
        graph.add((area, CITY.hasObservation, obs))

    human = CITY["authority/municipal-human"]
    graph.add((human, RDF.type, CITY.HumanAuthority))
    graph.add((human, RDFS.label, Literal("Accountable municipal decision-maker")))
    rec = CITY["recommendation/heat-official"]
    graph.add((rec, RDF.type, CITY.Recommendation))
    graph.add((rec, RDFS.label, Literal("Heat evidence review")))
    graph.add((rec, CITY.authority, Literal(Authority.HUMAN_DECISION_REQUIRED.value)))
    graph.add((rec, CITY.requiresHumanApproval, Literal(True, datatype=XSD.boolean)))
    graph.add((rec, CITY.controlledBy, human))
    graph.add((rec, CITY.because, Literal(
        "Structural climate evidence can inform prioritisation, but current danger and vulnerable people require additional current and social evidence."
    )))
    return graph


def run_official_heat(record: BerlinHeatRecord) -> dict[str, Any]:
    graph = build_graph(record)
    validation = validate_graph(graph)
    if not validation["conforms"]:
        raise WFSFetchError(f"Official heat graph failed SHACL: {validation['summary']}")
    rows = []
    for row in graph.query(OFFICIAL_HEAT_QUERY):
        item: dict[str, Any] = {}
        for name, value in row.asdict().items():
            if isinstance(value, Literal):
                item[str(name)] = value.toPython()
            elif isinstance(value, URIRef):
                text = str(value)
                item[str(name)] = text.replace(str(CITY), "city:") if text.startswith(str(CITY)) else text
            else:
                item[str(name)] = str(value)
        rows.append(item)
    return {
        "title": "Heat resilience — official Berlin evidence",
        "question": "What does the official structural heat evidence say about this area, and what is still missing before action?",
        "authority": Authority.HUMAN_DECISION_REQUIRED.value,
        "recommendation": (
            "Use PET, UTCI, 14:00 air temperature and heat-island evidence for human review. "
            "Do not infer a current heat emergency or vulnerable residents without additional evidence."
        ),
        "caveat": (
            "Klimaanalysekarten 2022 model a representative autochthonous summer day. "
            "Retrieval time is not observation time."
        ),
        "query": "\n".join(line.rstrip() for line in OFFICIAL_HEAT_QUERY.strip().splitlines()),
        "rows": rows,
        "validation": validation,
        "graph_stats": {"triples": len(graph)},
    }
