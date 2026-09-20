from __future__ import annotations

from statistics import mean
from typing import Any

from commons.attention_rule_lab import (
    first_alert_lead,
    group_paths,
    threshold_by_point,
)
from commons.hypothesis_lab import POINTS, build_records


def run_watch_alert_backtest(
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

    heavy_events = 0
    alert_heavy = 0
    watch_heavy = 0
    watch_only_signals = 0
    watch_only_true = 0
    earlier_watch_advantages: list[int] = []

    for path in paths:
        threshold = thresholds[path["point_id"]]
        heavy = path["actual_mm"] >= threshold
        if heavy:
            heavy_events += 1

        alert_lead = first_alert_lead(path, threshold, policy="strict")
        watch_lead = first_alert_lead(path, threshold, policy="revision_aware")

        if heavy and alert_lead is not None:
            alert_heavy += 1
        if heavy and watch_lead is not None:
            watch_heavy += 1

        if watch_lead is not None and alert_lead is None:
            watch_only_signals += 1
            if heavy:
                watch_only_true += 1

        if (
            heavy
            and watch_lead is not None
            and alert_lead is not None
            and watch_lead > alert_lead
        ):
            earlier_watch_advantages.append(watch_lead - alert_lead)

    alert_recall = alert_heavy / heavy_events if heavy_events else None
    watch_recall = watch_heavy / heavy_events if heavy_events else None
    extra_recall = (
        watch_recall - alert_recall
        if alert_recall is not None and watch_recall is not None
        else None
    )
    watch_only_precision = (
        watch_only_true / watch_only_signals if watch_only_signals else None
    )
    watch_burden_per_100_days = (
        100 * watch_only_signals / len(paths) if paths else None
    )
    mean_earlier_watch_days = (
        mean(earlier_watch_advantages) if earlier_watch_advantages else 0.0
    )

    supported = (
        extra_recall is not None
        and extra_recall >= 0.03
        and watch_only_precision is not None
        and watch_only_precision >= 0.20
        and watch_burden_per_100_days is not None
        and watch_burden_per_100_days <= 3.0
    )

    return {
        "schema_version":"0.1",
        "period":{"start":start_date,"end":end_date},
        "paths":len(paths),
        "heavy_events":heavy_events,
        "source_errors":source_errors,
        "alert_recall":round(alert_recall,4) if alert_recall is not None else None,
        "watch_recall":round(watch_recall,4) if watch_recall is not None else None,
        "extra_recall":round(extra_recall,4) if extra_recall is not None else None,
        "watch_only_signals":watch_only_signals,
        "watch_only_true":watch_only_true,
        "watch_only_precision":(
            round(watch_only_precision,4) if watch_only_precision is not None else None
        ),
        "watch_burden_per_100_days":(
            round(watch_burden_per_100_days,2)
            if watch_burden_per_100_days is not None
            else None
        ),
        "mean_earlier_watch_days":round(mean_earlier_watch_days,3),
        "hypothesis":{
            "id":"H15",
            "claim":"Separating WATCH from ALERT gains useful recall without materially increasing interruption burden.",
            "status":"supported" if supported else "not_supported",
            "product_update":(
                "Use a two-tier attention model: WATCH for revision-aware context, ALERT for strict threshold crossing."
                if supported
                else "Do not add a separate WATCH tier yet."
            ),
        },
        "limitations":[
            "WATCH is evaluated as a low-cost state; this does not measure human annoyance directly.",
            "The benchmark covers heavy precipitation, not flood damage.",
            "Three locations over roughly two months remain a small sample.",
        ],
    }
