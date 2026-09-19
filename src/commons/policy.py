from __future__ import annotations

from commons.models import Assessment, Route, RouteDecision

POLICY_VERSION = "0.1.0"

HIGH_STAKES_THRESHOLD = 0.70
HUMAN_REVIEW_THRESHOLD = 0.70
ENOUGH_INFORMATION_THRESHOLD = 0.45
MIN_CHOICE_CONFIDENCE = 0.55

CAPABILITY_ROUTES = {
    "retrieve": Route.RETRIEVE,
    "calculate": Route.CALCULATE,
    "reason": Route.REASON,
    "translate": Route.TRANSLATE,
    "specialist": Route.SPECIALIST,
    "workflow": Route.WORKFLOW,
    "human": Route.HUMAN,
    "other": Route.REASON,
}


def choose_route(a: Assessment) -> RouteDecision:
    """Apply inspectable authority rules to model judgments."""

    if a.high_stakes >= HIGH_STAKES_THRESHOLD:
        return RouteDecision(
            route=Route.HUMAN,
            reason=f"High-stakes probability {a.high_stakes:.2f} exceeds policy threshold.",
            policy_version=POLICY_VERSION,
        )

    if a.needs_human_review >= HUMAN_REVIEW_THRESHOLD:
        return RouteDecision(
            route=Route.HUMAN,
            reason=f"Human-review probability {a.needs_human_review:.2f} exceeds policy threshold.",
            policy_version=POLICY_VERSION,
        )

    if a.enough_information <= ENOUGH_INFORMATION_THRESHOLD:
        return RouteDecision(
            route=Route.REQUEST_INFO,
            reason=f"Information sufficiency {a.enough_information:.2f} is too low to route safely.",
            policy_version=POLICY_VERSION,
        )

    confidences = [
        value
        for value in (a.domain_confidence, a.capability_confidence)
        if value is not None
    ]
    if confidences and min(confidences) < MIN_CHOICE_CONFIDENCE:
        return RouteDecision(
            route=Route.REQUEST_INFO,
            reason=f"Decision confidence {min(confidences):.2f} is below policy threshold.",
            policy_version=POLICY_VERSION,
        )

    route = CAPABILITY_ROUTES.get(a.capability, Route.REASON)

    # v0.1 never gives workflow automation authority when Jev says automation is unsafe.
    if route is Route.WORKFLOW and a.safe_to_automate < 0.65:
        return RouteDecision(
            route=Route.HUMAN,
            reason=(
                f"Workflow was selected but automation-safety probability "
                f"{a.safe_to_automate:.2f} is below policy threshold."
            ),
            policy_version=POLICY_VERSION,
        )

    return RouteDecision(
        route=route,
        reason=f"Policy accepted capability route '{a.capability}'.",
        policy_version=POLICY_VERSION,
    )
