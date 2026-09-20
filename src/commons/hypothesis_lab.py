from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import json
import math
from pathlib import Path
from statistics import mean, median
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PREVIOUS_RUNS_URL = "https://previous-runs-api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

MODELS = {
    "ecmwf": "ecmwf_ifs025",
    "gfs": "gfs_global",
    "icon": "icon_global",
}

LEADS = (1, 3, 5)


@dataclass(frozen=True)
class BacktestPoint:
    id: str
    name: str
    country: str
    latitude: float
    longitude: float


POINTS: tuple[BacktestPoint, ...] = (
    BacktestPoint("nuwakot", "Nuwakot", "Nepal", 27.95, 85.18),
    BacktestPoint("manila", "Manila", "Philippines", 14.60, 120.98),
    BacktestPoint("delhi", "Delhi", "India", 28.61, 77.21),
    BacktestPoint("warsaw", "Warsaw", "Poland", 52.23, 21.01),
    BacktestPoint("niamey", "Niamey", "Niger", 13.51, 2.11),
)


def _request_json(url: str, params: dict[str, Any], timeout: int = 60) -> dict[str, Any]:
    request = Request(
        url + "?" + urlencode(params),
        headers={"User-Agent": "COMMONS-Hypothesis-Lab/0.1"},
    )
    with urlopen(request, timeout=timeout) as response:  # noqa: S310
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("error"):
        raise RuntimeError(str(payload.get("reason") or payload))
    return payload


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _hourly_daily_sum(payload: dict[str, Any], key: str) -> dict[str, float]:
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    values = hourly.get(key) or []
    out: dict[str, float] = {}
    counts: dict[str, int] = {}
    for raw_time, raw_value in zip(times, values):
        value = _safe_float(raw_value)
        if value is None:
            continue
        day = str(raw_time)[:10]
        out[day] = out.get(day, 0.0) + value
        counts[day] = counts.get(day, 0) + 1
    # Require at least 18 hourly values so sparse/partial days do not masquerade as totals.
    return {day: total for day, total in out.items() if counts.get(day, 0) >= 18}


def _daily_series(payload: dict[str, Any], key: str) -> dict[str, float]:
    daily = payload.get("daily") or {}
    times = daily.get("time") or []
    values = daily.get(key) or []
    out: dict[str, float] = {}
    for raw_time, raw_value in zip(times, values):
        value = _safe_float(raw_value)
        if value is not None:
            out[str(raw_time)[:10]] = value
    return out


def fetch_model_predictions(
    point: BacktestPoint,
    *,
    model: str,
    start_date: str,
    end_date: str,
) -> dict[int, dict[str, float]]:
    hourly = ",".join(f"precipitation_previous_day{lead}" for lead in LEADS)
    payload = _request_json(
        PREVIOUS_RUNS_URL,
        {
            "latitude": point.latitude,
            "longitude": point.longitude,
            "start_date": start_date,
            "end_date": end_date,
            "hourly": hourly,
            "models": model,
            "timezone": "UTC",
        },
    )
    return {
        lead: _hourly_daily_sum(payload, f"precipitation_previous_day{lead}")
        for lead in LEADS
    }


def fetch_verifying_precipitation(
    point: BacktestPoint,
    *,
    start_date: str,
    end_date: str,
) -> dict[str, float]:
    payload = _request_json(
        ARCHIVE_URL,
        {
            "latitude": point.latitude,
            "longitude": point.longitude,
            "start_date": start_date,
            "end_date": end_date,
            "daily": "precipitation_sum",
            "models": "era5",
            "timezone": "UTC",
        },
    )
    return _daily_series(payload, "precipitation_sum")


def pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 3:
        return None
    mx, my = mean(xs), mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def quantile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return ordered[lo]
    frac = pos - lo
    return ordered[lo] * (1 - frac) + ordered[hi] * frac


def build_records(
    *,
    start_date: str,
    end_date: str,
    points: tuple[BacktestPoint, ...] = POINTS,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    records: list[dict[str, Any]] = []
    source_errors: list[dict[str, str]] = []

    for point in points:
        try:
            actual = fetch_verifying_precipitation(
                point,
                start_date=start_date,
                end_date=end_date,
            )
        except Exception as exc:
            source_errors.append(
                {"point": point.id, "source": "era5", "error": str(exc)}
            )
            continue

        predictions: dict[str, dict[int, dict[str, float]]] = {}
        for provider, model in MODELS.items():
            try:
                predictions[provider] = fetch_model_predictions(
                    point,
                    model=model,
                    start_date=start_date,
                    end_date=end_date,
                )
            except Exception as exc:
                source_errors.append(
                    {"point": point.id, "source": provider, "error": str(exc)}
                )

        for lead in LEADS:
            candidate_dates = set(actual)
            for provider in predictions.values():
                candidate_dates &= set(provider.get(lead, {}))

            for day in sorted(candidate_dates):
                provider_values = {
                    provider: prediction[lead][day]
                    for provider, prediction in predictions.items()
                    if day in prediction.get(lead, {})
                }
                if len(provider_values) < 2:
                    continue
                values = list(provider_values.values())
                actual_value = actual[day]
                council = median(values)
                spread = max(values) - min(values)
                records.append(
                    {
                        "point_id": point.id,
                        "point_name": point.name,
                        "country": point.country,
                        "date": day,
                        "lead_days": lead,
                        "actual_precip_mm": round(actual_value, 3),
                        "predictions_mm": {
                            key: round(value, 3)
                            for key, value in provider_values.items()
                        },
                        "council_median_mm": round(council, 3),
                        "spread_mm": round(spread, 3),
                        "council_abs_error_mm": round(abs(council - actual_value), 3),
                    }
                )
    return records, source_errors


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    lead_summary: dict[str, Any] = {}

    for lead in LEADS:
        subset = [record for record in records if record["lead_days"] == lead]
        provider_errors: dict[str, list[float]] = {key: [] for key in MODELS}
        council_errors: list[float] = []
        spreads: list[float] = []

        for record in subset:
            actual = record["actual_precip_mm"]
            for provider, prediction in record["predictions_mm"].items():
                provider_errors.setdefault(provider, []).append(abs(prediction - actual))
            council_errors.append(record["council_abs_error_mm"])
            spreads.append(record["spread_mm"])

        provider_mae = {
            provider: round(mean(errors), 3)
            for provider, errors in provider_errors.items()
            if errors
        }
        average_model_mae = mean(provider_mae.values()) if provider_mae else None
        council_mae = mean(council_errors) if council_errors else None
        corr = pearson(spreads, council_errors)

        q25 = quantile(spreads, 0.25)
        q75 = quantile(spreads, 0.75)
        low_errors = [
            error
            for spread, error in zip(spreads, council_errors)
            if q25 is not None and spread <= q25
        ]
        high_errors = [
            error
            for spread, error in zip(spreads, council_errors)
            if q75 is not None and spread >= q75
        ]

        lead_summary[str(lead)] = {
            "samples": len(subset),
            "provider_mae_mm": provider_mae,
            "average_individual_model_mae_mm": (
                round(average_model_mae, 3)
                if average_model_mae is not None
                else None
            ),
            "council_median_mae_mm": (
                round(council_mae, 3) if council_mae is not None else None
            ),
            "council_improvement_vs_average_model_pct": (
                round(100 * (average_model_mae - council_mae) / average_model_mae, 1)
                if council_mae is not None
                and average_model_mae is not None
                and average_model_mae > 0
                else None
            ),
            "spread_error_correlation": round(corr, 3) if corr is not None else None,
            "low_disagreement_error_mm": (
                round(mean(low_errors), 3) if low_errors else None
            ),
            "high_disagreement_error_mm": (
                round(mean(high_errors), 3) if high_errors else None
            ),
            "high_vs_low_error_ratio": (
                round(mean(high_errors) / mean(low_errors), 2)
                if high_errors and low_errors and mean(low_errors) > 0
                else None
            ),
            "spread_q25_mm": round(q25, 3) if q25 is not None else None,
            "spread_q75_mm": round(q75, 3) if q75 is not None else None,
        }

    return lead_summary


def evaluate_hypotheses(summary: dict[str, Any]) -> list[dict[str, Any]]:
    def available(lead: int, key: str) -> Any:
        return (summary.get(str(lead)) or {}).get(key)

    hypotheses: list[dict[str, Any]] = []

    improvements = [
        available(lead, "council_improvement_vs_average_model_pct")
        for lead in LEADS
    ]
    valid_improvements = [value for value in improvements if value is not None]
    h1_score = mean(valid_improvements) if valid_improvements else None
    hypotheses.append(
        {
            "id": "H1",
            "claim": "The council median reduces precipitation error versus the average individual model.",
            "status": (
                "supported"
                if h1_score is not None and h1_score >= 2
                else "not_supported"
                if h1_score is not None and h1_score <= -2
                else "mixed"
                if h1_score is not None
                else "insufficient"
            ),
            "effect": (
                f"{h1_score:.1f}% mean error improvement"
                if h1_score is not None
                else None
            ),
            "product_update": (
                "Keep council median as the default headline."
                if h1_score is not None and h1_score >= 2
                else "Do not privilege the council median; show model-specific forecasts more prominently."
            ),
        }
    )

    correlations = [
        available(lead, "spread_error_correlation")
        for lead in LEADS
    ]
    ratios = [
        available(lead, "high_vs_low_error_ratio")
        for lead in LEADS
    ]
    valid_corr = [value for value in correlations if value is not None]
    valid_ratios = [value for value in ratios if value is not None]
    corr_score = mean(valid_corr) if valid_corr else None
    ratio_score = mean(valid_ratios) if valid_ratios else None
    h2_supported = (
        corr_score is not None
        and ratio_score is not None
        and corr_score >= 0.20
        and ratio_score >= 1.20
    )
    hypotheses.append(
        {
            "id": "H2",
            "claim": "Higher model disagreement predicts larger council forecast error.",
            "status": (
                "supported"
                if h2_supported
                else "not_supported"
                if corr_score is not None and ratio_score is not None
                else "insufficient"
            ),
            "effect": (
                f"corr={corr_score:.2f}; high/low error ratio={ratio_score:.2f}x"
                if corr_score is not None and ratio_score is not None
                else None
            ),
            "product_update": (
                "Use disagreement as an explicit confidence penalty."
                if h2_supported
                else "Do not treat disagreement as a confidence penalty yet; keep it visible as context only."
            ),
        }
    )

    lead_errors = {
        lead: available(lead, "council_median_mae_mm")
        for lead in LEADS
    }
    if all(value is not None for value in lead_errors.values()):
        day1 = lead_errors[1]
        day3 = lead_errors[3]
        day5 = lead_errors[5]
        monotonic = day1 <= day3 <= day5
        material = day5 >= day1 * 1.10 if day1 > 0 else False
        h3_supported = monotonic or material
        effect = f"{day1:.2f} → {day3:.2f} → {day5:.2f} mm MAE"
    else:
        h3_supported = False
        effect = None
    hypotheses.append(
        {
            "id": "H3",
            "claim": "Forecast skill materially degrades from 1 to 3 to 5 days.",
            "status": "supported" if h3_supported else "not_supported" if effect else "insufficient",
            "effect": effect,
            "product_update": (
                "Make forecast horizon a first-class confidence input."
                if h3_supported
                else "Do not apply a generic horizon penalty without more evidence."
            ),
        }
    )

    h2 = next(item for item in hypotheses if item["id"] == "H2")
    h3 = next(item for item in hypotheses if item["id"] == "H3")
    confidence_rule = (
        "confidence = source health + horizon skill + disagreement penalty"
        if h2["status"] == "supported" and h3["status"] == "supported"
        else "confidence should not yet combine both disagreement and horizon as penalties"
    )
    hypotheses.append(
        {
            "id": "H4",
            "claim": "COMMONS should lower confidence when model disagreement is high and lead time is long.",
            "status": (
                "supported"
                if h2["status"] == "supported" and h3["status"] == "supported"
                else "mixed"
            ),
            "effect": confidence_rule,
            "product_update": confidence_rule,
        }
    )

    return hypotheses


def run_backtest(
    *,
    start_date: str,
    end_date: str,
    points: tuple[BacktestPoint, ...] = POINTS,
) -> dict[str, Any]:
    records, source_errors = build_records(
        start_date=start_date,
        end_date=end_date,
        points=points,
    )
    summary = summarize(records)
    hypotheses = evaluate_hypotheses(summary)
    return {
        "schema_version": "0.1",
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "period": {"start": start_date, "end": end_date},
        "points": [
            {
                "id": point.id,
                "name": point.name,
                "country": point.country,
                "latitude": point.latitude,
                "longitude": point.longitude,
            }
            for point in points
        ],
        "models": MODELS,
        "leads_days": list(LEADS),
        "verification": "ERA5 daily precipitation",
        "records": len(records),
        "source_errors": source_errors,
        "summary_by_lead": summary,
        "hypotheses": hypotheses,
        "limitations": [
            "ERA5 is reanalysis, not a local rain gauge.",
            "Point precipitation is not basin-integrated precipitation.",
            "This evaluates precipitation forecast skill, not human flood impact.",
            "Operational model versions change over time.",
            "The council is a simple median, not a trained probabilistic ensemble.",
        ],
    }


def save_report(report: dict[str, Any], path: str | Path) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
