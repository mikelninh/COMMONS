from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
from statistics import median
from typing import Any, Iterable
from urllib.parse import urlencode
from urllib.request import Request, urlopen


FORECAST_PROVIDERS = {
    "ecmwf": "ECMWF IFS",
    "gfs": "NOAA GFS",
    "icon": "DWD ICON",
}

PUBLIC_ENDPOINTS = {
    "ecmwf": "https://api.open-meteo.com/v1/ecmwf",
    "gfs": "https://api.open-meteo.com/v1/gfs",
    "icon": "https://api.open-meteo.com/v1/dwd-icon",
    "archive": "https://archive-api.open-meteo.com/v1/archive",
    "flood": "https://flood-api.open-meteo.com/v1/flood",
}


@dataclass(frozen=True)
class WatchPoint:
    loop_id: str
    name: str
    country: str
    latitude: float
    longitude: float
    weather_relevant: bool = True
    full_memory: bool = False
    flood_relevant: bool = False


WATCHPOINTS: tuple[WatchPoint, ...] = (
    WatchPoint("water-rises", "Nuwakot", "Nepal", 27.95, 85.18, True, True, True),
    WatchPoint("storm-arrives", "Manila", "Philippines", 14.60, 120.98, True),
    WatchPoint("heat-we-cannot-see", "Delhi", "India", 28.61, 77.21, True),
    WatchPoint("forest-burns", "Los Angeles", "United States", 34.05, -118.24, True),
    WatchPoint("air-we-breathe", "Warsaw", "Poland", 52.23, 21.01, True),
    WatchPoint("rain-doesnt-come", "Niamey", "Niger", 13.51, 2.11, True),
    WatchPoint("stop-an-outbreak", "Kinshasa", "DRC", -4.33, 15.31, False),
    WatchPoint("ground-moves", "Tokyo", "Japan", 35.68, 139.76, False),
    WatchPoint("enough-to-eat", "Mogadishu", "Somalia", 2.05, 45.32, True),
    WatchPoint("humanity-succeeds", "Thimphu", "Bhutan", 27.47, 89.64, False),
)


class WorldModelError(RuntimeError):
    pass


class OpenMeteoClient:
    """Small dependency-free adapter for the research World Model prototype.

    Free Open-Meteo endpoints are used only in non-commercial research mode.
    Commercial mode deliberately fails closed unless customer endpoints and an
    API key are configured.
    """

    def __init__(
        self,
        *,
        commercial: bool | None = None,
        api_key: str | None = None,
        endpoints: dict[str, str] | None = None,
        timeout: int = 30,
    ) -> None:
        if commercial is None:
            commercial = os.getenv("COMMONS_COMMERCIAL_MODE", "0") == "1"
        self.commercial = commercial
        self.api_key = api_key or os.getenv("OPEN_METEO_API_KEY")
        self.timeout = timeout
        configured = dict(PUBLIC_ENDPOINTS)
        for key in configured:
            env_key = f"OPEN_METEO_{key.upper()}_URL"
            if os.getenv(env_key):
                configured[key] = os.environ[env_key]
        if endpoints:
            configured.update(endpoints)
        self.endpoints = configured

        if self.commercial:
            if not self.api_key:
                raise WorldModelError(
                    "Commercial mode requires OPEN_METEO_API_KEY. "
                    "Do not monetize on the free non-commercial endpoint."
                )
            non_customer = [
                url for url in configured.values() if "customer" not in url
            ]
            if non_customer:
                raise WorldModelError(
                    "Commercial mode requires customer Open-Meteo endpoints. "
                    "Set OPEN_METEO_*_URL explicitly."
                )

    def _get(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        payload = dict(params)
        if self.api_key:
            payload["apikey"] = self.api_key
        url = self.endpoints[endpoint] + "?" + urlencode(payload)
        request = Request(
            url,
            headers={
                "User-Agent": "COMMONS-World-Model/0.1 (+https://github.com/mikelninh/COMMONS)"
            },
        )
        with urlopen(request, timeout=self.timeout) as response:  # noqa: S310
            body = response.read().decode("utf-8")
        parsed = json.loads(body)
        if parsed.get("error"):
            raise WorldModelError(str(parsed.get("reason") or parsed))
        return parsed

    def forecast(self, provider: str, point: WatchPoint) -> dict[str, Any]:
        return self._get(
            provider,
            {
                "latitude": point.latitude,
                "longitude": point.longitude,
                "daily": ",".join(
                    (
                        "temperature_2m_max",
                        "temperature_2m_min",
                        "precipitation_sum",
                        "wind_gusts_10m_max",
                    )
                ),
                "timezone": "UTC",
                "forecast_days": 7,
            },
        )

    def era5_history(
        self,
        point: WatchPoint,
        *,
        start_date: str = "1940-01-01",
        end_date: str | None = None,
    ) -> dict[str, Any]:
        if end_date is None:
            end_date = (date.today() - timedelta(days=7)).isoformat()
        return self._get(
            "archive",
            {
                "latitude": point.latitude,
                "longitude": point.longitude,
                "start_date": start_date,
                "end_date": end_date,
                "daily": "precipitation_sum,temperature_2m_max",
                "timezone": "UTC",
                "models": "era5",
            },
        )

    def flood_history(
        self,
        point: WatchPoint,
        *,
        start_date: str = "1984-01-01",
        end_date: str = "2022-07-31",
    ) -> dict[str, Any]:
        return self._get(
            "flood",
            {
                "latitude": point.latitude,
                "longitude": point.longitude,
                "start_date": start_date,
                "end_date": end_date,
                "daily": "river_discharge",
            },
        )

    def flood_forecast(
        self,
        point: WatchPoint,
        *,
        forecast_days: int = 14,
    ) -> dict[str, Any]:
        return self._get(
            "flood",
            {
                "latitude": point.latitude,
                "longitude": point.longitude,
                "forecast_days": forecast_days,
                "daily": "river_discharge",
            },
        )


class FixtureClient:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def forecast(self, provider: str, point: WatchPoint) -> dict[str, Any]:
        return self.payload["forecast"][point.loop_id][provider]

    def era5_history(self, point: WatchPoint, **_: Any) -> dict[str, Any]:
        return self.payload["history"][point.loop_id]

    def flood_history(self, point: WatchPoint, **_: Any) -> dict[str, Any]:
        return self.payload["flood_history"][point.loop_id]

    def flood_forecast(self, point: WatchPoint, **_: Any) -> dict[str, Any]:
        return self.payload["flood_forecast"][point.loop_id]


def _clean(values: Iterable[Any]) -> list[float]:
    out: list[float] = []
    for value in values:
        if value is None:
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number):
            out.append(number)
    return out


def summarize_forecast_response(payload: dict[str, Any]) -> dict[str, Any]:
    daily = payload.get("daily") or {}
    times = daily.get("time") or []
    precip = _clean((daily.get("precipitation_sum") or [])[:3])
    temps = _clean((daily.get("temperature_2m_max") or [])[:3])
    mins = _clean((daily.get("temperature_2m_min") or [])[:3])
    gusts = _clean((daily.get("wind_gusts_10m_max") or [])[:3])
    if not times or not (precip or temps or gusts):
        raise WorldModelError("Forecast response did not contain usable daily data.")
    return {
        "start_date": times[0],
        "precip_72h_mm": round(sum(precip), 1) if precip else None,
        "temp_max_72h_c": round(max(temps), 1) if temps else None,
        "temp_min_72h_c": round(min(mins), 1) if mins else None,
        "gust_max_72h_kmh": round(max(gusts), 1) if gusts else None,
    }


def _agreement(values: list[float]) -> str:
    if len(values) < 2:
        return "unknown"
    center = abs(median(values))
    spread = max(values) - min(values)
    scale = max(center, 1.0)
    ratio = spread / scale
    if ratio <= 0.20:
        return "high"
    if ratio <= 0.45:
        return "medium"
    return "low"


def build_forecast_council(
    point: WatchPoint,
    client: OpenMeteoClient | FixtureClient,
) -> dict[str, Any]:
    members: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for provider, label in FORECAST_PROVIDERS.items():
        try:
            summary = summarize_forecast_response(client.forecast(provider, point))
            members.append({"provider": provider, "label": label, **summary})
        except Exception as exc:  # source failure is surfaced, not hidden
            errors.append({"provider": provider, "error": str(exc)})

    precip = _clean(member.get("precip_72h_mm") for member in members)
    temp = _clean(member.get("temp_max_72h_c") for member in members)
    gust = _clean(member.get("gust_max_72h_kmh") for member in members)
    return {
        "members": members,
        "source_errors": errors,
        "consensus": {
            "precip_72h_mm_median": round(median(precip), 1) if precip else None,
            "temp_max_72h_c_median": round(median(temp), 1) if temp else None,
            "gust_max_72h_kmh_median": round(median(gust), 1) if gust else None,
            "precip_agreement": _agreement(precip),
            "temperature_agreement": _agreement(temp),
            "gust_agreement": _agreement(gust),
        },
        "interpretation": (
            "Model agreement is a spread heuristic across deterministic forecasts; "
            "it is not a calibrated probability."
        ),
    }


def _seasonal_distance(day_a: int, day_b: int) -> int:
    diff = abs(day_a - day_b)
    return min(diff, 366 - diff)


def build_weather_memory(
    payload: dict[str, Any],
    *,
    target_precip_72h_mm: float | None,
    target_start_date: str,
) -> dict[str, Any]:
    daily = payload.get("daily") or {}
    times = daily.get("time") or []
    precip_raw = daily.get("precipitation_sum") or []
    if not target_precip_72h_mm or len(times) < 4:
        return {
            "status": "insufficient_data",
            "source": "ERA5",
            "analogues": [],
            "seasonal_percentile": None,
        }

    target_day = datetime.fromisoformat(target_start_date).timetuple().tm_yday
    candidates: list[tuple[str, float]] = []
    for index in range(len(times) - 2):
        try:
            dates = [
                datetime.fromisoformat(times[index + offset])
                for offset in range(3)
            ]
        except ValueError:
            continue
        dt = dates[0]
        if (dates[1].date() - dates[0].date()).days != 1:
            continue
        if (dates[2].date() - dates[1].date()).days != 1:
            continue
        if _seasonal_distance(dt.timetuple().tm_yday, target_day) > 45:
            continue
        values = _clean(precip_raw[index : index + 3])
        if len(values) != 3:
            continue
        candidates.append((times[index], sum(values)))

    if not candidates:
        return {
            "status": "insufficient_data",
            "source": "ERA5",
            "analogues": [],
            "seasonal_percentile": None,
        }

    amounts = sorted(value for _, value in candidates)
    rank = sum(1 for value in amounts if value <= target_precip_72h_mm)
    percentile = 100.0 * rank / len(amounts)
    analogues = sorted(
        candidates,
        key=lambda item: abs(item[1] - target_precip_72h_mm),
    )[:5]
    return {
        "status": "ok",
        "source": "ERA5",
        "historical_period_start": times[0],
        "historical_period_end": times[-1],
        "season_window_days": 45,
        "seasonal_percentile": round(percentile, 1),
        "analogues": [
            {
                "start_date": start,
                "precip_72h_mm": round(amount, 1),
                "difference_mm": round(abs(amount - target_precip_72h_mm), 1),
            }
            for start, amount in analogues
        ],
        "limitation": (
            "Analogues compare seasonal three-day precipitation totals only. "
            "They are not full atmospheric analogues and do not imply similar human impact."
        ),
    }


def percentile_rank(values: list[float], target: float) -> float | None:
    cleaned = sorted(_clean(values))
    if not cleaned:
        return None
    rank = sum(1 for value in cleaned if value <= target)
    return 100.0 * rank / len(cleaned)


def _discharge_pairs(payload: dict[str, Any]) -> list[tuple[date, float]]:
    daily = payload.get("daily") or {}
    times = daily.get("time") or []
    discharge = daily.get("river_discharge") or []
    paired: list[tuple[date, float]] = []
    for raw_date, raw_value in zip(times, discharge):
        try:
            dt = date.fromisoformat(raw_date)
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(value):
            paired.append((dt, value))
    return paired


def build_flood_signal(
    history_payload: dict[str, Any],
    forecast_payload: dict[str, Any],
    *,
    now: date | None = None,
) -> dict[str, Any]:
    now = now or date.today()
    history_pairs = _discharge_pairs(history_payload)
    forecast_pairs = _discharge_pairs(forecast_payload)
    historic = [value for _, value in history_pairs]
    future = [(dt, value) for dt, value in forecast_pairs if dt >= now]
    if not historic or not future:
        return {"status": "insufficient_data"}

    future_peak_date, future_peak = max(future[:14], key=lambda item: item[1])
    percentile = percentile_rank(historic, future_peak)
    return {
        "status": "ok",
        "forecast_peak_date": future_peak_date.isoformat(),
        "forecast_peak_discharge_m3s": round(future_peak, 1),
        "historical_percentile": round(percentile, 1) if percentile is not None else None,
        "historical_start": history_pairs[0][0].isoformat(),
        "historical_end": history_pairs[-1][0].isoformat(),
        "source": "GloFAS v4 via Open-Meteo Flood API",
        "limitation": (
            "GloFAS is simulated river discharge at roughly 5 km resolution. "
            "The API may select a nearby large river rather than the exact river of interest; "
            "this is flood guidance, not a local warning."
        ),
    }


def build_snapshot(
    client: OpenMeteoClient | FixtureClient,
    *,
    now: datetime | None = None,
    memory_cache: dict[str, Any] | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    loops: list[dict[str, Any]] = []
    cache = memory_cache if memory_cache is not None else {}
    cache.setdefault("schema_version", "0.1")
    era5_cache = cache.setdefault("era5", {})
    flood_history_cache = cache.setdefault("flood_history", {})

    for point in WATCHPOINTS:
        loop: dict[str, Any] = {
            "id": point.loop_id,
            "watchpoint": {
                "name": point.name,
                "country": point.country,
                "latitude": point.latitude,
                "longitude": point.longitude,
            },
            "physical_context": "not_applicable" if not point.weather_relevant else "live",
        }

        if point.weather_relevant:
            council = build_forecast_council(point, client)
            loop["forecast_council"] = council
            if point.full_memory and council["members"]:
                target = council["consensus"].get("precip_72h_mm_median")
                start_date = council["members"][0]["start_date"]
                try:
                    history_payload = era5_cache.get(point.loop_id)
                    if history_payload is None:
                        history_payload = client.era5_history(point)
                        era5_cache[point.loop_id] = history_payload
                    loop["weather_memory"] = build_weather_memory(
                        history_payload,
                        target_precip_72h_mm=target,
                        target_start_date=start_date,
                    )
                except Exception as exc:
                    loop["weather_memory"] = {
                        "status": "source_error",
                        "error": str(exc),
                    }
            else:
                loop["weather_memory"] = {"status": "not_yet_enabled"}

        if point.flood_relevant:
            try:
                history_payload = flood_history_cache.get(point.loop_id)
                if history_payload is None:
                    history_payload = client.flood_history(point)
                    flood_history_cache[point.loop_id] = history_payload
                forecast_payload = client.flood_forecast(point)
                loop["flood_signal"] = build_flood_signal(
                    history_payload,
                    forecast_payload,
                    now=now.date(),
                )
            except Exception as exc:
                loop["flood_signal"] = {"status": "source_error", "error": str(exc)}

        loops.append(loop)

    cache["updated_at"] = now.isoformat().replace("+00:00", "Z")

    return {
        "schema_version": "0.1",
        "generated_at": now.isoformat().replace("+00:00", "Z"),
        "mode": "research",
        "product": "COMMONS World Model v0",
        "source_contract": {
            "forecast": "ECMWF IFS + NOAA GFS + DWD ICON via Open-Meteo",
            "memory": "ERA5 reanalysis via Open-Meteo",
            "flood": "GloFAS v4 via Open-Meteo",
            "licensing_note": (
                "The public prototype uses non-commercial Open-Meteo access. "
                "Commercial mode fails closed unless paid/customer endpoints are configured."
            ),
        },
        "cache_contract": {
            "era5_history": "cached on world-model-data; not refetched every six hours",
            "glofas_history": "cached on world-model-data; live forecast refreshed each run",
        },
        "loops": loops,
    }


def load_fixture(path: str | Path) -> FixtureClient:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return FixtureClient(payload)
