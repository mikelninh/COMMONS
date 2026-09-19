import pytest

from commons.models import ProofLevel, ProofRecord
from commons.proof import ProofLedger


def test_provider_cannot_self_verify_external_outcome() -> None:
    ledger = ProofLedger()
    with pytest.raises(ValueError):
        ledger.record(
            ProofRecord(
                case_id="case-1",
                provider_id="provider-1",
                verifier_id="provider-1",
                level=ProofLevel.EXTERNALLY_VERIFIED,
            )
        )


def test_external_proof_requires_verifier() -> None:
    ledger = ProofLedger()
    with pytest.raises(ValueError):
        ledger.record(
            ProofRecord(
                case_id="case-1",
                provider_id="provider-1",
                level=ProofLevel.EXTERNALLY_VERIFIED,
            )
        )


def test_counterparty_confirmation_can_precede_external_verification() -> None:
    ledger = ProofLedger()
    ledger.record(
        ProofRecord(
            case_id="case-1",
            provider_id="provider-1",
            verifier_id="recipient-1",
            level=ProofLevel.COUNTERPARTY_CONFIRMED,
        )
    )
    ledger.record(
        ProofRecord(
            case_id="case-1",
            provider_id="provider-1",
            verifier_id="auditor-1",
            level=ProofLevel.EXTERNALLY_VERIFIED,
        )
    )
    assert ledger.strongest_level("case-1") is ProofLevel.EXTERNALLY_VERIFIED
