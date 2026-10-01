from __future__ import annotations

import os
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
    VerificationStatus,
)
from commons.registry import CapabilityRegistry
from commons.selector import JevCapabilitySelector


def add_provider(
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
    provider: ProviderProfile,
    capability_type: str,
    description: str,
    price: float,
    *,
    tags: list[str],
    languages: list[str] | None = None,
    authority: AuthorityLevel = AuthorityLevel.DRAFT,
    success: int = 0,
    failure: int = 0,
) -> None:
    registry.register_capability(
        CapabilityOffer(
            provider_id=provider.provider_id,
            capability_type=capability_type,
            description=description,
            tags=tags,
            languages=languages or [],
            location="Berlin",
            price_eur=price,
            authority_ceiling=authority,
            verification_status=VerificationStatus.VERIFIED,
            success_count=success,
            failure_count=failure,
        )
    )


def main() -> None:
    if not os.getenv("TYPESAFE_API_KEY"):
        raise SystemExit("TYPESAFE_API_KEY is required for the live capability demo.")

    registry = CapabilityRegistry()
    selector = JevCapabilitySelector()

    doc_agent = add_provider(registry, "Document Agent", ProviderKind.AI)
    service_agent = add_provider(registry, "Public Service Agent", ProviderKind.AI)
    translator = add_provider(registry, "Human Vietnamese/German Translator", ProviderKind.PERSON)
    helper = add_provider(registry, "Community Helper", ProviderKind.NONPROFIT)

    add_offer(
        registry,
        doc_agent,
        "document_reading",
        "Extracts structure, deadlines and requested information from administrative letters.",
        0.02,
        tags=["document", "official", "extract"],
        authority=AuthorityLevel.EXPLAIN,
        success=95,
        failure=5,
    )
    add_offer(
        registry,
        service_agent,
        "public_service_navigation",
        "Finds official Berlin public-service processes, sources and next steps.",
        0.03,
        tags=["official", "public-service", "evidence"],
        authority=AuthorityLevel.EXPLAIN,
        success=92,
        failure=8,
    )
    add_offer(
        registry,
        translator,
        "translation",
        "Vietnamese/German translation with human nuance for sensitive official communication.",
        0.80,
        tags=["official", "nuance", "sensitive"],
        languages=["vi", "de"],
        authority=AuthorityLevel.DRAFT,
        success=49,
        failure=1,
    )
    add_offer(
        registry,
        helper,
        "translation",
        "Community language support for routine German/Vietnamese communication.",
        0.40,
        tags=["official", "support"],
        languages=["vi", "de"],
        authority=AuthorityLevel.DRAFT,
        success=18,
        failure=2,
    )

    need = (
        "A Vietnamese-speaking person in Berlin received a German authority letter. "
        "They want to understand it and prepare the next response, but nothing should "
        "be submitted without their approval."
    )

    requirements = [
        CapabilityRequirement(
            capability_type="document_reading",
            tags=["document", "official", "extract"],
            preferred_provider_kinds=[ProviderKind.AI],
            max_price_eur=0.10,
        ),
        CapabilityRequirement(
            capability_type="public_service_navigation",
            tags=["official", "public-service", "evidence"],
            preferred_provider_kinds=[ProviderKind.AI],
            max_price_eur=0.10,
        ),
        CapabilityRequirement(
            capability_type="translation",
            tags=["official", "nuance", "sensitive"],
            language="vi",
            preferred_provider_kinds=[ProviderKind.PERSON],
            max_price_eur=1.00,
        ),
    ]

    print("COMMONS v0.3 — live capability menu demo")
    print("need:", need)
    print()

    total = 0.0
    for index, requirement in enumerate(requirements, start=1):
        candidates = registry.match(requirement, limit=8)
        if not candidates:
            raise SystemExit(f"No feasible candidates for requirement {requirement.capability_type!r}.")

        selection = selector.choose(
            need,
            candidates,
            context={
                "step": index,
                "required_capability": requirement.capability_type,
                "already_selected_cost_eur": total,
                "approval_rule": "Do not submit or execute consequential actions without explicit approval.",
            },
            providers=registry.providers,
        )

        offer = selection.selected.capability
        provider = registry.providers[offer.provider_id]
        total += float(offer.price_eur or 0.0)

        print(f"step {index}: {requirement.capability_type}")
        print(f"  live candidates: {selection.candidate_count}")
        print(f"  selected: {provider.name} [{provider.kind.value}]")
        print(f"  price: EUR {float(offer.price_eur or 0.0):.2f}")
        print(f"  confidence: {selection.confidence}")
        if selection.probabilities:
            print(f"  probability options: {len(selection.probabilities)}")
        print()

    print(f"total selected capability cost: EUR {total:.2f}")
    print("authority: READ / EXPLAIN / DRAFT only")
    print("next: execute only after explicit human approval where required")


if __name__ == "__main__":
    main()
