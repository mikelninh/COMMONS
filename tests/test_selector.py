from commons.models import (
    AuthorityLevel,
    CapabilityMatch,
    CapabilityOffer,
    ProviderKind,
    ProviderProfile,
    VerificationStatus,
)
from commons.selector import build_live_choice_criteria


def test_live_menu_contains_only_supplied_candidates_and_provider_type() -> None:
    human = ProviderProfile(
        name="Human Translator",
        kind=ProviderKind.PERSON,
        verification_status=VerificationStatus.VERIFIED,
    )
    agent = ProviderProfile(
        name="Translation Agent",
        kind=ProviderKind.AI,
        verification_status=VerificationStatus.VERIFIED,
    )

    human_offer = CapabilityOffer(
        provider_id=human.provider_id,
        capability_type="translation",
        description="Nuanced Vietnamese/German translation.",
        languages=["vi", "de"],
        price_eur=0.80,
        authority_ceiling=AuthorityLevel.DRAFT,
        verification_status=VerificationStatus.VERIFIED,
    )
    agent_offer = CapabilityOffer(
        provider_id=agent.provider_id,
        capability_type="translation",
        description="Fast machine translation.",
        languages=["vi", "de"],
        price_eur=0.05,
        authority_ceiling=AuthorityLevel.EXPLAIN,
        verification_status=VerificationStatus.VERIFIED,
    )

    candidates = [
        CapabilityMatch(capability=human_offer, score=0.92, reasons=["human preferred"]),
        CapabilityMatch(capability=agent_offer, score=0.80, reasons=["fast draft"]),
    ]
    criteria = build_live_choice_criteria(
        candidates,
        providers={human.provider_id: human, agent.provider_id: agent},
    )

    assert set(criteria) == {human_offer.capability_id, agent_offer.capability_id}
    assert "kind=person" in criteria[human_offer.capability_id]
    assert "kind=ai" in criteria[agent_offer.capability_id]
    assert "EUR 0.8000" in criteria[human_offer.capability_id]


def test_live_menu_rejects_empty_candidate_set() -> None:
    try:
        build_live_choice_criteria([])
    except ValueError as exc:
        assert "At least one feasible capability" in str(exc)
    else:
        raise AssertionError("Expected empty live menu to be rejected.")
