from __future__ import annotations

from commons.decision import JevDecisionEngine
from commons.models import CaseRecord, OutcomeInput, OutcomeRecord, ProblemInput
from commons.policy import choose_route
from commons.store import CaseStore


class CommonsService:
    def __init__(
        self,
        decision_engine: JevDecisionEngine | None = None,
        store: CaseStore | None = None,
    ) -> None:
        self.decision_engine = decision_engine or JevDecisionEngine()
        self.store = store or CaseStore()

    def assess(self, problem: ProblemInput) -> CaseRecord:
        assessment = self.decision_engine.evaluate(problem)
        decision = choose_route(assessment)
        record = CaseRecord(
            problem=problem,
            assessment=assessment,
            decision=decision,
        )
        self.store.save_case(record)
        return record

    def record_outcome(self, case_id: str, outcome: OutcomeInput) -> OutcomeRecord:
        return self.store.save_outcome(case_id, outcome)
