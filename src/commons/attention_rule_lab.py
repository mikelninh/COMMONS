from __future__ import annotations

from collections import defaultdict
from statistics import mean, median
from typing import Any

from commons.hypothesis_lab import POINTS, build_records, quantile
from commons.revision_lab import sign


HEAVY_QUANTILE = 0.90
LOOSE_FACTOR = 0.80
REVISION_THRESHOLD_MM = 1.0
LEADS = (5, 3, 1)


def group_paths(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[int, dict[str, Any]]] = defaultdict(dict)
    for record in records:
        grouped[(record["point_id"], record["date"])][int(record["lead_days"])] = record

    paths: list[dict[str, Any]] = []
    for (point_id, day), by_lead in grouped.items():
        if not all(lead in by_lead for lead in LEADS):
            continue
        r5, r3, r1 = by_lead[5], by_lead[3], by_lead[1]
        common_models = (
            set(r5["predictions_mm"])
            & set(r3["predictions_mm"])
            & set(r1["predictions_mm"])
        )
        if len(common_models) < 2:
            continue

        def council(record: dict[str, Any]) -> float:
            return float(record["council_median_mm"])

        def majority_direction(older: dict[str, Any], newer: dict[str, Any]) -> int:
            up = 0
            down = 0
            for model in common_models:
                delta = (
                    float(newer["predictions_mm"][model])
                    - float(older["predictions_mm"][model])
                )
                direction = sign(delta, REVISION_THRESHOLD_MM)
                if direction > 0:
                    up += 1
                elif direction < 0:
                    down += 1
            if up >= 2:
                return 1
            if down >= 2:
                return -1
            return 0

        paths.append(
            {
                "point_id": point_id,
                "date": day,
                "actual_mm": float(r1["actual_precip_mm"]),
                "council": {
                    5: council(r5),
                    3: council(r3),
                    1: council(r1),
                },
                "revision_5_to_3": majority_direction(r5, r3),
                "revision_3_to_1": majority_direction(r3, r1),
            }
        )
    return paths


def threshold_by_point(paths: list[dict[str, Any]]) -> dict[str, float]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for path in paths:
        grouped[path["point_id"]].append(path["actual_mm"])
    return {
        point_id: float(quantile(values, HEAVY_QUANTILE))
        for point_id, values in grouped.items()
        if values
    }


def first_alert_lead(
    path: dict[str, Any],
    threshold: float,
    *,
    policy: str,
) -> int | None:
    councils = path["council"]

    for lead in LEADS:
        value = councils[lead]

        if policy == "strict":
            if value >= threshold:
                return lead
            continue

        if policy == "loose":
            if value >= LOOSE_FACTOR * threshold:
                return lead
            continue

        if policy == "revision_aware":
            if value >= threshold:
                return lead

            if value < LOOSE_FACTOR * threshold:
                continue

            if lead == 3 and path["revision_5_to_3"] > 0:
                return lead

            if lead == 1 and path["revision_3_to_1"] > 0:
                return lead

    return None


def evaluate_policy(
    paths: list[dict[str, Any]],
    thresholds: dict[str, float],
    *,
    policy: str,
) -> dict[str, Any]:
    alerts = 0
    true_positives = 0
    heavy_events = 0
    lead_days: list[int] = []
    false_alerts = 0

    for path in paths:
        threshold = thresholds[path["point_id"]]
        heavy = path["actual_mm"] >= threshold
        if heavy:
            heavy_events += 1

        lead = first_alert_lead(path, threshold, policy=policy)
        if lead is None:
            continue

        alerts += 1
        if heavy:
            true_positives += 1
            lead_days.append(lead)
        else:
            false_alerts += 1

    precision = true_positives / alerts if alerts else None
    recall = true_positives / heavy_events if heavy_events else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None
        and recall is not None
        and precision + recall > 0
        else None
    )
    miss_rate = 1 - recall if recall is not None else None
    false_alert_rate = false_alerts / len(paths) if paths else None

    return {
        "policy": policy,
        "days_evaluated": len(paths),
        "heavy_events": heavy_events,
        "alerts": alerts,
        "true_positives": true_positives,
        "false_alerts": false_alerts,
        "precision": round(precision, 4) if precision is not None else None,
        "recall": round(recall, 4) if recall is not None else None,
        "f1": round(f1, 4) if f1 is not None else None,
        "miss_rate": round(miss_rate, 4) if miss_rate is not None else None,
        "false_alerts_per_100_days": (
            round(100 * false_alert_rate, 2)
            if false_alert_rate is not None
            else None
        ),
        "mean_true_alert_lead_days": (
            round(mean(lead_days), 3) if lead_days else None
        ),
    }


def run_attention_backtest(
    *,
    start_date: str = "2026-07-01",
    end_date: str = "2026-09-05",
) -> dict[str, Any]:
    records, source_errors = build_records(
        start_date=start_date,
        end_date=end_date,
        points=POINTS[:3],
    )
    paths = group_paths(records)
    thresholds = threshold_by_point(paths)

    strict = evaluate_policy(paths, thresholds, policy="strict")
    loose = evaluate_policy(paths, thresholds, policy="loose")
    revision = evaluate_policy(paths, thresholds, policy="revision_aware")

    strict_f1 = strict.get("f1")
    revision_f1 = revision.get("f1")
    strict_precision = strict.get("precision")
    revision_precision = revision.get("precision")
    strict_recall = strict.get("recall")
    revision_recall = revision.get("recall")
    strict_lead = strict.get("mean_true_alert_lead_days")
    revision_lead = revision.get("mean_true_alert_lead_days")

    f1_gain = (
        revision_f1 - strict_f1
        if revision_f1 is not None and strict_f1 is not None
        else None
    )
    recall_gain = (
        revision_recall - strict_recall
        if revision_recall is not None and strict_recall is not None
        else None
    )
    precision_change = (
        revision_precision - strict_precision
        if revision_precision is not None and strict_precision is not None
        else None
    )
    lead_gain = (
        revision_lead - strict_lead
        if revision_lead is not None and strict_lead is not None
        else None
    )

    # Revision-aware must improve the overall trade-off without paying most
    # of the precision penalty of simply lowering the threshold everywhere.
    revision_beats_strict = (
        f1_gain is not None
        and f1_gain >= 0.03
        and recall_gain is not None
        and recall_gain >= 0.03
        and precision_change is not None
        and precision_change >= -0.05
    )
    revision_beats_loose = (
        revision.get("precision") is not None
        and loose.get("precision") is not None
        and revision["precision"] >= loose["precision"] + 0.03
        and revision.get("recall") is not None
        and loose.get("recall") is not None
        and revision["recall"] >= loose["recall"] - 0.05
    )
    supported = revision_beats_strict and revision_beats_loose

    return {
        "schema_version": "0.1",
        "period": {"start": start_date, "end": end_date},
        "points": [point.id for point in POINTS[:3]],
        "verification": "ERA5 heavy-rain event at each location's 90th percentile",
        "heavy_event_quantile": HEAVY_QUANTILE,
        "loose_threshold_factor": LOOSE_FACTOR,
        "revision_threshold_mm": REVISION_THRESHOLD_MM,
        "paths": len(paths),
        "source_errors": source_errors,
        "thresholds_mm": {
            key: round(value, 3) for key, value in thresholds.items()
        },
        "policies": {
            "strict": strict,
            "loose": loose,
            "revision_aware": revision,
        },
        "hypothesis": {
            "id": "H12",
            "claim": "A revision-aware material-change rule improves the precision/recall/lead-time trade-off versus fixed forecast thresholds.",
            "status": (
                "supported"
                if supported
                else "not_supported"
                if f1_gain is not None
                else "insufficient"
            ),
            "f1_gain_vs_strict": round(f1_gain, 4) if f1_gain is not None else None,
            "recall_gain_vs_strict": (
                round(recall_gain, 4) if recall_gain is not None else None
            ),
            "precision_change_vs_strict": (
                round(precision_change, 4)
                if precision_change is not None
                else None
            ),
            "lead_gain_days_vs_strict": (
                round(lead_gain, 3) if lead_gain is not None else None
            ),
            "product_update": (
                "Use revision-aware material-change logic as the first candidate attention rule."
                if supported
                else "Do not replace fixed thresholds with the current revision-aware rule yet."
            ),
        },
        "limitations": [
            "The heavy-rain threshold is defined from the evaluation period's observed climatology.",
            "This evaluates heavy precipitation, not flood damage or human impact.",
            "The revision-aware rule and 80% threshold were chosen before this test but still require out-of-sample validation.",
            "Three locations and roughly two months are not enough for a production alert policy.",
        ],
    }
