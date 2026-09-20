from __future__ import annotations

from collections import defaultdict
from math import ceil
from statistics import median
from typing import Any

from commons.hypothesis_lab import MODELS, POINTS, build_records, quantile


BUDGETS = (0.10, 0.20, 0.30)
HEAVY_QUANTILE = 0.90


def _top_ids(rows: list[dict[str, Any]], score_key: str, budget: float) -> set[str]:
    count = max(1, ceil(len(rows) * budget))
    ranked = sorted(rows, key=lambda row: row[score_key], reverse=True)
    return {row["id"] for row in ranked[:count]}


def _catch_count(
    rows: list[dict[str, Any]],
    score_key: str,
    budget: float,
) -> int:
    selected = _top_ids(rows, score_key, budget)
    return sum(1 for row in rows if row["id"] in selected and row["heavy"])


def _thresholds_from_training(
    records: list[dict[str, Any]],
    *,
    train_start: str,
    train_end: str,
) -> dict[str, float]:
    grouped: dict[str, list[float]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()

    for record in records:
        if int(record["lead_days"]) != 3:
            continue
        if not (train_start <= record["date"] <= train_end):
            continue
        key = (record["point_id"], record["date"])
        if key in seen:
            continue
        seen.add(key)
        grouped[record["point_id"]].append(float(record["actual_precip_mm"]))

    return {
        point_id: float(quantile(values, HEAVY_QUANTILE))
        for point_id, values in grouped.items()
        if values
    }


def run_model_dropout_backtest(
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
    thresholds = _thresholds_from_training(
        records,
        train_start=train_start,
        train_end=train_end,
    )

    rows: list[dict[str, Any]] = []
    incomplete_test_records = 0

    for record in records:
        if int(record["lead_days"]) != 3:
            continue
        if not (test_start <= record["date"] <= test_end):
            continue

        predictions = record.get("predictions_mm") or {}
        if len(predictions) != len(MODELS):
            incomplete_test_records += 1
            continue

        threshold = thresholds.get(record["point_id"])
        if not threshold:
            continue

        all_values = [float(predictions[provider]) for provider in MODELS]
        row: dict[str, Any] = {
            "id": f'{record["point_id"]}-{record["date"]}',
            "point_id": record["point_id"],
            "date": record["date"],
            "heavy": float(record["actual_precip_mm"]) >= threshold,
            "full": median(all_values) / threshold,
        }

        for dropped in MODELS:
            remaining = [
                float(value)
                for provider, value in predictions.items()
                if provider != dropped
            ]
            row[f"drop_{dropped}"] = median(remaining) / threshold

        rows.append(row)

    heavy_events = sum(1 for row in rows if row["heavy"])
    dropout_results: dict[str, Any] = {}
    retention_values: list[float] = []
    alert_agreements: list[float] = []
    catch_losses: list[int] = []

    for dropped in MODELS:
        score_key = f"drop_{dropped}"
        alert_matches = sum(
            1
            for row in rows
            if (row["full"] >= 1.0) == (row[score_key] >= 1.0)
        )
        alert_agreement = alert_matches / len(rows) if rows else None
        if alert_agreement is not None:
            alert_agreements.append(alert_agreement)

        budget_results: dict[str, Any] = {}
        for budget in BUDGETS:
            full_top = _top_ids(rows, "full", budget)
            dropout_top = _top_ids(rows, score_key, budget)
            retained = len(full_top & dropout_top) / len(full_top) if full_top else None

            full_catches = _catch_count(rows, "full", budget)
            dropout_catches = _catch_count(rows, score_key, budget)
            catch_loss = full_catches - dropout_catches

            if retained is not None:
                retention_values.append(retained)
            catch_losses.append(catch_loss)

            budget_results[f"{int(budget * 100)}pct"] = {
                "review_count": len(full_top),
                "top_k_retention": round(retained, 4) if retained is not None else None,
                "full_catches": full_catches,
                "dropout_catches": dropout_catches,
                "catch_loss": catch_loss,
            }

        dropout_results[dropped] = {
            "alert_agreement": (
                round(alert_agreement, 4) if alert_agreement is not None else None
            ),
            "budgets": budget_results,
        }

    min_retention = min(retention_values) if retention_values else None
    mean_retention = (
        sum(retention_values) / len(retention_values) if retention_values else None
    )
    min_alert_agreement = min(alert_agreements) if alert_agreements else None
    max_catch_loss = max(catch_losses) if catch_losses else None

    enough = len(rows) >= 60 and heavy_events >= 6 and not source_errors
    supported = (
        enough
        and min_retention is not None
        and min_retention >= 0.80
        and min_alert_agreement is not None
        and min_alert_agreement >= 0.90
        and max_catch_loss is not None
        and max_catch_loss <= 1
    )
    rejected = (
        enough
        and (
            (min_retention is not None and min_retention < 0.60)
            or (max_catch_loss is not None and max_catch_loss >= 2)
        )
    )
    status = (
        "supported"
        if supported
        else "not_supported"
        if rejected
        else "mixed"
        if enough
        else "insufficient"
    )

    if status == "supported":
        update = (
            "Allow two-model graceful degradation for queue ranking, but visibly mark "
            "source degradation and keep evidence-health checks active."
        )
    elif status == "not_supported":
        update = (
            "Do not trust the attention queue when a council member disappears; "
            "degrade to context-only until the full council returns."
        )
    else:
        update = (
            "Keep model-dropout behavior observational. Do not change production "
            "attention rules until the stress test has enough complete holdout events."
        )

    return {
        "schema_version": "0.1",
        "train_period": {"start": train_start, "end": train_end},
        "test_period": {"start": test_start, "end": test_end},
        "models": list(MODELS),
        "test_cases": len(rows),
        "heavy_events": heavy_events,
        "incomplete_test_records": incomplete_test_records,
        "source_errors": source_errors,
        "dropouts": dropout_results,
        "summary": {
            "min_top_k_retention": (
                round(min_retention, 4) if min_retention is not None else None
            ),
            "mean_top_k_retention": (
                round(mean_retention, 4) if mean_retention is not None else None
            ),
            "min_alert_agreement": (
                round(min_alert_agreement, 4)
                if min_alert_agreement is not None
                else None
            ),
            "max_heavy_event_catch_loss": max_catch_loss,
        },
        "hypothesis": {
            "id": "H19",
            "claim": (
                "COMMONS attention ranking remains materially stable when any one "
                "forecast model is unavailable."
            ),
            "status": status,
            "effect": (
                f"min top-k retention "
                f"{round(min_retention, 4) if min_retention is not None else None}; "
                f"min alert agreement "
                f"{round(min_alert_agreement, 4) if min_alert_agreement is not None else None}; "
                f"max heavy-event catch loss {max_catch_loss}; "
                f"n={len(rows)}, heavy={heavy_events}"
            ),
            "product_update": update,
        },
        "limitations": [
            "This simulates single-model dropout using cases where all three models were originally available.",
            "The stress test covers precipitation ranking, not river impact or emergency-warning performance.",
            "Only three monitored locations and one temporal holdout are represented.",
            "Source outages in the underlying data pull make this run insufficient rather than evidence against robustness.",
        ],
    }
