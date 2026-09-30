import pytest

from commons.outcome_ledger import (
    OutcomeReceiptError,
    ingest_agency_receipt,
    summarize_outcomes,
)


def receipt(*, project="OpsPilot", synthetic=True, owner="human", authority="prepare", side_effects=False):
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
            "status": "measured",
            "evidence": ["time_saved_rate=0.4"],
            "synthetic": synthetic,
        },
        "learning": (
            {"next_unknown": "real outcome missing"}
            if synthetic
            else {"next_change": "turn correction into regression"}
        ),
    }


def test_synthetic_receipt_remains_synthetic_and_cannot_become_real_outcome_by_ingestion():
    record = ingest_agency_receipt(receipt())
    assert record["evidence_class"] == "synthetic"
    assert record["next_unknown"] == "real outcome missing"
    assert record["next_change"] is None


def test_observed_receipt_preserves_next_change():
    record = ingest_agency_receipt(receipt(synthetic=False))
    assert record["evidence_class"] == "observed"
    assert record["next_change"] == "turn correction into regression"


def test_unsafe_external_execution_without_human_or_policy_owner_is_rejected():
    with pytest.raises(OutcomeReceiptError, match="consequential_execute_requires"):
        ingest_agency_receipt(
            receipt(owner="shared", authority="execute", side_effects=True)
        )


def test_summary_keeps_domains_separate_instead_of_inventing_one_impact_score():
    records = [
        ingest_agency_receipt(receipt(project="OpsPilot", synthetic=False)),
        ingest_agency_receipt(receipt(project="HANA", synthetic=True)),
    ]
    summary = summarize_outcomes(records)
    assert summary["records"] == 2
    assert summary["by_project"]["OpsPilot"]["measured"] == 1
    assert summary["by_project"]["HANA"]["measured"] == 1
    assert "score" not in summary
    assert "Do not collapse" in summary["principle"]
