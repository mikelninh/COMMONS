from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from commons.models import (
    AuthorityLevel,
    CapabilityOffer,
    CapabilityRequirement,
    ProofLevel,
    ProofRecord,
    ProviderKind,
    ProviderProfile,
    ResourceBudget,
    VerificationStatus,
)
from commons.proof import ProofLedger
from commons.registry import CapabilityRegistry


def verified_provider(registry: CapabilityRegistry, name: str, kind: ProviderKind) -> ProviderProfile:
    return registry.register_provider(
        ProviderProfile(
            name=name,
            kind=kind,
            location="Berlin",
            verification_status=VerificationStatus.VERIFIED,
        )
    )


def main() -> None:
    registry = CapabilityRegistry()
    ledger = ProofLedger()

    bakery = verified_provider(registry, "Example Bakery", ProviderKind.BUSINESS)
    charity = verified_provider(registry, "Example Food Charity", ProviderKind.NONPROFIT)
    driver = verified_provider(registry, "Example Volunteer Driver", ProviderKind.PERSON)

    registry.register_capability(
        CapabilityOffer(
            provider_id=bakery.provider_id,
            capability_type="food_surplus",
            description="Up to 20 same-day surplus meals after closing.",
            tags=["food", "same-day", "surplus"],
            location="Berlin",
            capacity_available=20,
            unit="meal",
            price_eur=0,
            verification_status=VerificationStatus.VERIFIED,
            authority_ceiling=AuthorityLevel.DRAFT,
        )
    )
    registry.register_capability(
        CapabilityOffer(
            provider_id=charity.provider_id,
            capability_type="recipient_capacity",
            description="Can receive up to 25 prepared meals this evening.",
            tags=["food", "recipient", "same-day"],
            location="Berlin",
            capacity_available=25,
            unit="meal",
            price_eur=0,
            verification_status=VerificationStatus.VERIFIED,
            authority_ceiling=AuthorityLevel.DRAFT,
        )
    )
    registry.register_capability(
        CapabilityOffer(
            provider_id=driver.provider_id,
            capability_type="transport",
            description="Can transport food locally for one hour.",
            tags=["food", "delivery"],
            location="Berlin",
            capacity_available=1,
            unit="trip",
            price_eur=4,
            verification_status=VerificationStatus.VERIFIED,
            authority_ceiling=AuthorityLevel.EXECUTE_REVERSIBLE,
            success_count=9,
            failure_count=1,
        )
    )

    requirements = [
        CapabilityRequirement(
            capability_type="food_surplus",
            tags=["food", "surplus"],
            location="Berlin",
            required_authority=AuthorityLevel.READ,
            require_verified_provider=True,
        ),
        CapabilityRequirement(
            capability_type="recipient_capacity",
            tags=["food", "recipient"],
            location="Berlin",
            required_authority=AuthorityLevel.READ,
            require_verified_provider=True,
        ),
        CapabilityRequirement(
            capability_type="transport",
            tags=["food", "delivery"],
            location="Berlin",
            max_price_eur=5,
            required_authority=AuthorityLevel.EXECUTE_REVERSIBLE,
            require_verified_provider=True,
        ),
    ]

    plan = registry.plan(
        requirements,
        ResourceBudget(max_cost_eur=5.0, max_capabilities=3, prefer_verified=True),
    )
    assert plan.within_budget is True
    assert len(plan.matches) == 3
    assert plan.total_cost_eur == 4.0

    transport = next(
        match.capability
        for match in plan.matches
        if match.capability.capability_type == "transport"
    )
    assert transport.provider_id == driver.provider_id
    assert transport.price_eur == 4

    case_id = "food-sim-001"
    ledger.record(
        ProofRecord(
            case_id=case_id,
            capability_id=transport.capability_id,
            provider_id=driver.provider_id,
            verifier_id=charity.provider_id,
            level=ProofLevel.COUNTERPARTY_CONFIRMED,
            notes="Recipient confirmed the simulated delivery.",
        )
    )
    ledger.record(
        ProofRecord(
            case_id=case_id,
            capability_id=transport.capability_id,
            provider_id=driver.provider_id,
            verifier_id="independent-auditor",
            level=ProofLevel.EXTERNALLY_VERIFIED,
            notes="Independent verification layer simulated.",
        )
    )

    print("COMMONS v0.3 capability-network simulation")
    print("need: move surplus food to verified recipient")
    print("matched: food supply + recipient capacity + transport")
    print("hard budget: €5.00")
    print(f"selected plan cost: €{plan.total_cost_eur:.2f}")
    print("strongest proof:", ledger.strongest_level(case_id).value)
    print("authority: verified reversible execution only")
    print("result: PASS")


if __name__ == "__main__":
    main()
