from commons.models import (
    CapabilityOffer,
    CapabilityRequirement,
    ProviderKind,
    ProviderProfile,
    ResourceBudget,
    VerificationStatus,
)
from commons.registry import CapabilityRegistry


def test_mixed_network_can_choose_ai_human_and_hybrid() -> None:
    registry = CapabilityRegistry()

    ai = registry.register_provider(
        ProviderProfile(
            name="AI",
            kind=ProviderKind.AI,
            verification_status=VerificationStatus.VERIFIED,
        )
    )
    human = registry.register_provider(
        ProviderProfile(
            name="Human",
            kind=ProviderKind.PERSON,
            verification_status=VerificationStatus.VERIFIED,
        )
    )

    registry.register_capability(
        CapabilityOffer(
            provider_id=ai.provider_id,
            capability_type="draft",
            description="Fast draft",
            price_eur=0.05,
            verification_status=VerificationStatus.VERIFIED,
        )
    )
    registry.register_capability(
        CapabilityOffer(
            provider_id=human.provider_id,
            capability_type="review",
            description="Human review",
            price_eur=0.75,
            verification_status=VerificationStatus.VERIFIED,
        )
    )

    plan = registry.plan(
        [
            CapabilityRequirement(
                capability_type="draft",
                preferred_provider_kinds=[ProviderKind.AI],
            ),
            CapabilityRequirement(
                capability_type="review",
                preferred_provider_kinds=[ProviderKind.PERSON],
            ),
        ],
        ResourceBudget(max_cost_eur=1.0, max_capabilities=2),
    )

    assert plan.within_budget is True
    kinds = [
        registry.providers[m.capability.provider_id].kind
        for m in plan.matches
    ]
    assert kinds == [ProviderKind.AI, ProviderKind.PERSON]
