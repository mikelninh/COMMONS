from __future__ import annotations

from collections import defaultdict
from typing import Any

from commons.attention_rule_lab import LOOSE_FACTOR, group_paths, threshold_by_point
from commons.hypothesis_lab import POINTS, build_records


def build_attention_cases(
    *,
    start_date: str = "2026-07-01",
    end_date: str = "2026-09-05",
    limit: int = 12,
) -> dict[str, Any]:
    records, source_errors = build_records(
        start_date=start_date,
        end_date=end_date,
        points=POINTS[:3],
    )
    paths = group_paths(records)
    thresholds = threshold_by_point(paths)
    point_names = {point.id: (point.name, point.country) for point in POINTS}

    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for path in paths:
        threshold = thresholds[path["point_id"]]
        current = float(path["council"][3])
        older = float(path["council"][5])
        ratio = current / threshold if threshold else 0.0
        revision = int(path["revision_5_to_3"])

        alert = current >= threshold
        watch = alert or (current >= LOOSE_FACTOR * threshold and revision > 0)
        heavy = float(path["actual_mm"]) >= threshold

        state = "alert" if alert else "watch" if watch else "quiet"
        truth = "heavy" if heavy else "not_heavy"
        bucket = f"{state}_{truth}"

        name, country = point_names.get(path["point_id"], (path["point_id"], ""))
        reason = (
            "Council median crossed the heavy-rain threshold."
            if state == "alert"
            else "Sub-threshold rainfall plus an upward majority revision."
            if state == "watch"
            else "No threshold crossing and no validated WATCH condition."
        )

        buckets[bucket].append(
            {
                "id": f'{path["point_id"]}-{path["date"]}',
                "point_id": path["point_id"],
                "point_name": name,
                "country": country,
                "date": path["date"],
                "checkpoint": "T-3 days",
                "raw": {
                    "council_5d_mm": round(older, 2),
                    "council_3d_mm": round(current, 2),
                    "change_mm": round(current - older, 2),
                    "heavy_threshold_mm": round(threshold, 2),
                    "threshold_ratio": round(ratio, 3),
                    "revision_direction": revision,
                },
                "commons": {
                    "state": state,
                    "reason": reason,
                },
                "truth": {
                    "actual_mm": round(float(path["actual_mm"]), 2),
                    "heavy_event": heavy,
                },
                "_difficulty": abs(ratio - 1.0),
            }
        )

    # Prefer boundary cases, because these are where attention architecture matters.
    for items in buckets.values():
        items.sort(key=lambda item: (item["_difficulty"], item["date"]))

    preferred = [
        "alert_heavy",
        "alert_not_heavy",
        "watch_heavy",
        "watch_not_heavy",
        "quiet_heavy",
        "quiet_not_heavy",
    ]

    selected: list[dict[str, Any]] = []
    for bucket in preferred:
        selected.extend(buckets.get(bucket, [])[:2])

    if len(selected) < limit:
        chosen = {item["id"] for item in selected}
        leftovers = [
            item
            for bucket in preferred
            for item in buckets.get(bucket, [])[2:]
            if item["id"] not in chosen
        ]
        leftovers.sort(key=lambda item: (item["_difficulty"], item["date"]))
        selected.extend(leftovers[: max(0, limit - len(selected))])

    selected = selected[:limit]
    for item in selected:
        item.pop("_difficulty", None)

    counts = defaultdict(int)
    for item in selected:
        counts[item["commons"]["state"]] += 1
        counts["heavy" if item["truth"]["heavy_event"] else "not_heavy"] += 1

    return {
        "schema_version": "0.1",
        "hypothesis": {
            "id": "H16",
            "claim": "A low-cost WATCH layer reduces analyst monitoring time without creating perceived noise.",
        },
        "period": {"start": start_date, "end": end_date},
        "checkpoint": "3 days before outcome",
        "verification": "ERA5 daily precipitation against each location's 90th-percentile heavy-rain threshold.",
        "source_errors": source_errors,
        "case_count": len(selected),
        "case_mix": dict(counts),
        "cases": selected,
        "measurement": {
            "primary": "important changes correctly understood per minute of human attention",
            "secondary": [
                "decision time",
                "heavy-event recall",
                "false-open rate",
                "open precision",
                "perceived noise",
            ],
            "design": "within-person randomized comparison: raw signals vs COMMONS triage",
        },
        "limitations": [
            "This is an attention benchmark, not an emergency-warning validation.",
            "The cases are selected from three locations and a short historical window.",
            "Repeated exposure to the benchmark can create learning effects.",
            "A single participant session is exploratory; aggregate sessions are needed before updating H16.",
        ],
    }
