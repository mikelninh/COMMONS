from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from statistics import mean, pstdev
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FLOOD_URL = "https://flood-api.open-meteo.com/v1/flood"


@dataclass(frozen=True)
class HydroPoint:
    id: str
    name: str
    country: str
    latitude: float
    longitude: float


POINTS: tuple[HydroPoint, ...] = (
    HydroPoint("nuwakot", "Nuwakot", "Nepal", 27.95, 85.18),
    HydroPoint("warsaw", "Warsaw", "Poland", 52.23, 21.01),
    HydroPoint("niamey", "Niamey", "Niger", 13.51, 2.11),
)


def _request_json(url: str, params: dict[str, Any], timeout: int = 90) -> dict[str, Any]:
    request = Request(
        url + "?" + urlencode(params),
        headers={"User-Agent": "COMMONS-Hydrology-Lab/0.1"},
    )
    with urlopen(request, timeout=timeout) as response:  # noqa: S310
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("error"):
        raise RuntimeError(str(payload.get("reason") or payload))
    return payload


def _series(payload: dict[str, Any], key: str) -> dict[str, float]:
    daily = payload.get("daily") or {}
    times = daily.get("time") or []
    values = daily.get(key) or []
    out: dict[str, float] = {}
    for raw_time, raw_value in zip(times, values):
        if raw_value is None:
            continue
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(value):
            out[str(raw_time)[:10]] = value
    return out


def fetch_weather(point: HydroPoint, start_date: str, end_date: str) -> dict[str, dict[str, float]]:
    payload = _request_json(
        ARCHIVE_URL,
        {
            "latitude": point.latitude,
            "longitude": point.longitude,
            "start_date": start_date,
            "end_date": end_date,
            "daily": "precipitation_sum,soil_moisture_0_to_100cm_mean",
            "models": "era5",
            "timezone": "UTC",
        },
    )
    return {
        "precip": _series(payload, "precipitation_sum"),
        "soil": _series(payload, "soil_moisture_0_to_100cm_mean"),
    }


def fetch_discharge(point: HydroPoint, start_date: str, end_date: str) -> dict[str, float]:
    payload = _request_json(
        FLOOD_URL,
        {
            "latitude": point.latitude,
            "longitude": point.longitude,
            "start_date": start_date,
            "end_date": end_date,
            "daily": "river_discharge",
            "models": "glofas_consolidated_v4",
        },
    )
    return _series(payload, "river_discharge")


def quantile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("empty values")
    pos = (len(ordered) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return ordered[lo]
    frac = pos - lo
    return ordered[lo] * (1 - frac) + ordered[hi] * frac


def zscores(values: list[float]) -> list[float]:
    if not values:
        return []
    center = mean(values)
    spread = pstdev(values)
    if spread < 1e-9:
        return [0.0 for _ in values]
    return [(value - center) / spread for value in values]


def auc(scores: list[float], labels: list[int]) -> float | None:
    positives = [(score, idx) for idx, (score, label) in enumerate(zip(scores, labels)) if label == 1]
    negatives = [(score, idx) for idx, (score, label) in enumerate(zip(scores, labels)) if label == 0]
    if not positives or not negatives:
        return None

    # Pairwise AUC. Dataset is only a few thousand daily rows.
    wins = 0.0
    total = 0
    neg_scores = [score for score, _ in negatives]
    for pos_score, _ in positives:
        for neg_score in neg_scores:
            total += 1
            if pos_score > neg_score:
                wins += 1.0
            elif pos_score == neg_score:
                wins += 0.5
    return wins / total if total else None


def precision_at_fraction(scores: list[float], labels: list[int], fraction: float = 0.05) -> float | None:
    if not scores or len(scores) != len(labels):
        return None
    count = max(1, round(len(scores) * fraction))
    ranked = sorted(zip(scores, labels), key=lambda item: item[0], reverse=True)[:count]
    return sum(label for _, label in ranked) / len(ranked)


def build_point_rows(
    point: HydroPoint,
    *,
    start_date: str,
    end_date: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    weather = fetch_weather(point, start_date, end_date)
    discharge = fetch_discharge(point, start_date, end_date)

    dates = sorted(set(weather["precip"]) & set(weather["soil"]) & set(discharge))
    if len(dates) < 30:
        return [], {"point": point.id, "status": "insufficient_data", "days": len(dates)}

    discharge_values = [discharge[day] for day in dates]
    high_threshold = quantile(discharge_values, 0.95)

    rows: list[dict[str, Any]] = []
    for idx in range(9, len(dates)):
        window = dates[idx - 9 : idx + 1]
        recent_days = window[-3:]
        antecedent_days = window[:-3]
        day = dates[idx]
        recent3 = sum(weather["precip"][d] for d in recent_days)
        antecedent7 = sum(weather["precip"][d] for d in antecedent_days)
        rows.append(
            {
                "point": point.id,
                "date": day,
                "recent_rain_3d_mm": recent3,
                "antecedent_rain_7d_mm": antecedent7,
                "soil_moisture": weather["soil"][day],
                "discharge": discharge[day],
                "extreme_discharge": 1 if discharge[day] >= high_threshold else 0,
            }
        )

    return rows, {
        "point": point.id,
        "name": point.name,
        "country": point.country,
        "status": "ok",
        "days": len(rows),
        "high_discharge_threshold_m3s": round(high_threshold, 3),
        "extreme_days": sum(row["extreme_discharge"] for row in rows),
    }


def evaluate_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"status": "insufficient_data"}

    recent = [row["recent_rain_3d_mm"] for row in rows]
    antecedent = [row["antecedent_rain_7d_mm"] for row in rows]
    soil = [row["soil_moisture"] for row in rows]
    labels = [row["extreme_discharge"] for row in rows]

    z_recent = zscores(recent)
    z_antecedent = zscores(antecedent)
    z_soil = zscores(soil)

    scores = {
        "recent_rain_only": z_recent,
        "rain_memory": [
            a + b for a, b in zip(z_recent, z_antecedent)
        ],
        "rain_plus_soil_memory": [
            a + b + c
            for a, b, c in zip(z_recent, z_antecedent, z_soil)
        ],
    }

    metrics: dict[str, Any] = {}
    for name, values in scores.items():
        auc_value = auc(values, labels)
        precision = precision_at_fraction(values, labels, 0.05)
        metrics[name] = {
            "auc": round(auc_value, 4) if auc_value is not None else None,
            "precision_at_top_5pct": round(precision, 4) if precision is not None else None,
        }

    baseline = metrics["recent_rain_only"]
    wetness = metrics["rain_plus_soil_memory"]
    auc_gain = (
        wetness["auc"] - baseline["auc"]
        if wetness["auc"] is not None and baseline["auc"] is not None
        else None
    )
    precision_gain = (
        (wetness["precision_at_top_5pct"] - baseline["precision_at_top_5pct"])
        / baseline["precision_at_top_5pct"]
        if wetness["precision_at_top_5pct"] is not None
        and baseline["precision_at_top_5pct"] not in (None, 0)
        else None
    )

    return {
        "status": "ok",
        "samples": len(rows),
        "extreme_days": sum(labels),
        "metrics": metrics,
        "auc_gain_vs_recent_rain": round(auc_gain, 4) if auc_gain is not None else None,
        "precision_gain_vs_recent_rain_pct": (
            round(precision_gain * 100, 1) if precision_gain is not None else None
        ),
    }


def run_hydrology_backtest(
    *,
    start_date: str = "2019-01-01",
    end_date: str = "2022-07-31",
    points: tuple[HydroPoint, ...] = POINTS,
) -> dict[str, Any]:
    point_results = []
    source_errors = []

    for point in points:
        try:
            rows, metadata = build_point_rows(
                point,
                start_date=start_date,
                end_date=end_date,
            )
            evaluation = evaluate_rows(rows)
            point_results.append({**metadata, **evaluation})
        except Exception as exc:
            source_errors.append({"point": point.id, "error": str(exc)})

    valid = [item for item in point_results if item.get("status") == "ok"]
    auc_gains = [
        item["auc_gain_vs_recent_rain"]
        for item in valid
        if item.get("auc_gain_vs_recent_rain") is not None
    ]
    precision_gains = [
        item["precision_gain_vs_recent_rain_pct"]
        for item in valid
        if item.get("precision_gain_vs_recent_rain_pct") is not None
    ]

    mean_auc_gain = mean(auc_gains) if auc_gains else None
    mean_precision_gain = mean(precision_gains) if precision_gains else None
    supported = (
        mean_auc_gain is not None
        and mean_precision_gain is not None
        and mean_auc_gain >= 0.03
        and mean_precision_gain >= 20
    )

    return {
        "schema_version": "0.1",
        "period": {"start": start_date, "end": end_date},
        "verification": "GloFAS v4 consolidated/reanalysis discharge",
        "weather": "ERA5 precipitation + 0-100 cm soil moisture",
        "points": point_results,
        "source_errors": source_errors,
        "hypothesis": {
            "id": "H6",
            "claim": "Antecedent rainfall and soil moisture improve detection of top-5% discharge days beyond recent 3-day rainfall alone.",
            "status": (
                "supported"
                if supported
                else "not_supported"
                if mean_auc_gain is not None and mean_precision_gain is not None
                else "insufficient"
            ),
            "mean_auc_gain": round(mean_auc_gain, 4) if mean_auc_gain is not None else None,
            "mean_precision_gain_pct": (
                round(mean_precision_gain, 1) if mean_precision_gain is not None else None
            ),
            "product_update": (
                "Add antecedent wetness to the river explanation and attention model."
                if supported
                else "Do not add catchment wetness to the attention model yet."
            ),
        },
        "limitations": [
            "GloFAS discharge is modelled, not a local gauge observation.",
            "The selected river is the largest river in the model cell and may not match the exact local river.",
            "Weather features are sampled at one point, not integrated over the upstream basin.",
            "The composite score is deliberately simple and not a trained hydrological model.",
        ],
    }


def save_report(report: dict[str, Any], path: str | Path) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
