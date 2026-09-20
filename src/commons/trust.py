from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


ALLOWED_CLAIM_TYPES = {"observed", "derived", "inferred", "proposed"}


@dataclass(frozen=True)
class TrustCheck:
    id: str
    label: str
    passed: bool
    detail: str


def _parse_dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def load_registry(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def evaluate_registry(
    registry: dict[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    else:
        now = now.astimezone(timezone.utc)

    sources = {source["id"]: source for source in registry.get("sources", [])}
    active_claims = [
        claim for claim in registry.get("claims", [])
        if claim.get("status") == "active"
    ]

    complete_claims = []
    missing_sources: list[dict[str, str]] = []
    for claim in active_claims:
        source_ids = claim.get("source_ids") or []
        missing = [source_id for source_id in source_ids if source_id not in sources]
        if source_ids and not missing:
            complete_claims.append(claim)
        for source_id in missing:
            missing_sources.append(
                {"claim_id": claim["id"], "source_id": source_id}
            )

    provenance_coverage = (
        len(complete_claims) / len(active_claims) if active_claims else 0.0
    )

    stale_critical_claims = []
    for claim in active_claims:
        if claim.get("criticality") != "high":
            continue
        freshness_days = claim.get("freshness_days")
        if freshness_days is None:
            continue
        as_of = _parse_dt(claim["as_of"])
        age_days = (now - as_of).total_seconds() / 86400
        if age_days > float(freshness_days):
            stale_critical_claims.append(claim)

    sources_without_limits = [
        source for source in sources.values()
        if not str(source.get("limitations", "")).strip()
    ]
    unresolved_conflicts = [
        conflict for conflict in registry.get("conflicts", [])
        if conflict.get("status") == "unresolved"
    ]
    open_high_incidents = [
        incident for incident in registry.get("incidents", [])
        if incident.get("status") == "open"
        and str(incident.get("severity", "")).lower() in {"high", "critical"}
    ]
    invalid_claims = [
        claim for claim in active_claims
        if claim.get("claim_type") not in ALLOWED_CLAIM_TYPES
    ]

    checks = [
        TrustCheck(
            "provenance-coverage",
            "Every active claim has registered provenance",
            provenance_coverage == 1.0,
            f"{len(complete_claims)}/{len(active_claims)} active claims have complete registered provenance.",
        ),
        TrustCheck(
            "critical-freshness",
            "No active critical claim is stale",
            not stale_critical_claims,
            (
                "No active critical claim has exceeded its declared freshness window."
                if not stale_critical_claims
                else f"{len(stale_critical_claims)} critical claim(s) exceeded their freshness window."
            ),
        ),
        TrustCheck(
            "source-integrity",
            "Every referenced source exists and declares limitations",
            not missing_sources and not sources_without_limits,
            (
                "All referenced sources are registered and state limitations."
                if not missing_sources and not sources_without_limits
                else (
                    f"{len(missing_sources)} missing source reference(s); "
                    f"{len(sources_without_limits)} source(s) missing limitations."
                )
            ),
        ),
        TrustCheck(
            "conflict-safety",
            "No unresolved conflict is hidden",
            not unresolved_conflicts,
            (
                "No unresolved source conflict is currently registered."
                if not unresolved_conflicts
                else f"{len(unresolved_conflicts)} unresolved source conflict(s)."
            ),
        ),
        TrustCheck(
            "incident-safety",
            "No open high-severity trust incident",
            not open_high_incidents,
            (
                "No high-severity trust incident is open."
                if not open_high_incidents
                else f"{len(open_high_incidents)} high-severity trust incident(s) remain open."
            ),
        ),
        TrustCheck(
            "claim-taxonomy",
            "Every claim has an explicit epistemic type",
            not invalid_claims,
            (
                "Every active claim is observed, derived, inferred or proposed."
                if not invalid_claims
                else f"{len(invalid_claims)} claim(s) use an invalid type."
            ),
        ),
    ]

    registry_required_ids = {
        item["id"]
        for item in registry.get("evaluation_requirements", [])
        if item.get("required")
    }
    registry_check_ids = {check.id for check in checks}

    # Checks that require browser/action-loop behavior are enforced elsewhere in CI.
    browser_enforced_ids = {
        "action-causality",
        "external-action-verification",
        "no-invented-action",
        "degraded-mode",
    }
    missing_required_evaluators = registry_required_ids - registry_check_ids - browser_enforced_ids

    all_registry_checks_pass = all(check.passed for check in checks)
    healthy = (
        all_registry_checks_pass
        and provenance_coverage == 1.0
        and not stale_critical_claims
        and not unresolved_conflicts
        and not open_high_incidents
        and not missing_required_evaluators
    )

    return {
        "status": "HEALTHY" if healthy else "DEGRADED",
        "evaluated_at": now.isoformat().replace("+00:00", "Z"),
        "provenance_coverage": provenance_coverage,
        "stale_critical_claims": stale_critical_claims,
        "missing_sources": missing_sources,
        "sources_without_limits": sources_without_limits,
        "unresolved_conflicts": unresolved_conflicts,
        "open_high_incidents": open_high_incidents,
        "invalid_claims": invalid_claims,
        "missing_required_evaluators": sorted(missing_required_evaluators),
        "checks": [
            {
                "id": check.id,
                "label": check.label,
                "passed": check.passed,
                "detail": check.detail,
            }
            for check in checks
        ],
    }
