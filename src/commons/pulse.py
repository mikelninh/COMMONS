from __future__ import annotations

import csv
import io
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Callable, Literal

import httpx
from pydantic import BaseModel, Field


Freshness = Literal["live", "near_real_time", "periodic", "modelled"]


class PulseSignal(BaseModel):
    id: str
    category: str
    label: str
    value: float
    unit: str
    display_value: str
    freshness: Freshness
    confidence: Literal["high", "medium", "low"]
    as_of: str
    source_name: str
    source_url: str
    methodology: str
    trend: Literal["up", "down", "flat", "unknown"] = "unknown"
    trend_detail: str | None = None


class PulseSnapshot(BaseModel):
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    signals: list[PulseSignal]
    warnings: list[str] = Field(default_factory=list)


TIMEOUT = 8.0
CACHE_SECONDS = 300
UA = {"User-Agent": "COMMONS-WORLD-PULSE/0.1 (+https://github.com/mikelninh/COMMONS)"}
_cache_lock = Lock()
_cache_until = 0.0
_cache_snapshot: PulseSnapshot | None = None


def _json(url: str) -> Any:
    with httpx.Client(timeout=TIMEOUT, headers=UA, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.json()


def _text(url: str) -> str:
    with httpx.Client(timeout=TIMEOUT, headers=UA, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


def _latest_world_csv(url: str) -> tuple[int, float, str]:
    rows = list(csv.DictReader(io.StringIO(_text(url))))
    world_rows = [r for r in rows if r.get("Entity") == "World"]
    if not world_rows:
        raise ValueError("World row missing")
    value_keys = [k for k in world_rows[0].keys() if k not in {"Entity", "Code", "Year"}]
    if not value_keys:
        raise ValueError("Value column missing")
    key = value_keys[0]
    valid = [(int(r["Year"]), float(r[key])) for r in world_rows if r.get(key) not in {"", None}]
    if not valid:
        raise ValueError("No numeric world values")
    year, value = max(valid, key=lambda x: x[0])
    return year, value, key


def eonet_signals() -> list[PulseSignal]:
    data = _json("https://eonet.gsfc.nasa.gov/api/v3/events?status=open&limit=500")
    events = data.get("events", [])
    wildfires = [
        event
        for event in events
        if any(category.get("id") == "wildfires" for category in event.get("categories", []))
    ]
    wildfire_ids = {event.get("id") for event in wildfires}
    non_fire = [event for event in events if event.get("id") not in wildfire_ids]
    now = datetime.now(timezone.utc).date().isoformat()
    return [
        PulseSignal(
            id="open-natural-events",
            category="planet",
            label="Open natural events tracked by NASA EONET",
            value=float(len(non_fire)),
            unit="events",
            display_value=f"{len(non_fire):,}",
            freshness="near_real_time",
            confidence="high",
            as_of=now,
            source_name="NASA EONET",
            source_url="https://eonet.gsfc.nasa.gov/",
            methodology="Count of currently open EONET events excluding the wildfire category. EONET is a curated event tracker, not a complete census of every event on Earth.",
        ),
        PulseSignal(
            id="open-wildfires",
            category="planet",
            label="Open wildfire events tracked by NASA EONET",
            value=float(len(wildfires)),
            unit="events",
            display_value=f"{len(wildfires):,}",
            freshness="near_real_time",
            confidence="high",
            as_of=now,
            source_name="NASA EONET",
            source_url="https://eonet.gsfc.nasa.gov/",
            methodology="Count of currently open EONET events tagged as wildfires. This is event-level tracking, not the number of satellite fire detections.",
        ),
    ]


def usgs_signal() -> PulseSignal:
    data = _json("https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson")
    count = int(data.get("metadata", {}).get("count", len(data.get("features", []))))
    generated_ms = data.get("metadata", {}).get("generated")
    as_of = (
        datetime.fromtimestamp(generated_ms / 1000, tz=timezone.utc).isoformat()
        if generated_ms
        else datetime.now(timezone.utc).isoformat()
    )
    return PulseSignal(
        id="earthquakes-45-day",
        category="planet",
        label="M4.5+ earthquakes in the past 24 hours",
        value=float(count),
        unit="earthquakes",
        display_value=f"{count:,}",
        freshness="live",
        confidence="high",
        as_of=as_of,
        source_name="USGS Earthquake Hazards Program",
        source_url="https://earthquake.usgs.gov/earthquakes/feed/",
        methodology="USGS GeoJSON summary feed for magnitude 4.5+ earthquakes in the past day. The feed is updated every minute.",
    )


def world_bank_births_signal() -> PulseSignal:
    pop = _json("https://api.worldbank.org/v2/country/WLD/indicator/SP.POP.TOTL?format=json&per_page=10")
    birth = _json("https://api.worldbank.org/v2/country/WLD/indicator/SP.DYN.CBRT.IN?format=json&per_page=10")
    pop_by_year = {int(r["date"]): float(r["value"]) for r in pop[1] if r.get("value") is not None}
    birth_by_year = {int(r["date"]): float(r["value"]) for r in birth[1] if r.get("value") is not None}
    common = sorted(set(pop_by_year) & set(birth_by_year), reverse=True)
    if not common:
        raise ValueError("No overlapping population and birth-rate year")
    year = common[0]
    estimate = pop_by_year[year] * birth_by_year[year] / 1000 / 365.25
    return PulseSignal(
        id="births-per-day-model",
        category="humanity",
        label="Estimated births per day",
        value=estimate,
        unit="births/day",
        display_value=f"~{estimate:,.0f}",
        freshness="modelled",
        confidence="medium",
        as_of=str(year),
        source_name="World Bank / UN population data",
        source_url="https://data.worldbank.org/indicator/SP.DYN.CBRT.IN",
        methodology="Modelled estimate: world population × crude birth rate ÷ 1,000 ÷ 365.25 using the latest year available for both inputs. This is not a live birth counter.",
    )


def renewable_electricity_signal() -> PulseSignal:
    year, value, _ = _latest_world_csv(
        "https://ourworldindata.org/grapher/share-electricity-renewables.csv?v=1&csvType=full&useColumnShortNames=false"
    )
    return PulseSignal(
        id="renewable-electricity-share",
        category="progress",
        label="World electricity generated from renewables",
        value=value,
        unit="%",
        display_value=f"{value:.1f}%",
        freshness="periodic",
        confidence="high",
        as_of=str(year),
        source_name="Our World in Data / Ember and other sources",
        source_url="https://ourworldindata.org/grapher/share-electricity-renewables",
        methodology="Latest published annual world share of electricity generation from renewable sources. Periodic structural indicator, not a live grid reading.",
    )


def life_expectancy_signal() -> PulseSignal:
    year, value, _ = _latest_world_csv(
        "https://ourworldindata.org/grapher/life-expectancy.csv?v=1&csvType=full&useColumnShortNames=false"
    )
    return PulseSignal(
        id="life-expectancy",
        category="progress",
        label="Global life expectancy at birth",
        value=value,
        unit="years",
        display_value=f"{value:.1f} years",
        freshness="periodic",
        confidence="high",
        as_of=str(year),
        source_name="Our World in Data",
        source_url="https://ourworldindata.org/grapher/life-expectancy",
        methodology="Latest published annual world estimate. This is a slow-moving progress indicator and should not be interpreted as real-time.",
    )


def _producers() -> list[tuple[str, Callable[[], list[PulseSignal]]]]:
    return [
        ("NASA EONET", eonet_signals),
        ("USGS", lambda: [usgs_signal()]),
        ("World Bank births model", lambda: [world_bank_births_signal()]),
        ("OWID renewables", lambda: [renewable_electricity_signal()]),
        ("OWID life expectancy", lambda: [life_expectancy_signal()]),
    ]


def _fresh_snapshot() -> PulseSnapshot:
    signals: list[PulseSignal] = []
    warnings: list[str] = []
    producers = _producers()
    with ThreadPoolExecutor(max_workers=len(producers)) as pool:
        future_to_name = {pool.submit(producer): name for name, producer in producers}
        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                signals.extend(future.result())
            except Exception as exc:
                warnings.append(f"{name} unavailable: {type(exc).__name__}")
    order = {
        "open-natural-events": 0,
        "open-wildfires": 1,
        "earthquakes-45-day": 2,
        "births-per-day-model": 3,
        "renewable-electricity-share": 4,
        "life-expectancy": 5,
    }
    signals.sort(key=lambda signal: order.get(signal.id, 99))
    return PulseSnapshot(signals=signals, warnings=warnings)


def build_snapshot(force: bool = False) -> PulseSnapshot:
    global _cache_snapshot, _cache_until
    now = time.monotonic()
    with _cache_lock:
        if not force and _cache_snapshot is not None and now < _cache_until:
            return _cache_snapshot.model_copy(deep=True)

    snapshot = _fresh_snapshot()

    with _cache_lock:
        _cache_snapshot = snapshot
        _cache_until = time.monotonic() + CACHE_SECONDS
    return snapshot.model_copy(deep=True)
