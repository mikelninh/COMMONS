from __future__ import annotations

from typing import Any

from commons.attention_rule_lab import group_paths, threshold_by_point
from commons.hypothesis_lab import POINTS, build_records


def _rate(true_count: int, total: int) -> float | None:
    return true_count / total if total else None


def run_watch_value_backtest(
    *,
    start_date: str = "2026-07-01",
    end_date: str = "2026-09-05",
    near_threshold_factor: float = 0.60,
) -> dict[str, Any]:
    records, source_errors = build_records(
        start_date=start_date,
        end_date=end_date,
        points=POINTS[:3],
    )
    paths = group_paths(records)
    thresholds = threshold_by_point(paths)

    rows: list[dict[str, Any]] = []
    for path in paths:
        threshold = thresholds[path["point_id"]]
        council = float(path["council"][3])
        ratio = council / threshold if threshold else 0.0
        if not (near_threshold_factor <= ratio < 1.0):
            continue

        rows.append(
            {
                "point_id": path["point_id"],
                "date": path["date"],
                "ratio": ratio,
                "revision_up": int(path["revision_5_to_3"]) > 0,
                "heavy": float(path["actual_mm"]) >= threshold,
            }
        )

    up = [row for row in rows if row["revision_up"]]
    not_up = [row for row in rows if not row["revision_up"]]
    up_true = sum(1 for row in up if row["heavy"])
    not_up_true = sum(1 for row in not_up if row["heavy"])

    up_rate = _rate(up_true, len(up))
    not_up_rate = _rate(not_up_true, len(not_up))
    lift = (
        up_rate - not_up_rate
        if up_rate is not None and not_up_rate is not None
        else None
    )

    enough = len(up) >= 5 and len(not_up) >= 10
    supported = enough and lift is not None and lift >= 0.10
    status = "supported" if supported else "not_supported" if enough else "insufficient"

    return {
        "schema_version": "0.1",
        "period": {"start": start_date, "end": end_date},
        "checkpoint": "T-3 days",
        "near_threshold_factor": near_threshold_factor,
        "paths": len(paths),
        "near_threshold_cases": len(rows),
        "source_errors": source_errors,
        "revision_up": {
            "cases": len(up),
            "heavy_events": up_true,
            "heavy_event_rate": round(up_rate, 4) if up_rate is not None else None,
        },
        "revision_not_up": {
            "cases": len(not_up),
            "heavy_events": not_up_true,
            "heavy_event_rate": round(not_up_rate, 4) if not_up_rate is not None else None,
        },
        "heavy_event_rate_lift": round(lift, 4) if lift is not None else None,
        "hypothesis": {
            "id": "H17",
            "claim": "Among sub-threshold 3-day forecasts, upward model revisions identify cases that deserve more human attention.",
            "status": status,
            "effect": (
                f"upward-revision heavy-event rate {round(up_rate, 4) if up_rate is not None else None} "
                f"vs {round(not_up_rate, 4) if not_up_rate is not None else None}; "
                f"lift {round(lift, 4) if lift is not None else None}; "
                f"n={len(up)} vs {len(not_up)}"
            ),
            "product_update": (
                "Use upward revisions to rank sub-threshold WATCH candidates above otherwise similar cases."
                if supported
                else "Do not promote revision direction into the attention ranking yet; keep it as visible context."
                if enough
                else "Keep revision direction observational until the near-threshold sample is larger."
            ),
        },
        "limitations": [
            "The primary comparison uses one 3-day checkpoint and does not model serial dependence.",
            "Heavy precipitation is a proxy outcome, not observed flood impact.",
            "The 60% near-threshold boundary is exploratory and should be validated out of sample.",
            "Three locations over a short historical window remain a small benchmark.",
        ],
    }
