from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import re
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from rdflib import Graph, Literal, RDF, RDFS, URIRef, XSD

from commons.semantic_city import CITY, PROV, validate_graph

ENDPOINT = "https://geoportal.stadt-koeln.de/wss/service/baumkataster_extern_wfs/guest"
DATASET_URL = "https://data.gov.de/suche/daten/baumkataster-stadt-koln"

TREE_QUERY = """
PREFIX city: <https://commons.local/semantic-city/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?tree ?label ?species ?street ?sourceId WHERE {
  ?tree a city:UrbanTree ; rdfs:label ?label ; city:sourceObjectId ?sourceId .
  OPTIONAL { ?tree city:species ?species . }
  OPTIONAL { ?tree city:street ?street . }
}
"""


class CologneWFSFetchError(RuntimeError):
    pass


@dataclass(frozen=True)
class CologneTreeRecord:
    feature_type: str
    feature_id: str
    retrieved_at: str
    properties: dict[str, Any]
    normalized: dict[str, str]
    source_endpoint: str = ENDPOINT
    dataset_url: str = DATASET_URL
    license: str = "Datenlizenz Deutschland – Zero – Version 2.0"
    publisher: str = "Stadt Köln"

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
    with urlopen(request, timeout=40) as response:
        return response.read()


def _xml(payload: bytes, context: str) -> ET.Element:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise CologneWFSFetchError(
            f"Invalid XML from Cologne WFS during {context}: {exc}"
        ) from exc
    if "exception" in _local_name(root.tag).lower():
        detail = " ".join(
            text.strip() for text in root.itertext() if text.strip()
        )
        raise CologneWFSFetchError(
            f"Cologne WFS error during {context}: {detail[:500]}"
        )
    return root


def feature_types(
    fetch: Callable[[str], bytes] = _default_fetch,
) -> list[str]:
    for version in ("2.0.0", "1.1.0"):
        try:
            root = _xml(
                fetch(
                    _url(
                        {
                            "SERVICE": "WFS",
                            "VERSION": version,
                            "REQUEST": "GetCapabilities",
                        }
                    )
                ),
                "GetCapabilities",
            )
        except Exception:
            continue
        names: list[str] = []
        for feature in root.iter():
            if _local_name(feature.tag) != "FeatureType":
                continue
            for child in feature:
                if _local_name(child.tag) == "Name" and child.text:
                    names.append(child.text.strip())
                    break
        if names:
            return names
    raise CologneWFSFetchError(
        "Cologne WFS advertised no FeatureType names"
    )


def choose_tree_feature_type(names: list[str]) -> str:
    ranked = sorted(
        names,
        key=lambda name: (
            any(
                token in name.lower()
                for token in ("baum", "tree")
            ),
            "extern" in name.lower(),
            name,
        ),
        reverse=True,
    )
    if not ranked:
        raise CologneWFSFetchError(
            "No Cologne feature type available"
        )
    return ranked[0]


def _coerce(text: str) -> Any:
    value = text.strip()
    if not value:
        return value
    try:
        if re.fullmatch(r"[-+]?\d+", value):
            return int(value)
        if re.fullmatch(r"[-+]?\d+[.,]\d+", value):
            return float(value.replace(",", "."))
    except ValueError:
        pass
    return value


def _first_feature(
    payload: bytes,
) -> tuple[str, dict[str, Any]]:
    root = _xml(payload, "GetFeature")
    skip = {"boundedby", "pos", "poslist", "coordinates"}
    for member in root.iter():
        if _local_name(member.tag).lower() not in {
            "member",
            "featuremember",
        }:
            continue
        children = list(member)
        if not children:
            continue
        feature = children[0]
        feature_id = next(
            (
                value
                for key, value in feature.attrib.items()
                if _local_name(key).lower() == "id"
            ),
            "",
        )
        props: dict[str, Any] = {}
        for el in feature.iter():
            if list(el) or el.text is None:
                continue
            key = _local_name(el.tag)
            if key.lower() in skip:
                continue
            text = el.text.strip()
            if text and len(text) <= 500:
                props[key] = _coerce(text)
        if props:
            return (
                feature_id
                or str(next(iter(props.values()))),
                props,
            )
    raise CologneWFSFetchError(
        "Cologne WFS returned no scalar tree feature"
    )


def _get_feature(
    feature_type: str,
    fetch: Callable[[str], bytes],
) -> tuple[str, dict[str, Any]]:
    attempts = [
        {
            "SERVICE": "WFS",
            "VERSION": "2.0.0",
            "REQUEST": "GetFeature",
            "TYPENAMES": feature_type,
            "COUNT": 1,
        },
        {
            "SERVICE": "WFS",
            "VERSION": "1.1.0",
            "REQUEST": "GetFeature",
            "TYPENAME": feature_type,
            "MAXFEATURES": 1,
        },
    ]
    errors: list[str] = []
    for params in attempts:
        try:
            return _first_feature(fetch(_url(params)))
        except Exception as exc:
            errors.append(str(exc))
    raise CologneWFSFetchError(
        "Could not fetch Cologne tree feature: "
        + " | ".join(errors)
    )


def _pick(
    props: dict[str, Any],
    patterns: tuple[str, ...],
) -> str | None:
    for key, value in props.items():
        lowered = key.lower()
        if (
            any(pattern in lowered for pattern in patterns)
            and value not in (None, "")
        ):
            return str(value)
    return None


def normalize_properties(
    props: dict[str, Any],
) -> dict[str, str]:
    normalized: dict[str, str] = {}
    candidates = {
        "species": (
            "baumart",
            "gattung",
            "botan",
            "species",
            "artname",
        ),
        "street": (
            "strasse",
            "straße",
            "street",
            "standort",
            "adresse",
            "lage",
        ),
        "tree_number": (
            "baumnr",
            "baumnummer",
            "baum_nr",
            "treeid",
            "tree_id",
            "objekt",
        ),
        "status": (
            "status",
            "zustand",
            "vital",
            "pflege",
        ),
    }
    for target, patterns in candidates.items():
        value = _pick(props, patterns)
        if value:
            normalized[target] = value
    return normalized


def fetch_record(
    fetch: Callable[[str], bytes] = _default_fetch,
) -> CologneTreeRecord:
    names = feature_types(fetch)
    feature_type = choose_tree_feature_type(names)
    feature_id, props = _get_feature(feature_type, fetch)
    return CologneTreeRecord(
        feature_type=feature_type,
        feature_id=feature_id,
        retrieved_at=(
            datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        ),
        properties=props,
        normalized=normalize_properties(props),
    )


def _safe(value: str) -> str:
    return (
        re.sub(r"[^a-zA-Z0-9._-]+", "-", value)
        .strip("-")
        or "record"
    )


def build_graph(record: CologneTreeRecord) -> Graph:
    graph = Graph()
    graph.bind("city", CITY)
    graph.bind("prov", PROV)

    cologne = CITY["city/cologne"]
    graph.add((cologne, RDF.type, CITY.City))
    graph.add((cologne, RDFS.label, Literal("Köln")))

    source = CITY["source/cologne-tree-cadastre"]
    graph.add((source, RDF.type, CITY.EvidenceSource))
    graph.add(
        (
            source,
            RDFS.label,
            Literal("Baumkataster - Stadt Köln"),
        )
    )
    graph.add(
        (source, CITY.publisher, Literal(record.publisher))
    )
    graph.add(
        (
            source,
            CITY.endpoint,
            Literal(
                record.source_endpoint,
                datatype=XSD.anyURI,
            ),
        )
    )
    graph.add(
        (
            source,
            CITY.evidenceClass,
            Literal("official-operational-cadastre"),
        )
    )
    graph.add(
        (
            source,
            CITY.caveat,
            Literal(
                "Contains only trees managed by the City of "
                "Cologne and does not represent the complete urban "
                "tree population; positional accuracy is not "
                "guaranteed for construction surveying."
            ),
        )
    )

    key = _safe(record.feature_id)
    tree = CITY[f"asset/cologne-tree/{key}"]
    graph.add((tree, RDF.type, CITY.UrbanTree))
    label = (
        record.normalized.get("species")
        or record.normalized.get("tree_number")
        or record.feature_id
    )
    graph.add(
        (
            tree,
            RDFS.label,
            Literal(f"Cologne tree {label}"),
        )
    )
    graph.add((tree, CITY.locatedIn, cologne))
    graph.add(
        (
            tree,
            CITY.sourceObjectId,
            Literal(record.feature_id),
        )
    )
    if record.normalized.get("species"):
        graph.add(
            (
                tree,
                CITY.species,
                Literal(record.normalized["species"]),
            )
        )
    if record.normalized.get("street"):
        graph.add(
            (
                tree,
                CITY.street,
                Literal(record.normalized["street"]),
            )
        )
    if record.normalized.get("status"):
        graph.add(
            (
                tree,
                CITY.sourceStatus,
                Literal(record.normalized["status"]),
            )
        )

    evidence = CITY[
        f"evidence-record/cologne-tree/{key}"
    ]
    graph.add((evidence, RDF.type, CITY.EvidenceRecord))
    graph.add(
        (
            evidence,
            RDFS.label,
            Literal(
                f"Cologne WFS feature {record.feature_id}"
            ),
        )
    )
    graph.add((evidence, CITY.evidenceSource, source))
    graph.add(
        (
            evidence,
            CITY.sourceFeatureType,
            Literal(record.feature_type),
        )
    )
    graph.add(
        (
            evidence,
            CITY.sourceFeatureId,
            Literal(record.feature_id),
        )
    )
    graph.add(
        (
            evidence,
            CITY.rawPropertiesJson,
            Literal(
                json.dumps(
                    record.properties,
                    ensure_ascii=False,
                    sort_keys=True,
                )
            ),
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
    graph.add((tree, PROV.wasDerivedFrom, evidence))
    return graph


def run_official_tree(
    record: CologneTreeRecord,
) -> dict[str, Any]:
    graph = build_graph(record)
    validation = validate_graph(graph)
    if not validation["conforms"]:
        raise CologneWFSFetchError(
            "Cologne tree graph failed SHACL: "
            f"{validation['summary']}"
        )

    rows: list[dict[str, Any]] = []
    for row in graph.query(TREE_QUERY):
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
        "title": (
            "Portability proof — official Cologne tree cadastre"
        ),
        "question": (
            "Can the same semantic infrastructure ingest a "
            "different municipality and domain without "
            "Berlin-specific field assumptions?"
        ),
        "authority": "inform",
        "recommendation": (
            "Use the record as official municipal evidence with "
            "its coverage and surveying caveats intact; do not "
            "infer total canopy coverage from this cadastre alone."
        ),
        "caveat": (
            "The Cologne cadastre covers city-managed trees, not "
            "every tree in Cologne, and does not replace an "
            "official site survey."
        ),
        "query": "\n".join(
            line.rstrip()
            for line in TREE_QUERY.strip().splitlines()
        ),
        "rows": rows,
        "validation": validation,
        "graph_stats": {"triples": len(graph)},
    }
