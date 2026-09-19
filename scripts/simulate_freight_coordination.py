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


def add_provider(
    registry: CapabilityRegistry,
    provider_id: str,
    name: str,
    kind: ProviderKind,
    verified: bool = True,
) -> ProviderProfile:
    return registry.register_provider(
        ProviderProfile(
            provider_id=provider_id,
            name=name,
            kind=kind,
            verification_status=(
                VerificationStatus.VERIFIED if verified else VerificationStatus.DECLARED
            ),
        )
    )


def add_offer(
    registry: CapabilityRegistry,
    capability_id: str,
    provider: ProviderProfile,
    capability_type: str,
    price: float,
    *,
    authority: AuthorityLevel,
    tags: list[str],
    verified: bool = True,
) -> None:
    registry.register_capability(
        CapabilityOffer(
            capability_id=capability_id,
            provider_id=provider.provider_id,
            capability_type=capability_type,
            description=f"{provider.name}: {capability_type}",
            price_eur=price,
            authority_ceiling=authority,
            tags=tags,
            verification_status=(
                VerificationStatus.VERIFIED if verified else VerificationStatus.DECLARED
            ),
        )
    )


def build_registry() -> CapabilityRegistry:
    r = CapabilityRegistry()

    carrier = add_provider(r, "carrier-good", "Verified Regional Carrier", ProviderKind.BUSINESS)
    fake = add_provider(r, "carrier-fake", "Unverified Carrier", ProviderKind.BUSINESS, verified=False)
    broker_agent = add_provider(r, "broker-agent", "Coverage Agent", ProviderKind.AI)
    warehouse = add_provider(r, "warehouse", "Warehouse Dock", ProviderKind.BUSINESS)
    customs = add_provider(r, "customs", "Licensed Customs Review", ProviderKind.PERSON)
    payment = add_provider(r, "payment", "Payment Rail", ProviderKind.SOFTWARE)
    insurer = add_provider(r, "insurer", "Cargo Insurance API", ProviderKind.SOFTWARE)

    add_offer(
        r, "carrier-good-transport", carrier, "transport", 1800.0,
        authority=AuthorityLevel.EXECUTE_REVERSIBLE,
        tags=["truckload", "physical", "dry-van"],
    )
    add_offer(
        r, "carrier-fake-transport", fake, "transport", 1200.0,
        authority=AuthorityLevel.EXECUTE_REVERSIBLE,
        tags=["truckload", "physical", "dry-van"],
        verified=False,
    )
    add_offer(
        r, "agent-transport-claim", broker_agent, "transport", 1.0,
        authority=AuthorityLevel.EXECUTE_REVERSIBLE,
        tags=["truckload", "physical"],
    )
    add_offer(
        r, "warehouse-slot", warehouse, "warehouse_slot", 75.0,
        authority=AuthorityLevel.EXECUTE_REVERSIBLE,
        tags=["dock", "appointment"],
    )
    add_offer(
        r, "customs-review", customs, "customs_review", 125.0,
        authority=AuthorityLevel.DRAFT,
        tags=["cross-border", "documents", "human-review"],
    )
    add_offer(
        r, "payment-release", payment, "payment", 12.0,
        authority=AuthorityLevel.EXECUTE_REVERSIBLE,
        tags=["escrow", "payment"],
    )
    add_offer(
        r, "cargo-insurance", insurer, "insurance", 40.0,
        authority=AuthorityLevel.DRAFT,
        tags=["cargo", "risk"],
    )
    return r


def main() -> None:
    registry = build_registry()

    # 1. Routine domestic load: verified physical carrier + dock + payment.
    routine = registry.plan(
        [
            CapabilityRequirement(
                capability_type="transport",
                tags=["truckload", "physical", "dry-van"],
                required_authority=AuthorityLevel.EXECUTE_REVERSIBLE,
                require_verified_provider=True,
                allowed_provider_kinds=[ProviderKind.BUSINESS, ProviderKind.PERSON],
            ),
            CapabilityRequirement(
                capability_type="warehouse_slot",
                tags=["dock", "appointment"],
                required_authority=AuthorityLevel.EXECUTE_REVERSIBLE,
                require_verified_provider=True,
            ),
            CapabilityRequirement(
                capability_type="payment",
                tags=["escrow", "payment"],
                required_authority=AuthorityLevel.EXECUTE_REVERSIBLE,
                require_verified_provider=True,
            ),
        ],
        ResourceBudget(max_cost_eur=2000.0, max_capabilities=3),
    )
    assert routine.within_budget
    assert {m.capability.capability_id for m in routine.matches} == {
        "carrier-good-transport",
        "warehouse-slot",
        "payment-release",
    }

    # 2. Fake carrier is cheaper but cannot enter a verified transport plan.
    transport = registry.match(
        CapabilityRequirement(
            capability_type="transport",
            require_verified_provider=True,
            allowed_provider_kinds=[ProviderKind.BUSINESS, ProviderKind.PERSON],
            required_authority=AuthorityLevel.EXECUTE_REVERSIBLE,
        ),
        limit=10,
    )
    ids = {m.capability.capability_id for m in transport}
    assert "carrier-good-transport" in ids
    assert "carrier-fake-transport" not in ids

    # 3. AI can coordinate a truck, but it cannot pretend to physically transport freight.
    assert "agent-transport-claim" not in ids

    # 4. Cross-border load can require explicit human customs review.
    customs = registry.plan(
        [
            CapabilityRequirement(
                capability_type="customs_review",
                tags=["cross-border", "documents"],
                required_authority=AuthorityLevel.DRAFT,
                require_verified_provider=True,
                allowed_provider_kinds=[ProviderKind.PERSON],
            ),
            CapabilityRequirement(
                capability_type="transport",
                tags=["physical"],
                required_authority=AuthorityLevel.EXECUTE_REVERSIBLE,
                require_verified_provider=True,
                allowed_provider_kinds=[ProviderKind.BUSINESS],
            ),
        ],
        ResourceBudget(max_cost_eur=2000.0, max_capabilities=2),
    )
    assert customs.within_budget
    assert "customs-review" in {m.capability.capability_id for m in customs.matches}

    # 5. High-value/hazmat load: no qualified supply => safe unresolved plan.
    hazmat = registry.plan(
        [
            CapabilityRequirement(
                capability_type="hazmat_transport",
                tags=["hazmat", "high-value"],
                required_authority=AuthorityLevel.EXECUTE_REVERSIBLE,
                require_verified_provider=True,
                allowed_provider_kinds=[ProviderKind.BUSINESS],
            )
        ],
        ResourceBudget(max_cost_eur=10000.0),
    )
    assert not hazmat.within_budget
    assert len(hazmat.unresolved_requirements) == 1

    # 6. Budget too low: COMMONS does not silently substitute unverified/AI transport.
    poor_budget = registry.plan(
        [
            CapabilityRequirement(
                capability_type="transport",
                require_verified_provider=True,
                allowed_provider_kinds=[ProviderKind.BUSINESS, ProviderKind.PERSON],
                required_authority=AuthorityLevel.EXECUTE_REVERSIBLE,
            )
        ],
        ResourceBudget(max_cost_eur=1500.0),
    )
    assert not poor_budget.within_budget
    assert not poor_budget.matches

    print("COMMONS freight coordination arena")
    print("routine domestic load: PASS")
    print("cheap fake carrier excluded: PASS")
    print("AI cannot substitute for physical carrier: PASS")
    print("cross-border human customs review: PASS")
    print("missing hazmat supply fails safely: PASS")
    print("insufficient budget fails safely: PASS")
    print("NOTE: synthetic capability simulation; no real freight moved or money paid.")


if __name__ == "__main__":
    main()
