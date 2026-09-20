from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
VERIFY_LAG_DAYS = 7
MAX_OBSERVATIONS = 2500


def _request_json(url: str, params: dict[str, Any], timeout: int = 60) -> dict[str, Any]:
    request = Request(
        url + "?" + urlencode(params),
        headers={"User-Agent": "COMMONS-Attention-Ledger/0.1"},
    )
    with urlopen(request, timeout=timeout) as response:  # noqa: S310
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("error"):
        raise RuntimeError(str(payload.get("reason") or payload))
    return payload


def _actual_daily_rain_mm(
    *,
    latitude: float,
    longitude: float,
    target_date: str,
) -> float | None:
    payload = _request_json(
        ARCHIVE_URL,
        {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": target_date,
            "end_date": target_date,
            "daily": "precipitation_sum",
            "models": "era5",
            "timezone": "UTC",
        },
    )
    daily = payload.get("daily") or {}
    values = daily.get("precipitation_sum") or []
    if not values or values[0] is None:
        return None
    return float(values[0])


def _classification(state: str, heavy: bool) -> str:
    if state == "alert":
        return "alert_hit" if heavy else "false_alert"
    if state == "priority":
        return "priority_catch" if heavy else "priority_no_event"
    if state == "quiet":
        return "quiet_miss" if heavy else "correct_quiet"
    return "unavailable_outcome"


def _empty_ledger() -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "updated_at": None,
        "observations": [],
        "verification_cache": {},
        "source_errors": [],
        "summary": {},
        "contract": {
            "verification": "ERA5 daily precipitation after a 7-day availability lag",
            "purpose": "Track live Morning Brief decisions against later observed outcomes.",
            "not_measured_yet": "Human action effectiveness and harm reduction.",
        },
    }


def load_ledger(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return _empty_ledger()
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty_ledger()
    if not isinstance(payload, dict):
        return _empty_ledger()
    payload.setdefault("observations", [])
    payload.setdefault("verification_cache", {})
    payload.setdefault("source_errors", [])
    return payload


def append_brief(ledger: dict[str, Any], brief: dict[str, Any]) -> None:
    generated_at = brief.get("generated_at")
    existing = {
        item.get("observation_id")
        for item in ledger.get("observations") or []
        if item.get("observation_id")
    }
    for monitor in brief.get("monitors") or []:
        peak_date = monitor.get("forecast_peak_date")
        point_id = monitor.get("point_id")
        if not generated_at or not peak_date or not point_id:
            continue
        latitude = monitor.get("latitude")
        longitude = monitor.get("longitude")
        gate = monitor.get("heavy_rain_gate_mm")
        forecast = monitor.get("forecast_peak_daily_mm")
        if latitude is None or longitude is None or gate is None or forecast is None:
            continue
        observation_id = f"{point_id}|{generated_at}|{peak_date}"
        if observation_id in existing:
            continue
        ledger["observations"].append(
            {
                "observation_id": observation_id,
                "generated_at": generated_at,
                "point_id": point_id,
                "name": monitor.get("name"),
                "country": monitor.get("country"),
                "state": monitor.get("state"),
                "forecast_peak_date": peak_date,
                "forecast_peak_daily_mm": forecast,
                "heavy_rain_gate_mm": gate,
                "gate_ratio": monitor.get("gate_ratio"),
                "latitude": latitude,
                "longitude": longitude,
                "verification_status": "pending",
                "classification": None,
                "actual_daily_mm": None,
            }
        )
        existing.add(observation_id)

    ledger["observations"] = ledger["observations"][-MAX_OBSERVATIONS:]


def verify_matured(
    ledger: dict[str, Any],
    *,
    today: date | None = None,
) -> None:
    today = today or datetime.now(timezone.utc).date()
    cutoff = today - timedelta(days=VERIFY_LAG_DAYS)
    cache = ledger.setdefault("verification_cache", {})
    errors: list[dict[str, str]] = []

    for item in ledger.get("observations") or []:
        if item.get("verification_status") == "verified":
            continue
        raw_target = item.get("forecast_peak_date")
        if not raw_target:
            continue
        try:
            target = date.fromisoformat(str(raw_target))
        except ValueError:
            continue
        if target > cutoff:
            continue

        key = f'{item.get("point_id")}|{raw_target}'
        if key in cache:
            actual = cache[key].get("actual_daily_mm")
        else:
            try:
                actual = _actual_daily_rain_mm(
                    latitude=float(item["latitude"]),
                    longitude=float(item["longitude"]),
                    target_date=str(raw_target),
                )
            except Exception as exc:
                errors.append(
                    {
                        "point_id": str(item.get("point_id")),
                        "target_date": str(raw_target),
                        "error": str(exc),
                    }
                )
                continue
            if actual is None:
                continue
            cache[key] = {
                "actual_daily_mm": round(actual, 2),
                "source": "ERA5 via Open-Meteo",
                "verified_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            }

        if actual is None:
            continue
        gate = float(item["heavy_rain_gate_mm"])
        heavy = float(actual) >= gate
        item["actual_daily_mm"] = round(float(actual), 2)
        item["observed_heavy_event"] = heavy
        item["classification"] = _classification(str(item.get("state")), heavy)
        item["verification_status"] = "verified"
        item["verified_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    ledger["source_errors"] = errors[-100:]


def summarize_ledger(ledger: dict[str, Any]) -> dict[str, Any]:
    observations = ledger.get("observations") or []
    verified = [item for item in observations if item.get("verification_status") == "verified"]
    counts: dict[str, int] = {}
    for item in verified:
        label = str(item.get("classification") or "unknown")
        counts[label] = counts.get(label, 0) + 1

    alert_verified = counts.get("alert_hit", 0) + counts.get("false_alert", 0)
    alert_precision = (
        counts.get("alert_hit", 0) / alert_verified
        if alert_verified
        else None
    )
    observed_heavy = [item for item in verified if item.get("observed_heavy_event")]
    captured_before_quiet = sum(
        item.get("classification") in {"alert_hit", "priority_catch"}
        for item in observed_heavy
    )
    heavy_capture_rate = (
        captured_before_quiet / len(observed_heavy)
        if observed_heavy
        else None
    )

    return {
        "total_observations": len(observations),
        "pending": sum(item.get("verification_status") != "verified" for item in observations),
        "verified": len(verified),
        "classifications": counts,
        "alert_precision": round(alert_precision, 4) if alert_precision is not None else None,
        "heavy_event_capture_before_quiet": (
            round(heavy_capture_rate, 4) if heavy_capture_rate is not None else None
        ),
        "quiet_misses": counts.get("quiet_miss", 0),
        "priority_catches": counts.get("priority_catch", 0),
    }


def update_attention_ledger(
    brief: dict[str, Any],
    ledger: dict[str, Any] | None = None,
    *,
    today: date | None = None,
) -> dict[str, Any]:
    ledger = ledger or _empty_ledger()
    append_brief(ledger, brief)
    verify_matured(ledger, today=today)
    ledger["summary"] = summarize_ledger(ledger)
    ledger["updated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return ledger
