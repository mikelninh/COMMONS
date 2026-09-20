from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
import json
import math
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from commons.hypothesis_lab import BacktestPoint, build_records, quantile
from commons.scale_points import GLOBAL_POINTS


GDACS_SEARCH = "https://www.gdacs.org/gdacsapi/api/Events/geteventlist/SEARCH"
MATCH_RADIUS_KM = 250.0


def _get_json(url: str, params: dict[str, Any], timeout: int = 60) -> Any:
    request = Request(
        url + "?" + urlencode(params),
        headers={"User-Agent": "COMMONS-External-Alert-Lab/0.1"},
    )
    with urlopen(request, timeout=timeout) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


def _features(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        for key in ("features", "data", "events", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def _coordinates(item: dict[str, Any]) -> tuple[float, float] | None:
    geometry = item.get("geometry") or {}
    if geometry.get("type") == "Point":
        coords = geometry.get("coordinates") or []
        if len(coords) >= 2:
            try:
                return float(coords[1]), float(coords[0])
            except (TypeError, ValueError):
                pass
    props = item.get("properties") or item
    candidates = (
        ("latitude", "longitude"),
        ("lat", "lon"),
        ("lat", "lng"),
    )
    for lat_key, lon_key in candidates:
        if props.get(lat_key) is not None and props.get(lon_key) is not None:
            try:
                return float(props[lat_key]), float(props[lon_key])
            except (TypeError, ValueError):
                continue
    return None


def _event_dates(item: dict[str, Any]) -> tuple[date | None, date | None]:
    props = item.get("properties") or item

    def parse(keys: tuple[str, ...]) -> date | None:
        for key in keys:
            raw = props.get(key)
            if not raw:
                continue
            text = str(raw).replace("Z", "+00:00")
            try:
                return datetime.fromisoformat(text).date()
            except ValueError:
                try:
                    return date.fromisoformat(str(raw)[:10])
                except ValueError:
                    continue
        return None

    start = parse(("fromdate", "fromDate", "startdate", "startDate"))
    end = parse(("todate", "toDate", "enddate", "endDate")) or start
    return start, end


def _event_summary(item: dict[str, Any]) -> dict[str, Any]:
    props = item.get("properties") or item
    coords = _coordinates(item)
    start, end = _event_dates(item)
    return {
        "event_id": props.get("eventid") or props.get("eventId") or props.get("id"),
        "event_type": props.get("eventtype") or props.get("eventType"),
        "alert_level": props.get("alertlevel") or props.get("alertLevel"),
        "name": props.get("name") or props.get("eventname") or props.get("title"),
        "latitude": coords[0] if coords else None,
        "longitude": coords[1] if coords else None,
        "start_date": start.isoformat() if start else None,
        "end_date": end.isoformat() if end else None,
    }


def fetch_gdacs_events(start_date: str, end_date: str) -> list[dict[str, Any]]:
    payload = _get_json(
        GDACS_SEARCH,
        {
            "eventlist": "FL;TC",
            "fromdate": start_date,
            "todate": end_date,
            "alertlevel": "green;orange;red",
            "pagesize": 100,
            "pagenumber": 1,
        },
    )
    return [_event_summary(item) for item in _features(payload)]


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


def _event_matches(
    point: BacktestPoint,
    day: date,
    event: dict[str, Any],
    *,
    radius_km: float = MATCH_RADIUS_KM,
) -> bool:
    if event.get("latitude") is None or event.get("longitude") is None:
        return False
    start = date.fromisoformat(event["start_date"]) if event.get("start_date") else None
    end = date.fromisoformat(event["end_date"]) if event.get("end_date") else start
    if start and day < start - timedelta(days=1):
        return False
    if end and day > end + timedelta(days=1):
        return False
    distance = _haversine_km(
        point.latitude,
        point.longitude,
        float(event["latitude"]),
        float(event["longitude"]),
    )
    return distance <= radius_km


def run_external_alert_benchmark(
    *,
    start_date: str,
    end_date: str,
    points: tuple[BacktestPoint, ...] = GLOBAL_POINTS,
) -> dict[str, Any]:
    records, source_errors = build_records(
        start_date=start_date,
        end_date=end_date,
        points=points,
    )
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    split = start + (end - start) * 2 / 3

    train: dict[str, list[float]] = defaultdict(list)
    test_rows: list[dict[str, Any]] = []
    for row in records:
        if int(row["lead_days"]) != 3:
            continue
        row_day = date.fromisoformat(row["date"])
        if row_day < split:
            train[row["point_id"]].append(float(row["actual_precip_mm"]))
        else:
            test_rows.append(row)
    thresholds = {
        point_id: quantile(values, 0.90)
        for point_id, values in train.items()
        if values
    }

    gdacs_errors: list[str] = []
    try:
        events = fetch_gdacs_events(split.isoformat(), end_date)
    except Exception as exc:
        events = []
        gdacs_errors.append(str(exc))

    point_meta = {point.id: point for point in points}
    matched_days = 0
    common_alert_on_matched = 0
    common_alert_days = 0
    matches: list[dict[str, Any]] = []

    for row in test_rows:
        point = point_meta[row["point_id"]]
        threshold = thresholds.get(point.id)
        if not threshold:
            continue
        day = date.fromisoformat(row["date"])
        nearby = [event for event in events if _event_matches(point, day, event)]
        commons_alert = float(row["council_median_mm"]) >= float(threshold)
        if commons_alert:
            common_alert_days += 1
        if nearby:
            matched_days += 1
            if commons_alert:
                common_alert_on_matched += 1
            if len(matches) < 80:
                matches.append(
                    {
                        "point_id": point.id,
                        "name": point.name,
                        "date": row["date"],
                        "commons_alert": commons_alert,
                        "forecast_mm": row["council_median_mm"],
                        "heavy_gate_mm": round(float(threshold), 2),
                        "gdacs_events": nearby[:5],
                    }
                )

    overlap_rate = (
        common_alert_on_matched / matched_days if matched_days else None
    )
    status = "insufficient"
    return {
        "schema_version": "0.1",
        "source": "Global Disaster Alert and Coordination System (GDACS)",
        "source_url": "https://www.gdacs.org/",
        "period": {"start": split.isoformat(), "end": end_date},
        "match_radius_km": MATCH_RADIUS_KM,
        "gdacs_events": len(events),
        "gdacs_source_errors": gdacs_errors,
        "weather_source_errors": source_errors,
        "matched_point_days": matched_days,
        "commons_alert_days": common_alert_days,
        "commons_alert_on_matched_days": common_alert_on_matched,
        "overlap_rate": round(overlap_rate, 4) if overlap_rate is not None else None,
        "matches": matches,
        "hypothesis": {
            "id": "H22",
            "claim": "A public external disaster-alert stream can provide a useful independent benchmark for COMMONS attention changes.",
            "status": status,
            "effect": (
                f"GDACS events {len(events)}; matched point-days {matched_days}; "
                f"COMMONS overlap {round(overlap_rate, 4) if overlap_rate is not None else None}"
            ),
            "product_update": (
                "Keep GDACS as an external audit signal only. It is not a local official warning feed and must not control ALERT."
            ),
        },
        "official_warning_gap": {
            "status": "open",
            "note": (
                "National/local official warning archives require source-specific adapters or access. "
                "MeteoAlarm archived warning queries currently require re-user authentication."
            ),
        },
        "limitations": [
            "GDACS is a global disaster alert/coordination source, not a substitute for local meteorological or emergency authorities.",
            "A 250 km point match is deliberately coarse and cannot establish causal or local warning agreement.",
            "Flood and cyclone alerts are not equivalent to daily heavy-rain observations.",
            "This benchmark is diagnostic and does not update live thresholds.",
        ],
    }
