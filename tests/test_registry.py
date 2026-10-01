from commons.models import (
    AuthorityLevel,
    CapabilityOffer,
    CapabilityRequirement,
    ProviderKind,
    ProviderProfile,
    VerificationStatus,
)
from commons.registry import CapabilityRegistry


def test_unverified_provider_cannot_self_grant_execution_authority() -> None:
    registry = CapabilityRegistry()
    provider = registry.register_provider(
        ProviderProfile(name="New volunteer", kind=ProviderKind.PERSON)
    )
    offer = registry.register_capability(
        CapabilityOffer(
            provider_id=provider.provider_id,
            capability_type="transport",
            description="Can drive local deliveries.",
            authority_ceiling=AuthorityLevel.EXECUTE_CONSEQUENTIAL,
        )
    )
    assert offer.authority_ceiling is AuthorityLevel.DRAFT


def test_verified_capability_can_match_reversible_execution() -> None:
    registry = CapabilityRegistry()
    provider = registry.register_provider(
        ProviderProfile(
            name="Verified courier",
            kind=ProviderKind.BUSINESS,
            verification_status=VerificationStatus.VERIFIED,
        )
    )
    offer = registry.register_capability(
        CapabilityOffer(
            provider_id=provider.provider_id,
            capability_type="transport",
            description="Local same-day delivery.",
            tags=["food", "delivery"],
            location="Berlin",
            price_eur=4.0,
            authority_ceiling=AuthorityLevel.EXECUTE_REVERSIBLE,
            verification_status=VerificationStatus.VERIFIED,
            success_count=9,
            failure_count=1,
        )
    )
    matches = registry.match(
        CapabilityRequirement(
            capability_type="transport",
            tags=["food"],
            location="Berlin",
            max_price_eur=5.0,
            required_authority=AuthorityLevel.EXECUTE_REVERSIBLE,
            require_verified_provider=True,
        )
    )
    assert matches
    assert matches[0].capability.capability_id == offer.capability_id


def test_suspended_provider_is_never_matched() -> None:
    registry = CapabilityRegistry()
    provider = registry.register_provider(
        ProviderProfile(
            name="Suspended provider",
            kind=ProviderKind.PERSON,
            verification_status=VerificationStatus.SUSPENDED,
        )
    )
    registry.register_capability(
        CapabilityOffer(
            provider_id=provider.provider_id,
            capability_type="translation",
            description="Translation service",
            languages=["vi"],
        )
    )
    assert registry.match(
        CapabilityRequirement(capability_type="translation", language="vi")
    ) == []


def test_price_ceiling_is_respected() -> None:
    registry = CapabilityRegistry()
    provider = registry.register_provider(
        ProviderProfile(name="Translator", kind=ProviderKind.PERSON)
    )
    registry.register_capability(
        CapabilityOffer(
            provider_id=provider.provider_id,
            capability_type="translation",
            description="Vietnamese translation",
            languages=["vi"],
            price_eur=12.0,
        )
    )
    assert registry.match(
        CapabilityRequirement(
            capability_type="translation",
            language="vi",
            max_price_eur=5.0,
        )
    ) == []
