from __future__ import annotations

from typing import Any

from commons.world_model import _clean


METRICS = (
    ("precip_72h_mm", "precip_abs_error_mm"),
    ("temp_max_72h_c", "temp_abs_error_c"),
    ("gust_max_72h_kmh", "gust_abs_error_kmh"),
)


def score_forecast(values: dict[str, Any], observed: dict[str, Any]) -> dict[str, Any]:
    scored: dict[str, Any] = {}
    errors: list[float] = []
    for prediction_key, error_key in METRICS:
        predicted = values.get(prediction_key)
        actual = observed.get(prediction_key)
        if predicted is None or actual is None:
            scored[error_key] = None
            continue
        error = abs(float(predicted) - float(actual))
        scored[error_key] = round(error, 2)
        errors.append(error)
    scored["mean_absolute_error_across_available_metrics"] = (
        round(sum(errors) / len(errors), 2) if errors else None
    )
    return scored


def score_loop_snapshot(
    loop_snapshot: dict[str, Any],
    observed: dict[str, Any],
) -> dict[str, Any]:
    council = loop_snapshot.get("forecast_council") or {}
    members = []
    for member in council.get("members") or []:
        members.append(
            {
                "provider": member["provider"],
                "label": member["label"],
                **score_forecast(member, observed),
            }
        )

    consensus = council.get("consensus") or {}
    consensus_values = {
        "precip_72h_mm": consensus.get("precip_72h_mm_median"),
        "temp_max_72h_c": consensus.get("temp_max_72h_c_median"),
        "gust_max_72h_kmh": consensus.get("gust_max_72h_kmh_median"),
    }
    return {
        "loop_id": loop_snapshot.get("id"),
        "members": members,
        "consensus": score_forecast(consensus_values, observed),
        "observed": observed,
        "note": (
            "These are deterministic absolute-error diagnostics. "
            "They are not probabilistic calibration scores."
        ),
    }


def summarize_scores(backtests: list[dict[str, Any]]) -> dict[str, Any]:
    provider_errors: dict[str, list[float]] = {}
    consensus_errors: list[float] = []
    for result in backtests:
        for member in result.get("members") or []:
            value = member.get("mean_absolute_error_across_available_metrics")
            if value is not None:
                provider_errors.setdefault(member["provider"], []).append(float(value))
        value = (result.get("consensus") or {}).get(
            "mean_absolute_error_across_available_metrics"
        )
        if value is not None:
            consensus_errors.append(float(value))

    return {
        "providers": {
            provider: round(sum(values) / len(values), 2)
            for provider, values in provider_errors.items()
            if values
        },
        "consensus": (
            round(sum(consensus_errors) / len(consensus_errors), 2)
            if consensus_errors
            else None
        ),
        "events_scored": len(backtests),
    }
