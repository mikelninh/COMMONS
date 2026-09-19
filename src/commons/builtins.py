from __future__ import annotations

from commons.models import (
    AuthorityLevel,
    CapabilityOffer,
    ProviderKind,
    ProviderProfile,
    VerificationStatus,
)
from commons.registry import CapabilityRegistry


def seed_builtin_capabilities(registry: CapabilityRegistry) -> None:
    """Register capabilities COMMONS can actually provide today.

    These are internal, code-backed capabilities. Price remains unknown until
    measured provider/tool costs are wired into the cost ledger.
    """

    ai = registry.register_provider(
        ProviderProfile(
            provider_id="commons-ai",
            name="COMMONS Decision Agents",
            kind=ProviderKind.AI,
            description="Typed probabilistic decision capabilities backed by Jev.",
            verification_status=VerificationStatus.VERIFIED,
        )
    )

    software = registry.register_provider(
        ProviderProfile(
            provider_id="commons-core",
            name="COMMONS Deterministic Core",
            kind=ProviderKind.SOFTWARE,
            description="Inspectable policy, filtering, proof and budget constraints.",
            verification_status=VerificationStatus.VERIFIED,
        )
    )

    offers = [
        CapabilityOffer(
            capability_id="commons-need-router",
            provider_id=ai.provider_id,
            capability_type="need_routing",
            description="Classify a messy need into domain, stakes, information sufficiency and next capability.",
            tags=["routing", "triage", "classification"],
            authority_ceiling=AuthorityLevel.READ,
            verification_status=VerificationStatus.VERIFIED,
            price_eur=None,
        ),
        CapabilityOffer(
            capability_id="commons-authority-reviewer",
            provider_id=ai.provider_id,
            capability_type="authority_review",
            description="Evaluate whether a selected capability may be automated, needs human review, evidence or reversibility.",
            tags=["authority", "safety", "review"],
            authority_ceiling=AuthorityLevel.READ,
            verification_status=VerificationStatus.VERIFIED,
            price_eur=None,
        ),
        CapabilityOffer(
            capability_id="commons-evidence-integrity",
            provider_id=ai.provider_id,
            capability_type="evidence_integrity",
            description="Judge whether claimed evidence or outcome proof requires independent verification before reliance.",
            tags=["evidence", "verification", "integrity"],
            authority_ceiling=AuthorityLevel.READ,
            verification_status=VerificationStatus.VERIFIED,
            price_eur=None,
        ),
        CapabilityOffer(
            capability_id="commons-live-selector",
            provider_id=ai.provider_id,
            capability_type="capability_selection",
            description="Choose the best next fit among a deterministic shortlist of currently feasible live capabilities.",
            tags=["selection", "coordination", "matching"],
            authority_ceiling=AuthorityLevel.READ,
            verification_status=VerificationStatus.VERIFIED,
            price_eur=None,
        ),
        CapabilityOffer(
            capability_id="commons-capability-filter",
            provider_id=software.provider_id,
            capability_type="capability_filtering",
            description="Filter supply by authority, provider type, language, location, price and verification constraints.",
            tags=["filter", "policy", "matching"],
            authority_ceiling=AuthorityLevel.READ,
            verification_status=VerificationStatus.VERIFIED,
            price_eur=None,
        ),
        CapabilityOffer(
            capability_id="commons-proof-guard",
            provider_id=software.provider_id,
            capability_type="proof_integrity",
            description="Reject invalid external proof, including providers independently verifying their own outcomes.",
            tags=["proof", "integrity", "verification"],
            authority_ceiling=AuthorityLevel.READ,
            verification_status=VerificationStatus.VERIFIED,
            price_eur=None,
        ),
        CapabilityOffer(
            capability_id="commons-budget-guard",
            provider_id=software.provider_id,
            capability_type="budget_enforcement",
            description="Enforce hard resource budgets and refuse unpriced capabilities in cost-proof experiments.",
            tags=["budget", "cost", "guardrail"],
            authority_ceiling=AuthorityLevel.READ,
            verification_status=VerificationStatus.VERIFIED,
            price_eur=None,
        ),
    ]

    for offer in offers:
        registry.register_capability(offer)
