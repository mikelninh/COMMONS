from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from commons.hypothesis_lab import BacktestPoint, build_records, quantile
from commons.scale_points import GLOBAL_POINTS


def _split_date(start_date: str, end_date: str) -> str:
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    return (start + (end - start) * 2 / 3).isoformat()


def run_miss_lab(
    *,
    start_date: str,
    end_date: str,
    points: tuple[BacktestPoint, ...] = GLOBAL_POINTS,
) -> dict[str, Any]:
    records, source_errors = build_records(
        start_date=start_date,
        end_date=end_date,
        points=points,
    )
    split = _split_date(start_date, end_date)

    actual_train: dict[str, list[float]] = defaultdict(list)
    rows_by_case: dict[tuple[str, str], dict[int, dict[str, Any]]] = defaultdict(dict)

    for row in records:
        lead = int(row["lead_days"])
        if row["date"] < split and lead == 3:
            actual_train[row["point_id"]].append(float(row["actual_precip_mm"]))
        if row["date"] >= split:
            rows_by_case[(row["point_id"], row["date"])][lead] = row

    thresholds = {
        point_id: quantile(values, 0.90)
        for point_id, values in actual_train.items()
        if values
    }
    point_meta = {point.id: point for point in points}

    misses: list[dict[str, Any]] = []
    heavy_events = 0
    alerts = 0
    true_positives = 0

    for (point_id, day), leads in sorted(rows_by_case.items()):
        row3 = leads.get(3)
        if not row3:
            continue
        threshold = thresholds.get(point_id)
        if not threshold:
            continue

        actual = float(row3["actual_precip_mm"])
        forecast = float(row3["council_median_mm"])
        ratio = forecast / threshold
        heavy = actual >= threshold
        alert = forecast >= threshold
        if heavy:
            heavy_events += 1
        if alert:
            alerts += 1
        if heavy and alert:
            true_positives += 1
        if not heavy or alert:
            continue

        row5 = leads.get(5)
        revision = (
            forecast - float(row5["council_median_mm"])
            if row5 is not None
            else None
        )
        point = point_meta[point_id]
        misses.append(
            {
                "id": f"{point_id}-{day}",
                "point_id": point_id,
                "name": point.name,
                "country": point.country,
                "date": day,
                "actual_mm": round(actual, 2),
                "heavy_gate_mm": round(float(threshold), 2),
                "forecast_3d_mm": round(forecast, 2),
                "gate_ratio": round(ratio, 4),
                "miss_type": "near_threshold" if ratio >= 0.80 else "deep",
                "revision_5d_to_3d_mm": (
                    round(revision, 2) if revision is not None else None
                ),
                "relative_spread": row3.get("relative_spread"),
                "models": row3.get("predictions_mm"),
            }
        )

    misses.sort(
        key=lambda item: (
            item["gate_ratio"],
            -(item["actual_mm"] / item["heavy_gate_mm"]),
        )
    )
    near = sum(item["miss_type"] == "near_threshold" for item in misses)
    deep = sum(item["miss_type"] == "deep" for item in misses)
    near_share = near / len(misses) if misses else None
    enough = len(misses) >= 10

    if enough and near_share is not None and near_share >= 0.60:
        status = "supported"
        update = "Most misses are boundary cases. Focus next experiments on calibration around the threshold before adding broad new features."
    elif enough:
        status = "not_supported"
        update = "Misses are not mainly boundary cases. Audit deep misses for missing physical variables, model failure modes, and spatial context."
    else:
        status = "insufficient"
        update = "Keep collecting misses automatically; there are not enough holdout failures yet to identify the dominant failure mode."

    return {
        "schema_version": "0.1",
        "period": {"start": start_date, "end": end_date, "holdout_start": split},
        "verification": "daily ERA5 precipitation; 90th-percentile gate learned only from the earlier training segment",
        "requested_points": len(points),
        "source_errors": source_errors,
        "heavy_events": heavy_events,
        "alerts": alerts,
        "true_positives": true_positives,
        "misses": len(misses),
        "near_threshold_misses": near,
        "deep_misses": deep,
        "near_threshold_share": round(near_share, 4) if near_share is not None else None,
        "cases": misses[:60],
        "hypothesis": {
            "id": "H21",
            "claim": "Most strict-threshold heavy-event misses are near the decision boundary rather than deep misses.",
            "status": status,
            "effect": (
                f"near {near}; deep {deep}; "
                f"near share {round(near_share, 4) if near_share is not None else None}; "
                f"misses {len(misses)}"
            ),
            "product_update": update,
        },
        "limitations": [
            "ERA5 is reanalysis rather than a local rain gauge.",
            "The threshold is location-specific but does not model impact.",
            "The miss taxonomy is diagnostic; it does not itself justify lowering the live alert threshold.",
        ],
    }
