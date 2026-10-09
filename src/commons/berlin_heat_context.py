from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import math
import re
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from rdflib import Graph, Literal, RDF, RDFS, URIRef, XSD

from commons.berlin_heat_wfs import (
    BerlinHeatRecord,
    build_graph as build_heat_graph,
    fetch_record as fetch_heat_record,
)
from commons.semantic_city import Authority, CITY, PROV, validate_graph

JUSTICE_ENDPOINT = (
    "https://gdi.berlin.de/services/wfs/"
    "ua_umweltgerechtigkeit2023"
)
JUSTICE_TYPE = (
    "ua_umweltgerechtigkeit2023:"
    "z_gesamt_umwelt2023"
)
GREEN_ENDPOINT = (
    "https://gdi.berlin.de/services/wfs/gruenanlagen"
)
GREEN_TYPE = "gruenanlagen:gruenanlagen"
HOSPITAL_ENDPOINT = (
    "https://gdi.berlin.de/services/wfs/krankenhaeuser"
)
HOSPITAL_TYPES = (
    "krankenhaeuser:plankrankenhaeuser",
    "krankenhaeuser:weitere_krankenhaeuser",
)

CROSS_DOMAIN_QUERY = """
PREFIX city: <https://commons.local/semantic-city/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT
  ?area ?pet ?utci ?uhi
  ?plan ?planName ?multipleBurden ?bioclimate
  ?greenProvision ?socialStatus
  ?greenDistance ?greenName
  ?hospitalDistance ?hospitalName ?hospitalBeds
WHERE {
  ?area a city:Area ;
        city:overlapsPlanningArea ?plan ;
        city:nearestPublicGreen ?green ;
        city:nearestHospital ?hospital .

  ?p city:about ?area ; city:metric "pet14h" ; city:value ?pet .
  ?u city:about ?area ; city:metric "utci14h" ; city:value ?utci .
  ?h city:about ?area ; city:metric "uhi" ; city:value ?uhi .

  ?plan rdfs:label ?planName .
  ?m city:about ?plan ;
     city:metric "multipleBurdenCategory" ;
     city:value ?multipleBurden .
  ?b city:about ?plan ;
     city:metric "bioclimateBurden" ;
     city:value ?bioclimate .
  ?g city:about ?plan ;
     city:metric "greenProvision" ;
     city:value ?greenProvision .
  ?s city:about ?plan ;
     city:metric "socialStatusIndex" ;
     city:value ?socialStatus .

  ?green rdfs:label ?greenName .
  ?gd city:about ?area ;
      city:metric "nearestPublicGreenDistanceM" ;
      city:value ?greenDistance .

  ?hospital rdfs:label ?hospitalName .
  ?hd city:about ?area ;
      city:metric "nearestHospitalDistanceM" ;
      city:value ?hospitalDistance .
  OPTIONAL {
    ?beds city:about ?hospital ;
          city:metric "reportedBeds" ;
          city:value ?hospitalBeds .
  }
}
"""


class BerlinContextFetchError(RuntimeError):
    pass


@dataclass(frozen=True)
class JusticeRecord:
    feature_id: str
    planning_area_id: str
    planning_area_name: str
    multiple_burden: str | None
    bioclimate: str | None
    green_provision: str | None
    noise: str | None
    air: str | None
    social_status: str | None
    population_band: str | None
    retrieved_at: str
    raw_properties: dict[str, Any]
    source_endpoint: str = JUSTICE_ENDPOINT
    feature_type: str = JUSTICE_TYPE

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NearbyPlaceRecord:
    feature_id: str
    feature_type: str
    name: str
    distance_m: float
    properties: dict[str, Any]
    retrieved_at: str
    source_endpoint: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BerlinHeatDecisionContext:
    longitude: float
    latitude: float
    retrieved_at: str
    heat: BerlinHeatRecord
    justice: JusticeRecord
    nearest_green: NearbyPlaceRecord
    nearest_hospital: NearbyPlaceRecord
    green_features_within_radius: int
    green_radius_m: float
    hospital_radius_m: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _default_fetch_json(url: str) -> dict[str, Any]:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "COMMONS-Semantic-City/0.5 "
                "(+https://github.com/mikelninh/COMMONS)"
            ),
            "Accept": "application/json,*/*;q=0.8",
        },
    )
    with urlopen(request, timeout=35) as response:
        return json.load(response)


def _wfs_geojson(
    endpoint: str,
    feature_type: str,
    longitude: float,
    latitude: float,
    radius_m: float,
    count: int,
    fetch_json: Callable[[str], dict[str, Any]],
) -> list[dict[str, Any]]:
    if radius_m <= 0:
        raise BerlinContextFetchError(
            "radius_m must be positive"
        )

    lat_delta = radius_m / 110_540.0
    cos_lat = max(
        0.1,
        math.cos(math.radians(latitude)),
    )
    lon_delta = radius_m / (111_320.0 * cos_lat)
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": feature_type,
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
        "count": str(count),
        "bbox": (
            f"{longitude-lon_delta},"
            f"{latitude-lat_delta},"
            f"{longitude+lon_delta},"
            f"{latitude+lat_delta},"
            "EPSG:4326"
        ),
    }
    url = endpoint + "?" + urlencode(params)
    try:
        payload = fetch_json(url)
    except Exception as exc:
        raise BerlinContextFetchError(
            f"WFS request failed for {feature_type}: {exc}"
        ) from exc

    features = payload.get("features")
    if not isinstance(features, list):
        raise BerlinContextFetchError(
            f"WFS returned no feature list for {feature_type}"
        )
    return [
        feature
        for feature in features
        if isinstance(feature, dict)
    ]


def _rings(
    geometry: dict[str, Any] | None,
) -> list[list[list[float]]]:
    if not geometry:
        return []
    kind = geometry.get("type")
    coords = geometry.get("coordinates")
    if kind == "Polygon" and isinstance(coords, list):
        return [
            ring
            for ring in coords
            if isinstance(ring, list)
        ]
    if kind == "MultiPolygon" and isinstance(coords, list):
        return [
            ring
            for polygon in coords
            if isinstance(polygon, list)
            for ring in polygon
            if isinstance(ring, list)
        ]
    return []


def _point_in_ring(
    longitude: float,
    latitude: float,
    ring: list[list[float]],
) -> bool:
    inside = False
    j = len(ring) - 1
    for i, point in enumerate(ring):
        if (
            not isinstance(point, list)
            or len(point) < 2
        ):
            j = i
            continue
        xi, yi = float(point[0]), float(point[1])
        pj = ring[j]
        if (
            not isinstance(pj, list)
            or len(pj) < 2
        ):
            j = i
            continue
        xj, yj = float(pj[0]), float(pj[1])
        crosses = (
            (yi > latitude) != (yj > latitude)
        ) and (
            longitude
            < (
                (xj - xi)
                * (latitude - yi)
                / ((yj - yi) or 1e-15)
                + xi
            )
        )
        if crosses:
            inside = not inside
        j = i
    return inside


def _contains(
    geometry: dict[str, Any] | None,
    longitude: float,
    latitude: float,
) -> bool:
    rings = _rings(geometry)
    if not rings:
        return False
    # GeoJSON outer rings are followed by optional holes.
    # For our WFS selection, any outer-ring hit is sufficient
    # to choose the correct planning-area feature.
    return any(
        _point_in_ring(
            longitude,
            latitude,
            ring,
        )
        for ring in rings
    )


def _xy_m(
    longitude: float,
    latitude: float,
    origin_lon: float,
    origin_lat: float,
) -> tuple[float, float]:
    return (
        (
            longitude - origin_lon
        )
        * 111_320.0
        * math.cos(math.radians(origin_lat)),
        (latitude - origin_lat) * 110_540.0,
    )


def _segment_distance(
    ax: float,
    ay: float,
    bx: float,
    by: float,
) -> float:
    dx = bx - ax
    dy = by - ay
    denom = dx * dx + dy * dy
    if denom <= 1e-12:
        return math.hypot(ax, ay)
    t = max(
        0.0,
        min(
            1.0,
            -((ax * dx) + (ay * dy)) / denom,
        ),
    )
    return math.hypot(
        ax + t * dx,
        ay + t * dy,
    )


def _distance_to_geometry_m(
    geometry: dict[str, Any] | None,
    longitude: float,
    latitude: float,
) -> float:
    if not geometry:
        return float("inf")

    kind = geometry.get("type")
    coords = geometry.get("coordinates")

    if (
        kind == "Point"
        and isinstance(coords, list)
        and len(coords) >= 2
    ):
        x, y = _xy_m(
            float(coords[0]),
            float(coords[1]),
            longitude,
            latitude,
        )
        return math.hypot(x, y)

    if _contains(
        geometry,
        longitude,
        latitude,
    ):
        return 0.0

    best = float("inf")
    for ring in _rings(geometry):
        clean = [
            point
            for point in ring
            if isinstance(point, list)
            and len(point) >= 2
        ]
        for a, b in zip(
            clean,
            clean[1:],
            strict=False,
        ):
            ax, ay = _xy_m(
                float(a[0]),
                float(a[1]),
                longitude,
                latitude,
            )
            bx, by = _xy_m(
                float(b[0]),
                float(b[1]),
                longitude,
                latitude,
            )
            best = min(
                best,
                _segment_distance(
                    ax,
                    ay,
                    bx,
                    by,
                ),
            )
    return best


def fetch_justice(
    longitude: float,
    latitude: float,
    fetch_json: Callable[
        [str],
        dict[str, Any],
    ] = _default_fetch_json,
) -> JusticeRecord:
    features = _wfs_geojson(
        JUSTICE_ENDPOINT,
        JUSTICE_TYPE,
        longitude,
        latitude,
        radius_m=180.0,
        count=8,
        fetch_json=fetch_json,
    )
    if not features:
        raise BerlinContextFetchError(
            "No environmental-justice feature returned"
        )

    containing = [
        feature
        for feature in features
        if _contains(
            feature.get("geometry"),
            longitude,
            latitude,
        )
    ]
    feature = (
        containing[0]
        if containing
        else min(
            features,
            key=lambda item: _distance_to_geometry_m(
                item.get("geometry"),
                longitude,
                latitude,
            ),
        )
    )
    props = feature.get("properties") or {}
    return JusticeRecord(
        feature_id=str(
            feature.get("id")
            or props.get("plr_id")
            or "justice-record"
        ),
        planning_area_id=str(
            props.get("plr_id") or ""
        ),
        planning_area_name=str(
            props.get("plr_name")
            or "Berlin planning area"
        ),
        multiple_burden=_optional_text(
            props.get("kategorie")
        ),
        bioclimate=_optional_text(
            props.get("bioklima")
        ),
        green_provision=_optional_text(
            props.get("gruenvers")
        ),
        noise=_optional_text(
            props.get("laerm")
        ),
        air=_optional_text(
            props.get("luft")
        ),
        social_status=_optional_text(
            props.get("status_ind")
        ),
        population_band=_optional_text(
            props.get("einwohner")
        ),
        retrieved_at=_now(),
        raw_properties=props,
    )


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _nearest_record(
    features: list[dict[str, Any]],
    feature_type: str,
    endpoint: str,
    longitude: float,
    latitude: float,
    name_fields: tuple[str, ...],
) -> NearbyPlaceRecord:
    if not features:
        raise BerlinContextFetchError(
            f"No nearby features returned for {feature_type}"
        )

    ranked = sorted(
        features,
        key=lambda item: _distance_to_geometry_m(
            item.get("geometry"),
            longitude,
            latitude,
        ),
    )
    feature = ranked[0]
    props = feature.get("properties") or {}
    name = next(
        (
            str(props[field]).strip()
            for field in name_fields
            if props.get(field)
            and str(props[field]).strip()
        ),
        str(feature.get("id") or feature_type),
    )
    return NearbyPlaceRecord(
        feature_id=str(
            feature.get("id") or name
        ),
        feature_type=feature_type,
        name=name,
        distance_m=round(
            _distance_to_geometry_m(
                feature.get("geometry"),
                longitude,
                latitude,
            ),
            1,
        ),
        properties=props,
        retrieved_at=_now(),
        source_endpoint=endpoint,
    )


def fetch_nearest_green(
    longitude: float,
    latitude: float,
    radius_m: float = 1_200.0,
    fetch_json: Callable[
        [str],
        dict[str, Any],
    ] = _default_fetch_json,
) -> tuple[NearbyPlaceRecord, int]:
    features = _wfs_geojson(
        GREEN_ENDPOINT,
        GREEN_TYPE,
        longitude,
        latitude,
        radius_m=radius_m,
        count=180,
        fetch_json=fetch_json,
    )
    record = _nearest_record(
        features,
        GREEN_TYPE,
        GREEN_ENDPOINT,
        longitude,
        latitude,
        (
            "namenr",
            "namezusatz",
            "planname",
            "objartname",
        ),
    )
    return record, len(features)


def fetch_nearest_hospital(
    longitude: float,
    latitude: float,
    radius_m: float = 4_000.0,
    fetch_json: Callable[
        [str],
        dict[str, Any],
    ] = _default_fetch_json,
) -> NearbyPlaceRecord:
    candidates: list[NearbyPlaceRecord] = []
    for feature_type in HOSPITAL_TYPES:
        features = _wfs_geojson(
            HOSPITAL_ENDPOINT,
            feature_type,
            longitude,
            latitude,
            radius_m=radius_m,
            count=100,
            fetch_json=fetch_json,
        )
        if not features:
            continue
        candidates.append(
            _nearest_record(
                features,
                feature_type,
                HOSPITAL_ENDPOINT,
                longitude,
                latitude,
                (
                    "kkh_standort",
                    "kkh",
                    "name",
                ),
            )
        )
    if not candidates:
        raise BerlinContextFetchError(
            "No hospital features returned"
        )
    return min(
        candidates,
        key=lambda item: item.distance_m,
    )


def fetch_context(
    longitude: float = 13.4132,
    latitude: float = 52.5219,
    *,
    fetch_json: Callable[
        [str],
        dict[str, Any],
    ] = _default_fetch_json,
    heat_fetch: Callable[[str], bytes] | None = None,
) -> BerlinHeatDecisionContext:
    heat_kwargs: dict[str, Any] = {
        "longitude": longitude,
        "latitude": latitude,
        "radius_m": 25.0,
        "allow_fallback": False,
    }
    if heat_fetch is not None:
        heat_kwargs["fetch"] = heat_fetch
    heat = fetch_heat_record(**heat_kwargs)
    justice = fetch_justice(
        longitude,
        latitude,
        fetch_json,
    )
    green, green_count = fetch_nearest_green(
        longitude,
        latitude,
        fetch_json=fetch_json,
    )
    hospital = fetch_nearest_hospital(
        longitude,
        latitude,
        fetch_json=fetch_json,
    )
    return BerlinHeatDecisionContext(
        longitude=longitude,
        latitude=latitude,
        retrieved_at=_now(),
        heat=heat,
        justice=justice,
        nearest_green=green,
        nearest_hospital=hospital,
        green_features_within_radius=green_count,
        green_radius_m=1_200.0,
        hospital_radius_m=4_000.0,
    )


def _safe(value: str) -> str:
    return (
        re.sub(
            r"[^a-zA-Z0-9._-]+",
            "-",
            value,
        )
        .strip("-")
        or "record"
    )


def _source(
    graph: Graph,
    local: str,
    label: str,
    publisher: str,
    endpoint: str,
    evidence_class: str,
    caveat: str,
) -> URIRef:
    node = CITY[f"source/{local}"]
    graph.add((node, RDF.type, CITY.EvidenceSource))
    graph.add((node, RDFS.label, Literal(label)))
    graph.add((node, CITY.publisher, Literal(publisher)))
    graph.add(
        (
            node,
            CITY.endpoint,
            Literal(endpoint, datatype=XSD.anyURI),
        )
    )
    graph.add(
        (
            node,
            CITY.evidenceClass,
            Literal(evidence_class),
        )
    )
    graph.add((node, CITY.caveat, Literal(caveat)))
    return node


def _official_observation(
    graph: Graph,
    obs_id: str,
    subject: URIRef,
    metric: str,
    value: Any,
    source: URIRef,
    derived_from: URIRef | None = None,
    unit: str | None = None,
) -> URIRef:
    obs = CITY[f"observation/{obs_id}"]
    graph.add((obs, RDF.type, CITY.Observation))
    graph.add(
        (
            obs,
            RDFS.label,
            Literal(f"{metric}: {value}"),
        )
    )
    graph.add((obs, CITY.about, subject))
    graph.add((obs, CITY.metric, Literal(metric)))
    graph.add((obs, CITY.value, Literal(value)))
    graph.add((obs, CITY.evidenceSource, source))
    graph.add(
        (
            obs,
            CITY.evidenceClass,
            Literal("official-structural"),
        )
    )
    graph.add(
        (
            obs,
            CITY.isDemoValue,
            Literal(False, datatype=XSD.boolean),
        )
    )
    if unit:
        graph.add((obs, CITY.unit, Literal(unit)))
    if derived_from is not None:
        graph.add((obs, PROV.wasDerivedFrom, derived_from))
    graph.add((subject, CITY.hasObservation, obs))
    return obs


def _evidence_record(
    graph: Graph,
    source: URIRef,
    feature_type: str,
    feature_id: str,
    retrieved_at: str,
    raw_properties: dict[str, Any],
    local: str,
) -> URIRef:
    node = CITY[
        f"evidence-record/{local}/{_safe(feature_id)}"
    ]
    graph.add((node, RDF.type, CITY.EvidenceRecord))
    graph.add(
        (
            node,
            RDFS.label,
            Literal(
                f"{feature_type} feature {feature_id}"
            ),
        )
    )
    graph.add((node, CITY.evidenceSource, source))
    graph.add(
        (
            node,
            CITY.sourceFeatureType,
            Literal(feature_type),
        )
    )
    graph.add(
        (
            node,
            CITY.sourceFeatureId,
            Literal(feature_id),
        )
    )
    graph.add(
        (
            node,
            CITY.rawPropertiesJson,
            Literal(
                json.dumps(
                    raw_properties,
                    ensure_ascii=False,
                    sort_keys=True,
                )
            ),
        )
    )
    graph.add(
        (
            node,
            PROV.generatedAtTime,
            Literal(
                retrieved_at,
                datatype=XSD.dateTime,
            ),
        )
    )
    return node


def build_graph(
    context: BerlinHeatDecisionContext,
) -> Graph:
    graph = build_heat_graph(context.heat)
    area = next(
        graph.subjects(RDF.type, CITY.Area)
    )

    justice_source = _source(
        graph,
        "berlin-environmental-justice-2023-2024",
        "Umweltgerechtigkeit 2023/2024",
        (
            "Senatsverwaltung für Mobilität, Verkehr, "
            "Klimaschutz und Umwelt Berlin"
        ),
        JUSTICE_ENDPOINT,
        "official-structural",
        (
            "Relative Berlin-wide planning context. "
            "Method changes limit direct trend comparison "
            "with earlier editions."
        ),
    )
    justice = context.justice
    justice_evidence = _evidence_record(
        graph,
        justice_source,
        justice.feature_type,
        justice.feature_id,
        justice.retrieved_at,
        justice.raw_properties,
        "berlin-environmental-justice",
    )
    plan = CITY[
        "area/berlin-planning/"
        + _safe(justice.planning_area_id)
    ]
    graph.add((plan, RDF.type, CITY.Area))
    graph.add(
        (
            plan,
            RDFS.label,
            Literal(justice.planning_area_name),
        )
    )
    graph.add((area, CITY.overlapsPlanningArea, plan))

    for metric, value in (
        (
            "multipleBurdenCategory",
            justice.multiple_burden,
        ),
        (
            "bioclimateBurden",
            justice.bioclimate,
        ),
        (
            "greenProvision",
            justice.green_provision,
        ),
        (
            "noiseBurden",
            justice.noise,
        ),
        (
            "airBurden",
            justice.air,
        ),
        (
            "socialStatusIndex",
            justice.social_status,
        ),
        (
            "populationDensityBand",
            justice.population_band,
        ),
    ):
        if value is not None:
            _official_observation(
                graph,
                (
                    f"justice-{metric}-"
                    f"{justice.planning_area_id}"
                ),
                plan,
                metric,
                value,
                justice_source,
                justice_evidence,
            )

    green_source = _source(
        graph,
        "berlin-public-green-2026",
        "Grünanlagenbestand Berlin",
        (
            "Senatsverwaltung für Mobilität, Verkehr, "
            "Klimaschutz und Umwelt Berlin"
        ),
        GREEN_ENDPOINT,
        "official-structural",
        (
            "Dedicated public green-space mapping does "
            "not prove shade, cooling quality, opening "
            "conditions or accessibility."
        ),
    )
    green = context.nearest_green
    green_evidence = _evidence_record(
        graph,
        green_source,
        green.feature_type,
        green.feature_id,
        green.retrieved_at,
        green.properties,
        "berlin-green",
    )
    green_node = CITY[
        f"asset/public-green/{_safe(green.feature_id)}"
    ]
    graph.add((green_node, RDF.type, CITY.PublicGreenSpace))
    graph.add(
        (
            green_node,
            RDFS.label,
            Literal(green.name),
        )
    )
    graph.add((green_node, PROV.wasDerivedFrom, green_evidence))
    graph.add((area, CITY.nearestPublicGreen, green_node))
    _official_observation(
        graph,
        "nearest-public-green-distance",
        area,
        "nearestPublicGreenDistanceM",
        green.distance_m,
        green_source,
        green_evidence,
        "m",
    )
    _official_observation(
        graph,
        "public-green-feature-count",
        area,
        "publicGreenFeaturesWithin1200m",
        context.green_features_within_radius,
        green_source,
        green_evidence,
        "count",
    )

    hospital_source = _source(
        graph,
        "berlin-hospitals",
        "Krankenhäuser Berlin",
        (
            "Senatsverwaltung für Wissenschaft, "
            "Gesundheit, Pflege und Gleichstellung"
        ),
        HOSPITAL_ENDPOINT,
        "official-structural",
        (
            "Mapped location and reported beds do not "
            "prove current capacity, speciality, "
            "waiting time or heat-response availability."
        ),
    )
    hospital = context.nearest_hospital
    hospital_evidence = _evidence_record(
        graph,
        hospital_source,
        hospital.feature_type,
        hospital.feature_id,
        hospital.retrieved_at,
        hospital.properties,
        "berlin-hospital",
    )
    hospital_node = CITY[
        f"service/hospital/{_safe(hospital.feature_id)}"
    ]
    graph.add((hospital_node, RDF.type, CITY.CareService))
    graph.add(
        (
            hospital_node,
            RDFS.label,
            Literal(hospital.name),
        )
    )
    graph.add(
        (
            hospital_node,
            PROV.wasDerivedFrom,
            hospital_evidence,
        )
    )
    graph.add((area, CITY.nearestHospital, hospital_node))
    _official_observation(
        graph,
        "nearest-hospital-distance",
        area,
        "nearestHospitalDistanceM",
        hospital.distance_m,
        hospital_source,
        hospital_evidence,
        "m",
    )
    beds = (
        hospital.properties.get("betten_insgesamt")
        or hospital.properties.get("betten")
    )
    if beds not in (None, ""):
        try:
            beds_value: Any = int(str(beds))
        except ValueError:
            beds_value = str(beds)
        _official_observation(
            graph,
            "nearest-hospital-reported-beds",
            hospital_node,
            "reportedBeds",
            beds_value,
            hospital_source,
            hospital_evidence,
            "beds",
        )

    recommendation = CITY[
        "recommendation/heat-cross-domain"
    ]
    graph.add(
        (
            recommendation,
            RDF.type,
            CITY.Recommendation,
        )
    )
    graph.add(
        (
            recommendation,
            RDFS.label,
            Literal(
                "Cross-domain heat-planning review"
            ),
        )
    )
    graph.add(
        (
            recommendation,
            CITY.authority,
            Literal(
                Authority.HUMAN_DECISION_REQUIRED.value
            ),
        )
    )
    graph.add(
        (
            recommendation,
            CITY.requiresHumanApproval,
            Literal(True, datatype=XSD.boolean),
        )
    )
    graph.add(
        (
            recommendation,
            CITY.because,
            Literal(
                "Official climate, environmental-justice, "
                "green-space and hospital context can explain "
                "why an area deserves review, but do not by "
                "themselves establish a current emergency or "
                "authorise resource allocation."
            ),
        )
    )

    for gap_id, label in EVIDENCE_GAPS:
        gap = CITY[f"evidence-gap/{gap_id}"]
        graph.add((gap, RDF.type, CITY.EvidenceGap))
        graph.add((gap, RDFS.label, Literal(label)))
        graph.add(
            (
                recommendation,
                CITY.blockedByEvidenceGap,
                gap,
            )
        )

    return graph


EVIDENCE_GAPS = (
    (
        "current-heat-event",
        (
            "Current heat warning / forecast at decision "
            "time"
        ),
    ),
    (
        "vulnerable-populations",
        (
            "Current distribution of heat-vulnerable "
            "people and institutions"
        ),
    ),
    (
        "cooling-access",
        (
            "Cooling-space availability, opening hours, "
            "accessibility and usable shade"
        ),
    ),
    (
        "hospital-live-capacity",
        (
            "Current hospital capacity and relevant "
            "service availability"
        ),
    ),
)


def _term_to_json(value: Any) -> Any:
    if isinstance(value, Literal):
        return value.toPython()
    if isinstance(value, URIRef):
        text = str(value)
        if text.startswith(str(CITY)):
            return text.replace(str(CITY), "city:")
        return text
    return str(value)


def run_cross_domain_heat(
    context: BerlinHeatDecisionContext,
) -> dict[str, Any]:
    graph = build_graph(context)
    validation = validate_graph(graph)
    if not validation["conforms"]:
        raise BerlinContextFetchError(
            "Cross-domain graph failed SHACL: "
            + str(validation["summary"])
        )

    rows: list[dict[str, Any]] = []
    for row in graph.query(CROSS_DOMAIN_QUERY):
        rows.append(
            {
                str(name): _term_to_json(value)
                for name, value in row.asdict().items()
            }
        )

    justice = context.justice
    rationale = [
        {
            "signal": "Structural heat",
            "value": (
                f"PET {context.heat.properties.get('pet14h')} °C; "
                f"UTCI {context.heat.properties.get('utci14h')} °C; "
                f"UHI {context.heat.properties.get('uhi')} K"
            ),
            "meaning": (
                "Official Klimaanalysekarten 2022 "
                "planning evidence."
            ),
        },
        {
            "signal": "Environmental justice",
            "value": (
                f"{justice.planning_area_name}: "
                f"{justice.multiple_burden or 'unknown'}; "
                f"bioclimate {justice.bioclimate or 'unknown'}; "
                f"green provision "
                f"{justice.green_provision or 'unknown'}; "
                f"{justice.social_status or 'status unknown'}"
            ),
            "meaning": (
                "Official 2023/2024 planning-area "
                "context; no new composite score."
            ),
        },
        {
            "signal": "Nearby public green",
            "value": (
                f"{context.nearest_green.name} · "
                f"{context.nearest_green.distance_m:.0f} m "
                f"approx.; "
                f"{context.green_features_within_radius} "
                f"mapped features within "
                f"{context.green_radius_m:.0f} m query radius"
            ),
            "meaning": (
                "Proximity does not prove shade, cooling "
                "quality or accessibility."
            ),
        },
        {
            "signal": "Nearby hospital",
            "value": (
                f"{context.nearest_hospital.name} · "
                f"{context.nearest_hospital.distance_m:.0f} m "
                "approx."
            ),
            "meaning": (
                "Location and reported beds do not prove "
                "live capacity."
            ),
        },
    ]

    return {
        "status": "official_cross_domain_context",
        "title": (
            "Heat resilience — cross-domain Berlin evidence"
        ),
        "question": (
            "If a severe heat event is forecast, what "
            "official context should a planner review here, "
            "and what is still missing before action?"
        ),
        "authority": (
            Authority.HUMAN_DECISION_REQUIRED.value
        ),
        "decision": (
            "Prioritise accountable review of this planning "
            "area when a current heat trigger is present."
        ),
        "recommendation": (
            "The official structural heat evidence and "
            "environmental-justice context make this location "
            "a meaningful candidate for early review. Use "
            "green-space and hospital proximity as context, "
            "not proof of cooling access or care capacity. "
            "Do not allocate resources until the listed live "
            "evidence gaps are checked."
        ),
        "truth_boundary": (
            "This joins official datasets with different "
            "reference dates and purposes. Klimaanalysekarten "
            "2022 are structural modeled evidence; "
            "Umweltgerechtigkeit 2023/2024 is relative "
            "planning context; green and hospital layers are "
            "mapped assets, not live service state."
        ),
        "rationale": rationale,
        "evidence_gaps": [
            {
                "id": gap_id,
                "label": label,
            }
            for gap_id, label in EVIDENCE_GAPS
        ],
        "what_would_change_this": [
            (
                "A current forecast or warning that no longer "
                "meets the municipality's heat-response trigger."
            ),
            (
                "Verified cooling/shade access that materially "
                "reduces exposure for affected groups."
            ),
            (
                "More precise population-vulnerability evidence "
                "that changes who should be prioritised."
            ),
            (
                "Live care-capacity or accessibility evidence "
                "that changes the feasible response."
            ),
        ],
        "query": "\n".join(
            line.rstrip()
            for line in CROSS_DOMAIN_QUERY.strip().splitlines()
        ),
        "rows": rows,
        "context": context.to_dict(),
        "validation": validation,
        "graph_stats": {
            "triples": len(graph),
            "official_sources": 4,
            "synthetic_values": 0,
        },
    }
