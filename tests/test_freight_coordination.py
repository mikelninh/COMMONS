from scripts.simulate_freight_coordination import build_registry
from commons.models import (
    AuthorityLevel,
    CapabilityRequirement,
    ProviderKind,
    ResourceBudget,
)


def test_freight_plan_prefers_verified_physical_supply_over_cheaper_fake_or_ai() -> None:
    registry = build_registry()
    plan = registry.plan(
        [
            CapabilityRequirement(
                capability_type="transport",
                require_verified_provider=True,
                allowed_provider_kinds=[ProviderKind.BUSINESS, ProviderKind.PERSON],
                required_authority=AuthorityLevel.EXECUTE_REVERSIBLE,
            )
        ],
        ResourceBudget(max_cost_eur=2000.0),
    )
    assert plan.within_budget
    assert plan.matches[0].capability.capability_id == "carrier-good-transport"


def test_freight_plan_fails_closed_when_required_supply_is_missing() -> None:
    registry = build_registry()
    plan = registry.plan(
        [
            CapabilityRequirement(
                capability_type="hazmat_transport",
                require_verified_provider=True,
                allowed_provider_kinds=[ProviderKind.BUSINESS],
                required_authority=AuthorityLevel.EXECUTE_REVERSIBLE,
            )
        ],
        ResourceBudget(max_cost_eur=10000.0),
    )
    assert not plan.within_budget
    assert plan.unresolved_requirements
