from commons.models import Assessment, Route
from commons.policy import choose_route


def assessment(**overrides) -> Assessment:
    values = dict(
        domain="other",
        urgency=1.0,
        high_stakes=0.1,
        enough_information=0.9,
        safe_to_automate=0.8,
        needs_human_review=0.1,
        capability="reason",
        affected_groups_present=0.0,
        contested_values_present=0.0,
        evidence_need=1.0,
        reversibility=4.0,
        domain_confidence=0.9,
        capability_confidence=0.9,
    )
    values.update(overrides)
    return Assessment(**values)


def test_confidence_never_grants_unsafe_workflow_authority() -> None:
    d = choose_route(
        assessment(
            capability="workflow",
            capability_confidence=0.99,
            safe_to_automate=0.20,
        )
    )
    assert d.route is Route.HUMAN


def test_political_value_conflict_never_executes() -> None:
    d = choose_route(
        assessment(
            domain="democracy",
            capability="workflow",
            contested_values_present=0.95,
            affected_groups_present=0.95,
            high_stakes=0.90,
            safe_to_automate=0.95,
            needs_human_review=0.90,
        )
    )
    assert d.route is Route.DELIBERATE


def test_ambiguous_low_information_case_abstains() -> None:
    d = choose_route(
        assessment(
            enough_information=0.10,
            capability="workflow",
            safe_to_automate=0.95,
        )
    )
    assert d.route is Route.REQUEST_INFO


def test_high_stakes_finance_escalates_even_if_capability_seems_safe() -> None:
    d = choose_route(
        assessment(
            domain="finance",
            high_stakes=0.95,
            capability="reason",
            safe_to_automate=0.95,
        )
    )
    assert d.route is Route.HUMAN


def test_high_stakes_public_service_can_still_read_without_execution() -> None:
    d = choose_route(
        assessment(
            domain="public_services",
            high_stakes=0.90,
            capability="public_service_navigation",
            safe_to_automate=0.10,
            needs_human_review=0.90,
        )
    )
    assert d.route is Route.RETRIEVE


def test_verification_is_nonexecutive_even_when_payment_depends_on_it() -> None:
    d = choose_route(
        assessment(
            domain="logistics",
            capability="verify",
            capability_confidence=0.90,
            enough_information=0.80,
            high_stakes=0.60,
            needs_human_review=0.90,
            safe_to_automate=0.10,
        )
    )
    assert d.route is Route.VERIFY
