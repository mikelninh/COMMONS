from __future__ import annotations

from commons.models import (
    AuthorityLevel,
    CapabilityMatch,
    CapabilityOffer,
    CapabilityRequirement,
    ProviderProfile,
    VerificationStatus,
)

AUTHORITY_RANK = {
    AuthorityLevel.READ: 1,
    AuthorityLevel.EXPLAIN: 2,
    AuthorityLevel.TRANSLATE: 2,
    AuthorityLevel.DRAFT: 3,
    AuthorityLevel.EXECUTE_REVERSIBLE: 4,
    AuthorityLevel.EXECUTE_CONSEQUENTIAL: 5,
    AuthorityLevel.PROHIBITED: 99,
}


class CapabilityRegistry:
    """Small v0.3 registry for declared supply.

    Important invariant: declaration is not authority. Unverified capabilities
    are capped at DRAFT even if a provider asks for a higher authority ceiling.
    """

    def __init__(self) -> None:
        self.providers: dict[str, ProviderProfile] = {}
        self.capabilities: dict[str, CapabilityOffer] = {}

    def register_provider(self, provider: ProviderProfile) -> ProviderProfile:
        self.providers[provider.provider_id] = provider
        return provider

    def register_capability(self, offer: CapabilityOffer) -> CapabilityOffer:
        provider = self.providers.get(offer.provider_id)
        if provider is None:
            raise KeyError(f"Unknown provider: {offer.provider_id}")

        effective = offer.model_copy(deep=True)

        provider_verified = provider.verification_status is VerificationStatus.VERIFIED
        offer_verified = offer.verification_status is VerificationStatus.VERIFIED
        if not (provider_verified and offer_verified):
            if AUTHORITY_RANK[effective.authority_ceiling] > AUTHORITY_RANK[AuthorityLevel.DRAFT]:
                effective.authority_ceiling = AuthorityLevel.DRAFT

        self.capabilities[effective.capability_id] = effective
        return effective

    def list_active(self) -> list[CapabilityOffer]:
        return [c for c in self.capabilities.values() if c.active]

    def match(self, requirement: CapabilityRequirement, limit: int = 5) -> list[CapabilityMatch]:
        matches: list[CapabilityMatch] = []
        requested_tags = {t.lower() for t in requirement.tags}

        for offer in self.list_active():
            provider = self.providers.get(offer.provider_id)
            if provider is None or provider.verification_status is VerificationStatus.SUSPENDED:
                continue
            if offer.verification_status is VerificationStatus.SUSPENDED:
                continue
            if offer.capability_type != requirement.capability_type:
                continue
            if AUTHORITY_RANK[offer.authority_ceiling] < AUTHORITY_RANK[requirement.required_authority]:
                continue
            if requirement.require_verified_provider and (
                provider.verification_status is not VerificationStatus.VERIFIED
                or offer.verification_status is not VerificationStatus.VERIFIED
            ):
                continue
            if requirement.max_price_eur is not None and offer.price_eur is not None:
                if offer.price_eur > requirement.max_price_eur:
                    continue
            if requirement.language and offer.languages:
                if requirement.language.lower() not in {x.lower() for x in offer.languages}:
                    continue

            reasons: list[str] = ["capability type matched"]
            score = 0.55

            offer_tags = {t.lower() for t in offer.tags}
            if requested_tags:
                overlap = len(requested_tags & offer_tags) / len(requested_tags)
                score += 0.20 * overlap
                if overlap:
                    reasons.append(f"{overlap:.0%} tag overlap")

            if requirement.language and requirement.language.lower() in {x.lower() for x in offer.languages}:
                score += 0.10
                reasons.append("language matched")

            if requirement.location and offer.location:
                if requirement.location.lower() in offer.location.lower() or offer.location.lower() in requirement.location.lower():
                    score += 0.08
                    reasons.append("location matched")

            if provider.verification_status is VerificationStatus.VERIFIED and offer.verification_status is VerificationStatus.VERIFIED:
                score += 0.05
                reasons.append("verified provider + capability")

            total_history = offer.success_count + offer.failure_count
            if total_history:
                success_rate = offer.success_count / total_history
                score += 0.02 * success_rate
                reasons.append(f"{success_rate:.0%} observed success")

            matches.append(
                CapabilityMatch(
                    capability=offer,
                    score=min(score, 1.0),
                    reasons=reasons,
                )
            )

        matches.sort(
            key=lambda m: (
                m.score,
                -(m.capability.price_eur if m.capability.price_eur is not None else 0.0),
            ),
            reverse=True,
        )
        return matches[:limit]
