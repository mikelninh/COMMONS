from __future__ import annotations

from collections import defaultdict
from statistics import mean, median
from typing import Any

from commons.hypothesis_lab import GLOBAL_POINTS if False else BacktestPoint
from commons.hypothesis_lab import build_records
from commons.scale_points import GLOBAL_POINTS


def run_scale_backtest(
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
    by_point: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        if int(record["lead_days"]) == 3:
            by_point[record["point_id"]].append(record)

    point_meta = {point.id: point for point in points}
    results: list[dict[str, Any]] = []
    for point_id, rows in sorted(by_point.items()):
        if len(rows) < 20:
            continue
        provider_errors: dict[str, list[float]] = defaultdict(list)
        council_errors: list[float] = []
        heavy_rows = [row for row in rows if row["rain_regime"] == "heavy"]
        for row in rows:
            actual = float(row["actual_precip_mm"])
            council_errors.append(abs(float(row["council_median_mm"]) - actual))
            for provider, prediction in (row.get("predictions_mm") or {}).items():
                provider_errors[provider].append(abs(float(prediction) - actual))

        provider_mae = [
            mean(values) for values in provider_errors.values() if values
        ]
        average_model_mae = mean(provider_mae) if provider_mae else None
        council_mae = mean(council_errors) if council_errors else None
        improvement = (
            100 * (average_model_mae - council_mae) / average_model_mae
            if average_model_mae and council_mae is not None
            else None
        )
        point = point_meta[point_id]
        results.append(
            {
                "id": point_id,
                "name": point.name,
                "country": point.country,
                "samples": len(rows),
                "heavy_samples": len(heavy_rows),
                "council_mae_mm": round(council_mae, 3) if council_mae is not None else None,
                "average_model_mae_mm": (
                    round(average_model_mae, 3)
                    if average_model_mae is not None
                    else None
                ),
                "improvement_pct": (
                    round(improvement, 1) if improvement is not None else None
                ),
                "council_better": bool(improvement is not None and improvement > 0),
            }
        )

    improvements = [
        float(item["improvement_pct"])
        for item in results
        if item["improvement_pct"] is not None
    ]
    wins = sum(bool(item["council_better"]) for item in results)
    win_rate = wins / len(results) if results else None
    median_improvement = median(improvements) if improvements else None

    enough = len(results) >= 24
    supported = (
        enough
        and win_rate is not None
        and win_rate >= 0.70
        and median_improvement is not None
        and median_improvement > 0
    )
    status = "supported" if supported else "not_supported" if enough else "insufficient"
    update = (
        "The council generalises well enough to justify expanding validated monitoring, while preserving location-specific thresholds."
        if supported
        else "Do not generalise the three-location result yet; inspect where council skill fails before expanding live coverage."
        if status == "not_supported"
        else "Collect a healthier global sample before changing live monitor coverage."
    )

    return {
        "schema_version": "0.1",
        "period": {"start": start_date, "end": end_date},
        "lead_days": 3,
        "requested_points": len(points),
        "usable_points": len(results),
        "source_errors": source_errors,
        "point_results": results,
        "summary": {
            "council_win_points": wins,
            "council_win_rate": round(win_rate, 4) if win_rate is not None else None,
            "median_improvement_pct": (
                round(median_improvement, 1)
                if median_improvement is not None
                else None
            ),
        },
        "hypothesis": {
            "id": "H20",
            "claim": "The three-model council improves 3-day daily-precipitation accuracy across diverse global climates, not only the original pilot locations.",
            "status": status,
            "effect": (
                f"wins {wins}/{len(results)} locations; "
                f"median improvement {round(median_improvement, 1) if median_improvement is not None else None}%"
            ),
            "product_update": update,
        },
        "limitations": [
            "Point precipitation is not basin-integrated precipitation.",
            "This tests forecast error, not human impact.",
            "Locations are a deliberately diverse convenience sample, not a statistically representative sample of Earth.",
            "Operational model versions can change over time.",
        ],
    }
