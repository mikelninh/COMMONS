from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
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
METRICS = ("pet14h", "utci14h", "t2m14h", "uhi")
CONTEXT_FIELDS = ("schl5", "typklar")
INTEREST_FIELDS = CONTEXT_FIELDS + METRICS

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
class MetricLayer:
    metric: str
    feature_type: str
    fields: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BerlinHeatRecord:
    feature_type: str
    feature_id: str
    retrieved_at: str
    longitude: float
    latitude: float
    radius_m: float
    match_mode: str
    join_mode: str
    properties: dict[str, Any]
    layers: dict[str, dict[str, Any]]
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
            "User-Agent": "COMMONS-Semantic-City/0.3 (+https://github.com/mikelninh/COMMONS)",
            "Accept": "application/xml,text/xml,*/*;q=0.8",
        },
    )
    with urlopen(request, timeout=30) as response:
        return response.read()


def _xml(payload: bytes, context: str) -> ET.Element:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise WFSFetchError(
            f"Invalid XML from Berlin WFS during {context}: {exc}"
        ) from exc
    if "exception" in _local_name(root.tag).lower():
        detail = " ".join(
            text.strip() for text in root.itertext() if text.strip()
        )
        raise WFSFetchError(
            f"Berlin WFS error during {context}: {detail[:500]}"
        )
    return root


def _feature_types(
    fetch: Callable[[str], bytes] = _default_fetch,
) -> list[str]:
    root = _xml(
        fetch(
            _url(
                {
                    "SERVICE": "WFS",
                    "VERSION": "2.0.0",
                    "REQUEST": "GetCapabilities",
                }
            )
        ),
        "GetCapabilities",
    )
    names: list[str] = []
    for feature in root.iter():
        if _local_name(feature.tag) != "FeatureType":
            continue
        for child in feature:
            if _local_name(child.tag) == "Name" and child.text:
                names.append(child.text.strip())
                break
    if not names:
        raise WFSFetchError("Berlin WFS advertised no FeatureType names")
    return names


def _schema_fields(
    feature_type: str,
    fetch: Callable[[str], bytes],
) -> set[str]:
    schema = _xml(
        fetch(
            _url(
                {
                    "SERVICE": "WFS",
                    "VERSION": "2.0.0",
                    "REQUEST": "DescribeFeatureType",
                    "TYPENAMES": feature_type,
                }
            )
        ),
        f"DescribeFeatureType {feature_type}",
    )
    return {
        str(el.attrib.get("name", "")).lower()
        for el in schema.iter()
        if _local_name(el.tag) == "element"
        and el.attrib.get("name")
    }


def discover_metric_layers(
    fetch: Callable[[str], bytes] = _default_fetch,
) -> dict[str, MetricLayer]:
    """Discover the actual WFS layer that carries each heat metric.

    Berlin publishes Klimaanalysekarten as several feature types. The adapter
    intentionally discovers that split instead of assuming all climate fields
    live in one table.
    """
    feature_types = _feature_types(fetch)
    schemas: dict[str, set[str]] = {}

    def inspect(name: str) -> tuple[str, set[str]]:
        return name, _schema_fields(name, fetch)

    workers = min(8, max(1, len(feature_types)))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(inspect, feature_type): feature_type
            for feature_type in feature_types
        }
        for future in as_completed(futures):
            feature_type = futures[future]
            try:
                name, fields = future.result()
            except Exception:
                continue
            schemas[name] = fields

    layers: dict[str, MetricLayer] = {}
    for metric in METRICS:
        candidates = [
            (name, fields)
            for name, fields in schemas.items()
            if metric in fields
        ]
        if not candidates:
            overlaps = {
                name: sorted(set(INTEREST_FIELDS) & fields)
                for name, fields in schemas.items()
                if set(INTEREST_FIELDS) & fields
            }
            raise WFSFetchError(
                f"No FeatureType exposes '{metric}'. "
                f"Relevant discovered schemas: {overlaps}"
            )

        # Prefer a layer that also carries the shared ISU5 key; then prefer
        # richer context. Stable name ordering keeps discovery deterministic.
        candidates.sort(
            key=lambda item: (
                "schl5" in item[1],
                len(set(CONTEXT_FIELDS) & item[1]),
                len(set(INTEREST_FIELDS) & item[1]),
                item[0],
            ),
            reverse=True,
        )
        name, fields = candidates[0]
        layers[metric] = MetricLayer(
            metric=metric,
            feature_type=name,
            fields=tuple(sorted(fields)),
        )
    return layers


def _coerce(name: str, value: str) -> Any:
    value = value.strip()
    if name in METRICS:
        try:
            return float(value.replace(",", "."))
        except ValueError:
            return value
    return value


def _records(
    payload: bytes,
    allowed_fields: set[str] | None = None,
) -> list[tuple[str, dict[str, Any]]]:
    root = _xml(payload, "GetFeature")
    records: list[tuple[str, dict[str, Any]]] = []
    allowed = allowed_fields or set(INTEREST_FIELDS)
    for member in root.iter():
        if _local_name(member.tag) not in {"member", "featureMember"}:
            continue
        children = list(member)
        if not children:
            continue
        feature = children[0]
        feature_id = next(
            (
                value
                for key, value in feature.attrib.items()
                if _local_name(key) == "id"
            ),
            "",
        )
        props: dict[str, Any] = {}
        for el in feature.iter():
            if list(el) or el.text is None:
                continue
            key = _local_name(el.tag).lower()
            text = el.text.strip()
            if key in allowed and text:
                props[key] = _coerce(key, text)
        if props:
            records.append(
                (
                    feature_id
                    or str(props.get("schl5", "record")),
                    props,
                )
            )
    return records


def _project(
    longitude: float,
    latitude: float,
) -> tuple[float, float]:
    try:
        from pyproj import Transformer
    except ImportError as exc:
        raise WFSFetchError(
            "pyproj is required for Berlin point queries"
        ) from exc
    transformer = Transformer.from_crs(
        "EPSG:4326",
        "EPSG:25833",
        always_xy=True,
    )
    return transformer.transform(longitude, latitude)


def _fetch_metric(
    layer: MetricLayer,
    x: float,
    y: float,
    radius_m: float,
    fetch: Callable[[str], bytes],
    *,
    allow_fallback: bool,
) -> tuple[str, dict[str, Any], str]:
    available = set(layer.fields)
    requested = [
        field
        for field in (*CONTEXT_FIELDS, layer.metric)
        if field in available
    ]
    base: dict[str, Any] = {
        "SERVICE": "WFS",
        "VERSION": "2.0.0",
        "REQUEST": "GetFeature",
        "TYPENAMES": layer.feature_type,
        "COUNT": 8,
        "SRSNAME": "EPSG:25833",
    }
    if requested:
        base["PROPERTYNAME"] = ",".join(requested)

    point = dict(base)
    point["BBOX"] = (
        f"{x-radius_m},{y-radius_m},"
        f"{x+radius_m},{y+radius_m},EPSG:25833"
    )
    allowed = set(requested) | {layer.metric}

    try:
        found = _records(fetch(_url(point)), allowed)
    except WFSFetchError:
        # Some WFS deployments are fussy about PROPERTYNAME. Retrying without
        # projection keeps the spatial filter while preserving source fidelity.
        point.pop("PROPERTYNAME", None)
        found = _records(fetch(_url(point)), set(INTEREST_FIELDS))

    match_mode = "point_bbox"
    if not found and allow_fallback:
        fallback = dict(base)
        fallback.pop("PROPERTYNAME", None)
        found = _records(
            fetch(_url(fallback)),
            set(INTEREST_FIELDS),
        )
        match_mode = "fallback_first_feature"

    candidates = [
        item
        for item in found
        if isinstance(item[1].get(layer.metric), (int, float))
    ]
    if not candidates:
        raise WFSFetchError(
            f"No numeric '{layer.metric}' feature from "
            f"{layer.feature_type} near the requested point"
        )
    feature_id, props = candidates[0]
    return feature_id, props, match_mode


def fetch_record(
    longitude: float = 13.4132,
    latitude: float = 52.5219,
    radius_m: float = 20.0,
    fetch: Callable[[str], bytes] = _default_fetch,
    *,
    allow_fallback: bool = True,
) -> BerlinHeatRecord:
    layers = discover_metric_layers(fetch)
    x, y = _project(longitude, latitude)

    combined: dict[str, Any] = {}
    layer_records: dict[str, dict[str, Any]] = {}
    ids: list[str] = []
    shared_keys: list[str] = []
    modes: list[str] = []

    for metric in METRICS:
        layer = layers[metric]
        feature_id, props, match_mode = _fetch_metric(
            layer,
            x,
            y,
            radius_m,
            fetch,
            allow_fallback=allow_fallback,
        )
        combined[metric] = props[metric]
        for context in CONTEXT_FIELDS:
            if context in props and context not in combined:
                combined[context] = props[context]
        if props.get("schl5"):
            shared_keys.append(str(props["schl5"]))
        ids.append(feature_id)
        modes.append(match_mode)
        layer_records[metric] = {
            "feature_type": layer.feature_type,
            "feature_id": feature_id,
            "raw_field": metric,
            "value": props[metric],
            "schl5": props.get("schl5"),
            "typklar": props.get("typklar"),
            "match_mode": match_mode,
        }

    point_only = all(mode == "point_bbox" for mode in modes)
    same_key = (
        len(shared_keys) == len(METRICS)
        and len(set(shared_keys)) == 1
    )
    if same_key:
        feature_id = shared_keys[0]
        join_mode = "shared_schl5"
    else:
        feature_id = "spatial-" + _safe(
            f"{latitude:.5f}-{longitude:.5f}"
        )
        join_mode = "spatial_point"

    return BerlinHeatRecord(
        feature_type="multi-layer-wfs",
        feature_id=feature_id,
        retrieved_at=datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        longitude=longitude,
        latitude=latitude,
        radius_m=radius_m,
        match_mode=(
            "point_bbox"
            if point_only
            else "contains_fallback_feature"
        ),
        join_mode=join_mode,
        properties=combined,
        layers=layer_records,
    )


def _safe(value: str) -> str:
    return (
        re.sub(r"[^a-zA-Z0-9._-]+", "-", value)
        .strip("-")
        or "record"
    )


def build_graph(record: BerlinHeatRecord) -> Graph:
    """Transform official multi-layer WFS evidence to the shared ontology."""
    graph = Graph()
    graph.bind("city", CITY)
    graph.bind("prov", PROV)

    berlin = CITY["city/berlin"]
    graph.add((berlin, RDF.type, CITY.City))
    graph.add((berlin, RDFS.label, Literal("Berlin")))

    source = CITY["source/berlin-klimaanalyse-2022"]
    graph.add((source, RDF.type, CITY.EvidenceSource))
    graph.add(
        (
            source,
            RDFS.label,
            Literal("Klimaanalysekarten 2022"),
        )
    )
    graph.add(
        (
            source,
            CITY.publisher,
            Literal(
                "Senatsverwaltung für Stadtentwicklung, "
                "Bauen und Wohnen Berlin"
            ),
        )
    )
    graph.add(
        (
            source,
            CITY.endpoint,
            Literal(ENDPOINT, datatype=XSD.anyURI),
        )
    )
    graph.add(
        (
            source,
            CITY.evidenceClass,
            Literal("official-structural-modeled"),
        )
    )
    graph.add(
        (
            source,
            CITY.caveat,
            Literal(
                "Representative 2022 climate-model evidence; "
                "not current weather."
            ),
        )
    )

    key = _safe(record.feature_id)
    area = CITY[f"area/berlin-heat/{key}"]
    label = str(
        record.properties.get("schl5")
        or f"{record.latitude:.5f},{record.longitude:.5f}"
    )
    graph.add((area, RDF.type, CITY.Area))
    graph.add(
        (
            area,
            RDFS.label,
            Literal(f"Berlin climate location {label}"),
        )
    )
    graph.add((area, CITY.locatedIn, berlin))
    graph.add(
        (
            area,
            CITY.joinMode,
            Literal(record.join_mode),
        )
    )
    if "typklar" in record.properties:
        graph.add(
            (
                area,
                CITY.structureType,
                Literal(str(record.properties["typklar"])),
            )
        )

    units = {
        "pet14h": "degC",
        "utci14h": "degC",
        "t2m14h": "degC",
        "uhi": "K",
    }
    for metric in METRICS:
        value = record.properties.get(metric)
        layer = record.layers.get(metric, {})
        if not isinstance(value, (int, float)):
            continue

        evidence_key = _safe(
            f"{metric}-{layer.get('feature_id', metric)}"
        )
        evidence = CITY[
            f"evidence-record/berlin-heat/{evidence_key}"
        ]
        graph.add((evidence, RDF.type, CITY.EvidenceRecord))
        graph.add(
            (
                evidence,
                RDFS.label,
                Literal(
                    f"Berlin WFS {layer.get('feature_type', 'layer')} "
                    f"feature {layer.get('feature_id', '')}"
                ),
            )
        )
        graph.add((evidence, CITY.evidenceSource, source))
        graph.add(
            (
                evidence,
                CITY.sourceFeatureType,
                Literal(str(layer.get("feature_type", ""))),
            )
        )
        graph.add(
            (
                evidence,
                CITY.sourceFeatureId,
                Literal(str(layer.get("feature_id", ""))),
            )
        )
        graph.add(
            (
                evidence,
                CITY.matchMode,
                Literal(str(layer.get("match_mode", ""))),
            )
        )
        graph.add(
            (
                evidence,
                PROV.generatedAtTime,
                Literal(
                    record.retrieved_at,
                    datatype=XSD.dateTime,
                ),
            )
        )

        obs = CITY[
            f"observation/official-{metric}-{key}"
        ]
        graph.add((obs, RDF.type, CITY.Observation))
        graph.add(
            (obs, RDFS.label, Literal(f"{metric}: {value}"))
        )
        graph.add((obs, CITY.about, area))
        graph.add((obs, CITY.metric, Literal(metric)))
        graph.add(
            (
                obs,
                CITY.value,
                Literal(float(value), datatype=XSD.decimal),
            )
        )
        graph.add((obs, CITY.unit, Literal(units[metric])))
        graph.add((obs, CITY.evidenceSource, source))
        graph.add(
            (
                obs,
                CITY.evidenceClass,
                Literal("official-structural-modeled"),
            )
        )
        graph.add(
            (
                obs,
                CITY.isDemoValue,
                Literal(False, datatype=XSD.boolean),
            )
        )
        graph.add((obs, CITY.rawField, Literal(metric)))
        graph.add((obs, PROV.wasDerivedFrom, evidence))
        graph.add((area, CITY.hasObservation, obs))

    human = CITY["authority/municipal-human"]
    graph.add((human, RDF.type, CITY.HumanAuthority))
    graph.add(
        (
            human,
            RDFS.label,
            Literal("Accountable municipal decision-maker"),
        )
    )

    rec = CITY["recommendation/heat-official"]
    graph.add((rec, RDF.type, CITY.Recommendation))
    graph.add(
        (
            rec,
            RDFS.label,
            Literal("Heat evidence review"),
        )
    )
    graph.add(
        (
            rec,
            CITY.authority,
            Literal(
                Authority.HUMAN_DECISION_REQUIRED.value
            ),
        )
    )
    graph.add(
        (
            rec,
            CITY.requiresHumanApproval,
            Literal(True, datatype=XSD.boolean),
        )
    )
    graph.add((rec, CITY.controlledBy, human))
    graph.add(
        (
            rec,
            CITY.because,
            Literal(
                "Structural climate evidence can inform "
                "prioritisation, but current danger and vulnerable "
                "people require additional current and social evidence."
            ),
        )
    )
    return graph


def run_official_heat(
    record: BerlinHeatRecord,
) -> dict[str, Any]:
    graph = build_graph(record)
    validation = validate_graph(graph)
    if not validation["conforms"]:
        raise WFSFetchError(
            "Official heat graph failed SHACL: "
            f"{validation['summary']}"
        )

    rows: list[dict[str, Any]] = []
    for row in graph.query(OFFICIAL_HEAT_QUERY):
        item: dict[str, Any] = {}
        for name, value in row.asdict().items():
            if isinstance(value, Literal):
                item[str(name)] = value.toPython()
            elif isinstance(value, URIRef):
                text = str(value)
                item[str(name)] = (
                    text.replace(str(CITY), "city:")
                    if text.startswith(str(CITY))
                    else text
                )
            else:
                item[str(name)] = str(value)
        rows.append(item)

    return {
        "title": "Heat resilience — official Berlin evidence",
        "question": (
            "What does the official structural heat evidence say "
            "about this location, and what is still missing before action?"
        ),
        "authority": (
            Authority.HUMAN_DECISION_REQUIRED.value
        ),
        "recommendation": (
            "Use PET, UTCI, 14:00 air temperature and heat-island "
            "evidence for human review. Do not infer a current heat "
            "emergency or vulnerable residents without additional evidence."
        ),
        "caveat": (
            "Klimaanalysekarten 2022 model a representative "
            "autochthonous summer day. Retrieval time is not observation time."
        ),
        "query": "\n".join(
            line.rstrip()
            for line in OFFICIAL_HEAT_QUERY.strip().splitlines()
        ),
        "rows": rows,
        "validation": validation,
        "graph_stats": {"triples": len(graph)},
    }
