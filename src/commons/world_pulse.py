from __future__ import annotations

import hashlib
import math
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field


USGS_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"
EONET_URL = "https://eonet.gsfc.nasa.gov/api/v3/events/geojson?status=open&limit=100"
GDACS_URL = "https://gdacs.org/xml/rss_7d.xml"

_TIMEOUT = 12.0
_previous_fingerprints: dict[str, str] = {}


class SourceState(BaseModel):
    source: str
    ok: bool
    fetched_at: datetime
    count: int = 0
    detail: str | None = None
    freshness: Literal["live", "near_real_time"] = "near_real_time"
    cadence: str = "unspecified"
    source_url: str = ""
    scope_note: str = ""


class WorldSignal(BaseModel):
    signal_id: str
    source: Literal["USGS", "GDACS", "NASA EONET"]
    source_event_id: str
    kind: str
    title: str
    latitude: float
    longitude: float
    occurred_at: datetime | None = None
    updated_at: datetime | None = None
    magnitude: float | None = None
    magnitude_unit: str | None = None
    severity: str | None = None
    source_url: str | None = None
    state: Literal["new", "updated", "known"] = "known"
    attention_reasons: list[str] = Field(default_factory=list)

    @property
    def fingerprint_payload(self) -> str:
        return "|".join(
            [
                self.title,
                f"{self.latitude:.4f}",
                f"{self.longitude:.4f}",
                str(self.occurred_at),
                str(self.updated_at),
                str(self.magnitude),
                str(self.severity),
            ]
        )


class SignalCluster(BaseModel):
    cluster_id: str
    signal_ids: list[str]
    sources: list[str]
    latitude: float
    longitude: float
    distance_km: float
    time_window_hours: float
    reason: str


class WorldPulseStats(BaseModel):
    total_signals: int
    new_signals: int
    updated_signals: int
    attention_signals: int
    possible_multi_source_clusters: int


class WorldPulseResponse(BaseModel):
    generated_at: datetime
    baseline_observation: bool
    source_states: list[SourceState]
    stats: WorldPulseStats
    signals: list[WorldSignal]
    clusters: list[SignalCluster]


def _utc_from_ms(value: int | float | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromtimestamp(float(value) / 1000.0, tz=timezone.utc)


def _utc_parse(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    text = str(value).strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc)
    except ValueError:
        pass
    try:
        parsed = parsedate_to_datetime(text)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _first_point(geometry: dict[str, Any] | None) -> tuple[float, float] | None:
    if not geometry:
        return None
    kind = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if kind == "Point" and isinstance(coordinates, list) and len(coordinates) >= 2:
        try:
            return float(coordinates[1]), float(coordinates[0])
        except (TypeError, ValueError):
            return None
    if kind in {"Polygon", "MultiPolygon", "LineString", "MultiLineString"}:
        def descend(value: Any) -> tuple[float, float] | None:
            if (
                isinstance(value, list)
                and len(value) >= 2
                and isinstance(value[0], (int, float))
                and isinstance(value[1], (int, float))
            ):
                return float(value[1]), float(value[0])
            if isinstance(value, list):
                for child in value:
                    point = descend(child)
                    if point is not None:
                        return point
            return None
        return descend(coordinates)
    return None


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].split(":")[-1].lower()


def _child_text(item: ET.Element, names: set[str]) -> str | None:
    for child in item.iter():
        if _local_name(child.tag) in names and child.text and child.text.strip():
            return child.text.strip()
    return None


def _parse_lat_lon(item: ET.Element) -> tuple[float, float] | None:
    lat = _child_text(item, {"lat", "latitude"})
    lon = _child_text(item, {"long", "lon", "longitude"})
    if lat and lon:
        try:
            return float(lat), float(lon)
        except ValueError:
            pass

    point = _child_text(item, {"point"})
    if point:
        parts = point.replace(",", " ").split()
        if len(parts) >= 2:
            try:
                return float(parts[0]), float(parts[1])
            except ValueError:
                pass
    return None


def _attention_for(signal: WorldSignal) -> list[str]:
    reasons: list[str] = []
    if signal.source == "USGS" and signal.magnitude is not None:
        if signal.magnitude >= 6:
            reasons.append("earthquake magnitude ≥ 6.0")
        elif signal.magnitude >= 5:
            reasons.append("earthquake magnitude ≥ 5.0")
    if signal.source == "GDACS" and signal.severity:
        severity = signal.severity.lower()
        if "red" in severity:
            reasons.append("GDACS red alert")
        elif "orange" in severity:
            reasons.append("GDACS orange alert")
    return reasons


async def _fetch_usgs(client: httpx.AsyncClient) -> tuple[list[WorldSignal], SourceState]:
    fetched_at = datetime.now(timezone.utc)
    try:
        response = await client.get(USGS_URL)
        response.raise_for_status()
        body = response.json()
        signals: list[WorldSignal] = []
        for feature in body.get("features", []):
            props = feature.get("properties") or {}
            point = _first_point(feature.get("geometry"))
            if point is None:
                continue
            source_id = str(feature.get("id") or props.get("code") or "")
            if not source_id:
                continue
            signal = WorldSignal(
                signal_id=f"usgs:{source_id}",
                source="USGS",
                source_event_id=source_id,
                kind="earthquake",
                title=str(props.get("title") or props.get("place") or "Earthquake"),
                latitude=point[0],
                longitude=point[1],
                occurred_at=_utc_from_ms(props.get("time")),
                updated_at=_utc_from_ms(props.get("updated")),
                magnitude=float(props["mag"]) if props.get("mag") is not None else None,
                magnitude_unit=str(props.get("magType")) if props.get("magType") else None,
                severity=str(props.get("alert")) if props.get("alert") else None,
                source_url=props.get("url"),
            )
            signal.attention_reasons = _attention_for(signal)
            signals.append(signal)
        return signals, SourceState(
            source="USGS",
            ok=True,
            fetched_at=fetched_at,
            count=len(signals),
            freshness="live",
            cadence="feed updated about every minute",
            source_url="https://earthquake.usgs.gov/earthquakes/feed/",
            scope_note="Rolling public earthquake feed; this view is not a complete measure of disaster impact.",
        )
    except Exception as exc:
        return [], SourceState(
            source="USGS",
            ok=False,
            fetched_at=fetched_at,
            detail=str(exc),
            freshness="live",
            cadence="feed updated about every minute",
            source_url="https://earthquake.usgs.gov/earthquakes/feed/",
            scope_note="Rolling public earthquake feed; this view is not a complete measure of disaster impact.",
        )


async def _fetch_eonet(client: httpx.AsyncClient) -> tuple[list[WorldSignal], SourceState]:
    fetched_at = datetime.now(timezone.utc)
    try:
        response = await client.get(EONET_URL)
        response.raise_for_status()
        body = response.json()
        signals: list[WorldSignal] = []
        for feature in body.get("features", []):
            props = feature.get("properties") or {}
            point = _first_point(feature.get("geometry"))
            if point is None:
                continue
            source_id = str(props.get("id") or feature.get("id") or "")
            if not source_id:
                continue
            categories = props.get("categories") or []
            category = "natural event"
            if isinstance(categories, list) and categories:
                first = categories[0]
                category = str(first.get("title") or first.get("id") or category) if isinstance(first, dict) else str(first)
            sources = props.get("sources") or []
            source_url = None
            if isinstance(sources, list) and sources and isinstance(sources[0], dict):
                source_url = sources[0].get("url")
            signal = WorldSignal(
                signal_id=f"eonet:{source_id}",
                source="NASA EONET",
                source_event_id=source_id,
                kind=category.lower().replace(" ", "_"),
                title=str(props.get("title") or category),
                latitude=point[0],
                longitude=point[1],
                occurred_at=_utc_parse(props.get("date")),
                updated_at=_utc_parse(props.get("date")),
                magnitude=float(props["magnitudeValue"]) if props.get("magnitudeValue") is not None else None,
                magnitude_unit=props.get("magnitudeUnit"),
                source_url=source_url,
            )
            signals.append(signal)
        return signals, SourceState(
            source="NASA EONET",
            ok=True,
            fetched_at=fetched_at,
            count=len(signals),
            freshness="near_real_time",
            cadence="curated open-event feed",
            source_url="https://eonet.gsfc.nasa.gov/",
            scope_note="Curated natural-event tracking; not a complete census of every event on Earth.",
        )
    except Exception as exc:
        return [], SourceState(
            source="NASA EONET",
            ok=False,
            fetched_at=fetched_at,
            detail=str(exc),
            freshness="near_real_time",
            cadence="curated open-event feed",
            source_url="https://eonet.gsfc.nasa.gov/",
            scope_note="Curated natural-event tracking; not a complete census of every event on Earth.",
        )


async def _fetch_gdacs(client: httpx.AsyncClient) -> tuple[list[WorldSignal], SourceState]:
    fetched_at = datetime.now(timezone.utc)
    try:
        response = await client.get(GDACS_URL)
        response.raise_for_status()
        root = ET.fromstring(response.text)
        signals: list[WorldSignal] = []
        for item in root.iter():
            if _local_name(item.tag) != "item":
                continue
            point = _parse_lat_lon(item)
            if point is None:
                continue
            guid = _child_text(item, {"guid"}) or _child_text(item, {"link"}) or _child_text(item, {"title"})
            if not guid:
                continue
            source_id = hashlib.sha1(guid.encode("utf-8")).hexdigest()[:16]
            event_type = (_child_text(item, {"eventtype"}) or "disaster").strip()
            normalized_event_type = {
                "EQ": "earthquake",
                "TC": "cyclone",
                "FL": "flood",
                "VO": "volcano",
                "WF": "wildfire",
                "DR": "drought",
            }.get(event_type.upper(), event_type.lower())
            alert = _child_text(item, {"alertlevel", "alertscore"})
            title = _child_text(item, {"title"}) or event_type
            magnitude_text = _child_text(item, {"severity", "magnitude"})
            magnitude = None
            if magnitude_text:
                try:
                    magnitude = float(magnitude_text.split()[0])
                except ValueError:
                    magnitude = None
            signal = WorldSignal(
                signal_id=f"gdacs:{source_id}",
                source="GDACS",
                source_event_id=source_id,
                kind=normalized_event_type.replace(" ", "_"),
                title=title,
                latitude=point[0],
                longitude=point[1],
                occurred_at=_utc_parse(_child_text(item, {"pubdate", "fromdate", "date"})),
                updated_at=_utc_parse(_child_text(item, {"pubdate", "todate", "date"})),
                magnitude=magnitude,
                severity=alert,
                source_url=_child_text(item, {"link"}),
            )
            signal.attention_reasons = _attention_for(signal)
            signals.append(signal)
        return signals, SourceState(
            source="GDACS",
            ok=True,
            fetched_at=fetched_at,
            count=len(signals),
            freshness="near_real_time",
            cadence="7-day disaster alert feed",
            source_url="https://gdacs.org/",
            scope_note="Disaster alert feed for situational awareness; alert presence is not a casualty or need estimate.",
        )
    except Exception as exc:
        return [], SourceState(
            source="GDACS",
            ok=False,
            fetched_at=fetched_at,
            detail=str(exc),
            freshness="near_real_time",
            cadence="7-day disaster alert feed",
            source_url="https://gdacs.org/",
            scope_note="Disaster alert feed for situational awareness; alert presence is not a casualty or need estimate.",
        )


def _haversine_km(a: WorldSignal, b: WorldSignal) -> float:
    radius = 6371.0
    lat1, lon1, lat2, lon2 = map(
        math.radians,
        [a.latitude, a.longitude, b.latitude, b.longitude],
    )
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return radius * 2 * math.asin(min(1.0, math.sqrt(h)))


def _time_hours(a: WorldSignal, b: WorldSignal) -> float | None:
    at = a.updated_at or a.occurred_at
    bt = b.updated_at or b.occurred_at
    if at is None or bt is None:
        return None
    return abs((at - bt).total_seconds()) / 3600.0


def _compatible_kind(a: WorldSignal, b: WorldSignal) -> bool:
    left = a.kind.lower()
    right = b.kind.lower()
    pairs = [
        ("earthquake", "earthquake"),
        ("wildfire", "fire"),
        ("fire", "wildfire"),
        ("severe_storm", "cyclone"),
        ("cyclone", "severe_storm"),
        ("flood", "flood"),
        ("volcano", "volcano"),
    ]
    if left == right:
        return True
    return any(x in left and y in right for x, y in pairs)


def _clusters(signals: list[WorldSignal]) -> list[SignalCluster]:
    clusters: list[SignalCluster] = []
    used_pairs: set[tuple[str, str]] = set()
    for index, left in enumerate(signals):
        for right in signals[index + 1 :]:
            if left.source == right.source or not _compatible_kind(left, right):
                continue
            distance = _haversine_km(left, right)
            if distance > 250:
                continue
            hours = _time_hours(left, right)
            if hours is not None and hours > 72:
                continue
            pair = tuple(sorted((left.signal_id, right.signal_id)))
            if pair in used_pairs:
                continue
            used_pairs.add(pair)
            sources = sorted({left.source, right.source})
            cluster_id = hashlib.sha1("|".join(pair).encode("utf-8")).hexdigest()[:12]
            clusters.append(
                SignalCluster(
                    cluster_id=cluster_id,
                    signal_ids=list(pair),
                    sources=sources,
                    latitude=(left.latitude + right.latitude) / 2,
                    longitude=(left.longitude + right.longitude) / 2,
                    distance_km=round(distance, 1),
                    time_window_hours=round(hours or 0.0, 1),
                    reason=(
                        f"Possible multi-source cluster: compatible event types from "
                        f"{' + '.join(sources)} within {distance:.0f} km"
                        + (f" and {hours:.1f} h" if hours is not None else "")
                        + ". Correlation is not proof that they describe the same event."
                    ),
                )
            )
    return sorted(clusters, key=lambda item: (item.distance_km, item.time_window_hours))


def _apply_change_state(signals: list[WorldSignal]) -> bool:
    global _previous_fingerprints
    current: dict[str, str] = {}
    baseline = not bool(_previous_fingerprints)
    for signal in signals:
        fingerprint = hashlib.sha1(signal.fingerprint_payload.encode("utf-8")).hexdigest()
        current[signal.signal_id] = fingerprint
        previous = _previous_fingerprints.get(signal.signal_id)
        if baseline:
            signal.state = "known"
        elif previous is None:
            signal.state = "new"
        elif previous != fingerprint:
            signal.state = "updated"
        else:
            signal.state = "known"
    _previous_fingerprints = current
    return baseline


async def collect_world_pulse() -> WorldPulseResponse:
    async with httpx.AsyncClient(
        timeout=_TIMEOUT,
        headers={"User-Agent": "COMMONS-World-Pulse/0.1 (+https://github.com/mikelninh/COMMONS)"},
        follow_redirects=True,
    ) as client:
        import asyncio

        results = await asyncio.gather(
            _fetch_usgs(client),
            _fetch_eonet(client),
            _fetch_gdacs(client),
        )

    signals: list[WorldSignal] = []
    source_states: list[SourceState] = []
    for source_signals, source_state in results:
        signals.extend(source_signals)
        source_states.append(source_state)

    baseline = _apply_change_state(signals)
    clusters = _clusters(signals)
    clustered_ids = {signal_id for cluster in clusters for signal_id in cluster.signal_ids}
    for signal in signals:
        if signal.signal_id in clustered_ids:
            if "possible multi-source cluster" not in signal.attention_reasons:
                signal.attention_reasons.append("possible multi-source cluster")

    signals.sort(
        key=lambda signal: (
            0 if signal.state == "new" else 1 if signal.state == "updated" else 2,
            -(signal.updated_at or signal.occurred_at or datetime(1970, 1, 1, tzinfo=timezone.utc)).timestamp(),
        )
    )

    stats = WorldPulseStats(
        total_signals=len(signals),
        new_signals=sum(signal.state == "new" for signal in signals),
        updated_signals=sum(signal.state == "updated" for signal in signals),
        attention_signals=sum(bool(signal.attention_reasons) for signal in signals),
        possible_multi_source_clusters=len(clusters),
    )
    return WorldPulseResponse(
        generated_at=datetime.now(timezone.utc),
        baseline_observation=baseline,
        source_states=source_states,
        stats=stats,
        signals=signals,
        clusters=clusters,
    )
