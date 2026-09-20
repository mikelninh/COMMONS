from __future__ import annotations

from datetime import datetime
from typing import Any


VALIDATED_MONITORS: tuple[dict[str, str], ...] = (
    {
        "point_id": "nuwakot",
        "loop_id": "water-rises",
        "name": "Nuwakot",
        "country": "Nepal",
        "signal": "peak daily rainfall · next 72h",
    },
    {
        "point_id": "manila",
        "loop_id": "storm-arrives",
        "name": "Manila",
        "country": "Philippines",
        "signal": "peak daily rainfall · next 72h",
    },
    {
        "point_id": "delhi",
        "loop_id": "heat-we-cannot-see",
        "name": "Delhi",
        "country": "India",
        "signal": "peak daily rainfall · next 72h",
    },
)

STATE_ORDER = {"alert": 0, "priority": 1, "quiet": 2, "unavailable": 3}
PRIORITY_RATIO = 0.80
REVISION_MM = 0.50


def _loop_map(snapshot: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not snapshot:
        return {}
    return {
        str(loop.get("id")): loop
        for loop in snapshot.get("loops") or []
        if loop.get("id")
    }


def _catalog_map(catalog: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not catalog:
        return {}
    return {
        str(loop.get("id")): loop
        for loop in catalog.get("loops") or []
        if loop.get("id")
    }


def _provider_precip(loop: dict[str, Any] | None) -> dict[str, float]:
    council = (loop or {}).get("forecast_council") or {}
    out: dict[str, float] = {}
    for member in council.get("members") or []:
        provider = member.get("provider")
        raw = member.get("precip_peak_daily_mm")
        if not provider or raw is None:
            continue
        try:
            out[str(provider)] = float(raw)
        except (TypeError, ValueError):
            continue
    return out


def _consensus_precip(loop: dict[str, Any] | None) -> float | None:
    council = (loop or {}).get("forecast_council") or {}
    raw = (council.get("consensus") or {}).get("precip_peak_daily_mm_median")
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _consensus_peak_date(loop: dict[str, Any] | None) -> str | None:
    council = (loop or {}).get("forecast_council") or {}
    raw = (council.get("consensus") or {}).get("precip_peak_date")
    return str(raw) if raw else None


def _revision_context(
    previous: dict[str, Any] | None,
    current: dict[str, Any] | None,
) -> dict[str, Any]:
    old = _provider_precip(previous)
    new = _provider_precip(current)
    providers = sorted(set(old) & set(new))
    deltas = {provider: new[provider] - old[provider] for provider in providers}

    up = sum(delta > REVISION_MM for delta in deltas.values())
    down = sum(delta < -REVISION_MM for delta in deltas.values())
    direction = "up" if up >= 2 else "down" if down >= 2 else "mixed"
    supporters = max(up, down) if direction != "mixed" else 0

    old_median = _consensus_precip(previous)
    new_median = _consensus_precip(current)
    median_delta = (
        new_median - old_median
        if old_median is not None and new_median is not None
        else None
    )

    return {
        "direction": direction,
        "supporting_models": supporters,
        "models_compared": len(providers),
        "median_delta_mm": (
            round(median_delta, 1) if median_delta is not None else None
        ),
        "role": "context_only",
        "note": (
            "Six-hour revision context is visible but does not change priority rank."
        ),
    }


def _state_for_ratio(ratio: float | None, model_count: int) -> str:
    if ratio is None or model_count < 2:
        return "unavailable"
    if ratio >= 1.0:
        return "alert"
    if ratio >= PRIORITY_RATIO:
        return "priority"
    return "quiet"


def build_morning_brief(
    snapshot: dict[str, Any],
    *,
    previous_snapshot: dict[str, Any] | None = None,
    attention_report: dict[str, Any] | None = None,
    hypothesis_report: dict[str, Any] | None = None,
    loop_catalog: dict[str, Any] | None = None,
    exposure_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current_loops = _loop_map(snapshot)
    previous_loops = _loop_map(previous_snapshot)
    catalog = _catalog_map(loop_catalog)

    thresholds = (attention_report or {}).get("thresholds_mm") or {}
    exposure_by_point = {
        str((item.get("point") or {}).get("id")): item
        for item in (exposure_report or {}).get("points") or []
        if (item.get("point") or {}).get("id")
    }
    monitored: list[dict[str, Any]] = []

    for monitor in VALIDATED_MONITORS:
        loop_id = monitor["loop_id"]
        loop = current_loops.get(loop_id) or {}
        council = loop.get("forecast_council") or {}
        members = council.get("members") or []
        model_count = len(members)
        current_mm = _consensus_precip(loop)
        peak_date = _consensus_peak_date(loop)

        raw_threshold = thresholds.get(monitor["point_id"])
        try:
            threshold = float(raw_threshold) if raw_threshold is not None else None
        except (TypeError, ValueError):
            threshold = None

        ratio = (
            current_mm / threshold
            if current_mm is not None and threshold not in (None, 0)
            else None
        )
        state = _state_for_ratio(ratio, model_count)
        revision = _revision_context(previous_loops.get(loop_id), loop)
        source_errors = council.get("source_errors") or []

        if state == "alert":
            why = "Forecast council crossed the validated heavy-rain research gate."
            next_step = (
                "Inspect now. Confirm conditions with local official warnings before acting."
            )
        elif state == "priority":
            why = "Forecast rainfall is close to the heavy-rain research gate."
            next_step = "Worth a glance. No interruption is justified by this signal alone."
        elif state == "quiet":
            why = "Forecast rainfall remains below the current priority band."
            next_step = "No review needed from this rainfall monitor."
        else:
            why = "The validated rainfall monitor does not have enough live model data."
            next_step = "Treat this monitor as unavailable until source health recovers."

        flood = loop.get("flood_signal") or {}
        flood_context = None
        if flood.get("status") == "ok":
            flood_context = {
                "historical_percentile": flood.get("historical_percentile"),
                "forecast_peak_date": flood.get("forecast_peak_date"),
                "role": "context_only",
                "note": "River percentile is context, not the rainfall alert gate.",
            }

        exposure = exposure_by_point.get(monitor["point_id"])
        exposure_context = None
        if exposure:
            exposure_context = {
                "population": exposure.get("population"),
                "radius_km": exposure.get("radius_km"),
                "data_year": exposure.get("data_year"),
                "source": exposure.get("data_source") or "WorldPop",
                "role": "context_only",
                "note": "Nearby population is context, not estimated people impacted.",
            }

        monitored.append(
            {
                "point_id": monitor["point_id"],
                "loop_id": loop_id,
                "loop_title": (catalog.get(loop_id) or {}).get("title"),
                "name": monitor["name"],
                "country": monitor["country"],
                "signal": monitor["signal"],
                "state": state,
                "rank_score": round(ratio, 4) if ratio is not None else None,
                "forecast_peak_daily_mm": (
                    round(current_mm, 1) if current_mm is not None else None
                ),
                "forecast_peak_date": peak_date,
                "forecast_72h_mm": (council.get("consensus") or {}).get(
                    "precip_72h_mm_median"
                ),
                "heavy_rain_gate_mm": (
                    round(threshold, 2) if threshold is not None else None
                ),
                "gate_ratio": round(ratio, 4) if ratio is not None else None,
                "models_available": model_count,
                "models_expected": 3,
                "source_errors": source_errors,
                "why": why,
                "next_step": next_step,
                "revision": revision,
                "flood_context": flood_context,
                "exposure_context": exposure_context,
            }
        )

    monitored.sort(
        key=lambda item: (
            STATE_ORDER[item["state"]],
            -(item["rank_score"] if item["rank_score"] is not None else -1),
        )
    )
    for rank, item in enumerate(monitored, start=1):
        item["rank"] = rank

    alerts = sum(item["state"] == "alert" for item in monitored)
    priorities = sum(item["state"] == "priority" for item in monitored)
    quiet = sum(item["state"] == "quiet" for item in monitored)
    unavailable = sum(item["state"] == "unavailable" for item in monitored)

    if alerts:
        headline = (
            f"{alerts} validated rainfall monitor"
            f"{' has' if alerts == 1 else 's have'} crossed the research alert gate."
        )
        close_message = "Inspect the alert first. Everything else can wait."
    elif priorities:
        headline = (
            "Nothing needs to interrupt you. "
            f"{priorities} monitor{' is' if priorities == 1 else 's are'} worth a glance."
        )
        close_message = "No alert. Review the priority queue when you have a moment."
    else:
        headline = "Nothing in the validated rainfall pilot needs your attention right now."
        close_message = "You are caught up."

    quality = (hypothesis_report or {}).get("data_quality") or {}
    evidence_status = str(quality.get("status") or "unknown")
    learning_allowed = evidence_status == "healthy"

    generated_at = snapshot.get("generated_at")
    previous_generated_at = (previous_snapshot or {}).get("generated_at")

    return {
        "schema_version": "0.1",
        "generated_at": generated_at,
        "previous_generated_at": previous_generated_at,
        "product": "COMMONS Morning Brief v1",
        "headline": headline,
        "close_message": close_message,
        "summary": {
            "alerts": alerts,
            "priority": priorities,
            "quiet": quiet,
            "unavailable": unavailable,
            "ranked_monitors": len(VALIDATED_MONITORS),
            "world_model_loops": len((loop_catalog or {}).get("loops") or []),
        },
        "evidence": {
            "status": evidence_status,
            "learning_allowed": learning_allowed,
            "temporal_coverage": quality.get("temporal_coverage"),
            "full_council_ratio": quality.get("full_council_ratio"),
            "note": (
                "Research rules may update from this evidence."
                if learning_allowed
                else "Learning is held until evidence health returns to healthy."
            ),
        },
        "ranking_rule": {
            "primary": "peak daily forecast council median / validated daily heavy-rain gate",
            "alert_gate": "ratio >= 1.00",
            "priority_band": "0.80 <= ratio < 1.00",
            "quiet_band": "ratio < 0.80",
            "revision_role": "visible context only; does not change rank",
            "why": (
                "H18 did not show revision-priority beating threshold proximity "
                "under fixed attention budgets."
            ),
        },
        "monitors": monitored,
        "unranked_loops": [
            {
                "id": loop.get("id"),
                "title": loop.get("title"),
                "coverage": loop.get("coverage"),
            }
            for loop in (loop_catalog or {}).get("loops") or []
            if loop.get("id") not in {m["loop_id"] for m in VALIDATED_MONITORS}
        ],
        "trust_contract": [
            "ALERT means a research threshold crossed; it is not a local emergency warning.",
            "PRIORITY means inspect sooner; it is not a notification tier.",
            "Live rainfall gates compare daily forecast with daily historical threshold; 72h totals are context only.",
            "Revision direction is context only.",
            "Population exposure is context only until impact-labelled validation earns ranking authority.",
            "Only validated monitors are ranked.",
            "If evidence health is degraded, COMMONS holds new learning.",
        ],
    }
