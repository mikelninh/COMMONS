from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
import math
from statistics import median
from typing import Any

from commons.deep_miss_lab import (
    LEADS,
    MODELS,
    PREVIOUS_RUNS_URL,
    _cells_within,
    _provider_value,
    _request_json_multi,
    _thresholds,
    build_cases,
    fetch_h23_evidence,
)
from commons.hypothesis_lab import BacktestPoint, _hourly_daily_sum, quantile
from commons.scale_points import GLOBAL_POINTS


H24_MIN_RECOVERY = 0.20
H25_MIN_RECOVERY = 0.33
MAX_EXTRA_FALSE_ALERTS_PER_100 = 3.0
MAX_PRECISION_DROP = 0.05
MIN_TEST_DEEP = 5
MIN_TEST_BLIND = 5


def _hourly_daily_max(payload: dict[str, Any], key: str) -> dict[str, float]:
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    values = hourly.get(key) or []
    out: dict[str, float] = {}
    counts: dict[str, int] = {}
    for raw_time, raw_value in zip(times, values):
        if raw_value is None:
            continue
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(value):
            continue
        day = str(raw_time)[:10]
        out[day] = max(out.get(day, value), value)
        counts[day] = counts.get(day, 0) + 1
    return {day: value for day, value in out.items() if counts.get(day, 0) >= 12}


def _provider_spatial_p90(
    evidence: dict[str, Any],
    *,
    point_id: str,
    provider: str,
    lead: int,
    target_date: date,
    radius_km: int,
) -> float | None:
    values: list[float] = []
    cells = _cells_within(radius_km)
    for cell in cells:
        value = _provider_value(
            evidence,
            point_id=point_id,
            cell=cell,
            provider=provider,
            lead=lead,
            target_date=target_date,
        )
        if value is not None:
            values.append(value)
    if len(values) < max(3, math.ceil(0.75 * len(cells))):
        return None
    result = quantile(values, 0.90)
    return float(result) if result is not None else None


def _provider_footprint(
    evidence: dict[str, Any],
    *,
    point_id: str,
    provider: str,
    lead: int,
    target_date: date,
    radius_km: int,
    threshold: float,
) -> float | None:
    values: list[float] = []
    cells = _cells_within(radius_km)
    for cell in cells:
        value = _provider_value(
            evidence,
            point_id=point_id,
            cell=cell,
            provider=provider,
            lead=lead,
            target_date=target_date,
        )
        if value is not None:
            values.append(value)
    if len(values) < max(3, math.ceil(0.75 * len(cells))):
        return None
    return sum(value >= threshold for value in values) / len(values)


def _minority_candidates_for_case(
    case: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, bool]:
    point_id = str(case["point_id"])
    decision = date.fromisoformat(str(case["decision_date"]))
    threshold = float(case["heavy_gate_mm"])

    hits: dict[str, bool] = {
        "minority_p90_25km": False,
        "minority_p90_50km": False,
        "minority_p90_100km": False,
        "minority_footprint_50km": False,
        "minority_strong_50km": False,
    }

    for offset, lead in ((1, 1), (2, 2), (3, 3)):
        target = decision + timedelta(days=offset)
        for provider in MODELS:
            center = _provider_value(
                evidence,
                point_id=point_id,
                cell="center",
                provider=provider,
                lead=lead,
                target_date=target,
            )
            if center is None:
                continue
            center_ratio = center / threshold

            p90_25 = _provider_spatial_p90(
                evidence,
                point_id=point_id,
                provider=provider,
                lead=lead,
                target_date=target,
                radius_km=25,
            )
            p90_50 = _provider_spatial_p90(
                evidence,
                point_id=point_id,
                provider=provider,
                lead=lead,
                target_date=target,
                radius_km=50,
            )
            p90_100 = _provider_spatial_p90(
                evidence,
                point_id=point_id,
                provider=provider,
                lead=lead,
                target_date=target,
                radius_km=100,
            )
            footprint_50 = _provider_footprint(
                evidence,
                point_id=point_id,
                provider=provider,
                lead=lead,
                target_date=target,
                radius_km=50,
                threshold=threshold,
            )

            if center_ratio >= 1.0 and p90_25 is not None and p90_25 / threshold >= 1.0:
                hits["minority_p90_25km"] = True
            if center_ratio >= 1.0 and p90_50 is not None and p90_50 / threshold >= 1.0:
                hits["minority_p90_50km"] = True
            if center_ratio >= 1.0 and p90_100 is not None and p90_100 / threshold >= 1.0:
                hits["minority_p90_100km"] = True
            if (
                center_ratio >= 1.0
                and footprint_50 is not None
                and footprint_50 >= 1 / 3
            ):
                hits["minority_footprint_50km"] = True
            if (
                center_ratio >= 1.5
                and p90_50 is not None
                and p90_50 / threshold >= 0.80
            ):
                hits["minority_strong_50km"] = True

    return hits


def _is_rain_consensus_blind(case: dict[str, Any]) -> bool:
    scores = case.get("scores") or {}
    any_model = float(scores.get("any_model_center") or 0.0)
    spatial = [
        float(value or 0.0)
        for key, value in scores.items()
        if str(key).startswith("spatial_")
    ]
    return any_model < 1.0 and max(spatial or [0.0]) < 1.0


def _rule_metrics(
    cases: list[dict[str, Any]],
    *,
    rescue_key: str,
    recovery_target: str = "deep",
) -> dict[str, Any]:
    usable = [
        case
        for case in cases
        if (case.get("scores") or {}).get("baseline_center") is not None
        and rescue_key in (case.get("rescue") or {})
    ]
    heavy = [case for case in usable if case["observed_heavy_next_72h"]]
    alerts = [
        case
        for case in usable
        if float(case["scores"]["baseline_center"]) >= 1.0
        or bool(case["rescue"][rescue_key])
    ]
    true_positives = [case for case in alerts if case["observed_heavy_next_72h"]]
    false_alerts = len(alerts) - len(true_positives)
    precision = len(true_positives) / len(alerts) if alerts else None
    recall = len(true_positives) / len(heavy) if heavy else None

    if recovery_target == "blind":
        misses = [
            case
            for case in heavy
            if float(case["scores"]["baseline_center"]) < 0.80
            and _is_rain_consensus_blind(case)
        ]
    else:
        misses = [
            case
            for case in heavy
            if float(case["scores"]["baseline_center"]) < 0.80
        ]
    recovered = [case for case in misses if bool(case["rescue"][rescue_key])]

    rescue_only = [
        case
        for case in usable
        if float(case["scores"]["baseline_center"]) < 1.0
        and bool(case["rescue"][rescue_key])
    ]
    rescue_true = sum(case["observed_heavy_next_72h"] for case in rescue_only)
    rescue_precision = rescue_true / len(rescue_only) if rescue_only else None

    return {
        "cases": len(usable),
        "heavy_events": len(heavy),
        "alerts": len(alerts),
        "true_positives": len(true_positives),
        "false_alerts": false_alerts,
        "precision": round(precision, 4) if precision is not None else None,
        "recall": round(recall, 4) if recall is not None else None,
        "false_alerts_per_100": round(100 * false_alerts / len(usable), 2) if usable else None,
        "target_misses": len(misses),
        "target_misses_recovered": len(recovered),
        "target_recovery_rate": round(len(recovered) / len(misses), 4) if misses else None,
        "rescue_only_reviews": len(rescue_only),
        "rescue_only_precision": (
            round(rescue_precision, 4) if rescue_precision is not None else None
        ),
    }


def _baseline_metrics(cases: list[dict[str, Any]], recovery_target: str) -> dict[str, Any]:
    prepared: list[dict[str, Any]] = []
    for case in cases:
        copy = dict(case)
        copy["rescue"] = {"__never__": False}
        prepared.append(copy)
    return _rule_metrics(
        prepared,
        rescue_key="__never__",
        recovery_target=recovery_target,
    )


def _compare(base: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    def delta(key: str) -> float | None:
        a = base.get(key)
        b = candidate.get(key)
        if a is None or b is None:
            return None
        return round(float(b) - float(a), 4)

    false_delta = None
    if base.get("false_alerts_per_100") is not None and candidate.get("false_alerts_per_100") is not None:
        false_delta = round(
            float(candidate["false_alerts_per_100"]) - float(base["false_alerts_per_100"]),
            2,
        )
    return {
        "recall_change": delta("recall"),
        "precision_change": delta("precision"),
        "incremental_false_alerts_per_100": false_delta,
    }


def _passes(
    candidate: dict[str, Any],
    comparison: dict[str, Any],
    *,
    min_recovery: float,
) -> bool:
    recovery = candidate.get("target_recovery_rate")
    false_delta = comparison.get("incremental_false_alerts_per_100")
    precision_delta = comparison.get("precision_change")
    return bool(
        recovery is not None
        and recovery >= min_recovery
        and false_delta is not None
        and false_delta <= MAX_EXTRA_FALSE_ALERTS_PER_100
        and precision_delta is not None
        and precision_delta >= -MAX_PRECISION_DROP
    )


def _select_candidate(
    development: list[dict[str, Any]],
    keys: list[str],
    *,
    recovery_target: str,
    min_recovery: float,
) -> tuple[str, dict[str, Any]]:
    base = _baseline_metrics(development, recovery_target)
    scored: list[tuple[bool, float, float, float, str, dict[str, Any]]] = []
    for key in keys:
        metrics = _rule_metrics(
            development,
            rescue_key=key,
            recovery_target=recovery_target,
        )
        comparison = _compare(base, metrics)
        passes = _passes(metrics, comparison, min_recovery=min_recovery)
        false_cost = comparison.get("incremental_false_alerts_per_100")
        rescue_precision = metrics.get("rescue_only_precision")
        scored.append(
            (
                passes,
                float(metrics.get("target_recovery_rate") or 0.0),
                -float(false_cost) if false_cost is not None else -999.0,
                float(rescue_precision) if rescue_precision is not None else 0.0,
                key,
                {
                    "metrics": metrics,
                    "comparison": comparison,
                    "passes": passes,
                },
            )
        )
    scored.sort(reverse=True)
    best = scored[0]
    return best[4], best[5]


def _fetch_convective_evidence(
    evidence: dict[str, Any],
) -> dict[str, Any]:
    points: tuple[BacktestPoint, ...] = evidence["affected_points"]
    point_ids = [point.id for point in points]
    latitudes = ",".join(str(point.latitude) for point in points)
    longitudes = ",".join(str(point.longitude) for point in points)
    start = evidence["query_start"].isoformat()
    end = evidence["end"].isoformat()

    variables = []
    for lead in LEADS:
        variables.extend(
            (
                f"cape_previous_day{lead}",
                f"showers_previous_day{lead}",
            )
        )

    output: dict[str, dict[str, Any]] = {point_id: {} for point_id in point_ids}
    errors: list[dict[str, str]] = []

    for provider, model in MODELS.items():
        try:
            payload = _request_json_multi(
                PREVIOUS_RUNS_URL,
                {
                    "latitude": latitudes,
                    "longitude": longitudes,
                    "start_date": start,
                    "end_date": end,
                    "hourly": ",".join(variables),
                    "models": model,
                    "timezone": "UTC",
                },
            )
            items = payload if isinstance(payload, list) else [payload]
            if len(items) != len(points):
                raise RuntimeError(
                    f"convective multi-coordinate response length {len(items)} != {len(points)}"
                )
            for point, item in zip(points, items):
                output[point.id][provider] = {
                    "cape": {
                        lead: _hourly_daily_max(
                            item, f"cape_previous_day{lead}"
                        )
                        for lead in LEADS
                    },
                    "showers": {
                        lead: _hourly_daily_sum(
                            item, f"showers_previous_day{lead}"
                        )
                        for lead in LEADS
                    },
                }
        except Exception as exc:
            errors.append({"provider": provider, "error": str(exc)})

    provider_coverage: dict[str, int] = {}
    for provider in MODELS:
        usable = 0
        for point_id in point_ids:
            provider_data = output[point_id].get(provider) or {}
            cape = provider_data.get("cape") or {}
            showers = provider_data.get("showers") or {}
            cape_ok = all(bool(cape.get(lead)) for lead in LEADS)
            showers_ok = all(bool(showers.get(lead)) for lead in LEADS)
            if cape_ok and showers_ok:
                usable += 1
        provider_coverage[provider] = usable

    expected = len(point_ids) * len(MODELS)
    observed = sum(provider_coverage.values())
    return {
        "by_point": output,
        "errors": errors,
        "health": {
            "status": "healthy" if expected and observed / expected >= 0.66 else "insufficient",
            "expected_point_provider_bundles": expected,
            "observed_point_provider_bundles": observed,
            "bundle_ratio": round(observed / expected, 4) if expected else 0.0,
            "provider_coverage": provider_coverage,
        },
    }


def _convective_features_for_case(
    case: dict[str, Any],
    convective: dict[str, Any],
) -> dict[str, float | None]:
    point_id = str(case["point_id"])
    decision = date.fromisoformat(str(case["decision_date"]))
    threshold = float(case["heavy_gate_mm"])
    point_data = convective["by_point"].get(point_id) or {}

    cape_council: list[float] = []
    cape_any: list[float] = []
    showers_council_ratio: list[float] = []
    showers_any_ratio: list[float] = []

    for offset, lead in ((1, 1), (2, 2), (3, 3)):
        target = (decision + timedelta(days=offset)).isoformat()
        capes: list[float] = []
        showers: list[float] = []
        for provider in MODELS:
            provider_data = point_data.get(provider) or {}
            cape = ((provider_data.get("cape") or {}).get(lead) or {}).get(target)
            shower = ((provider_data.get("showers") or {}).get(lead) or {}).get(target)
            if cape is not None:
                capes.append(float(cape))
            if shower is not None:
                showers.append(float(shower))
        if len(capes) >= 2:
            cape_council.append(float(median(capes)))
            cape_any.append(max(capes))
        if len(showers) >= 2:
            showers_council_ratio.append(float(median(showers)) / threshold)
            showers_any_ratio.append(max(showers) / threshold)

    return {
        "cape_council_max": max(cape_council) if len(cape_council) == 3 else None,
        "cape_any_max": max(cape_any) if len(cape_any) == 3 else None,
        "showers_council_ratio": (
            max(showers_council_ratio) if len(showers_council_ratio) == 3 else None
        ),
        "showers_any_ratio": max(showers_any_ratio) if len(showers_any_ratio) == 3 else None,
    }


def _convective_thresholds(development: list[dict[str, Any]]) -> dict[str, float | None]:
    nonheavy = [
        case for case in development if not case["observed_heavy_next_72h"]
    ]

    def q(feature: str, level: float) -> float | None:
        values = [
            float(case["convective"][feature])
            for case in nonheavy
            if (case.get("convective") or {}).get(feature) is not None
        ]
        return quantile(values, level)

    return {
        "cape_any_q75": q("cape_any_max", 0.75),
        "cape_any_q90": q("cape_any_max", 0.90),
        "cape_council_q75": q("cape_council_max", 0.75),
        "cape_council_q90": q("cape_council_max", 0.90),
    }


def _apply_convective_candidates(
    cases: list[dict[str, Any]],
    thresholds: dict[str, float | None],
) -> None:
    for case in cases:
        features = case.get("convective") or {}
        blind = _is_rain_consensus_blind(case)
        cape_any = features.get("cape_any_max")
        cape_council = features.get("cape_council_max")
        showers_any = features.get("showers_any_ratio")
        showers_council = features.get("showers_council_ratio")

        def ge(value: Any, threshold: Any) -> bool:
            return value is not None and threshold is not None and float(value) >= float(threshold)

        case.setdefault("rescue", {})
        case["rescue"].update(
            {
                "blind_cape_any_q90": blind and ge(cape_any, thresholds.get("cape_any_q90")),
                "blind_cape_council_q90": blind and ge(
                    cape_council, thresholds.get("cape_council_q90")
                ),
                "blind_cape75_showers25": (
                    blind
                    and ge(cape_any, thresholds.get("cape_any_q75"))
                    and showers_any is not None
                    and float(showers_any) >= 0.25
                ),
                "blind_cape75_council_showers15": (
                    blind
                    and ge(cape_council, thresholds.get("cape_council_q75"))
                    and showers_council is not None
                    and float(showers_council) >= 0.15
                ),
                "blind_showers_any50": (
                    blind
                    and showers_any is not None
                    and float(showers_any) >= 0.50
                ),
            }
        )


def _split_cases(cases: list[dict[str, Any]]) -> tuple[str | None, list[dict[str, Any]], list[dict[str, Any]]]:
    if not cases:
        return None, [], []
    dates = sorted({str(case["decision_date"]) for case in cases})
    split = dates[max(1, len(dates) // 2) - 1]
    return (
        split,
        [case for case in cases if str(case["decision_date"]) <= split],
        [case for case in cases if str(case["decision_date"]) > split],
    )


def run_minority_convective_lab(
    miss_report: dict[str, Any],
    *,
    points: tuple[BacktestPoint, ...] = GLOBAL_POINTS,
) -> dict[str, Any]:
    evidence = fetch_h23_evidence(miss_report, points=points)
    cases = build_cases(evidence, miss_report)
    split_date, development, test = _split_cases(cases)

    for case in cases:
        case["rescue"] = _minority_candidates_for_case(case, evidence)

    h24_keys = [
        "minority_p90_25km",
        "minority_p90_50km",
        "minority_p90_100km",
        "minority_footprint_50km",
        "minority_strong_50km",
    ]
    h24_selected, h24_dev = _select_candidate(
        development,
        h24_keys,
        recovery_target="deep",
        min_recovery=H24_MIN_RECOVERY,
    )
    h24_base_test = _baseline_metrics(test, "deep")
    h24_test = _rule_metrics(test, rescue_key=h24_selected, recovery_target="deep")
    h24_compare = _compare(h24_base_test, h24_test)
    h24_healthy = (evidence.get("health") or {}).get("status") == "healthy"
    h24_enough = (h24_base_test.get("target_misses") or 0) >= MIN_TEST_DEEP
    h24_supported = (
        h24_healthy
        and h24_enough
        and _passes(h24_test, h24_compare, min_recovery=H24_MIN_RECOVERY)
    )
    h24_status = (
        "supported"
        if h24_supported
        else "not_supported"
        if h24_healthy and h24_enough
        else "insufficient"
    )

    convective = _fetch_convective_evidence(evidence)
    for case in cases:
        case["convective"] = _convective_features_for_case(case, convective)

    development = [case for case in cases if split_date and str(case["decision_date"]) <= split_date]
    test = [case for case in cases if split_date and str(case["decision_date"]) > split_date]
    conv_thresholds = _convective_thresholds(development)
    _apply_convective_candidates(development, conv_thresholds)
    _apply_convective_candidates(test, conv_thresholds)

    h25_keys = [
        "blind_cape_any_q90",
        "blind_cape_council_q90",
        "blind_cape75_showers25",
        "blind_cape75_council_showers15",
        "blind_showers_any50",
    ]
    h25_selected, h25_dev = _select_candidate(
        development,
        h25_keys,
        recovery_target="blind",
        min_recovery=H25_MIN_RECOVERY,
    )
    h25_base_test = _baseline_metrics(test, "blind")
    h25_test = _rule_metrics(test, rescue_key=h25_selected, recovery_target="blind")
    h25_compare = _compare(h25_base_test, h25_test)
    h25_health = (convective.get("health") or {}).get("status") == "healthy"
    h25_enough = (h25_base_test.get("target_misses") or 0) >= MIN_TEST_BLIND
    h25_supported = (
        h25_health
        and h25_enough
        and _passes(h25_test, h25_compare, min_recovery=H25_MIN_RECOVERY)
    )
    h25_status = (
        "supported"
        if h25_supported
        else "not_supported"
        if h25_health and h25_enough
        else "insufficient"
    )

    blind_test_examples = []
    for case in test:
        if (
            case["observed_heavy_next_72h"]
            and float(case["scores"]["baseline_center"]) < 0.80
            and _is_rain_consensus_blind(case)
        ):
            blind_test_examples.append(
                {
                    "point_id": case["point_id"],
                    "decision_date": case["decision_date"],
                    "observed_peak_mm": case["observed_peak_mm"],
                    "heavy_gate_mm": case["heavy_gate_mm"],
                    "baseline_score": case["scores"]["baseline_center"],
                    "convective": case.get("convective"),
                    "selected_rule_fired": bool(
                        (case.get("rescue") or {}).get(h25_selected)
                    ),
                }
            )

    return {
        "schema_version": "0.1",
        "source_period": miss_report.get("period"),
        "split_date": split_date,
        "rain_evidence_health": evidence.get("health"),
        "convective_evidence_health": convective.get("health"),
        "source_errors": {
            "rain": evidence.get("errors"),
            "convective": convective.get("errors"),
        },
        "h24": {
            "hypothesis": {
                "id": "H24",
                "claim": (
                    "A minority-model heavy-rain signal becomes trustworthy enough for a "
                    "shadow rescue only when the same provider is spatially corroborated."
                ),
                "status": h24_status,
                "effect": (
                    f"selected {h24_selected}; test recovery {h24_test.get('target_recovery_rate')}; "
                    f"extra false alerts {h24_compare.get('incremental_false_alerts_per_100')}/100; "
                    f"precision change {h24_compare.get('precision_change')}"
                ),
                "product_update": (
                    f"Promote {h24_selected} to shadow PRIORITY context only; do not change ALERT until another independent window."
                    if h24_supported
                    else "Do not give minority rainfall signals ranking authority yet; keep them inspectable context and continue learning provider/spatial reliability."
                    if h24_status == "not_supported"
                    else "Keep minority corroboration observational until evidence health and final-test misses are sufficient."
                ),
            },
            "development": {
                "selected_rule": h24_selected,
                "selection": h24_dev,
            },
            "test": {
                "baseline": h24_base_test,
                "selected": h24_test,
                "comparison": h24_compare,
                "passes_guardrails": (
                    _passes(h24_test, h24_compare, min_recovery=H24_MIN_RECOVERY)
                    if test
                    else False
                ),
            },
        },
        "h25": {
            "hypothesis": {
                "id": "H25",
                "claim": (
                    "Archived convective instability and shower forecasts recover at least "
                    "one third of rainfall-consensus-blind heavy events within the same scarcity guardrails."
                ),
                "status": h25_status,
                "effect": (
                    f"selected {h25_selected}; blind test misses {h25_base_test.get('target_misses')}; "
                    f"recovery {h25_test.get('target_recovery_rate')}; "
                    f"extra false alerts {h25_compare.get('incremental_false_alerts_per_100')}/100; "
                    f"precision change {h25_compare.get('precision_change')}"
                ),
                "product_update": (
                    f"Keep {h25_selected} as shadow convective context for consensus-blind cases; do not change ALERT until a larger independent sample confirms it."
                    if h25_supported
                    else "Do not add CAPE/showers to live attention logic from this sample. Use the blind-case diagnostics to choose the next physical signals or higher-resolution models."
                    if h25_status == "not_supported"
                    else "Convective blindness remains an open hypothesis; archived CAPE/showers coverage or blind-case count is not yet sufficient."
                ),
            },
            "development": {
                "convective_thresholds": {
                    key: round(value, 3) if value is not None else None
                    for key, value in conv_thresholds.items()
                },
                "selected_rule": h25_selected,
                "selection": h25_dev,
            },
            "test": {
                "baseline": h25_base_test,
                "selected": h25_test,
                "comparison": h25_compare,
                "passes_guardrails": (
                    _passes(h25_test, h25_compare, min_recovery=H25_MIN_RECOVERY)
                    if test
                    else False
                ),
                "blind_examples": blind_test_examples,
            },
        },
        "guardrails": {
            "h24_min_deep_miss_recovery": H24_MIN_RECOVERY,
            "h25_min_blind_miss_recovery": H25_MIN_RECOVERY,
            "max_extra_false_alerts_per_100": MAX_EXTRA_FALSE_ALERTS_PER_100,
            "max_precision_drop": MAX_PRECISION_DROP,
            "promotion_scope": "shadow priority/context only; never direct ALERT from this sprint",
        },
        "limitations": [
            "H24 corroboration is sampled on coarse 25/50/100 km cardinal grids rather than full native model fields.",
            "H25 uses archived CAPE and showers where available; model-specific variable availability can make the result insufficient.",
            "The development/test split is temporal but remains inside one two-month historical period.",
            "ERA5 precipitation is an outcome proxy, not impact or harm.",
        ],
    }
