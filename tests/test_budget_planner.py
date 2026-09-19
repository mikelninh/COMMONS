from commons.models import (
    AuthorityLevel,
    CapabilityOffer,
    CapabilityRequirement,
    ProviderKind,
    ProviderProfile,
    ResourceBudget,
    VerificationStatus,
)
from commons.registry import CapabilityRegistry


def add_provider(
    registry: CapabilityRegistry,
    name: str,
    verified: bool = True,
) -> ProviderProfile:
    return registry.register_provider(
        ProviderProfile(
            name=name,
            kind=ProviderKind.BUSINESS,
            verification_status=(
                VerificationStatus.VERIFIED
                if verified
                else VerificationStatus.DECLARED
            ),
        )
    )


def test_budget_planner_chooses_cheapest_verified_sufficient_capability() -> None:
    registry = CapabilityRegistry()
    expensive = add_provider(registry, "Expensive")
    cheap = add_provider(registry, "Cheap")

    registry.register_capability(
        CapabilityOffer(
            provider_id=expensive.provider_id,
            capability_type="translation",
            description="Verified translation",
            languages=["vi"],
            price_eur=0.80,
            verification_status=VerificationStatus.VERIFIED,
        )
    )
    cheap_offer = registry.register_capability(
        CapabilityOffer(
            provider_id=cheap.provider_id,
            capability_type="translation",
            description="Verified translation",
            languages=["vi"],
            price_eur=0.20,
            verification_status=VerificationStatus.VERIFIED,
        )
    )

    plan = registry.plan(
        [CapabilityRequirement(capability_type="translation", language="vi")],
        ResourceBudget(max_cost_eur=1.0),
    )

    assert plan.within_budget is True
    assert plan.total_cost_eur == 0.20
    assert plan.matches[0].capability.capability_id == cheap_offer.capability_id


def test_budget_planner_refuses_unknown_price_for_one_euro_proof() -> None:
    registry = CapabilityRegistry()
    provider = add_provider(registry, "Unknown price")

    registry.register_capability(
        CapabilityOffer(
            provider_id=provider.provider_id,
            capability_type="research",
            description="Research capability with no declared price",
            price_eur=None,
            verification_status=VerificationStatus.VERIFIED,
        )
    )

    plan = registry.plan(
        [CapabilityRequirement(capability_type="research")],
        ResourceBudget(max_cost_eur=1.0),
    )

    assert plan.within_budget is False
    assert len(plan.unresolved_requirements) == 1


def test_budget_planner_never_exceeds_hard_cost_limit() -> None:
    registry = CapabilityRegistry()
    provider = add_provider(registry, "Courier")

    registry.register_capability(
        CapabilityOffer(
            provider_id=provider.provider_id,
            capability_type="transport",
            description="Verified delivery",
            price_eur=4.0,
            authority_ceiling=AuthorityLevel.EXECUTE_REVERSIBLE,
            verification_status=VerificationStatus.VERIFIED,
        )
    )

    plan = registry.plan(
        [
            CapabilityRequirement(
                capability_type="transport",
                required_authority=AuthorityLevel.EXECUTE_REVERSIBLE,
            )
        ],
        ResourceBudget(max_cost_eur=1.0),
    )

    assert plan.within_budget is False
    assert plan.total_cost_eur == 0.0
    assert not plan.matches


def test_budget_planner_respects_max_capability_count() -> None:
    registry = CapabilityRegistry()
    provider = add_provider(registry, "Multi")

    for capability_type in ("a", "b"):
        registry.register_capability(
            CapabilityOffer(
                provider_id=provider.provider_id,
                capability_type=capability_type,
                description=capability_type,
                price_eur=0.10,
                verification_status=VerificationStatus.VERIFIED,
            )
        )

    plan = registry.plan(
        [
            CapabilityRequirement(capability_type="a"),
            CapabilityRequirement(capability_type="b"),
        ],
        ResourceBudget(max_cost_eur=1.0, max_capabilities=1),
    )

    assert plan.within_budget is False
    assert len(plan.matches) == 1
    assert len(plan.unresolved_requirements) == 1
