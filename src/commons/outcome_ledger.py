from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime
from typing import Any


class OutcomeReceiptError(ValueError):
    pass


_ALLOWED_OWNERS = {"human", "shared", "policy"}
_ALLOWED_AUTHORITIES = {"observe", "propose", "prepare", "execute"}
_ALLOWED_OUTCOMES = {"succeeded", "partial", "failed", "unknown"}
_ALLOWED_EVIDENCE_CLASSES = {"synthetic", "observed", "external", "failure"}


def _valid_ref_items(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) > 0
        and all(
            isinstance(item, dict)
            and isinstance(item.get("ref"), str)
            and bool(item["ref"].strip())
            for item in value
        )
    )


def _valid_observed_at(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def validate_agency_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(receipt, dict):
        raise OutcomeReceiptError("receipt_must_be_object")

    if receipt.get("schema") != "openaction.agency-receipt.v1":
        errors.append("unsupported_schema")
    for field in ("mission_id", "project"):
        if not isinstance(receipt.get(field), str) or not receipt[field].strip():
            errors.append(f"{field}_required")
    if not _valid_observed_at(receipt.get("observed_at")):
        errors.append("observed_at_must_be_iso_date")
    if not _valid_ref_items(receipt.get("evidence")):
        errors.append("evidence_requires_nonempty_refs")

    decision = receipt.get("decision") or {}
    action = receipt.get("action") or {}
    outcome = receipt.get("outcome") or {}
    learning = receipt.get("learning") or {}

    owner = decision.get("owner")
    if owner not in _ALLOWED_OWNERS:
        errors.append("invalid_decision_owner" if owner else "decision_owner_required")
    if not isinstance(decision.get("rationale"), str) or not decision["rationale"].strip():
        errors.append("decision_rationale_required")

    authority = action.get("authority")
    if authority not in _ALLOWED_AUTHORITIES:
        errors.append("invalid_action_authority" if authority else "action_authority_required")
    if not isinstance(action.get("external_side_effects"), bool):
        errors.append("external_side_effects_boolean_required")
    if not isinstance(action.get("description"), str) or not action["description"].strip():
        errors.append("action_description_required")

    status = outcome.get("status")
    if status not in _ALLOWED_OUTCOMES:
        errors.append("invalid_outcome_status" if status else "outcome_status_required")

    evidence_class = outcome.get("evidence_class")
    if evidence_class not in _ALLOWED_EVIDENCE_CLASSES:
        errors.append(
            "invalid_outcome_evidence_class"
            if evidence_class
            else "outcome_evidence_class_required"
        )

    if status == "succeeded" and not outcome.get("evidence"):
        errors.append("successful_outcome_requires_evidence")

    if (
        authority == "execute"
        and action.get("external_side_effects") is True
        and owner not in {"human", "policy"}
    ):
        errors.append("consequential_execute_requires_human_or_policy_owner")

    if not learning.get("next_change") and not learning.get("next_unknown"):
        errors.append("learning_requires_next_change_or_unknown")

    if errors:
        raise OutcomeReceiptError("; ".join(errors))
    return receipt


def ingest_agency_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    """Normalize a portable outcome receipt without inventing evidence quality or a utility score."""
    clean = deepcopy(validate_agency_receipt(receipt))
    outcome = clean["outcome"]

    return {
        "schema": "commons.outcome-record.v1",
        "mission_id": clean["mission_id"],
        "project": clean["project"],
        "observed_at": clean["observed_at"],
        "decision_owner": clean["decision"]["owner"],
        "authority": clean["action"]["authority"],
        "external_side_effects": clean["action"]["external_side_effects"],
        "outcome_status": outcome["status"],
        "evidence_class": outcome["evidence_class"],
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
