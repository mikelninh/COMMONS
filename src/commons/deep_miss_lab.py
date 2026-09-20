from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
import json
import math
from statistics import mean, median
from time import sleep
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from commons.hypothesis_lab import (
    ARCHIVE_URL,
    MODELS,
    PREVIOUS_RUNS_URL,
    BacktestPoint,
    _daily_series,
    _hourly_daily_sum,
    _request_json,
    quantile,
)
from commons.scale_points import GLOBAL_POINTS


RADII_KM = (25, 50, 100)
CARDINALS = (
    ("n", 1.0, 0.0),
    ("s", -1.0, 0.0),
    ("e", 0.0, 1.0),
    ("w", 0.0, -1.0),
)
LEADS = (1, 2, 3)
MAX_WORKERS = 8
FALSE_ALERT_BUDGET_PER_100 = 3.0
MAX_PRECISION_DROP = 0.05
MIN_DEEP_MISS_RECOVERY = 0.20


def _offset_point(
    point: BacktestPoint,
    *,
    radius_km: int,
    lat_direction: float,
    lon_direction: float,
    label: str,
) -> dict[str, Any]:
    dlat = (radius_km / 111.0) * lat_direction
    cos_lat = max(0.15, abs(math.cos(math.radians(point.latitude))))
    dlon = (radius_km / (111.0 * cos_lat)) * lon_direction
    return {
        "label": label,
        "radius_km": radius_km,
        "latitude": point.latitude + dlat,
        "longitude": point.longitude + dlon,
    }


def spatial_cells(point: BacktestPoint) -> list[dict[str, Any]]:
    cells = [
        {
            "label": "center",
            "radius_km": 0,
            "latitude": point.latitude,
            "longitude": point.longitude,
        }
    ]
    for radius in RADII_KM:
        for direction, lat_dir, lon_dir in CARDINALS:
            cells.append(
                _offset_point(
                    point,
                    radius_km=radius,
                    lat_direction=lat_dir,
                    lon_direction=lon_dir,
                    label=f"{direction}{radius}",
                )
            )
    return cells


def _request_json_multi(
    url: str,
    params: dict[str, Any],
    *,
    timeout: int = 90,
    attempts: int = 3,
) -> Any:
    request = Request(
        url + "?" + urlencode(params),
        headers={"User-Agent": "COMMONS-H23-Spatial/0.2"},
    )
    for attempt in range(max(1, attempts)):
        try:
            with urlopen(request, timeout=timeout) as response:  # noqa: S310
                payload = json.loads(response.read().decode("utf-8"))
            if isinstance(payload, dict) and payload.get("error"):
                raise RuntimeError(str(payload.get("reason") or payload))
            return payload
        except HTTPError as exc:
            transient = exc.code in {408, 425, 429, 500, 502, 503, 504}
            if not transient or attempt + 1 >= attempts:
                raise
        except (URLError, TimeoutError, OSError):
            if attempt + 1 >= attempts:
                raise
        sleep(0.75 * (2**attempt))
    raise RuntimeError("unreachable multi-coordinate retry state")


def _forecast_bundle_batch(
    *,
    cells: list[dict[str, Any]],
    model: str,
    start_date: str,
    end_date: str,
) -> dict[str, dict[int, dict[str, float]]]:
    hourly = ",".join(f"precipitation_previous_day{lead}" for lead in LEADS)
    payload = _request_json_multi(
        PREVIOUS_RUNS_URL,
        {
            "latitude": ",".join(str(cell["latitude"]) for cell in cells),
            "longitude": ",".join(str(cell["longitude"]) for cell in cells),
            "start_date": start_date,
            "end_date": end_date,
            "hourly": hourly,
            "models": model,
            "timezone": "UTC",
        },
    )
    items = payload if isinstance(payload, list) else [payload]
    if len(items) != len(cells):
        raise RuntimeError(
            f"multi-coordinate response length {len(items)} != {len(cells)}"
        )
    out: dict[str, dict[int, dict[str, float]]] = {}
    for cell, item in zip(cells, items):
        out[cell["label"]] = {
            lead: _hourly_daily_sum(
                item, f"precipitation_previous_day{lead}"
            )
            for lead in LEADS
        }
    return out


def _actual_series(
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


def _affected_points(
    miss_report: dict[str, Any],
    points: tuple[BacktestPoint, ...],
) -> tuple[BacktestPoint, ...]:
    ids = {
        str(case.get("point_id"))
        for case in miss_report.get("cases") or []
        if case.get("miss_type") == "deep" and case.get("point_id")
    }
    return tuple(point for point in points if point.id in ids)


def _thresholds(miss_report: dict[str, Any]) -> dict[str, float]:
    out: dict[str, float] = {}
    for case in miss_report.get("cases") or []:
        point_id = case.get("point_id")
        gate = case.get("heavy_gate_mm")
        if not point_id or gate is None:
            continue
        try:
            out[str(point_id)] = float(gate)
        except (TypeError, ValueError):
            continue
    return out


def fetch_h23_evidence(
    miss_report: dict[str, Any],
    *,
    points: tuple[BacktestPoint, ...] = GLOBAL_POINTS,
) -> dict[str, Any]:
    period = miss_report.get("period") or {}
    holdout_start = date.fromisoformat(str(period["holdout_start"]))
    end = date.fromisoformat(str(period["end"]))
    query_start = holdout_start - timedelta(days=2)

    affected = _affected_points(miss_report, points)
    forecasts: dict[str, dict[str, dict[str, dict[int, dict[str, float]]]]] = {}
    actual: dict[str, dict[str, float]] = {}
    errors: list[dict[str, str]] = []

    tasks: list[tuple[str, str, str, list[dict[str, Any]]]] = []
    for point in affected:
        cells = spatial_cells(point)
        forecasts[point.id] = {
            cell["label"]: {} for cell in cells
        }
        for provider, model in MODELS.items():
            tasks.append((point.id, provider, model, cells))

    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, max(1, len(tasks)))) as executor:
        future_map = {
            executor.submit(
                _forecast_bundle_batch,
                cells=cells,
                model=model,
                start_date=query_start.isoformat(),
                end_date=end.isoformat(),
            ): (point_id, provider)
            for point_id, provider, model, cells in tasks
        }
        for future in as_completed(future_map):
            point_id, provider = future_map[future]
            try:
                by_cell = future.result()
                for cell_label, bundle in by_cell.items():
                    forecasts[point_id][cell_label][provider] = bundle
            except Exception as exc:
                errors.append({
                    "point_id": point_id,
                    "cell": "batched_spatial_cells",
                    "provider": provider,
                    "error": str(exc),
                })

    with ThreadPoolExecutor(max_workers=min(6, max(1, len(affected)))) as executor:
        future_map = {
            executor.submit(
                _actual_series,
                point,
                start_date=query_start.isoformat(),
                end_date=end.isoformat(),
            ): point
            for point in affected
        }
        for future in as_completed(future_map):
            point = future_map[future]
            try:
                actual[point.id] = future.result()
            except Exception as exc:
                errors.append({
                    "point_id": point.id,
                    "cell": "actual",
                    "provider": "era5",
                    "error": str(exc),
                })

    expected_forecast_bundles = len(affected) * 13 * len(MODELS)
    observed_forecast_bundles = sum(
        len(providers)
        for point_cells in forecasts.values()
        for providers in point_cells.values()
    )
    forecast_bundle_ratio = (
        observed_forecast_bundles / expected_forecast_bundles
        if expected_forecast_bundles
        else 0.0
    )
    actual_ratio = len(actual) / len(affected) if affected else 0.0

    return {
        "affected_points": affected,
        "forecasts": forecasts,
        "actual": actual,
        "errors": errors,
        "query_start": query_start,
        "holdout_start": holdout_start,
        "end": end,
        "health": {
            "status": (
                "healthy"
                if forecast_bundle_ratio >= 0.95 and actual_ratio >= 0.95
                else "insufficient"
            ),
            "affected_points": len(affected),
            "request_mode": "batched_multi_coordinate",
            "forecast_requests_expected": len(affected) * len(MODELS),
            "expected_forecast_bundles": expected_forecast_bundles,
            "observed_forecast_bundles": observed_forecast_bundles,
            "forecast_bundle_ratio": round(forecast_bundle_ratio, 4),
            "actual_point_ratio": round(actual_ratio, 4),
        },
    }


def _provider_value(
    evidence: dict[str, Any],
    *,
    point_id: str,
    cell: str,
    provider: str,
    lead: int,
    target_date: date,
) -> float | None:
    try:
        return float(
            evidence["forecasts"][point_id][cell][provider][lead][
                target_date.isoformat()
            ]
        )
    except (KeyError, TypeError, ValueError):
        return None


def _cell_council(
    evidence: dict[str, Any],
    *,
    point_id: str,
    cell: str,
    lead: int,
    target_date: date,
) -> float | None:
    values = [
        _provider_value(
            evidence,
            point_id=point_id,
            cell=cell,
            provider=provider,
            lead=lead,
            target_date=target_date,
        )
        for provider in MODELS
    ]
    cleaned = [value for value in values if value is not None]
    if len(cleaned) != len(MODELS):
        return None
    return float(median(cleaned))


def _center_any_model(
    evidence: dict[str, Any],
    *,
    point_id: str,
    lead: int,
    target_date: date,
) -> float | None:
    values = [
        _provider_value(
            evidence,
            point_id=point_id,
            cell="center",
            provider=provider,
            lead=lead,
            target_date=target_date,
        )
        for provider in MODELS
    ]
    cleaned = [value for value in values if value is not None]
    if len(cleaned) != len(MODELS):
        return None
    return max(cleaned)


def _cells_within(radius_km: int) -> list[str]:
    labels = ["center"]
    for radius in RADII_KM:
        if radius > radius_km:
            continue
        labels.extend(f"{direction}{radius}" for direction, _, _ in CARDINALS)
    return labels


def _spatial_value(
    evidence: dict[str, Any],
    *,
    point_id: str,
    lead: int,
    target_date: date,
    radius_km: int,
    aggregate: str,
) -> float | None:
    values = [
        _cell_council(
            evidence,
            point_id=point_id,
            cell=cell,
            lead=lead,
            target_date=target_date,
        )
        for cell in _cells_within(radius_km)
    ]
    cleaned = [value for value in values if value is not None]
    expected = len(_cells_within(radius_km))
    if len(cleaned) < max(3, math.ceil(expected * 0.75)):
        return None
    if aggregate == "mean":
        return float(mean(cleaned))
    if aggregate == "p90":
        value = quantile(cleaned, 0.90)
        return float(value) if value is not None else None
    if aggregate == "max":
        return max(cleaned)
    raise ValueError(f"unknown aggregate {aggregate}")


def _window_scores(
    evidence: dict[str, Any],
    *,
    point_id: str,
    decision_date: date,
    threshold: float,
) -> dict[str, float | None]:
    raw: dict[str, list[float]] = {
        "baseline_center": [],
        "any_model_center": [],
    }
    for radius in RADII_KM:
        for aggregate in ("mean", "p90", "max"):
            raw[f"spatial_{aggregate}_{radius}km"] = []

    for offset, lead in ((1, 1), (2, 2), (3, 3)):
        target = decision_date + timedelta(days=offset)
        center = _cell_council(
            evidence,
            point_id=point_id,
            cell="center",
            lead=lead,
            target_date=target,
        )
        any_model = _center_any_model(
            evidence,
            point_id=point_id,
            lead=lead,
            target_date=target,
        )
        if center is not None:
            raw["baseline_center"].append(center / threshold)
        if any_model is not None:
            raw["any_model_center"].append(any_model / threshold)

        for radius in RADII_KM:
            for aggregate in ("mean", "p90", "max"):
                value = _spatial_value(
                    evidence,
                    point_id=point_id,
                    lead=lead,
                    target_date=target,
                    radius_km=radius,
                    aggregate=aggregate,
                )
                if value is not None:
                    raw[f"spatial_{aggregate}_{radius}km"].append(value / threshold)

    return {
        key: max(values) if len(values) == 3 else None
        for key, values in raw.items()
    }


def _window_outcome(
    evidence: dict[str, Any],
    *,
    point_id: str,
    decision_date: date,
    threshold: float,
) -> tuple[bool | None, float | None, str | None]:
    series = evidence["actual"].get(point_id) or {}
    values: list[tuple[str, float]] = []
    for offset in (1, 2, 3):
        target = decision_date + timedelta(days=offset)
        raw = series.get(target.isoformat())
        if raw is None:
            return None, None, None
        values.append((target.isoformat(), float(raw)))
    peak_date, peak = max(values, key=lambda item: item[1])
    return peak >= threshold, peak, peak_date


def build_cases(
    evidence: dict[str, Any],
    miss_report: dict[str, Any],
) -> list[dict[str, Any]]:
    thresholds = _thresholds(miss_report)
    cases: list[dict[str, Any]] = []
    final_decision_date = evidence["end"] - timedelta(days=3)

    day = evidence["holdout_start"]
    while day <= final_decision_date:
        for point in evidence["affected_points"]:
            threshold = thresholds.get(point.id)
            if not threshold:
                continue
            scores = _window_scores(
                evidence,
                point_id=point.id,
                decision_date=day,
                threshold=threshold,
            )
            if scores["baseline_center"] is None:
                continue
            heavy, actual_peak, actual_peak_date = _window_outcome(
                evidence,
                point_id=point.id,
                decision_date=day,
                threshold=threshold,
            )
            if heavy is None:
                continue
            cases.append({
                "point_id": point.id,
                "name": point.name,
                "country": point.country,
                "decision_date": day.isoformat(),
                "heavy_gate_mm": round(threshold, 2),
                "observed_heavy_next_72h": heavy,
                "observed_peak_mm": round(float(actual_peak), 2),
                "observed_peak_date": actual_peak_date,
                "scores": {
                    key: round(value, 4) if value is not None else None
                    for key, value in scores.items()
                },
            })
        day += timedelta(days=1)
    return cases


def _metrics(
    cases: list[dict[str, Any]],
    strategy: str,
    *,
    baseline_strategy: str = "baseline_center",
) -> dict[str, Any]:
    usable = [
        case
        for case in cases
        if case["scores"].get(strategy) is not None
        and case["scores"].get(baseline_strategy) is not None
    ]
    heavy = [case for case in usable if case["observed_heavy_next_72h"]]
    alerts = [case for case in usable if float(case["scores"][strategy]) >= 1.0]
    true_positives = [
        case
        for case in alerts
        if case["observed_heavy_next_72h"]
    ]
    false_alerts = len(alerts) - len(true_positives)
    precision = len(true_positives) / len(alerts) if alerts else None
    recall = len(true_positives) / len(heavy) if heavy else None

    deep = [
        case
        for case in heavy
        if float(case["scores"][baseline_strategy]) < 0.80
    ]
    recovered = [
        case for case in deep if float(case["scores"][strategy]) >= 1.0
    ]

    return {
        "cases": len(usable),
        "heavy_events": len(heavy),
        "alerts": len(alerts),
        "true_positives": len(true_positives),
        "false_alerts": false_alerts,
        "precision": round(precision, 4) if precision is not None else None,
        "recall": round(recall, 4) if recall is not None else None,
        "false_alerts_per_100": (
            round(100 * false_alerts / len(usable), 2) if usable else None
        ),
        "baseline_deep_misses": len(deep),
        "deep_misses_recovered": len(recovered),
        "deep_miss_recovery_rate": (
            round(len(recovered) / len(deep), 4) if deep else None
        ),
    }


def _comparison(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    base_burden = baseline.get("false_alerts_per_100")
    candidate_burden = candidate.get("false_alerts_per_100")
    base_precision = baseline.get("precision")
    candidate_precision = candidate.get("precision")
    return {
        "incremental_false_alerts_per_100": (
            round(float(candidate_burden) - float(base_burden), 2)
            if candidate_burden is not None and base_burden is not None
            else None
        ),
        "precision_change": (
            round(float(candidate_precision) - float(base_precision), 4)
            if candidate_precision is not None and base_precision is not None
            else None
        ),
        "recall_change": (
            round(float(candidate["recall"]) - float(baseline["recall"]), 4)
            if candidate.get("recall") is not None and baseline.get("recall") is not None
            else None
        ),
    }


def _passes_guardrails(metrics: dict[str, Any], comparison: dict[str, Any]) -> bool:
    recovery = metrics.get("deep_miss_recovery_rate")
    burden = comparison.get("incremental_false_alerts_per_100")
    precision_change = comparison.get("precision_change")
    return bool(
        recovery is not None
        and recovery >= MIN_DEEP_MISS_RECOVERY
        and burden is not None
        and burden <= FALSE_ALERT_BUDGET_PER_100
        and precision_change is not None
        and precision_change >= -MAX_PRECISION_DROP
    )


def _select_strategy(
    development: list[dict[str, Any]],
) -> tuple[str, dict[str, Any]]:
    baseline = _metrics(development, "baseline_center")
    candidates = [
        "any_model_center",
        *[
            f"spatial_{aggregate}_{radius}km"
            for radius in RADII_KM
            for aggregate in ("mean", "p90", "max")
        ],
    ]
    scored: list[tuple[bool, float, float, float, str, dict[str, Any]]] = []
    for strategy in candidates:
        metrics = _metrics(development, strategy)
        comparison = _comparison(baseline, metrics)
        passes = _passes_guardrails(metrics, comparison)
        recovery = float(metrics.get("deep_miss_recovery_rate") or 0.0)
        burden = float(comparison.get("incremental_false_alerts_per_100") or 999.0)
        precision = float(metrics.get("precision") or 0.0)
        scored.append(
            (
                passes,
                recovery,
                -burden,
                precision,
                strategy,
                {"metrics": metrics, "comparison": comparison, "passes": passes},
            )
        )
    scored.sort(reverse=True)
    best = scored[0]
    return best[4], best[5]


def _failure_taxonomy(
    cases: list[dict[str, Any]],
    selected_strategy: str,
) -> dict[str, Any]:
    deep = [
        case
        for case in cases
        if case["observed_heavy_next_72h"]
        and case["scores"]["baseline_center"] is not None
        and float(case["scores"]["baseline_center"]) < 0.80
    ]
    counts = {
        "model_and_spatial": 0,
        "one_model_saw_it": 0,
        "spatial_displacement": 0,
        "consensus_blind": 0,
    }
    low_gate = 0
    extreme = 0
    examples: list[dict[str, Any]] = []

    spatial_keys = [
        key for key in (deep[0]["scores"].keys() if deep else [])
        if key.startswith("spatial_")
    ]

    for case in deep:
        any_model = float(case["scores"].get("any_model_center") or 0.0) >= 1.0
        spatial = any(
            float(case["scores"].get(key) or 0.0) >= 1.0
            for key in spatial_keys
        )
        if any_model and spatial:
            label = "model_and_spatial"
        elif any_model:
            label = "one_model_saw_it"
        elif spatial:
            label = "spatial_displacement"
        else:
            label = "consensus_blind"
        counts[label] += 1

        if float(case["heavy_gate_mm"]) < 5.0:
            low_gate += 1
        if float(case["observed_peak_mm"]) >= 2 * float(case["heavy_gate_mm"]):
            extreme += 1

        if len(examples) < 20:
            examples.append({
                "point_id": case["point_id"],
                "decision_date": case["decision_date"],
                "observed_peak_mm": case["observed_peak_mm"],
                "heavy_gate_mm": case["heavy_gate_mm"],
                "baseline_score": case["scores"]["baseline_center"],
                "any_model_score": case["scores"].get("any_model_center"),
                "selected_strategy": selected_strategy,
                "selected_score": case["scores"].get(selected_strategy),
                "failure_mode": label,
            })

    return {
        "deep_misses": len(deep),
        "counts": counts,
        "low_absolute_gate_misses": low_gate,
        "extreme_observed_misses": extreme,
        "examples": examples,
    }


def _exact_day_semantics_correction(
    miss_report: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    thresholds = _thresholds(miss_report)
    deep_cases = [
        case
        for case in miss_report.get("cases") or []
        if case.get("miss_type") == "deep"
        and case.get("point_id") in {point.id for point in evidence["affected_points"]}
    ]
    evaluable = 0
    no_longer_deep = 0
    live_alert = 0
    for case in deep_cases:
        event_date = date.fromisoformat(str(case["date"]))
        decision_date = event_date - timedelta(days=3)
        threshold = thresholds.get(str(case["point_id"]))
        if not threshold:
            continue
        scores = _window_scores(
            evidence,
            point_id=str(case["point_id"]),
            decision_date=decision_date,
            threshold=threshold,
        )
        baseline = scores.get("baseline_center")
        if baseline is None:
            continue
        evaluable += 1
        if baseline >= 0.80:
            no_longer_deep += 1
        if baseline >= 1.0:
            live_alert += 1

    return {
        "h21_exact_day_deep_cases": len(deep_cases),
        "evaluable": evaluable,
        "no_longer_deep_under_live_72h_window": no_longer_deep,
        "would_alert_under_live_72h_window": live_alert,
        "note": (
            "H21 classified one target day at a 3-day lead. Morning Brief instead "
            "looks across the next three target days at lead 1/2/3."
        ),
    }


def run_deep_miss_killer(
    miss_report: dict[str, Any],
    *,
    points: tuple[BacktestPoint, ...] = GLOBAL_POINTS,
) -> dict[str, Any]:
    evidence = fetch_h23_evidence(miss_report, points=points)
    cases = build_cases(evidence, miss_report)

    if cases:
        dates = sorted({case["decision_date"] for case in cases})
        split_date = dates[max(1, len(dates) // 2) - 1]
        development = [case for case in cases if case["decision_date"] <= split_date]
        test = [case for case in cases if case["decision_date"] > split_date]
    else:
        split_date = None
        development = []
        test = []

    selected_strategy, development_selection = _select_strategy(development) if development else (
        "baseline_center",
        {"metrics": {}, "comparison": {}, "passes": False},
    )

    development_baseline = _metrics(development, "baseline_center")
    test_baseline = _metrics(test, "baseline_center")
    test_selected = _metrics(test, selected_strategy)
    test_comparison = _comparison(test_baseline, test_selected)

    evidence_healthy = (evidence.get("health") or {}).get("status") == "healthy"
    enough_test_misses = (test_baseline.get("baseline_deep_misses") or 0) >= 5
    supported = (
        evidence_healthy
        and enough_test_misses
        and _passes_guardrails(test_selected, test_comparison)
    )
    status = (
        "supported"
        if supported
        else "not_supported"
        if evidence_healthy and enough_test_misses
        else "insufficient"
    )

    if supported:
        update = (
            f"Promote {selected_strategy} to a shadow ranking experiment only; "
            "it recovered deep misses inside the predefined false-alert and precision budget. "
            "Do not change ALERT until it survives another independent window."
        )
    elif status == "not_supported":
        update = (
            "Do not add the tested spatial or single-model rescue rule to live ALERT. "
            "Deep misses remain a model/physics problem; continue with basin context, "
            "convective/local signals and impact-labelled evaluation."
        )
    else:
        update = (
            "Keep H23 observational until the spatial evidence and final test contain "
            "enough complete deep-miss cases."
        )

    return {
        "schema_version": "0.1",
        "source_period": miss_report.get("period"),
        "evidence_health": evidence.get("health"),
        "source_errors": evidence.get("errors"),
        "spatial_design": {
            "radii_km": list(RADII_KM),
            "directions": [item[0] for item in CARDINALS],
            "cells_per_point": 13,
            "aggregates": ["mean", "p90", "max"],
            "one_model_rescue": True,
        },
        "live_semantics_correction": _exact_day_semantics_correction(
            miss_report, evidence
        ),
        "case_count": len(cases),
        "development": {
            "end_date": split_date,
            "baseline": development_baseline,
            "selected_strategy": selected_strategy,
            "selection": development_selection,
        },
        "test": {
            "baseline": test_baseline,
            "selected_strategy": selected_strategy,
            "selected": test_selected,
            "comparison": test_comparison,
            "passes_guardrails": _passes_guardrails(
                test_selected, test_comparison
            ) if test else False,
        },
        "failure_taxonomy": _failure_taxonomy(test, selected_strategy),
        "hypothesis": {
            "id": "H23",
            "claim": (
                "A predeclared spatial or single-model rescue strategy recovers at least "
                "20% of live-window deep misses while adding no more than 3 false alerts "
                "per 100 decisions and losing no more than 5 percentage points of precision."
            ),
            "status": status,
            "effect": (
                f"selected {selected_strategy}; test deep-miss recovery "
                f"{test_selected.get('deep_miss_recovery_rate')}; incremental false alerts "
                f"{test_comparison.get('incremental_false_alerts_per_100')}/100; "
                f"precision change {test_comparison.get('precision_change')}"
            ),
            "product_update": update,
        },
        "limitations": [
            "Spatial cells are coarse cardinal samples, not basin polygons or convection-resolving grids.",
            "Candidate selection uses the first half of the holdout and evaluation uses the second half; both are still within one historical period.",
            "Daily ERA5 precipitation is a weather outcome proxy, not human impact.",
            "The one-model rescue candidate deliberately tests whether the median can erase a useful minority signal; it does not justify trusting a single model by default.",
        ],
    }
