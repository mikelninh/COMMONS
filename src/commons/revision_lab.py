from __future__ import annotations

from collections import defaultdict
from statistics import mean, median
from typing import Any

from commons.hypothesis_lab import POINTS, build_records


MEANINGFUL_DELTA_MM = 1.0


def sign(value: float, threshold: float = 0.0) -> int:
    if value > threshold:
        return 1
    if value < -threshold:
        return -1
    return 0


def council_for(record: dict[str, Any]) -> float:
    return float(record["council_median_mm"])


def group_revision_paths(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[int, dict[str, Any]]] = defaultdict(dict)
    for record in records:
        grouped[(record["point_id"], record["date"])][int(record["lead_days"])] = record

    paths: list[dict[str, Any]] = []
    for (point_id, day), by_lead in grouped.items():
        if not all(lead in by_lead for lead in (1, 3, 5)):
            continue

        r1, r3, r5 = by_lead[1], by_lead[3], by_lead[5]
        c1, c3, c5 = council_for(r1), council_for(r3), council_for(r5)
        actual = float(r1["actual_precip_mm"])

        common_models = (
            set(r1["predictions_mm"])
            & set(r3["predictions_mm"])
            & set(r5["predictions_mm"])
        )
        if len(common_models) < 2:
            continue

        model_revision_53 = {
            model: float(r3["predictions_mm"][model]) - float(r5["predictions_mm"][model])
            for model in common_models
        }
        model_revision_31 = {
            model: float(r1["predictions_mm"][model]) - float(r3["predictions_mm"][model])
            for model in common_models
        }

        d53 = c3 - c5
        d31 = c1 - c3
        direction_53 = sign(d53, MEANINGFUL_DELTA_MM)
        direction_31 = sign(d31, MEANINGFUL_DELTA_MM)
        persistent = direction_53 != 0 and direction_53 == direction_31

        one_off = (
            direction_53 == 0 and direction_31 != 0
        )
        reversal = (
            direction_53 != 0 and direction_31 != 0 and direction_53 != direction_31
        )

        provider_dirs_31 = {
            model: sign(delta, MEANINGFUL_DELTA_MM)
            for model, delta in model_revision_31.items()
        }
        up = sum(direction == 1 for direction in provider_dirs_31.values())
        down = sum(direction == -1 for direction in provider_dirs_31.values())
        majority_direction = 1 if up >= 2 else -1 if down >= 2 else 0
        majority_count = max(up, down)

        needed_from_3 = sign(actual - c3, MEANINGFUL_DELTA_MM)
        needed_from_5 = sign(actual - c5, MEANINGFUL_DELTA_MM)

        paths.append(
            {
                "point_id": point_id,
                "date": day,
                "actual_mm": actual,
                "council_5d_mm": c5,
                "council_3d_mm": c3,
                "council_1d_mm": c1,
                "revision_5_to_3_mm": d53,
                "revision_3_to_1_mm": d31,
                "persistent": persistent,
                "one_off": one_off,
                "reversal": reversal,
                "persistent_direction": direction_31 if persistent else 0,
                "needed_direction_from_5": needed_from_5,
                "needed_direction_from_3": needed_from_3,
                "majority_revision_direction_3_to_1": majority_direction,
                "majority_revision_count": majority_count,
                "model_revision_directions_3_to_1": provider_dirs_31,
                "error_5d_mm": abs(c5 - actual),
                "error_3d_mm": abs(c3 - actual),
                "error_1d_mm": abs(c1 - actual),
                "spread_3d_mm": float(r3["spread_mm"]),
                "relative_spread_3d": float(r3["relative_spread"]),
                "rain_regime": r1["rain_regime"],
            }
        )
    return paths


def rate(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return numerator / denominator


def summarize_revision_paths(paths: list[dict[str, Any]]) -> dict[str, Any]:
    persistent = [path for path in paths if path["persistent"]]
    one_off = [path for path in paths if path["one_off"]]
    reversal = [path for path in paths if path["reversal"]]

    persistent_direction_hits = [
        path
        for path in persistent
        if path["needed_direction_from_5"] != 0
        and path["persistent_direction"] == path["needed_direction_from_5"]
    ]
    persistent_improvements = [
        path for path in persistent if path["error_1d_mm"] < path["error_5d_mm"]
    ]

    one_off_direction_hits = [
        path
        for path in one_off
        if path["needed_direction_from_3"] != 0
        and path["majority_revision_direction_3_to_1"] == path["needed_direction_from_3"]
    ]
    one_off_improvements = [
        path for path in one_off if path["error_1d_mm"] < path["error_3d_mm"]
    ]

    majority = [
        path
        for path in paths
        if path["majority_revision_direction_3_to_1"] != 0
        and path["needed_direction_from_3"] != 0
    ]
    majority_hits = [
        path
        for path in majority
        if path["majority_revision_direction_3_to_1"] == path["needed_direction_from_3"]
    ]
    majority_improvements = [
        path for path in majority if path["error_1d_mm"] < path["error_3d_mm"]
    ]

    strong_majority = [path for path in majority if path["majority_revision_count"] >= 3]
    strong_majority_hits = [
        path
        for path in strong_majority
        if path["majority_revision_direction_3_to_1"] == path["needed_direction_from_3"]
    ]

    no_majority = [
        path
        for path in paths
        if path["majority_revision_direction_3_to_1"] == 0
    ]

    # Compare direction agreement against raw spread as a change signal:
    # high spread should not be promoted unless it meaningfully predicts 3d error.
    ordered_spread = sorted(path["relative_spread_3d"] for path in paths)
    q75 = (
        ordered_spread[round((len(ordered_spread) - 1) * 0.75)]
        if ordered_spread
        else None
    )
    high_spread = (
        [path for path in paths if q75 is not None and path["relative_spread_3d"] >= q75]
        if q75 is not None
        else []
    )
    all_error = mean(path["error_3d_mm"] for path in paths) if paths else None
    high_spread_error = mean(path["error_3d_mm"] for path in high_spread) if high_spread else None

    by_regime: dict[str, Any] = {}
    for regime in ("dry", "moderate", "heavy"):
        subset = [path for path in majority if path["rain_regime"] == regime]
        hits = [
            path
            for path in subset
            if path["majority_revision_direction_3_to_1"] == path["needed_direction_from_3"]
        ]
        by_regime[regime] = {
            "samples": len(subset),
            "direction_accuracy": round(rate(len(hits), len(subset)), 4)
            if subset
            else None,
        }

    persistent_direction_accuracy = rate(
        len(persistent_direction_hits),
        len([p for p in persistent if p["needed_direction_from_5"] != 0]),
    )
    persistent_improvement_rate = rate(len(persistent_improvements), len(persistent))
    one_off_direction_accuracy = rate(
        len(one_off_direction_hits),
        len(
            [
                p
                for p in one_off
                if p["needed_direction_from_3"] != 0
                and p["majority_revision_direction_3_to_1"] != 0
            ]
        ),
    )
    one_off_improvement_rate = rate(len(one_off_improvements), len(one_off))
    majority_direction_accuracy = rate(len(majority_hits), len(majority))
    majority_improvement_rate = rate(len(majority_improvements), len(majority))
    unanimous_direction_accuracy = rate(len(strong_majority_hits), len(strong_majority))

    return {
        "paths": len(paths),
        "persistent_cases": len(persistent),
        "one_off_cases": len(one_off),
        "reversal_cases": len(reversal),
        "persistent_direction_accuracy": (
            round(persistent_direction_accuracy, 4)
            if persistent_direction_accuracy is not None
            else None
        ),
        "persistent_error_improvement_rate": (
            round(persistent_improvement_rate, 4)
            if persistent_improvement_rate is not None
            else None
        ),
        "one_off_direction_accuracy": (
            round(one_off_direction_accuracy, 4)
            if one_off_direction_accuracy is not None
            else None
        ),
        "one_off_error_improvement_rate": (
            round(one_off_improvement_rate, 4)
            if one_off_improvement_rate is not None
            else None
        ),
        "majority_revision_cases": len(majority),
        "majority_direction_accuracy": (
            round(majority_direction_accuracy, 4)
            if majority_direction_accuracy is not None
            else None
        ),
        "majority_error_improvement_rate": (
            round(majority_improvement_rate, 4)
            if majority_improvement_rate is not None
            else None
        ),
        "unanimous_revision_cases": len(strong_majority),
        "unanimous_direction_accuracy": (
            round(unanimous_direction_accuracy, 4)
            if unanimous_direction_accuracy is not None
            else None
        ),
        "no_majority_cases": len(no_majority),
        "direction_accuracy_by_rain_regime": by_regime,
        "high_spread_q75": round(q75, 4) if q75 is not None else None,
        "all_3d_mae_mm": round(all_error, 3) if all_error is not None else None,
        "high_spread_3d_mae_mm": (
            round(high_spread_error, 3) if high_spread_error is not None else None
        ),
    }


def evaluate_revision_hypotheses(summary: dict[str, Any]) -> list[dict[str, Any]]:
    p_acc = summary.get("persistent_direction_accuracy")
    p_improve = summary.get("persistent_error_improvement_rate")
    o_acc = summary.get("one_off_direction_accuracy")
    o_improve = summary.get("one_off_error_improvement_rate")

    h8_supported = (
        p_acc is not None
        and p_improve is not None
        and o_acc is not None
        and o_improve is not None
        and p_acc >= o_acc + 0.05
        and p_improve >= o_improve + 0.05
    )

    majority_acc = summary.get("majority_direction_accuracy")
    majority_improve = summary.get("majority_error_improvement_rate")
    h9_supported = (
        majority_acc is not None
        and majority_improve is not None
        and majority_acc >= 0.60
        and majority_improve >= 0.55
    )

    return [
        {
            "id": "H8",
            "claim": "A revision sustained across multiple lead checkpoints is more useful than a one-off late jump.",
            "status": (
                "supported"
                if h8_supported
                else "not_supported"
                if None not in (p_acc, p_improve, o_acc, o_improve)
                else "insufficient"
            ),
            "effect": (
                f"persistent direction {p_acc:.1%}, improvement {p_improve:.1%}; "
                f"one-off direction {o_acc:.1%}, improvement {o_improve:.1%}"
                if None not in (p_acc, p_improve, o_acc, o_improve)
                else None
            ),
            "product_update": (
                "Promote sustained multi-checkpoint revisions as a material-change signal."
                if h8_supported
                else "Do not privilege persistence over a single revision yet."
            ),
        },
        {
            "id": "H9",
            "claim": "When at least 2 of 3 models revise in the same direction, that direction is useful for what-changed alerts.",
            "status": (
                "supported"
                if h9_supported
                else "not_supported"
                if majority_acc is not None and majority_improve is not None
                else "insufficient"
            ),
            "effect": (
                f"direction accuracy {majority_acc:.1%}; next-checkpoint error improved {majority_improve:.1%}"
                if majority_acc is not None and majority_improve is not None
                else None
            ),
            "product_update": (
                'Surface "2/3 models revised upward/downward" as a directional change signal.'
                if h9_supported
                else "Keep model revision direction in the Lab only for now."
            ),
        },
    ]


def run_revision_backtest(
    *,
    start_date: str = "2026-07-01",
    end_date: str = "2026-09-05",
) -> dict[str, Any]:
    records, source_errors = build_records(
        start_date=start_date,
        end_date=end_date,
        points=POINTS[:3],
    )
    paths = group_revision_paths(records)
    summary = summarize_revision_paths(paths)
    hypotheses = evaluate_revision_hypotheses(summary)
    return {
        "schema_version": "0.1",
        "period": {"start": start_date, "end": end_date},
        "points": [point.id for point in POINTS[:3]],
        "verification": "ERA5 daily precipitation",
        "meaningful_revision_threshold_mm": MEANINGFUL_DELTA_MM,
        "source_errors": source_errors,
        "summary": summary,
        "hypotheses": hypotheses,
        "limitations": [
            "Lead-5, lead-3 and lead-1 checkpoints are proxies for persistent revision, not consecutive six-hour runs.",
            "Daily precipitation can be highly skewed and location-specific.",
            "ERA5 is reanalysis rather than a local rain gauge.",
            "A useful revision signal for precipitation is not automatically a useful flood-impact alert.",
        ],
    }
