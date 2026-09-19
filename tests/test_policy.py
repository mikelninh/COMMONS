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


def test_high_stakes_health_escalates() -> None:
    decision = choose_route(
        base_assessment(domain="health", high_stakes=0.91, capability="reason")
    )
    assert decision.route is Route.HUMAN


def test_high_stakes_public_service_can_still_retrieve() -> None:
    decision = choose_route(
        base_assessment(
            domain="public_services",
            high_stakes=0.91,
            needs_human_review=0.85,
            capability="public_service_navigation",
            safe_to_automate=0.20,
        )
    )
    assert decision.route is Route.RETRIEVE
    assert "non-executive" in decision.reason


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


def test_workflow_needing_review_does_not_execute() -> None:
    decision = choose_route(
        base_assessment(
            capability="workflow",
            safe_to_automate=0.95,
            needs_human_review=0.90,
        )
    )
    assert decision.route is Route.HUMAN


def test_safe_reasoning_routes_normally() -> None:
    decision = choose_route(base_assessment(capability="reason"))
    assert decision.route is Route.REASON


def test_civic_value_conflict_routes_to_deliberation_not_execution() -> None:
    decision = choose_route(
        base_assessment(
            domain="democracy",
            capability="deliberate",
            contested_values_present=0.91,
            affected_groups_present=0.97,
            high_stakes=0.82,
            needs_human_review=0.88,
        )
    )
    assert decision.route is Route.DELIBERATE
    assert "may not make the political choice" in decision.reason


def test_civic_deliberation_requests_missing_information_first() -> None:
    decision = choose_route(
        base_assessment(
            domain="community",
            contested_values_present=0.90,
            enough_information=0.20,
        )
    )
    assert decision.route is Route.REQUEST_INFO


def test_domain_ambiguity_does_not_block_clear_capability() -> None:
    decision = choose_route(
        base_assessment(
            domain="education",
            domain_confidence=0.40,
            capability="public_service_navigation",
            capability_confidence=0.90,
            enough_information=0.60,
        )
    )
    assert decision.route is Route.RETRIEVE


def test_information_at_threshold_is_not_automatically_rejected() -> None:
    decision = choose_route(
        base_assessment(
            enough_information=0.45,
            capability="public_service_navigation",
            capability_confidence=0.90,
        )
    )
    assert decision.route is Route.RETRIEVE
