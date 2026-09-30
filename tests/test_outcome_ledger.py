import json
from pathlib import Path

import pytest

from commons.outcome_ledger import (
    OutcomeReceiptError,
    ingest_agency_receipt,
    summarize_outcomes,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "agency-receipts"


def receipt(
    *,
    project="OpsPilot",
    evidence_class="synthetic",
    owner="human",
    authority="prepare",
    side_effects=False,
    status="succeeded",
):
    learning = (
        {"next_unknown": "real outcome missing"}
        if evidence_class == "synthetic"
        else {"next_change": "turn correction into regression"}
    )
    return {
        "schema": "openaction.agency-receipt.v1",
        "mission_id": "mission-1",
        "project": project,
        "observed_at": "2026-09-30T00:00:00Z",
        "evidence": [{"ref": "case evidence"}],
        "decision": {"owner": owner, "rationale": "bounded test"},
        "action": {
            "authority": authority,
            "external_side_effects": side_effects,
            "description": "prepare work",
        },
        "outcome": {
            "status": status,
            "evidence_class": evidence_class,
            "evidence": ["test evidence"],
        },
        "learning": learning,
    }


def test_synthetic_success_remains_synthetic_and_cannot_become_real_outcome_by_ingestion():
    record = ingest_agency_receipt(receipt())
    assert record["evidence_class"] == "synthetic"
    assert record["outcome_status"] == "succeeded"
    assert record["next_unknown"] == "real outcome missing"
    assert record["next_change"] is None


def test_observed_receipt_preserves_next_change():
    record = ingest_agency_receipt(receipt(evidence_class="observed"))
    assert record["evidence_class"] == "observed"
    assert record["next_change"] == "turn correction into regression"


def test_missing_or_invented_evidence_class_fails_closed():
    missing = receipt()
    del missing["outcome"]["evidence_class"]
    with pytest.raises(OutcomeReceiptError, match="outcome_evidence_class_required"):
        ingest_agency_receipt(missing)

    invented = receipt()
    invented["outcome"]["evidence_class"] = "trust_me"
    with pytest.raises(OutcomeReceiptError, match="invalid_outcome_evidence_class"):
        ingest_agency_receipt(invented)


def test_unsafe_external_execution_without_human_or_policy_owner_is_rejected():
    with pytest.raises(OutcomeReceiptError, match="consequential_execute_requires"):
        ingest_agency_receipt(
            receipt(owner="shared", authority="execute", side_effects=True)
        )


def test_current_openaction_receipt_shapes_ingest_without_evidence_laundering():
    records = []
    for path in sorted(FIXTURE_DIR.glob("*.json")):
        records.append(ingest_agency_receipt(json.loads(path.read_text(encoding="utf-8"))))

    assert len(records) == 3
    assert {record["project"] for record in records} == {
        "Digital Worker Factory / OpsPilot",
        "Game Studio / Agent Lab",
        "HANA Commerce",
    }
    assert {record["evidence_class"] for record in records} == {"synthetic"}
    assert next(record for record in records if record["project"] == "Game Studio / Agent Lab")["outcome_status"] == "partial"


def test_summary_keeps_domains_separate_instead_of_inventing_one_impact_score():
    records = [
        ingest_agency_receipt(receipt(project="OpsPilot", evidence_class="observed")),
        ingest_agency_receipt(receipt(project="HANA", evidence_class="synthetic", status="partial")),
    ]
    summary = summarize_outcomes(records)
    assert summary["records"] == 2
    assert summary["by_project"]["OpsPilot"]["succeeded"] == 1
    assert summary["by_project"]["HANA"]["partial"] == 1
    assert summary["evidence_classes"] == {"observed": 1, "synthetic": 1}
    assert "score" not in summary
    assert "Do not collapse" in summary["principle"]
