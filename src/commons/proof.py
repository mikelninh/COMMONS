from __future__ import annotations

from commons.models import ProofLevel, ProofRecord


class ProofLedger:
    """Append-only in-memory proof ledger for v0.3 experiments."""

    def __init__(self) -> None:
        self.records: list[ProofRecord] = []

    def record(self, proof: ProofRecord) -> ProofRecord:
        if proof.level in {ProofLevel.EXTERNALLY_VERIFIED, ProofLevel.DURABLE}:
            if not proof.verifier_id:
                raise ValueError("Independent verifier required for external or durable proof.")
            if proof.provider_id and proof.verifier_id == proof.provider_id:
                raise ValueError("Provider cannot independently verify its own outcome.")

        self.records.append(proof)
        return proof

    def for_case(self, case_id: str) -> list[ProofRecord]:
        return [r for r in self.records if r.case_id == case_id]

    def strongest_level(self, case_id: str) -> ProofLevel | None:
        rank = {
            ProofLevel.DECLARED: 1,
            ProofLevel.ACTIONED: 2,
            ProofLevel.COUNTERPARTY_CONFIRMED: 3,
            ProofLevel.EXTERNALLY_VERIFIED: 4,
            ProofLevel.DURABLE: 5,
        }
        rows = self.for_case(case_id)
        return max((r.level for r in rows), key=lambda x: rank[x], default=None)
