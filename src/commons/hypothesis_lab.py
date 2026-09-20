from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import json
import math
from pathlib import Path
from statistics import mean, median
from time import sleep
from typing import Any
from urllib.error import HTTPError, URLError
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


def _request_json(
    url: str,
    params: dict[str, Any],
    timeout: int = 60,
    *,
    attempts: int = 3,
    backoff_seconds: float = 0.75,
) -> dict[str, Any]:
    request = Request(
        url + "?" + urlencode(params),
        headers={"User-Agent": "COMMONS-Hypothesis-Lab/0.2"},
    )
    attempts = max(1, attempts)
    for attempt in range(attempts):
        try:
            with urlopen(request, timeout=timeout) as response:  # noqa: S310
                payload = json.loads(response.read().decode("utf-8"))
            if payload.get("error"):
                raise RuntimeError(str(payload.get("reason") or payload))
            return payload
        except HTTPError as exc:
            transient = exc.code in {408, 425, 429, 500, 502, 503, 504}
            if not transient or attempt + 1 >= attempts:
                raise
        except (URLError, TimeoutError, OSError):
            if attempt + 1 >= attempts:
                raise
        sleep(backoff_seconds * (2**attempt))

    raise RuntimeError("unreachable request retry state")


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


def symmetric_percentage_error(predicted: float, actual: float) -> float:
    denominator = abs(predicted) + abs(actual)
    if denominator < 1e-9:
        return 0.0
    return 2.0 * abs(predicted - actual) / denominator


def rain_regime(actual_mm: float) -> str:
    if actual_mm < 1.0:
        return "dry"
    if actual_mm < 10.0:
        return "moderate"
    return "heavy"


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
                        "relative_spread": round(spread / max(council, actual_value, 1.0), 4),
                        "rain_regime": rain_regime(actual_value),
                        "council_abs_error_mm": round(abs(council - actual_value), 3),
                        "council_sape": round(
                            symmetric_percentage_error(council, actual_value), 4
                        ),
                    }
                )
    return records, source_errors


def evaluate_data_quality(
    records: list[dict[str, Any]],
    *,
    start_date: str,
    end_date: str,
    points: tuple[BacktestPoint, ...],
) -> dict[str, Any]:
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    calendar_days = max(0, (end - start).days + 1)
    expected_records = calendar_days * len(points) * len(LEADS)
    observed_records = len(records)
    temporal_coverage = (
        observed_records / expected_records if expected_records else 0.0
    )
    full_council_records = sum(
        1 for record in records if len(record.get("predictions_mm") or {}) == len(MODELS)
    )
    full_council_ratio = (
        full_council_records / observed_records if observed_records else 0.0
    )

    point_coverage: dict[str, float] = {}
    expected_per_point = calendar_days * len(LEADS)
    for point in points:
        observed = sum(1 for record in records if record["point_id"] == point.id)
        point_coverage[point.id] = (
            round(observed / expected_per_point, 4) if expected_per_point else 0.0
        )

    healthy = temporal_coverage >= 0.95 and full_council_ratio >= 0.90
    usable = temporal_coverage >= 0.66 and observed_records >= 60
    status = "healthy" if healthy else "degraded" if usable else "insufficient"

    return {
        "status": status,
        "expected_records": expected_records,
        "observed_records": observed_records,
        "temporal_coverage": round(temporal_coverage, 4),
        "full_council_ratio": round(full_council_ratio, 4),
        "point_coverage": point_coverage,
    }


def build_headline_metrics(summary: dict[str, Any]) -> dict[str, Any]:
    def values(key: str) -> list[float]:
        return [
            float(summary[str(lead)][key])
            for lead in LEADS
            if (summary.get(str(lead)) or {}).get(key) is not None
        ]

    improvements = values("council_improvement_vs_average_model_pct")
    heavy_improvements = values("council_heavy_rain_improvement_pct")
    ratios = values("high_vs_low_normalized_error_ratio")
    lead_mae = {
        str(lead): (summary.get(str(lead)) or {}).get("council_median_mae_mm")
        for lead in LEADS
    }
    return {
        "council_mean_error_improvement_pct": (
            round(mean(improvements), 1) if improvements else None
        ),
        "council_heavy_rain_error_improvement_pct": (
            round(mean(heavy_improvements), 1) if heavy_improvements else None
        ),
        "council_mae_by_lead_mm": lead_mae,
        "high_vs_low_normalized_error_ratio": (
            round(mean(ratios), 2) if ratios else None
        ),
    }


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    lead_summary: dict[str, Any] = {}

    for lead in LEADS:
        subset = [record for record in records if record["lead_days"] == lead]
        provider_errors: dict[str, list[float]] = {key: [] for key in MODELS}
        provider_heavy_errors: dict[str, list[float]] = {key: [] for key in MODELS}
        council_errors: list[float] = []
        council_sape: list[float] = []
        spreads: list[float] = []
        relative_spreads: list[float] = []
        heavy_errors: list[float] = []
        heavy_relative_spreads: list[float] = []
        heavy_sape: list[float] = []
        daily_council_vs_average_wins = 0

        for record in subset:
            actual = record["actual_precip_mm"]
            individual_errors: list[float] = []
            for provider, prediction in record["predictions_mm"].items():
                error = abs(prediction - actual)
                provider_errors.setdefault(provider, []).append(error)
                individual_errors.append(error)
                if record["rain_regime"] == "heavy":
                    provider_heavy_errors.setdefault(provider, []).append(error)

            error = record["council_abs_error_mm"]
            sape = record["council_sape"]
            council_errors.append(error)
            council_sape.append(sape)
            spreads.append(record["spread_mm"])
            relative_spreads.append(record["relative_spread"])

            if individual_errors and error <= mean(individual_errors):
                daily_council_vs_average_wins += 1

            if record["rain_regime"] == "heavy":
                heavy_errors.append(error)
                heavy_sape.append(sape)
                heavy_relative_spreads.append(record["relative_spread"])

        provider_mae = {
            provider: round(mean(errors), 3)
            for provider, errors in provider_errors.items()
            if errors
        }
        provider_heavy_mae = {
            provider: round(mean(errors), 3)
            for provider, errors in provider_heavy_errors.items()
            if errors
        }
        average_model_mae = mean(provider_mae.values()) if provider_mae else None
        average_model_heavy_mae = (
            mean(provider_heavy_mae.values()) if provider_heavy_mae else None
        )
        council_mae = mean(council_errors) if council_errors else None
        council_heavy_mae = mean(heavy_errors) if heavy_errors else None

        raw_corr = pearson(spreads, council_errors)
        normalized_corr = pearson(relative_spreads, council_sape)
        heavy_corr = pearson(heavy_relative_spreads, heavy_sape)

        q25 = quantile(relative_spreads, 0.25)
        q75 = quantile(relative_spreads, 0.75)
        low_sape = [
            error
            for spread, error in zip(relative_spreads, council_sape)
            if q25 is not None and spread <= q25
        ]
        high_sape = [
            error
            for spread, error in zip(relative_spreads, council_sape)
            if q75 is not None and spread >= q75
        ]
        retained_errors = [
            error
            for spread, error in zip(relative_spreads, council_errors)
            if q75 is not None and spread < q75
        ]

        lead_summary[str(lead)] = {
            "samples": len(subset),
            "heavy_rain_samples": len(heavy_errors),
            "provider_mae_mm": provider_mae,
            "provider_heavy_rain_mae_mm": provider_heavy_mae,
            "average_individual_model_mae_mm": (
                round(average_model_mae, 3)
                if average_model_mae is not None
                else None
            ),
            "average_individual_model_heavy_rain_mae_mm": (
                round(average_model_heavy_mae, 3)
                if average_model_heavy_mae is not None
                else None
            ),
            "council_median_mae_mm": (
                round(council_mae, 3) if council_mae is not None else None
            ),
            "council_median_heavy_rain_mae_mm": (
                round(council_heavy_mae, 3)
                if council_heavy_mae is not None
                else None
            ),
            "council_improvement_vs_average_model_pct": (
                round(100 * (average_model_mae - council_mae) / average_model_mae, 1)
                if council_mae is not None
                and average_model_mae is not None
                and average_model_mae > 0
                else None
            ),
            "council_heavy_rain_improvement_pct": (
                round(
                    100
                    * (average_model_heavy_mae - council_heavy_mae)
                    / average_model_heavy_mae,
                    1,
                )
                if council_heavy_mae is not None
                and average_model_heavy_mae is not None
                and average_model_heavy_mae > 0
                else None
            ),
            "council_win_rate_vs_daily_average_model_error_pct": (
                round(100 * daily_council_vs_average_wins / len(subset), 1)
                if subset
                else None
            ),
            "raw_spread_vs_absolute_error_correlation": (
                round(raw_corr, 3) if raw_corr is not None else None
            ),
            "relative_spread_vs_normalized_error_correlation": (
                round(normalized_corr, 3) if normalized_corr is not None else None
            ),
            "heavy_rain_relative_spread_vs_normalized_error_correlation": (
                round(heavy_corr, 3) if heavy_corr is not None else None
            ),
            "low_disagreement_normalized_error": (
                round(mean(low_sape), 3) if low_sape else None
            ),
            "high_disagreement_normalized_error": (
                round(mean(high_sape), 3) if high_sape else None
            ),
            "high_vs_low_normalized_error_ratio": (
                round(mean(high_sape) / mean(low_sape), 2)
                if high_sape and low_sape and mean(low_sape) > 0
                else None
            ),
            "relative_spread_q25": round(q25, 3) if q25 is not None else None,
            "relative_spread_q75": round(q75, 3) if q75 is not None else None,
            "mae_if_abstain_top_disagreement_quartile_mm": (
                round(mean(retained_errors), 3) if retained_errors else None
            ),
            "error_reduction_if_abstain_top_disagreement_quartile_pct": (
                round(100 * (council_mae - mean(retained_errors)) / council_mae, 1)
                if council_mae is not None
                and council_mae > 0
                and retained_errors
                else None
            ),
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

    normalized_correlations = [
        available(lead, "relative_spread_vs_normalized_error_correlation")
        for lead in LEADS
    ]
    heavy_correlations = [
        available(lead, "heavy_rain_relative_spread_vs_normalized_error_correlation")
        for lead in LEADS
    ]
    ratios = [
        available(lead, "high_vs_low_normalized_error_ratio")
        for lead in LEADS
    ]
    abstention_gains = [
        available(lead, "error_reduction_if_abstain_top_disagreement_quartile_pct")
        for lead in LEADS
    ]
    valid_corr = [value for value in normalized_correlations if value is not None]
    valid_heavy_corr = [value for value in heavy_correlations if value is not None]
    valid_ratios = [value for value in ratios if value is not None]
    valid_abstention = [value for value in abstention_gains if value is not None]
    corr_score = mean(valid_corr) if valid_corr else None
    heavy_corr_score = mean(valid_heavy_corr) if valid_heavy_corr else None
    ratio_score = mean(valid_ratios) if valid_ratios else None
    abstention_score = mean(valid_abstention) if valid_abstention else None
    h2_supported = (
        corr_score is not None
        and ratio_score is not None
        and corr_score >= 0.10
        and ratio_score >= 1.15
        and (heavy_corr_score is None or heavy_corr_score >= 0.05)
    )
    hypotheses.append(
        {
            "id": "H2",
            "claim": "Higher model disagreement predicts larger forecast error even after normalizing for rainfall magnitude.",
            "status": (
                "supported"
                if h2_supported
                else "not_supported"
                if corr_score is not None and ratio_score is not None
                else "insufficient"
            ),
            "effect": (
                f"normalized corr={corr_score:.2f}; high/low normalized-error ratio={ratio_score:.2f}x; "
                f"heavy-rain corr={heavy_corr_score:.2f}; abstention gain={abstention_score:.1f}%"
                if corr_score is not None
                and ratio_score is not None
                and heavy_corr_score is not None
                and abstention_score is not None
                else None
            ),
            "product_update": (
                "Use disagreement as an explicit confidence penalty and consider abstaining on the top disagreement quartile."
                if h2_supported
                else "Keep disagreement visible, but do not convert it into a confidence penalty yet."
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

    heavy_improvements = [
        available(lead, "council_heavy_rain_improvement_pct")
        for lead in LEADS
    ]
    valid_heavy_improvements = [
        value for value in heavy_improvements if value is not None
    ]
    heavy_improvement = (
        mean(valid_heavy_improvements) if valid_heavy_improvements else None
    )
    hypotheses.append(
        {
            "id": "H5",
            "claim": "The council median remains useful on heavy-rain days, not only on easy dry days.",
            "status": (
                "supported"
                if heavy_improvement is not None and heavy_improvement >= 2
                else "not_supported"
                if heavy_improvement is not None and heavy_improvement <= -2
                else "mixed"
                if heavy_improvement is not None
                else "insufficient"
            ),
            "effect": (
                f"{heavy_improvement:.1f}% heavy-rain error improvement"
                if heavy_improvement is not None
                else None
            ),
            "product_update": (
                "Keep the council as the main heavy-rain summary."
                if heavy_improvement is not None and heavy_improvement >= 2
                else "On heavy-rain days, foreground individual models rather than the council median."
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
    data_quality = evaluate_data_quality(
        records,
        start_date=start_date,
        end_date=end_date,
        points=points,
    )
    hypotheses = evaluate_hypotheses(summary)
    if data_quality["status"] != "healthy":
        for hypothesis in hypotheses:
            hypothesis["observed_status"] = hypothesis["status"]
            hypothesis["status"] = "insufficient"
            hypothesis["product_update"] = (
                "Hold the previous product rule; rerun when evidence health is healthy."
            )
    return {
        "schema_version": "0.2",
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
        "data_quality": data_quality,
        "summary_by_lead": summary,
        "headline_metrics": build_headline_metrics(summary),
        "hypotheses": hypotheses,
        "limitations": [
            "ERA5 is reanalysis, not a local rain gauge.",
            "Point precipitation is not basin-integrated precipitation.",
            "This evaluates precipitation forecast skill, not human flood impact.",
            "Operational model versions change over time.",
            "The council is a simple median, not a trained probabilistic ensemble.",
            "Product rules are not updated from runs whose evidence health is degraded or insufficient.",
        ],
    }


def save_report(report: dict[str, Any], path: str | Path) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
