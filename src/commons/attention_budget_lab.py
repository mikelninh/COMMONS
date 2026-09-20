from __future__ import annotations

from collections import defaultdict
from math import ceil, log2
from typing import Any

from commons.attention_rule_lab import LOOSE_FACTOR, group_paths, threshold_by_point
from commons.hypothesis_lab import POINTS, build_records


BUDGETS = (0.10, 0.20, 0.30)


def _average_precision(rows: list[dict[str, Any]]) -> float | None:
    positives = sum(1 for row in rows if row["heavy"])
    if not positives:
        return None
    hits = 0
    total = 0.0
    for rank, row in enumerate(rows, start=1):
        if not row["heavy"]:
            continue
        hits += 1
        total += hits / rank
    return total / positives


def _ndcg(rows: list[dict[str, Any]]) -> float | None:
    positives = sum(1 for row in rows if row["heavy"])
    if not positives:
        return None
    dcg = sum(
        1.0 / log2(rank + 1)
        for rank, row in enumerate(rows, start=1)
        if row["heavy"]
    )
    ideal = sum(1.0 / log2(rank + 1) for rank in range(1, positives + 1))
    return dcg / ideal if ideal else None


def _rank(rows: list[dict[str, Any]], strategy: str) -> list[dict[str, Any]]:
    if strategy == "threshold":
        return sorted(rows, key=lambda row: row["ratio"], reverse=True)

    if strategy == "revision_priority":
        def key(row: dict[str, Any]) -> tuple[int, float]:
            if row["ratio"] >= 1.0:
                tier = 2
            elif row["ratio"] >= LOOSE_FACTOR and row["revision_up"]:
                tier = 1
            else:
                tier = 0
            return tier, row["ratio"]

        return sorted(rows, key=key, reverse=True)

    raise ValueError(f"unknown strategy: {strategy}")


def _budget_metrics(
    ranked: list[dict[str, Any]],
    *,
    heavy_total: int,
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for budget in BUDGETS:
        reviews = max(1, ceil(len(ranked) * budget))
        selected = ranked[:reviews]
        catches = sum(1 for row in selected if row["heavy"])
        precision = catches / reviews if reviews else None
        recall = catches / heavy_total if heavy_total else None
        out[f"{int(budget * 100)}pct"] = {
            "reviews": reviews,
            "catches": catches,
            "precision": round(precision, 4) if precision is not None else None,
            "recall": round(recall, 4) if recall is not None else None,
            "reviews_per_catch": round(reviews / catches, 3) if catches else None,
        }
    return out


def run_attention_budget_backtest(
    *,
    train_start: str = "2026-07-01",
    train_end: str = "2026-08-10",
    test_start: str = "2026-08-11",
    test_end: str = "2026-09-10",
) -> dict[str, Any]:
    records, source_errors = build_records(
        start_date=train_start,
        end_date=test_end,
        points=POINTS[:3],
    )
    paths = group_paths(records)

    train_paths = [path for path in paths if train_start <= path["date"] <= train_end]
    test_paths = [path for path in paths if test_start <= path["date"] <= test_end]
    thresholds = threshold_by_point(train_paths)

    rows: list[dict[str, Any]] = []
    for path in test_paths:
        threshold = thresholds.get(path["point_id"])
        if not threshold:
            continue
        council = float(path["council"][3])
        ratio = council / threshold
        rows.append(
            {
                "point_id": path["point_id"],
                "date": path["date"],
                "ratio": ratio,
                "revision_up": int(path["revision_5_to_3"]) > 0,
                "heavy": float(path["actual_mm"]) >= threshold,
            }
        )

    heavy_total = sum(1 for row in rows if row["heavy"])
    threshold_ranked = _rank(rows, "threshold")
    revision_ranked = _rank(rows, "revision_priority")

    threshold_metrics = _budget_metrics(threshold_ranked, heavy_total=heavy_total)
    revision_metrics = _budget_metrics(revision_ranked, heavy_total=heavy_total)

    comparisons: dict[str, Any] = {}
    improved = 0
    worse = 0
    for budget in BUDGETS:
        key = f"{int(budget * 100)}pct"
        base = threshold_metrics[key]
        revised = revision_metrics[key]
        catch_gain = revised["catches"] - base["catches"]
        precision_gain = (
            revised["precision"] - base["precision"]
            if revised["precision"] is not None and base["precision"] is not None
            else None
        )
        if catch_gain > 0:
            improved += 1
        elif catch_gain < 0:
            worse += 1
        comparisons[key] = {
            "catch_gain": catch_gain,
            "precision_gain": (
                round(precision_gain, 4) if precision_gain is not None else None
            ),
        }

    base_ap = _average_precision(threshold_ranked)
    revised_ap = _average_precision(revision_ranked)
    base_ndcg = _ndcg(threshold_ranked)
    revised_ndcg = _ndcg(revision_ranked)
    ap_gain = (
        revised_ap - base_ap
        if revised_ap is not None and base_ap is not None
        else None
    )
    ndcg_gain = (
        revised_ndcg - base_ndcg
        if revised_ndcg is not None and base_ndcg is not None
        else None
    )

    enough = len(rows) >= 60 and heavy_total >= 6
    supported = enough and improved >= 2 and worse == 0 and (ap_gain or 0) >= 0
    not_supported = enough and worse >= 2
    status = (
        "supported"
        if supported
        else "not_supported"
        if not_supported
        else "mixed"
        if enough
        else "insufficient"
    )

    if status == "supported":
        update = (
            "Rank review queues ALERT first, then upward-revision near-threshold "
            "candidates, then remaining cases by threshold proximity."
        )
    elif status == "mixed":
        update = (
            "Use upward revision only as a secondary tie-breaker until a broader "
            "holdout shows consistent gains across attention budgets."
        )
    else:
        update = (
            "Keep threshold proximity as the primary queue ranking; revision direction "
            "does not yet earn priority."
        )

    return {
        "schema_version": "0.1",
        "train_period": {"start": train_start, "end": train_end},
        "test_period": {"start": test_start, "end": test_end},
        "verification": "ERA5 heavy-rain event using thresholds learned only from the training period.",
        "test_cases": len(rows),
        "heavy_events": heavy_total,
        "source_errors": source_errors,
        "near_threshold_factor": LOOSE_FACTOR,
        "strategies": {
            "threshold_proximity": {
                "average_precision": round(base_ap, 4) if base_ap is not None else None,
                "ndcg": round(base_ndcg, 4) if base_ndcg is not None else None,
                "budgets": threshold_metrics,
            },
            "revision_priority": {
                "average_precision": round(revised_ap, 4) if revised_ap is not None else None,
                "ndcg": round(revised_ndcg, 4) if revised_ndcg is not None else None,
                "budgets": revision_metrics,
            },
        },
        "comparison": {
            "average_precision_gain": round(ap_gain, 4) if ap_gain is not None else None,
            "ndcg_gain": round(ndcg_gain, 4) if ndcg_gain is not None else None,
            "improved_budgets": improved,
            "worse_budgets": worse,
            "by_budget": comparisons,
        },
        "hypothesis": {
            "id": "H18",
            "claim": "Under a fixed human review budget, prioritizing upward-revision near-threshold cases catches more heavy events than threshold proximity alone.",
            "status": status,
            "effect": (
                f"improved budgets {improved}/{len(BUDGETS)}; worse {worse}; "
                f"AP gain {round(ap_gain, 4) if ap_gain is not None else None}; "
                f"NDCG gain {round(ndcg_gain, 4) if ndcg_gain is not None else None}"
            ),
            "product_update": update,
        },
        "limitations": [
            "The ranking rule was motivated by adjacent historical data, so this is a temporal holdout rather than a fully independent external validation.",
            "Only three monitored locations are represented.",
            "Heavy precipitation is a proxy outcome, not human impact or flood damage.",
            "The near-threshold boundary remains exploratory and should be learned without test-set tuning.",
        ],
    }
