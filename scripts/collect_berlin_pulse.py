#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import statistics
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "public" / "data" / "berlin-pulse"
HISTORY_PATH = DATA_DIR / "history.json"
LEDGER_PATH = DATA_DIR / "ledger.json"
LATEST_PATH = DATA_DIR / "latest.json"
UTC = timezone.utc
BERLIN = {"lat": 52.52, "lon": 13.405}
BBOX = {"north": 52.70, "west": 13.08, "south": 52.34, "east": 13.78}
BERLIN_TZ = ZoneInfo("Europe/Berlin")


def now_utc() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def parse_iso(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def http_text(url: str, timeout: int = 25) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "COMMONS-Berlin-Pulse/1.0 (+https://github.com/mikelninh/COMMONS)"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def http_json(url: str, timeout: int = 25) -> Any:
    return json.loads(http_text(url, timeout=timeout))


def api_url(base: str, params: dict[str, Any]) -> str:
    return base + "?" + urllib.parse.urlencode(params, doseq=True)


def safe_float(value: Any) -> float | None:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def closest_index(times: list[str], target: datetime) -> int | None:
    if not times:
        return None
    parsed = []
    for i, value in enumerate(times):
        try:
            parsed.append((abs((parse_iso(value) - target).total_seconds()), i))
        except Exception:
            continue
    return min(parsed)[1] if parsed else None


def series_pairs(payload: dict[str, Any], key: str) -> list[tuple[datetime, float]]:
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    values = hourly.get(key) or []
    pairs: list[tuple[datetime, float]] = []
    for stamp, value in zip(times, values):
        number = safe_float(value)
        if number is None:
            continue
        try:
            pairs.append((parse_iso(stamp), number))
        except Exception:
            continue
    return pairs


def fetch_weather() -> dict[str, Any]:
    url = api_url(
        "https://api.open-meteo.com/v1/forecast",
        {
            "latitude": BERLIN["lat"],
            "longitude": BERLIN["lon"],
            "current": "temperature_2m,apparent_temperature,precipitation,wind_speed_10m",
            "hourly": "temperature_2m,apparent_temperature,precipitation,wind_speed_10m",
            "past_hours": 48,
            "forecast_hours": 25,
            "timezone": "UTC",
        },
    )
    return http_json(url)


def fetch_air() -> dict[str, Any]:
    url = api_url(
        "https://air-quality-api.open-meteo.com/v1/air-quality",
        {
            "latitude": BERLIN["lat"],
            "longitude": BERLIN["lon"],
            "current": "pm2_5,nitrogen_dioxide,ozone",
            "hourly": "pm2_5,nitrogen_dioxide,ozone",
            "past_hours": 48,
            "forecast_hours": 25,
            "timezone": "UTC",
        },
    )
    return http_json(url)


def fetch_flood() -> dict[str, Any]:
    url = api_url(
        "https://flood-api.open-meteo.com/v1/flood",
        {
            "latitude": BERLIN["lat"],
            "longitude": BERLIN["lon"],
            "daily": "river_discharge",
            "past_days": 14,
            "forecast_days": 7,
            "timezone": "UTC",
        },
    )
    return http_json(url)


def fetch_transit() -> dict[str, Any]:
    url = api_url(
        "https://v6.vbb.transport.rest/radar",
        {
            **BBOX,
            "results": 600,
            "duration": 30,
        },
    )
    raw = http_json(url)
    movements = raw.get("movements", []) if isinstance(raw, dict) else raw if isinstance(raw, list) else []
    counts = {"bus": 0, "tram": 0, "subway": 0, "train": 0, "other": 0}
    for movement in movements:
        line = movement.get("line") or {}
        product = str(line.get("product") or line.get("mode") or line.get("productName") or "").lower()
        if "subway" in product or "u-bahn" in product:
            counts["subway"] += 1
        elif "tram" in product:
            counts["tram"] += 1
        elif "bus" in product:
            counts["bus"] += 1
        elif "train" in product or "regional" in product or "suburban" in product:
            counts["train"] += 1
        else:
            counts["other"] += 1
    return {"count": len(movements), "modes": counts}


def fetch_official_water(now: datetime) -> dict[str, Any]:
    start = (now - timedelta(days=14)).astimezone(UTC)
    date = start.strftime("%d.%m.%Y")
    url = (
        "https://wasserportal.berlin.de/station.php?anzeige=d&station=582720"
        f"&thema=odf&sreihe=tw&smode=c&sdatum={date}"
    )
    raw = http_text(url)
    parsed: list[float] = []
    for row in csv.reader(raw.splitlines(), delimiter=";"):
        if len(row) < 2:
            continue
        numbers: list[float] = []
        for cell in row:
            cleaned = "".join(ch for ch in cell.replace(",", ".") if ch.isdigit() or ch in ".-")
            value = safe_float(cleaned)
            if value is not None:
                numbers.append(value)
        if numbers:
            value = numbers[-1]
            if 0 <= value < 10000:
                parsed.append(value)
    if len(parsed) < 3:
        raise RuntimeError("official water response did not contain a readable numeric series")
    return {"value": parsed[-1], "history": parsed[-60:], "source": "Wasserportal Berlin · Mühlendamm"}


def flood_current(flood: dict[str, Any], now: datetime) -> tuple[float | None, list[float]]:
    daily = flood.get("daily") or {}
    times = daily.get("time") or []
    values = daily.get("river_discharge") or []
    idx = closest_index(times, now)
    current = safe_float(values[idx]) if idx is not None and idx < len(values) else None
    history: list[float] = []
    for stamp, value in zip(times, values):
        number = safe_float(value)
        if number is None:
            continue
        try:
            if parse_iso(stamp) <= now:
                history.append(number)
        except Exception:
            continue
    return current, history[-14:]


def robust_anomaly(current: float | None, baseline: list[float]) -> dict[str, Any]:
    values = [float(v) for v in baseline if safe_float(v) is not None]
    if current is None or len(values) < 6:
        return {"label": "learning", "score": None, "n": len(values), "baseline": None}
    median = statistics.median(values)
    deviations = [abs(v - median) for v in values]
    mad = statistics.median(deviations)
    if mad > 1e-9:
        score = 0.6745 * (current - median) / mad
    else:
        sd = statistics.pstdev(values)
        score = (current - median) / sd if sd > 1e-9 else 0.0
    magnitude = abs(score)
    label = "unusual" if magnitude >= 2.5 else "watch" if magnitude >= 1.5 else "usual"
    return {
        "label": label,
        "score": round(score, 3),
        "n": len(values),
        "baseline": round(median, 3),
    }


def collected_values(history: dict[str, Any], metric: str, limit: int = 60) -> list[float]:
    values: list[float] = []
    for snapshot in history.get("snapshots", [])[-limit:]:
        value = safe_float((snapshot.get("metrics") or {}).get(metric))
        if value is not None:
            values.append(value)
    return values


def point_at(payload: dict[str, Any], key: str, target: datetime) -> tuple[str | None, float | None]:
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    values = hourly.get(key) or []
    idx = closest_index(times, target)
    if idx is None or idx >= len(values):
        return None, None
    return times[idx], safe_float(values[idx])


def resolve_predictions(ledger: dict[str, Any], metrics: dict[str, Any], now: datetime) -> None:
    for prediction in ledger.get("predictions", []):
        if prediction.get("status") != "pending":
            continue
        try:
            target = parse_iso(prediction["target_at"])
        except Exception:
            continue
        if target > now + timedelta(minutes=15):
            continue
        if now - target > timedelta(minutes=90):
            prediction["status"] = "expired"
            prediction["resolved_at"] = iso(now)
            prediction["reason"] = "collection missed the 90-minute scoring window"
            continue
        actual = safe_float(metrics.get(prediction.get("metric")))
        if actual is None:
            continue
        candidate = safe_float(prediction.get("candidate"))
        baseline = safe_float(prediction.get("baseline"))
        prediction["status"] = "resolved"
        prediction["resolved_at"] = iso(now)
        prediction["actual"] = actual
        prediction["candidate_abs_error"] = round(abs(actual - candidate), 4) if candidate is not None else None
        prediction["baseline_abs_error"] = round(abs(actual - baseline), 4) if baseline is not None else None


def issue_prediction(ledger: dict[str, Any], metric: str, current: float | None, candidate: float | None, target_at: str | None, unit: str, source: str, now: datetime) -> None:
    if current is None or candidate is None or not target_at:
        return
    if any(p.get("metric") == metric and p.get("target_at") == target_at for p in ledger.get("predictions", [])):
        return
    ledger.setdefault("predictions", []).append(
        {
            "id": f"{metric}:{iso(now)}",
            "issued_at": iso(now),
            "target_at": target_at if target_at.endswith("Z") else target_at + "Z",
            "horizon_hours": round((parse_iso(target_at) - now).total_seconds() / 3600, 1),
            "metric": metric,
            "unit": unit,
            "candidate": round(candidate, 4),
            "baseline": round(current, 4),
            "candidate_source": source,
            "baseline_source": "persistence",
            "status": "pending",
        }
    )


def forecast_score(ledger: dict[str, Any]) -> dict[str, Any]:
    resolved = [
        p for p in ledger.get("predictions", [])
        if p.get("status") == "resolved" and safe_float(p.get("candidate_abs_error")) is not None and safe_float(p.get("baseline_abs_error")) is not None
    ]
    if not resolved:
        return {"resolved": 0, "candidate_mae": None, "baseline_mae": None, "candidate_better_rate": None}
    candidate_errors = [float(p["candidate_abs_error"]) for p in resolved]
    baseline_errors = [float(p["baseline_abs_error"]) for p in resolved]
    wins = sum(c < b for c, b in zip(candidate_errors, baseline_errors))
    return {
        "resolved": len(resolved),
        "candidate_mae": round(statistics.fmean(candidate_errors), 4),
        "baseline_mae": round(statistics.fmean(baseline_errors), 4),
        "candidate_better_rate": round(wins / len(resolved), 4),
    }


def headline(signals: dict[str, Any]) -> dict[str, str]:
    candidates: list[tuple[float, str, dict[str, Any]]] = []
    for key, signal in signals.items():
        score = safe_float((signal.get("anomaly") or {}).get("score"))
        if score is not None:
            candidates.append((abs(score), key, signal))
    if not candidates:
        return {
            "level": "learning",
            "title": "Berlin Pulse is learning its baseline.",
            "explanation": "The tape has started. Anomaly claims wait until each signal has enough recent context.",
        }
    magnitude, key, signal = max(candidates)
    anomaly = signal.get("anomaly") or {}
    if magnitude < 1.5:
        return {
            "level": "usual",
            "title": "Nothing unusual is shouting right now.",
            "explanation": "All scored signals are inside their recent baselines. Quiet is a result too.",
        }
    score = float(anomaly["score"])
    direction = "above" if score > 0 else "below"
    titles = {
        "temperature_2m": "Berlin is warmer than its recent pattern." if score > 0 else "Berlin is cooler than its recent pattern.",
        "pm2_5": "Modeled fine-particle air is elevated." if score > 0 else "Modeled fine-particle air is unusually low.",
        "river_discharge": "Spree discharge is above its recent pattern." if score > 0 else "Spree discharge is below its recent pattern.",
        "transit_vehicles": "Transit movement is unusually high for the tape." if score > 0 else "Transit movement is unusually quiet for the tape.",
    }
    return {
        "level": anomaly.get("label", "watch"),
        "title": titles.get(key, f"{signal.get('label', key)} is {direction} its recent pattern."),
        "explanation": f"{signal.get('label', key)} is {direction} a recent median baseline (robust z {score:+.1f}, n={anomaly.get('n', 0)}).",
    }



def build_changes(history: dict[str, Any]) -> list[dict[str, Any]]:
    snapshots = history.get("snapshots", [])
    if len(snapshots) < 2:
        return []
    previous = snapshots[-2].get("metrics") or {}
    current = snapshots[-1].get("metrics") or {}
    specs = {
        "temperature_2m": ("Temperature", "°C", 1),
        "pm2_5": ("PM2.5", "µg/m³", 1),
        "river_discharge": ("Spree / river", "m³/s", 2),
        "transit_vehicles": ("Transit movement", "vehicles", 0),
    }
    changes: list[dict[str, Any]] = []
    for metric, (label, unit, digits) in specs.items():
        before, after = safe_float(previous.get(metric)), safe_float(current.get(metric))
        if before is None or after is None:
            continue
        delta = after - before
        diffs: list[float] = []
        for left, right in zip(snapshots[:-1], snapshots[1:]):
            a = safe_float((left.get("metrics") or {}).get(metric))
            b = safe_float((right.get("metrics") or {}).get(metric))
            if a is not None and b is not None:
                diffs.append(abs(b - a))
        typical = statistics.median(diffs[:-1]) if len(diffs) > 2 else None
        salience = abs(delta) / typical if typical and typical > 1e-9 else abs(delta)
        direction = "up" if delta > 0 else "down" if delta < 0 else "flat"
        pct = (delta / abs(before) * 100) if before else None
        changes.append({
            "metric": metric,
            "label": label,
            "unit": unit,
            "digits": digits,
            "previous": round(before, 3),
            "current": round(after, 3),
            "delta": round(delta, 3),
            "percent": round(pct, 1) if pct is not None else None,
            "direction": direction,
            "salience": round(salience, 3),
            "basis": "since the previous Pulse snapshot",
        })
    return sorted(changes, key=lambda item: item["salience"], reverse=True)


def build_hypotheses(history: dict[str, Any]) -> list[dict[str, Any]]:
    snapshots = history.get("snapshots", [])
    transitions: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for left, right in zip(snapshots[:-1], snapshots[1:]):
        try:
            gap = (parse_iso(right["timestamp"]) - parse_iso(left["timestamp"])).total_seconds() / 3600
        except Exception:
            continue
        if 1.5 <= gap <= 5.5:
            transitions.append((left.get("metrics") or {}, right.get("metrics") or {}))

    wet_pm: list[float] = []
    dry_pm: list[float] = []
    for before, after in transitions:
        rain = safe_float(before.get("precipitation"))
        p0, p1 = safe_float(before.get("pm2_5")), safe_float(after.get("pm2_5"))
        if rain is None or p0 is None or p1 is None:
            continue
        (wet_pm if rain >= 0.2 else dry_pm).append(p1 - p0)
    if len(wet_pm) < 4:
        air_status = "learning"
        air_evidence = f"{len(wet_pm)} rainy transitions captured; 4 are required before comparing them with dry periods."
    else:
        wet_mean = statistics.fmean(wet_pm)
        dry_mean = statistics.fmean(dry_pm) if dry_pm else None
        if dry_mean is None:
            air_status = "learning"
            air_evidence = f"Rainy periods changed modeled PM2.5 by {wet_mean:+.1f} µg/m³ on average, but a dry comparison is still missing."
        else:
            effect = wet_mean - dry_mean
            air_status = "candidate" if effect <= -0.5 else "no_clear_signal"
            air_evidence = f"Rainy transitions vs dry transitions differ by {effect:+.1f} µg/m³ in modeled PM2.5 ({len(wet_pm)} wet / {len(dry_pm)} dry)."

    wet_river: list[float] = []
    for i, snapshot in enumerate(snapshots):
        before = snapshot.get("metrics") or {}
        rain = safe_float(before.get("precipitation"))
        river0 = safe_float(before.get("river_discharge"))
        if rain is None or rain < 0.2 or river0 is None:
            continue
        try:
            start = parse_iso(snapshot["timestamp"])
        except Exception:
            continue
        candidates: list[tuple[float, float]] = []
        for later in snapshots[i + 1:]:
            try:
                gap = (parse_iso(later["timestamp"]) - start).total_seconds() / 3600
            except Exception:
                continue
            if 6 <= gap <= 15:
                river1 = safe_float((later.get("metrics") or {}).get("river_discharge"))
                if river1 is not None:
                    candidates.append((abs(gap - 9), river1 - river0))
        if candidates:
            wet_river.append(min(candidates)[1])
    if len(wet_river) < 4:
        river_status = "learning"
        river_evidence = f"{len(wet_river)} rain→river lag observations captured; 4 are required before interpreting the pattern."
    else:
        river_mean = statistics.fmean(wet_river)
        river_status = "candidate" if river_mean > 0 else "no_clear_signal"
        river_evidence = f"After rainy snapshots, river discharge changed by {river_mean:+.3f} m³/s on average 6–15 hours later (n={len(wet_river)})."

    buckets: dict[int, list[float]] = {}
    for snapshot in snapshots:
        value = safe_float((snapshot.get("metrics") or {}).get("transit_vehicles"))
        if value is None:
            continue
        try:
            local = parse_iso(snapshot["timestamp"]).astimezone(BERLIN_TZ)
        except Exception:
            continue
        bucket = (local.hour // 3) * 3
        buckets.setdefault(bucket, []).append(value)
    repeated = {hour: values for hour, values in buckets.items() if len(values) >= 3}
    if len(repeated) < 2:
        transit_status = "learning"
        transit_evidence = f"{len(repeated)} time-of-day buckets have 3+ observations; 2 are required to test a repeating daily rhythm."
    else:
        medians = {hour: statistics.median(values) for hour, values in repeated.items()}
        low_hour = min(medians, key=medians.get)
        high_hour = max(medians, key=medians.get)
        spread = medians[high_hour] - medians[low_hour]
        transit_status = "candidate" if spread >= 20 else "no_clear_signal"
        transit_evidence = f"Median movement differs by {spread:.0f} vehicles between {low_hour:02d}:00 and {high_hour:02d}:00 Berlin-time buckets."

    return [
        {
            "id": "rain-air",
            "question": "Does rain reduce modeled fine-particle air afterwards?",
            "status": air_status,
            "evidence": air_evidence,
            "kind": "observational · modeled air",
        },
        {
            "id": "rain-river",
            "question": "Does the river respond measurably after rain?",
            "status": river_status,
            "evidence": river_evidence,
            "kind": "lag test · water source may be modeled fallback",
        },
        {
            "id": "transit-rhythm",
            "question": "Does Berlin's transit pulse repeat by time of day?",
            "status": transit_status,
            "evidence": transit_evidence,
            "kind": "time-of-day pattern · VBB radar",
        },
    ]

def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    now = now_utc()
    history = load_json(HISTORY_PATH, {"version": 1, "snapshots": []})
    ledger = load_json(LEDGER_PATH, {"version": 1, "predictions": []})
    source_health: dict[str, str] = {}

    weather: dict[str, Any] = {}
    air: dict[str, Any] = {}
    flood: dict[str, Any] = {}
    transit: dict[str, Any] = {}

    for name, fn in (("weather", fetch_weather), ("air", fetch_air), ("flood", fetch_flood), ("transit", fetch_transit)):
        try:
            value = fn()
            source_health[name] = "ready"
            if name == "weather":
                weather = value
            elif name == "air":
                air = value
            elif name == "flood":
                flood = value
            elif name == "transit":
                transit = value
        except Exception as exc:
            source_health[name] = f"unavailable: {type(exc).__name__}"

    current_weather = weather.get("current") or {}
    current_air = air.get("current") or {}
    river_value: float | None = None
    river_history: list[float] = []
    river_source = "Unavailable"
    try:
        official_water = fetch_official_water(now)
        river_value = safe_float(official_water.get("value"))
        river_history = [v for v in official_water.get("history", []) if safe_float(v) is not None]
        river_source = official_water["source"]
        source_health["water"] = "measured"
    except Exception:
        try:
            river_value, river_history = flood_current(flood, now)
            river_source = "GloFAS via Open-Meteo · modeled fallback"
            source_health["water"] = "modeled fallback"
        except Exception as exc:
            source_health["water"] = f"unavailable: {type(exc).__name__}"

    metrics = {
        "temperature_2m": safe_float(current_weather.get("temperature_2m")),
        "apparent_temperature": safe_float(current_weather.get("apparent_temperature")),
        "precipitation": safe_float(current_weather.get("precipitation")),
        "wind_speed_10m": safe_float(current_weather.get("wind_speed_10m")),
        "pm2_5": safe_float(current_air.get("pm2_5")),
        "nitrogen_dioxide": safe_float(current_air.get("nitrogen_dioxide")),
        "ozone": safe_float(current_air.get("ozone")),
        "river_discharge": river_value,
        "transit_vehicles": safe_float(transit.get("count")),
    }

    resolve_predictions(ledger, metrics, now)

    weather_baseline = [v for t, v in series_pairs(weather, "temperature_2m") if t < now][-48:]
    air_baseline = [v for t, v in series_pairs(air, "pm2_5") if t < now][-48:]
    transit_baseline = collected_values(history, "transit_vehicles", 40)
    collected_water = collected_values(history, "river_discharge", 40)
    water_baseline = collected_water if len(collected_water) >= 6 else river_history

    target = now + timedelta(hours=12)
    weather_target_at, weather_candidate = point_at(weather, "temperature_2m", target)
    air_target_at, air_candidate = point_at(air, "pm2_5", target)
    issue_prediction(ledger, "temperature_2m", metrics["temperature_2m"], weather_candidate, weather_target_at, "°C", "Open-Meteo 12h forecast", now)
    issue_prediction(ledger, "pm2_5", metrics["pm2_5"], air_candidate, air_target_at, "µg/m³", "CAMS via Open-Meteo 12h forecast", now)

    snapshot = {
        "timestamp": iso(now),
        "metrics": metrics,
        "source_health": source_health,
    }
    history.setdefault("snapshots", []).append(snapshot)
    history["snapshots"] = history["snapshots"][-730:]

    signals = {
        "temperature_2m": {
            "label": "Temperature",
            "value": metrics["temperature_2m"],
            "unit": "°C",
            "source": "Open-Meteo weather model",
            "anomaly": {**robust_anomaly(metrics["temperature_2m"], weather_baseline), "baseline_scope": "previous 48 model-hours"},
            "forecast": {"hours": 12, "value": weather_candidate, "unit": "°C", "source": "Open-Meteo", "target_at": weather_target_at},
        },
        "pm2_5": {
            "label": "PM2.5",
            "value": metrics["pm2_5"],
            "unit": "µg/m³",
            "source": "CAMS via Open-Meteo · modeled",
            "anomaly": {**robust_anomaly(metrics["pm2_5"], air_baseline), "baseline_scope": "previous 48 model-hours"},
            "forecast": {"hours": 12, "value": air_candidate, "unit": "µg/m³", "source": "CAMS", "target_at": air_target_at},
        },
        "river_discharge": {
            "label": "Spree / river",
            "value": metrics["river_discharge"],
            "unit": "m³/s",
            "source": river_source,
            "anomaly": {**robust_anomaly(metrics["river_discharge"], water_baseline), "baseline_scope": "recent water series"},
        },
        "transit_vehicles": {
            "label": "Transit movement",
            "value": metrics["transit_vehicles"],
            "unit": "vehicles",
            "source": "VBB realtime radar",
            "anomaly": {**robust_anomaly(metrics["transit_vehicles"], transit_baseline), "baseline_scope": "recorded Pulse snapshots"},
        },
    }

    ledger["predictions"] = ledger.get("predictions", [])[-1500:]
    latest = {
        "version": 1,
        "generated_at": iso(now),
        "status": "recorded",
        "sample_count": len(history["snapshots"]),
        "history_basis": "Direct Pulse snapshots accumulate every three hours; weather and air anomaly baselines use the previous 48 model-hours until the tape is deep enough.",
        "headline": headline(signals),
        "changes": build_changes(history),
        "hypotheses": build_hypotheses(history),
        "signals": signals,
        "forecast_score": forecast_score(ledger),
        "source_health": source_health,
        "transit_modes": transit.get("modes") if isinstance(transit, dict) else None,
        "principle": "Missing evidence stays missing. Forecast skill is compared with persistence before trust is earned.",
    }

    write_json(HISTORY_PATH, history)
    write_json(LEDGER_PATH, ledger)
    write_json(LATEST_PATH, latest)
    print(json.dumps({"generated_at": latest["generated_at"], "sample_count": latest["sample_count"], "headline": latest["headline"], "forecast_score": latest["forecast_score"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
