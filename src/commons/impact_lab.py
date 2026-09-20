from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
import json
import math
from pathlib import Path
from statistics import mean
from typing import Any, Iterable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from commons.hypothesis_lab import BacktestPoint
from commons.scale_points import GLOBAL_POINTS


GDACS_SEARCH = "https://www.gdacs.org/gdacsapi/api/Events/geteventlist/SEARCH"
GDACS_EMDAT = "https://www.gdacs.org/gdacsapi/api/Emdat/getemdatbyeventkey"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
LIVE_POINT_IDS = ("nuwakot", "manila", "delhi")
HISTORICAL_RADIUS_KM = 250.0
INFRA_RADIUS_M = 20000
ALERT_WEIGHT = {"green": 1.0, "orange": 2.0, "red": 3.0}


def _request_json(
    url: str,
    params: dict[str, Any] | None = None,
    *,
    method: str = "GET",
    body: bytes | None = None,
    timeout: int = 60,
) -> Any:
    target = url
    if params:
        target += "?" + urlencode(params)
    request = Request(
        target,
        data=body,
        method=method,
        headers={
            "User-Agent": "COMMONS-Impact-v0/0.1",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with urlopen(request, timeout=timeout) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


def _features(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("features", "data", "events", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _properties(item: dict[str, Any]) -> dict[str, Any]:
    props = item.get("properties")
    return props if isinstance(props, dict) else item


def _coordinates(item: dict[str, Any]) -> tuple[float, float] | None:
    geometry = item.get("geometry") or {}
    if geometry.get("type") == "Point":
        coords = geometry.get("coordinates") or []
        if len(coords) >= 2:
            try:
                return float(coords[1]), float(coords[0])
            except (TypeError, ValueError):
                pass
    props = _properties(item)
    for lat_key, lon_key in (
        ("latitude", "longitude"),
        ("lat", "lon"),
        ("lat", "lng"),
    ):
        if props.get(lat_key) is None or props.get(lon_key) is None:
            continue
        try:
            return float(props[lat_key]), float(props[lon_key])
        except (TypeError, ValueError):
            continue
    return None


def _date_value(props: dict[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        raw = props.get(key)
        if raw:
            return str(raw)[:10]
    return None


def _event_summary(item: dict[str, Any]) -> dict[str, Any]:
    props = _properties(item)
    coords = _coordinates(item)
    alert = str(
        props.get("alertlevel")
        or props.get("alertLevel")
        or props.get("alert_level")
        or "unknown"
    ).lower()
    return {
        "event_id": props.get("eventid") or props.get("eventId") or props.get("id"),
        "event_type": props.get("eventtype") or props.get("eventType"),
        "alert_level": alert,
        "name": props.get("name") or props.get("eventname") or props.get("title"),
        "country": props.get("country") or props.get("countryname"),
        "latitude": coords[0] if coords else None,
        "longitude": coords[1] if coords else None,
        "start_date": _date_value(
            props, ("fromdate", "fromDate", "startdate", "startDate")
        ),
        "end_date": _date_value(
            props, ("todate", "toDate", "enddate", "endDate")
        ),
        "hazard_score": ALERT_WEIGHT.get(alert, 0.0),
        "population_signal": _recursive_numeric(
            props,
            ("population", "popexposed", "exposedpopulation", "populationexposed"),
        ),
        "vulnerability_signal": _recursive_numeric(
            props,
            ("vulnerability", "vulnerabilityvalue", "informrisk"),
        ),
    }


def _canonical_key(value: Any) -> str:
    return "".join(ch for ch in str(value).lower() if ch.isalnum())


def _recursive_items(value: Any) -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield _canonical_key(key), child
            yield from _recursive_items(child)
    elif isinstance(value, list):
        for child in value:
            yield from _recursive_items(child)


def _to_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, str):
        cleaned = (
            value.replace(",", "")
            .replace("$", "")
            .replace("USD", "")
            .replace("usd", "")
            .strip()
        )
        try:
            number = float(cleaned)
        except ValueError:
            return None
        return number if math.isfinite(number) else None
    return None


def _recursive_numeric(value: Any, aliases: Iterable[str]) -> float | None:
    wanted = {_canonical_key(alias) for alias in aliases}
    for key, child in _recursive_items(value):
        if key in wanted:
            number = _to_number(child)
            if number is not None:
                return number
    return None


def _haversine_km(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    radius = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    value = (
        math.sin(dlat / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(value))


def fetch_gdacs_events(
    *,
    start_date: str,
    end_date: str,
    event_types: str = "FL;TC",
    pages: int = 4,
) -> list[dict[str, Any]]:
    events: dict[str, dict[str, Any]] = {}
    for page in range(1, pages + 1):
        payload = _request_json(
            GDACS_SEARCH,
            {
                "eventlist": event_types,
                "fromdate": start_date,
                "todate": end_date,
                "alertlevel": "green;orange;red",
                "pagesize": 100,
                "pagenumber": page,
            },
        )
        items = _features(payload)
        if not items:
            break
        for raw in items:
            event = _event_summary(raw)
            if not event["event_id"] or not event["event_type"]:
                continue
            key = f'{event["event_type"]}|{event["event_id"]}'
            events[key] = event
        if len(items) < 100:
            break
    return list(events.values())


def fetch_emdat(event: dict[str, Any]) -> Any:
    return _request_json(
        GDACS_EMDAT,
        {
            "eventtype": event["event_type"],
            "eventid": event["event_id"],
        },
    )


def parse_consequence(payload: Any) -> dict[str, Any] | None:
    records = _features(payload)
    if not records and isinstance(payload, dict):
        records = [payload]
    if not records:
        return None

    best: dict[str, Any] | None = None
    for record in records:
        deaths = _recursive_numeric(
            record,
            (
                "totaldeaths",
                "deaths",
                "totaldead",
                "killed",
            ),
        )
        affected = _recursive_numeric(
            record,
            (
                "totalaffected",
                "affected",
                "peopleaffected",
                "totalaffectedpeople",
            ),
        )
        damage_thousand_usd = _recursive_numeric(
            record,
            (
                "totaldamage000usd",
                "totaldamages000usd",
                "damage000usd",
                "totaldamage",
            ),
        )
        damage_usd = (
            damage_thousand_usd * 1000
            if damage_thousand_usd is not None
            else None
        )
        score = (
            (deaths or 0) * 1000000
            + (affected or 0)
            + ((damage_usd or 0) / 1000)
        )
        candidate = {
            "deaths": deaths,
            "affected": affected,
            "damage_usd": damage_usd,
            "consequential": bool(
                (deaths or 0) >= 1
                or (affected or 0) >= 10000
                or (damage_usd or 0) >= 1_000_000
            ),
            "label_source": "EM-DAT via GDACS",
        }
        if best is None or score > float(best["_score"]):
            best = {**candidate, "_score": score}

    if best is None:
        return None
    best.pop("_score", None)
    return best


def fetch_infrastructure(point: BacktestPoint) -> dict[str, Any]:
    lat, lon = point.latitude, point.longitude
    around = f"around:{INFRA_RADIUS_M},{lat},{lon}"
    query = f"""
[out:json][timeout:40];
(
  nwr(around:{INFRA_RADIUS_M},{lat},{lon})[amenity~"^(hospital|clinic)$"];
  nwr(around:{INFRA_RADIUS_M},{lat},{lon})[amenity="school"];
  nwr(around:{INFRA_RADIUS_M},{lat},{lon})[power="substation"];
  way(around:{INFRA_RADIUS_M},{lat},{lon})[bridge="yes"];
  way(around:{INFRA_RADIUS_M},{lat},{lon})[highway~"^(motorway|trunk|primary)$"];
);
out tags center;
""".strip()
    payload = _request_json(
        OVERPASS_URL,
        method="POST",
        body=urlencode({"data": query}).encode("utf-8"),
        timeout=60,
    )
    counts = {
        "health_facilities": 0,
        "schools": 0,
        "power_substations": 0,
        "bridges": 0,
        "major_road_segments": 0,
    }
    for element in payload.get("elements") or []:
        tags = element.get("tags") or {}
        amenity = tags.get("amenity")
        if amenity in {"hospital", "clinic"}:
            counts["health_facilities"] += 1
        if amenity == "school":
            counts["schools"] += 1
        if tags.get("power") == "substation":
            counts["power_substations"] += 1
        if tags.get("bridge") == "yes":
            counts["bridges"] += 1
        if tags.get("highway") in {"motorway", "trunk", "primary"}:
            counts["major_road_segments"] += 1
    return {
        **counts,
        "radius_km": INFRA_RADIUS_M / 1000,
        "source": "OpenStreetMap via Overpass API",
        "role": "context_only",
    }


def _exposure_map(exposure_report: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in (exposure_report or {}).get("points") or []:
        point_id = str((item.get("point") or {}).get("id") or "")
        if point_id:
            out[point_id] = item
    return out


def _nearby_events(
    point: BacktestPoint,
    events: list[dict[str, Any]],
    consequences: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    nearby: list[dict[str, Any]] = []
    for event in events:
        if event.get("latitude") is None or event.get("longitude") is None:
            continue
        distance = _haversine_km(
            point.latitude,
            point.longitude,
            float(event["latitude"]),
            float(event["longitude"]),
        )
        if distance > HISTORICAL_RADIUS_KM:
            continue
        key = f'{event["event_type"]}|{event["event_id"]}'
        consequence = consequences.get(key)
        nearby.append(
            {
                **event,
                "distance_km": round(distance, 1),
                "consequence": consequence,
            }
        )
    nearby.sort(
        key=lambda item: (
            not bool((item.get("consequence") or {}).get("consequential")),
            -float(item.get("hazard_score") or 0),
            item.get("distance_km") or 9999,
        )
    )
    return nearby[:12]


def _action_options(
    *,
    population: float | None,
    infrastructure: dict[str, Any] | None,
    historical: list[dict[str, Any]],
) -> list[dict[str, str]]:
    actions = [
        {
            "id": "verify-local",
            "label": "Verify local authority warnings",
            "why": "COMMONS is research guidance, not an emergency authority.",
            "authority": "human",
        }
    ]
    if infrastructure and (
        infrastructure.get("health_facilities", 0) > 0
        or infrastructure.get("major_road_segments", 0) > 0
        or infrastructure.get("bridges", 0) > 0
    ):
        actions.append(
            {
                "id": "check-access",
                "label": "Check critical access and services",
                "why": "Nearby health, road, bridge or power assets can turn weather into disruption.",
                "authority": "human",
            }
        )
    if population and population >= 100000:
        actions.append(
            {
                "id": "review-exposure",
                "label": "Review who may be exposed",
                "why": "Nearby population is large enough that distribution matters, not only hazard magnitude.",
                "authority": "human",
            }
        )
    if any((item.get("consequence") or {}).get("consequential") for item in historical):
        actions.append(
            {
                "id": "review-precedent",
                "label": "Review nearby historical consequences",
                "why": "Past events in the area provide precedent for what failed or mattered.",
                "authority": "human",
            }
        )
    return actions


def average_precision(rows: list[dict[str, Any]], score_key: str) -> float | None:
    ranked = sorted(
        [row for row in rows if row.get(score_key) is not None],
        key=lambda row: float(row[score_key]),
        reverse=True,
    )
    positives = sum(bool(row.get("consequential")) for row in ranked)
    if positives == 0:
        return None
    hits = 0
    precision_sum = 0.0
    for index, row in enumerate(ranked, start=1):
        if row.get("consequential"):
            hits += 1
            precision_sum += hits / index
    return precision_sum / positives


def top_fraction_recall(
    rows: list[dict[str, Any]],
    score_key: str,
    *,
    fraction: float = 0.20,
) -> float | None:
    ranked = sorted(
        [row for row in rows if row.get(score_key) is not None],
        key=lambda row: float(row[score_key]),
        reverse=True,
    )
    positives = sum(bool(row.get("consequential")) for row in ranked)
    if positives == 0 or not ranked:
        return None
    k = max(1, math.ceil(len(ranked) * fraction))
    caught = sum(bool(row.get("consequential")) for row in ranked[:k])
    return caught / positives


def _rank_percentiles(rows: list[dict[str, Any]], key: str) -> dict[str, float]:
    values = sorted(
        float(row[key]) for row in rows if row.get(key) is not None
    )
    out: dict[str, float] = {}
    if not values:
        return out
    for row in rows:
        if row.get(key) is None:
            continue
        value = float(row[key])
        rank = sum(item <= value for item in values)
        out[str(row["event_key"])] = rank / len(values)
    return out


def build_benchmark_rows(
    events: list[dict[str, Any]],
    consequences: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event in events:
        key = f'{event["event_type"]}|{event["event_id"]}'
        consequence = consequences.get(key)
        if not consequence:
            continue
        rows.append(
            {
                "event_key": key,
                "start_date": event.get("start_date"),
                "hazard_score": event.get("hazard_score"),
                "population_signal": event.get("population_signal"),
                "vulnerability_signal": event.get("vulnerability_signal"),
                "consequential": consequence.get("consequential"),
                "consequence": consequence,
            }
        )
    return rows


def evaluate_impact_ordering(rows: list[dict[str, Any]]) -> dict[str, Any]:
    dated = [row for row in rows if row.get("start_date")]
    dated.sort(key=lambda row: str(row["start_date"]))
    split_index = max(1, int(len(dated) * 0.67))
    development = dated[:split_index]
    test = dated[split_index:]

    def add_scores(subset: list[dict[str, Any]]) -> None:
        hazard_pct = _rank_percentiles(subset, "hazard_score")
        pop_pct = _rank_percentiles(subset, "population_signal")
        vuln_pct = _rank_percentiles(subset, "vulnerability_signal")
        for row in subset:
            key = str(row["event_key"])
            h = hazard_pct.get(key)
            p = pop_pct.get(key)
            v = vuln_pct.get(key)
            row["hazard_rank"] = h
            row["hazard_population_rank"] = (
                mean([h, p]) if h is not None and p is not None else None
            )
            row["impact_components_rank"] = (
                mean([h, p, v])
                if h is not None and p is not None and v is not None
                else None
            )

    add_scores(development)
    add_scores(test)

    candidates = ("hazard_population_rank", "impact_components_rank")
    dev_baseline = average_precision(development, "hazard_rank")
    selected = None
    selected_ap = -1.0
    for key in candidates:
        ap = average_precision(development, key)
        if ap is not None and ap > selected_ap:
            selected = key
            selected_ap = ap

    if selected is None:
        selected = "hazard_population_rank"

    test_base_ap = average_precision(test, "hazard_rank")
    test_candidate_ap = average_precision(test, selected)
    test_base_recall = top_fraction_recall(test, "hazard_rank")
    test_candidate_recall = top_fraction_recall(test, selected)
    feature_coverage = (
        sum(row.get(selected) is not None for row in test) / len(test)
        if test
        else 0.0
    )

    ap_gain = (
        test_candidate_ap - test_base_ap
        if test_candidate_ap is not None and test_base_ap is not None
        else None
    )
    recall_gain = (
        test_candidate_recall - test_base_recall
        if test_candidate_recall is not None and test_base_recall is not None
        else None
    )
    enough = (
        len(test) >= 20
        and sum(bool(row.get("consequential")) for row in test) >= 5
        and feature_coverage >= 0.70
    )
    supported = bool(
        enough
        and ap_gain is not None
        and ap_gain >= 0.05
        and recall_gain is not None
        and recall_gain >= 0.10
    )
    status = "supported" if supported else "not_supported" if enough else "insufficient"

    return {
        "development_rows": len(development),
        "test_rows": len(test),
        "test_consequential_events": sum(
            bool(row.get("consequential")) for row in test
        ),
        "selected_ordering": selected,
        "feature_coverage": round(feature_coverage, 4),
        "hazard_only": {
            "average_precision": round(test_base_ap, 4)
            if test_base_ap is not None
            else None,
            "top20_recall": round(test_base_recall, 4)
            if test_base_recall is not None
            else None,
        },
        "impact_aware": {
            "average_precision": round(test_candidate_ap, 4)
            if test_candidate_ap is not None
            else None,
            "top20_recall": round(test_candidate_recall, 4)
            if test_candidate_recall is not None
            else None,
        },
        "comparison": {
            "average_precision_gain": round(ap_gain, 4)
            if ap_gain is not None
            else None,
            "top20_recall_gain": round(recall_gain, 4)
            if recall_gain is not None
            else None,
        },
        "hypothesis": {
            "id": "H27",
            "claim": (
                "Explicit hazard + exposure + vulnerability components rank historically "
                "consequential flood/cyclone events better than hazard severity alone."
            ),
            "status": status,
            "effect": (
                f"selected {selected}; test n={len(test)}; feature coverage "
                f"{round(feature_coverage, 4)}; AP gain "
                f"{round(ap_gain, 4) if ap_gain is not None else None}; "
                f"top20 recall gain {round(recall_gain, 4) if recall_gain is not None else None}"
            ),
            "product_update": (
                "Allow impact-aware ordering into a shadow queue only; keep hazard ALERT authority unchanged."
                if supported
                else "Keep impact components visible but do not let them change live ranking yet."
                if status == "not_supported"
                else "Impact labels or component coverage are not sufficient yet; keep Impact v0 context-only."
            ),
        },
    }


def run_impact_v0(
    *,
    exposure_report: dict[str, Any] | None,
    points: tuple[BacktestPoint, ...] = GLOBAL_POINTS,
    history_start: str | None = None,
    history_end: str | None = None,
) -> dict[str, Any]:
    end = date.fromisoformat(history_end) if history_end else date.today()
    start = (
        date.fromisoformat(history_start)
        if history_start
        else end - timedelta(days=730)
    )
    source_errors: list[dict[str, str]] = []

    try:
        events = fetch_gdacs_events(
            start_date=start.isoformat(),
            end_date=end.isoformat(),
            pages=3,
        )
    except Exception as exc:
        events = []
        source_errors.append({"source": "GDACS events", "error": str(exc)})

    consequences: dict[str, dict[str, Any]] = {}

    def consequence_task(event: dict[str, Any]):
        key = f'{event["event_type"]}|{event["event_id"]}'
        parsed = parse_consequence(fetch_emdat(event))
        return key, parsed

    with ThreadPoolExecutor(max_workers=min(8, max(1, len(events)))) as executor:
        future_map = {
            executor.submit(consequence_task, event): event
            for event in events
        }
        for future in as_completed(future_map):
            event = future_map[future]
            key = f'{event["event_type"]}|{event["event_id"]}'
            try:
                event_key, parsed = future.result()
                if parsed:
                    consequences[event_key] = parsed
            except Exception as exc:
                source_errors.append(
                    {
                        "source": "EM-DAT",
                        "event_key": key,
                        "error": str(exc),
                    }
                )

    exposure = _exposure_map(exposure_report)
    point_map = {point.id: point for point in points}
    profiles: list[dict[str, Any]] = []

    for point_id in LIVE_POINT_IDS:
        point = point_map[point_id]
        infrastructure = None
        try:
            infrastructure = fetch_infrastructure(point)
        except Exception as exc:
            source_errors.append(
                {
                    "source": "OpenStreetMap/Overpass",
                    "point_id": point_id,
                    "error": str(exc),
                }
            )

        exp = exposure.get(point_id) or {}
        population = _to_number(exp.get("population"))
        historical = _nearby_events(point, events, consequences)
        consequential_history = [
            item
            for item in historical
            if (item.get("consequence") or {}).get("consequential")
        ]
        profiles.append(
            {
                "point_id": point_id,
                "name": point.name,
                "country": point.country,
                "components": {
                    "hazard": {
                        "role": "provided live by Morning Brief",
                        "note": "Impact v0 does not replace the validated hazard gate.",
                    },
                    "exposure": {
                        "population_within_radius": population,
                        "radius_km": exp.get("radius_km"),
                        "source": exp.get("data_source") or "WorldPop",
                        "role": "context_only",
                    },
                    "infrastructure": infrastructure,
                    "historical_consequence": {
                        "nearby_events": len(historical),
                        "consequential_events": len(consequential_history),
                        "examples": consequential_history[:4],
                        "source": "GDACS + EM-DAT where available",
                        "role": "context_only",
                    },
                },
                "action_options": _action_options(
                    population=population,
                    infrastructure=infrastructure,
                    historical=historical,
                ),
            }
        )

    benchmark_rows = build_benchmark_rows(events, consequences)
    benchmark = evaluate_impact_ordering(benchmark_rows)

    emdat_coverage = len(consequences) / len(events) if events else 0.0
    return {
        "schema_version": "0.1",
        "product": "COMMONS Impact v0",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "principle": (
            "Hazard, exposure, infrastructure and historical consequence stay visible "
            "as separate components. No opaque production risk score."
        ),
        "source_health": {
            "gdacs_events": len(events),
            "emdat_labels": len(consequences),
            "emdat_coverage": round(emdat_coverage, 4),
            "profiles": len(profiles),
            "source_errors": source_errors[-100:],
        },
        "profiles": profiles,
        "benchmark": benchmark,
        "trust_contract": [
            "Population near a point is not the number of people impacted.",
            "Infrastructure counts indicate nearby assets, not damage or service failure.",
            "Historical consequences are precedent, not a forecast of future harm.",
            "Impact components do not change ALERT unless impact-labelled validation supports it.",
            "All action options require human authorization.",
        ],
        "sources": [
            {
                "name": "GDACS",
                "role": "historical disaster events",
                "url": "https://www.gdacs.org/",
            },
            {
                "name": "EM-DAT via GDACS API",
                "role": "historical consequence labels when available",
                "url": GDACS_EMDAT,
            },
            {
                "name": "WorldPop",
                "role": "population exposure context",
                "url": "https://www.worldpop.org/",
            },
            {
                "name": "OpenStreetMap / Overpass",
                "role": "nearby critical infrastructure context",
                "url": "https://wiki.openstreetmap.org/wiki/Overpass_API",
            },
        ],
    }
