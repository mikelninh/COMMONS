from __future__ import annotations

from commons.models import Assessment, Route, RouteDecision

POLICY_VERSION = "0.2.1"

HIGH_STAKES_THRESHOLD = 0.70
HUMAN_REVIEW_THRESHOLD = 0.70
ENOUGH_INFORMATION_THRESHOLD = 0.45
MIN_CHOICE_CONFIDENCE = 0.55
CONTESTED_VALUES_THRESHOLD = 0.65
AUTOMATION_SAFETY_THRESHOLD = 0.65

# A high-stakes *case* is not automatically a high-authority *action*.
# Informational support can remain useful in consequential situations.
# These domains are the v0.2.1 exception: when the underlying domain itself
# is health/legal/finance and stakes are high, route to accountable human help.
HIGH_STAKES_ESCALATION_DOMAINS = {"health", "legal", "finance"}

CAPABILITY_ROUTES = {
    "retrieve": Route.RETRIEVE,
    "calculate": Route.CALCULATE,
    "reason": Route.REASON,
    "deliberate": Route.DELIBERATE,
    "coordinate": Route.REASON,
    "public_service_navigation": Route.RETRIEVE,
    "translate": Route.TRANSLATE,
    "specialist": Route.SPECIALIST,
    "workflow": Route.WORKFLOW,
    "human": Route.HUMAN,
    "ask_for_information": Route.REQUEST_INFO,
    "other": Route.REASON,
}


def choose_route(a: Assessment) -> RouteDecision:
    """Apply inspectable authority rules to model judgments.

    v0.2.1 separates *stakes* from *authority*. A consequential situation may
    still safely receive read/explain/translate support. The policy becomes
    stricter when the selected route itself can execute or when the underlying
    domain requires accountable professional review.

    DELIBERATE is intentionally non-executive: the system may structure evidence,
    affected groups, uncertainty and trade-offs, but the contested value choice
    remains with people and legitimate institutions.
    """

    confidences = [
        value
        for value in (a.domain_confidence, a.capability_confidence)
        if value is not None
    ]

    civic_value_conflict = (
        a.domain in {"democracy", "community"}
        and a.contested_values_present >= CONTESTED_VALUES_THRESHOLD
    )

    if civic_value_conflict:
        if a.enough_information <= ENOUGH_INFORMATION_THRESHOLD:
            return RouteDecision(
                route=Route.REQUEST_INFO,
                reason=(
                    "The issue contains a civic value conflict, but information sufficiency "
                    f"{a.enough_information:.2f} is too low for responsible deliberation."
                ),
                policy_version=POLICY_VERSION,
            )
        if confidences and min(confidences) < MIN_CHOICE_CONFIDENCE:
            return RouteDecision(
                route=Route.REQUEST_INFO,
                reason=(
                    "The issue contains a civic value conflict, but decision confidence "
                    f"{min(confidences):.2f} is below policy threshold."
                ),
                policy_version=POLICY_VERSION,
            )
        return RouteDecision(
            route=Route.DELIBERATE,
            reason=(
                "Legitimate value trade-offs are present. COMMONS may structure evidence, "
                "affected groups, uncertainties and options, but may not make the political choice."
            ),
            policy_version=POLICY_VERSION,
        )

    if a.enough_information <= ENOUGH_INFORMATION_THRESHOLD:
        return RouteDecision(
            route=Route.REQUEST_INFO,
            reason=f"Information sufficiency {a.enough_information:.2f} is too low to route safely.",
            policy_version=POLICY_VERSION,
        )

    if confidences and min(confidences) < MIN_CHOICE_CONFIDENCE:
        return RouteDecision(
            route=Route.REQUEST_INFO,
            reason=f"Decision confidence {min(confidences):.2f} is below policy threshold.",
            policy_version=POLICY_VERSION,
        )

    route = CAPABILITY_ROUTES.get(a.capability, Route.REASON)

    if (
        a.high_stakes >= HIGH_STAKES_THRESHOLD
        and a.domain in HIGH_STAKES_ESCALATION_DOMAINS
    ):
        return RouteDecision(
            route=Route.HUMAN,
            reason=(
                f"High-stakes probability {a.high_stakes:.2f} in '{a.domain}' "
                "requires accountable human review before consequential guidance."
            ),
            policy_version=POLICY_VERSION,
        )

    if route in {Route.HUMAN, Route.SPECIALIST}:
        return RouteDecision(
            route=Route.HUMAN,
            reason=f"Selected capability '{a.capability}' requires accountable human help.",
            policy_version=POLICY_VERSION,
        )

    if route is Route.WORKFLOW:
        if a.needs_human_review >= HUMAN_REVIEW_THRESHOLD:
            return RouteDecision(
                route=Route.HUMAN,
                reason=(
                    f"Workflow was selected but human-review probability "
                    f"{a.needs_human_review:.2f} exceeds policy threshold."
                ),
                policy_version=POLICY_VERSION,
            )
        if a.safe_to_automate < AUTOMATION_SAFETY_THRESHOLD:
            return RouteDecision(
                route=Route.HUMAN,
                reason=(
                    f"Workflow was selected but automation-safety probability "
                    f"{a.safe_to_automate:.2f} is below policy threshold."
                ),
                policy_version=POLICY_VERSION,
            )

    if a.high_stakes >= HIGH_STAKES_THRESHOLD:
        return RouteDecision(
            route=route,
            reason=(
                f"Case stakes are high ({a.high_stakes:.2f}), but the selected route "
                f"'{route.value}' is non-executive. COMMONS may assist without granting execution authority."
            ),
            policy_version=POLICY_VERSION,
        )

    return RouteDecision(
        route=route,
        reason=f"Policy accepted capability route '{a.capability}'.",
        policy_version=POLICY_VERSION,
    )
