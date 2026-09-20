from __future__ import annotations

import math
from statistics import mean, pstdev
from typing import Any

from commons.hydrology_lab import POINTS, auc, fetch_discharge, precision_at_fraction, quantile


def percentile_rank(sorted_values: list[float], value: float) -> float:
    if not sorted_values:
        return 0.0
    count = sum(item <= value for item in sorted_values)
    return count / len(sorted_values)


def zscore(value: float, center: float, spread: float) -> float:
    if spread < 1e-9:
        return 0.0
    return (value - center) / spread


def build_trajectory_rows(
    discharge: dict[str, float],
    *,
    future_days: int = 3,
) -> list[dict[str, Any]]:
    dates = sorted(discharge)
    values = [discharge[day] for day in dates]
    if len(values) < 60:
        return []

    ordered = sorted(values)
    extreme_threshold = quantile(values, 0.95)
    center = mean(values)
    spread = pstdev(values)

    rows: list[dict[str, Any]] = []
    for idx in range(6, len(dates) - future_days):
        day = dates[idx]
        current = discharge[day]
        prev3 = [discharge[dates[j]] for j in range(idx - 3, idx)]
        prev6 = [discharge[dates[j]] for j in range(idx - 6, idx)]
        future = [
            discharge[dates[j]]
            for j in range(idx + 1, idx + future_days + 1)
        ]

        current_pct = percentile_rank(ordered, current)
        slope3 = current - mean(prev3)
        slope6 = current - mean(prev6)
        recent_acceleration = slope3 - (mean(prev3) - mean(prev6))

        rows.append(
            {
                "date": day,
                "current_discharge": current,
                "current_percentile": current_pct,
                "slope3_z": zscore(slope3, 0.0, spread),
                "slope6_z": zscore(slope6, 0.0, spread),
                "acceleration_z": zscore(recent_acceleration, 0.0, spread),
                "future_max_discharge": max(future),
                "future_extreme": 1 if max(future) >= extreme_threshold else 0,
                "extreme_threshold": extreme_threshold,
            }
        )
    return rows


def evaluate_trajectory(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"status": "insufficient_data"}

    labels = [row["future_extreme"] for row in rows]
    baseline = [row["current_percentile"] for row in rows]
    trajectory = [
        row["current_percentile"]
        + 0.20 * row["slope3_z"]
        + 0.10 * row["slope6_z"]
        + 0.10 * row["acceleration_z"]
        for row in rows
    ]

    baseline_auc = auc(baseline, labels)
    trajectory_auc = auc(trajectory, labels)
    baseline_precision = precision_at_fraction(baseline, labels, 0.05)
    trajectory_precision = precision_at_fraction(trajectory, labels, 0.05)

    return {
        "status": "ok",
        "samples": len(rows),
        "extreme_future_windows": sum(labels),
        "baseline_current_percentile": {
            "auc": round(baseline_auc, 4) if baseline_auc is not None else None,
            "precision_at_top_5pct": (
                round(baseline_precision, 4)
                if baseline_precision is not None
                else None
            ),
        },
        "trajectory_score": {
            "auc": round(trajectory_auc, 4) if trajectory_auc is not None else None,
            "precision_at_top_5pct": (
                round(trajectory_precision, 4)
                if trajectory_precision is not None
                else None
            ),
        },
        "auc_gain": (
            round(trajectory_auc - baseline_auc, 4)
            if trajectory_auc is not None and baseline_auc is not None
            else None
        ),
        "precision_gain_pct": (
            round(
                100 * (trajectory_precision - baseline_precision) / baseline_precision,
                1,
            )
            if trajectory_precision is not None
            and baseline_precision not in (None, 0)
            else None
        ),
    }


def run_river_attention_backtest(
    *,
    start_date: str = "2019-01-01",
    end_date: str = "2022-07-31",
) -> dict[str, Any]:
    results = []
    errors = []
    for point in POINTS:
        try:
            discharge = fetch_discharge(point, start_date, end_date)
            rows = build_trajectory_rows(discharge)
            evaluation = evaluate_trajectory(rows)
            results.append(
                {
                    "point": point.id,
                    "name": point.name,
                    "country": point.country,
                    **evaluation,
                }
            )
        except Exception as exc:
            errors.append({"point": point.id, "error": str(exc)})

    valid = [item for item in results if item.get("status") == "ok"]
    auc_gains = [
        item["auc_gain"] for item in valid if item.get("auc_gain") is not None
    ]
    precision_gains = [
        item["precision_gain_pct"]
        for item in valid
        if item.get("precision_gain_pct") is not None
    ]
    positive = sum(1 for gain in auc_gains if gain >= 0.01)
    negative = sum(1 for gain in auc_gains if gain < 0)

    mean_auc_gain = mean(auc_gains) if auc_gains else None
    mean_precision_gain = mean(precision_gains) if precision_gains else None
    supported = (
        len(valid) >= 3
        and positive >= 2
        and negative == 0
        and mean_auc_gain is not None
        and mean_auc_gain >= 0.01
        and mean_precision_gain is not None
        and mean_precision_gain >= 10
    )
    mixed = (
        not supported
        and mean_auc_gain is not None
        and any(gain >= 0.02 for gain in auc_gains)
    )

    return {
        "schema_version": "0.1",
        "period": {"start": start_date, "end": end_date},
        "future_window_days": 3,
        "verification": "future GloFAS discharge",
        "points": results,
        "source_errors": errors,
        "hypothesis": {
            "id": "H10",
            "claim": "Current river percentile plus recent trajectory improves detection of an extreme next three days versus current percentile alone.",
            "status": (
                "supported"
                if supported
                else "mixed"
                if mixed
                else "not_supported"
                if mean_auc_gain is not None and mean_precision_gain is not None
                else "insufficient"
            ),
            "mean_auc_gain": round(mean_auc_gain, 4) if mean_auc_gain is not None else None,
            "mean_precision_gain_pct": (
                round(mean_precision_gain, 1)
                if mean_precision_gain is not None
                else None
            ),
            "product_update": (
                "Add river trajectory as a validated attention feature."
                if supported
                else "Use river trajectory only in basins where its backtest is positive."
                if mixed
                else "Keep current river percentile as the primary river-state feature."
            ),
        },
        "limitations": [
            "The target is modelled GloFAS discharge, not observed damage or a local gauge.",
            "Current discharge naturally contains persistence information about near-future discharge.",
            "The trajectory score weights are fixed heuristics, not trained parameters.",
            "Performance may vary strongly by basin.",
        ],
    }
