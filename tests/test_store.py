from commons.models import (
    Assessment,
    CaseRecord,
    OutcomeInput,
    OutcomeStatus,
    ProblemInput,
    Route,
    RouteDecision,
)
from commons.store import CaseStore


def test_case_can_receive_outcome(tmp_path) -> None:
    store = CaseStore(str(tmp_path / "commons.db"))
    case = CaseRecord(
        problem=ProblemInput(text="Help me understand this maths problem."),
        assessment=Assessment(
            domain="education",
            urgency=1,
            high_stakes=0.1,
            enough_information=0.9,
            safe_to_automate=0.9,
            needs_human_review=0.1,
            capability="reason",
            domain_confidence=0.9,
            capability_confidence=0.9,
        ),
        decision=RouteDecision(
            route=Route.REASON,
            reason="test",
            policy_version="test",
        ),
    )
    store.save_case(case)

    outcome = store.save_outcome(
        case.case_id,
        OutcomeInput(status=OutcomeStatus.RESOLVED, verified=True),
    )

    assert outcome.case_id == case.case_id
    assert store.get_outcome(case.case_id).status is OutcomeStatus.RESOLVED
