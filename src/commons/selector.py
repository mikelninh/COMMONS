from __future__ import annotations

from typing import Any

from typesafe_sdk import Choice, TypeSafeClient

from commons.models import CapabilityMatch, LiveCapabilitySelection, ProviderProfile


def _distribution(answer: Any) -> dict[str, float]:
    """Best-effort extraction across SDK response shapes."""
    for attr in ("probabilities", "distribution", "probs"):
        value = getattr(answer, attr, None)
        if isinstance(value, dict):
            out: dict[str, float] = {}
            for key, probability in value.items():
                try:
                    out[str(key)] = float(probability)
                except (TypeError, ValueError):
                    continue
            return out
    return {}


def build_live_choice_criteria(
    candidates: list[CapabilityMatch],
    providers: dict[str, ProviderProfile] | None = None,
) -> dict[str, str]:
    """Turn currently feasible capabilities into Jev Choice options.

    The option set is rebuilt every call from live state. Jev cannot select a
    capability that deterministic filtering has excluded.
    """
    if not candidates:
        raise ValueError("At least one feasible capability is required.")
    if len(candidates) > 255:
        raise ValueError("Jev Choice supports at most 255 live capability options.")

    criteria: dict[str, str] = {}
    for match in candidates:
        offer = match.capability
        provider = (providers or {}).get(offer.provider_id)
        price = "unknown" if offer.price_eur is None else f"EUR {offer.price_eur:.4f}"
        provider_text = (
            f"Provider={provider.name}; kind={provider.kind.value}; "
            f"provider verification={provider.verification_status.value}. "
            if provider is not None
            else "Provider metadata unavailable. "
        )
        criteria[offer.capability_id] = (
            f"{provider_text}"
            f"{offer.description} "
            f"Type={offer.capability_type}. "
            f"Authority ceiling={offer.authority_ceiling.value}. "
            f"Verification={offer.verification_status.value}. "
            f"Languages={','.join(offer.languages) or 'unspecified'}. "
            f"Location={offer.location or 'unspecified'}. "
            f"Capacity={offer.capacity_available:g} {offer.unit}. "
            f"Price={price}. "
            f"Deterministic fit score={match.score:.3f}. "
            f"Fit reasons={'; '.join(match.reasons) or 'none'}."
        )
    return criteria


class JevCapabilitySelector:
    """Choose among capabilities that code has already deemed feasible."""

    def choose(
        self,
        need: str,
        candidates: list[CapabilityMatch],
        *,
        context: dict[str, Any] | None = None,
        providers: dict[str, ProviderProfile] | None = None,
    ) -> LiveCapabilitySelection:
        criteria = build_live_choice_criteria(candidates, providers)
        state = {
            "need": need,
            "context": context or {},
            "candidate_count": len(candidates),
            "selection_principle": (
                "Choose the capability most likely to resolve the need well. "
                "Do not minimize price alone. Respect human-required or human-preferred "
                "constraints already encoded by the candidate set and fit scores. "
                "Prefer trustworthy fit, appropriate authority, expected outcome quality, "
                "and efficient use of resources."
            ),
        }

        with TypeSafeClient() as client:
            response = client.system_one(
                state=state,
                questions={
                    "capability": Choice(
                        instructions=(
                            "Which currently available capability is the best next fit "
                            "for this need? Choose only from the supplied live candidates."
                        ),
                        criteria=criteria,
                    )
                },
            )

        answer = response.choices["capability"]
        by_id = {match.capability.capability_id: match for match in candidates}
        selected = by_id.get(answer.choice)
        if selected is None:
            raise RuntimeError("Jev selected a capability outside the live candidate set.")

        return LiveCapabilitySelection(
            selected=selected,
            confidence=getattr(answer, "confidence", None),
            probabilities=_distribution(answer),
            candidate_count=len(candidates),
        )
