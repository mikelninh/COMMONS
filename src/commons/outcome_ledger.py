from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from typing import Any


class OutcomeReceiptError(ValueError):
    pass


def validate_agency_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if receipt.get("schema") != "openaction.agency-receipt.v1":
        errors.append("unsupported_schema")
    for field in ("mission_id", "project", "observed_at"):
        if not receipt.get(field):
            errors.append(f"{field}_required")
    if not receipt.get("evidence"):
        errors.append("evidence_required")

    decision = receipt.get("decision") or {}
    action = receipt.get("action") or {}
    outcome = receipt.get("outcome") or {}
    learning = receipt.get("learning") or {}

    if not decision.get("owner"):
        errors.append("decision_owner_required")
    if not decision.get("rationale"):
        errors.append("decision_rationale_required")
    if not action.get("authority"):
        errors.append("action_authority_required")
    if not isinstance(action.get("external_side_effects"), bool):
        errors.append("external_side_effects_boolean_required")
    if not outcome.get("status"):
        errors.append("outcome_status_required")
    if outcome.get("status") == "succeeded" and not outcome.get("evidence"):
        errors.append("successful_outcome_requires_evidence")
    if (
        action.get("authority") == "execute"
        and action.get("external_side_effects") is True
        and decision.get("owner") not in {"human", "policy"}
    ):
        errors.append("consequential_execute_requires_human_or_policy_owner")
    if not learning.get("next_change") and not learning.get("next_unknown"):
        errors.append("learning_requires_next_change_or_unknown")

    if errors:
        raise OutcomeReceiptError("; ".join(errors))
    return receipt


def ingest_agency_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    """Normalize a portable outcome receipt without inventing a cross-domain utility score."""
    clean = deepcopy(validate_agency_receipt(receipt))
    outcome = clean["outcome"]
    synthetic = outcome.get("synthetic") is True
    evidence_class = "synthetic" if synthetic else "observed"
    if outcome.get("status") in {"blocked", "failed"}:
        evidence_class = "failure"

    return {
        "schema": "commons.outcome-record.v1",
        "mission_id": clean["mission_id"],
        "project": clean["project"],
        "observed_at": clean["observed_at"],
        "decision_owner": clean["decision"]["owner"],
        "authority": clean["action"]["authority"],
        "external_side_effects": clean["action"]["external_side_effects"],
        "outcome_status": outcome["status"],
        "evidence_class": evidence_class,
        "evidence": deepcopy(outcome.get("evidence") or []),
        "next_change": clean["learning"].get("next_change"),
        "next_unknown": clean["learning"].get("next_unknown"),
        "source_receipt": clean,
    }


def summarize_outcomes(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Describe outcome evidence by project/status. Deliberately no single 'impact score'."""
    by_project: dict[str, Counter] = defaultdict(Counter)
    evidence_classes = Counter()
    for record in records:
        if record.get("schema") != "commons.outcome-record.v1":
            raise OutcomeReceiptError("unsupported_outcome_record")
        by_project[record["project"]][record["outcome_status"]] += 1
        evidence_classes[record["evidence_class"]] += 1

    return {
        "schema": "commons.outcome-summary.v1",
        "records": len(records),
        "by_project": {project: dict(counts) for project, counts in sorted(by_project.items())},
        "evidence_classes": dict(evidence_classes),
        "principle": "Do not collapse art, wellbeing, rights, care or money into one universal utility score.",
    }
