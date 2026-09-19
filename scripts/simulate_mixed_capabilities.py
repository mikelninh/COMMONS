from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

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


def provider(
    registry: CapabilityRegistry,
    name: str,
    kind: ProviderKind,
) -> ProviderProfile:
    return registry.register_provider(
        ProviderProfile(
            name=name,
            kind=kind,
            location="Berlin",
            verification_status=VerificationStatus.VERIFIED,
        )
    )


def add_offer(
    registry: CapabilityRegistry,
    p: ProviderProfile,
    capability_type: str,
    description: str,
    price: float,
    *,
    tags: list[str] | None = None,
    languages: list[str] | None = None,
    authority: AuthorityLevel = AuthorityLevel.DRAFT,
    success: int = 0,
    failure: int = 0,
) -> CapabilityOffer:
    return registry.register_capability(
        CapabilityOffer(
            provider_id=p.provider_id,
            capability_type=capability_type,
            description=description,
            tags=tags or [],
            languages=languages or [],
            location="Berlin",
            price_eur=price,
            verification_status=VerificationStatus.VERIFIED,
            authority_ceiling=authority,
            success_count=success,
            failure_count=failure,
        )
    )


def selected_names(registry: CapabilityRegistry, plan) -> list[str]:
    return [
        registry.providers[m.capability.provider_id].name
        for m in plan.matches
    ]


def main() -> None:
    registry = CapabilityRegistry()

    ai_reader = provider(registry, "Document Agent", ProviderKind.AI)
    ai_router = provider(registry, "Public Service Agent", ProviderKind.AI)
    human_translator = provider(registry, "Human Translator", ProviderKind.PERSON)
    human_specialist = provider(registry, "Accountable Specialist", ProviderKind.PERSON)
    community = provider(registry, "Community Helper", ProviderKind.NONPROFIT)
    courier = provider(registry, "Local Courier", ProviderKind.BUSINESS)

    add_offer(
        registry,
        ai_reader,
        "document_reading",
        "Extracts and summarizes administrative documents.",
        0.02,
        tags=["document", "extract", "summary"],
        authority=AuthorityLevel.EXPLAIN,
        success=95,
        failure=5,
    )
    add_offer(
        registry,
        ai_router,
        "public_service_navigation",
        "Finds official public-service processes and next steps.",
        0.03,
        tags=["official", "navigation", "public-service"],
        authority=AuthorityLevel.EXPLAIN,
        success=92,
        failure=8,
    )
    add_offer(
        registry,
        human_translator,
        "translation",
        "Human Vietnamese/German translation with nuance and context.",
        0.80,
        tags=["official", "nuance", "sensitive"],
        languages=["vi", "de"],
        authority=AuthorityLevel.DRAFT,
        success=49,
        failure=1,
    )
    add_offer(
        registry,
        human_specialist,
        "accountable_review",
        "Qualified accountable review for consequential interpretation.",
        1.00,
        tags=["accountable", "consequential", "review"],
        authority=AuthorityLevel.DRAFT,
        success=98,
        failure=2,
    )
    add_offer(
        registry,
        community,
        "human_support",
        "Helps people understand next steps and complete low-authority tasks.",
        0.50,
        tags=["support", "trust", "guidance"],
        authority=AuthorityLevel.DRAFT,
        success=45,
        failure=5,
    )
    add_offer(
        registry,
        courier,
        "transport",
        "Local delivery and pickup.",
        4.00,
        tags=["delivery", "physical"],
        authority=AuthorityLevel.EXECUTE_REVERSIBLE,
        success=90,
        failure=10,
    )

    # Case 1: pure AI is appropriate.
    plan_ai = registry.plan(
        [
            CapabilityRequirement(
                capability_type="document_reading",
                tags=["document", "summary"],
                preferred_provider_kinds=[ProviderKind.AI],
            )
        ],
        ResourceBudget(max_cost_eur=0.10),
    )
    assert plan_ai.within_budget
    assert selected_names(registry, plan_ai) == ["Document Agent"]

    # Case 2: hybrid is better than replacing the human.
    plan_hybrid = registry.plan(
        [
            CapabilityRequirement(
                capability_type="document_reading",
                tags=["document", "extract"],
                preferred_provider_kinds=[ProviderKind.AI],
            ),
            CapabilityRequirement(
                capability_type="translation",
                tags=["official", "nuance", "sensitive"],
                languages=["vi"],
                preferred_provider_kinds=[ProviderKind.PERSON],
            ),
        ],
        ResourceBudget(max_cost_eur=1.0, max_capabilities=2),
    )
    assert plan_hybrid.within_budget
    assert set(selected_names(registry, plan_hybrid)) == {
        "Document Agent",
        "Human Translator",
    }

    # Case 3: human is required despite cheaper automation being imaginable.
    plan_human = registry.plan(
        [
            CapabilityRequirement(
                capability_type="accountable_review",
                tags=["accountable", "consequential"],
                allowed_provider_kinds=[ProviderKind.PERSON],
            )
        ],
        ResourceBudget(max_cost_eur=1.0),
    )
    assert plan_human.within_budget
    assert selected_names(registry, plan_human) == ["Accountable Specialist"]

    # Case 4: physical-world need requires a real-world provider.
    plan_physical = registry.plan(
        [
            CapabilityRequirement(
                capability_type="transport",
                tags=["delivery", "physical"],
                allowed_provider_kinds=[ProviderKind.BUSINESS, ProviderKind.PERSON],
                required_authority=AuthorityLevel.EXECUTE_REVERSIBLE,
            )
        ],
        ResourceBudget(max_cost_eur=5.0),
    )
    assert plan_physical.within_budget
    assert selected_names(registry, plan_physical) == ["Local Courier"]

    print("COMMONS v0.3 mixed capability simulation")
    print("case 1: simple document understanding -> AI")
    print("case 2: sensitive translation -> AI + human")
    print("case 3: consequential accountable review -> human")
    print("case 4: physical delivery -> business/physical-world provider")
    print("principle: best fit within budget, not cheapest worker")
    print("result: PASS")


if __name__ == "__main__":
    main()
