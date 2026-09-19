from commons.models import Assessment, Route
from commons.policy import choose_route


def base_assessment(**overrides) -> Assessment:
    values = {
        "domain": "software",
        "urgency": 1.0,
        "high_stakes": 0.10,
        "enough_information": 0.90,
        "safe_to_automate": 0.90,
        "needs_human_review": 0.10,
        "capability": "reason",
        "domain_confidence": 0.90,
        "capability_confidence": 0.90,
    }
    values.update(overrides)
    return Assessment(**values)


def test_high_stakes_escalates() -> None:
    decision = choose_route(base_assessment(high_stakes=0.91))
    assert decision.route is Route.HUMAN


def test_missing_information_abstains() -> None:
    decision = choose_route(base_assessment(enough_information=0.20))
    assert decision.route is Route.REQUEST_INFO


def test_low_confidence_abstains() -> None:
    decision = choose_route(base_assessment(capability_confidence=0.31))
    assert decision.route is Route.REQUEST_INFO


def test_unsafe_workflow_does_not_execute() -> None:
    decision = choose_route(
        base_assessment(capability="workflow", safe_to_automate=0.30)
    )
    assert decision.route is Route.HUMAN


def test_safe_reasoning_routes_normally() -> None:
    decision = choose_route(base_assessment(capability="reason"))
    assert decision.route is Route.REASON
