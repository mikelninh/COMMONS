from __future__ import annotations

from typing import Any

from typesafe_sdk import Choice, Noul, NoulCriteria, Score, TypeSafeClient

from commons.models import Assessment, ProblemInput


DOMAIN_CRITERIA = {
    "education": "Learning, teaching, tutoring, skills or educational access.",
    "health": "Physical or mental health, healthcare or medical services.",
    "legal": "Laws, rights, legal processes or legal representation.",
    "public_services": "Government, benefits, public administration or social services.",
    "democracy": "Public policy, legislation, civic participation, consultation, elections or democratic processes.",
    "community": "A local collective problem requiring people or organisations to coordinate.",
    "finance": "Personal money, debt, payments, insurance or financial planning.",
    "business": "Running or starting an organisation or commercial activity.",
    "software": "Programming, debugging, infrastructure or digital systems.",
    "science": "Research, evidence, experiments or scientific questions.",
    "agriculture": "Farming, crops, soil, irrigation, livestock or food production.",
    "logistics": "Transport, supply chains, storage, delivery or coordination of goods.",
    "personal": "A personal practical problem not better covered elsewhere.",
    "other": "None of the listed domains clearly fits.",
}

CAPABILITY_CRITERIA = {
    "retrieve": "Find authoritative information, rules, services or evidence.",
    "calculate": "Use deterministic computation, optimisation or data processing.",
    "reason": "Perform deeper analysis, planning, explanation or synthesis.",
    "deliberate": "Structure evidence, affected groups, uncertainties and trade-offs while leaving the contested choice to humans.",
    "coordinate": "Coordinate people, organisations, tasks, resources or hand-offs.",
    "public_service_navigation": "Navigate a government, public-administration, benefits or public-service process. Do not use this for private landlord, utility, banking or ordinary commercial disputes.",
    "translate": "Translate or mediate language as the primary capability.",
    "specialist": "A qualified domain specialist is needed, for example for consequential legal, financial, clinical or technical interpretation or advice.",
    "workflow": "Use software tools or APIs to execute a bounded multi-step task.",
    "human": "A human expert or accountable reviewer is the appropriate next capability.",
    "ask_for_information": "Obtain missing information before choosing another route.",
    "other": "None of the listed capabilities clearly fits.",
}


def _input_tokens(response: Any) -> int | None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    if isinstance(usage, dict):
        value = usage.get("input_tokens")
    else:
        value = getattr(usage, "input_tokens", None)
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


class JevDecisionEngine:
    """Turn messy problem state into typed probabilistic judgments."""

    def evaluate(self, problem: ProblemInput) -> Assessment:
        state: dict[str, Any] = {
            "problem": problem.text,
            "language": problem.language,
            "mode": problem.mode,
            "context": problem.context,
            "purpose": (
                "COMMONS decision support. Classify and route. For political or civic value conflicts, "
                "structure evidence and deliberation but do not decide how a person should vote or which political choice is correct."
            ),
        }

        questions = {
            "domain": Choice(
                instructions="What is the primary domain of the concrete need?",
                criteria=DOMAIN_CRITERIA,
            ),
            "urgency": Score(
                instructions="How time-sensitive is this problem?",
                criteria=[
                    "No meaningful time pressure.",
                    "Routine; delay is unlikely to matter.",
                    "Time-sensitive; delay could noticeably worsen the outcome.",
                    "Urgent; action should happen soon.",
                    "Immediate; delay could cause serious harm or irreversible loss.",
                ],
            ),
            "high_stakes": Noul(
                instructions=(
                    "Could a wrong next action materially affect health, safety, legal status, rights, "
                    "significant finances, democratic legitimacy, or another consequential interest?"
                ),
                criteria=NoulCriteria(
                    true="A wrong action could cause meaningful harm, loss, rights impact or legitimacy failure.",
                    false="The likely consequences of a wrong route are limited and recoverable.",
                ),
            ),
            "enough_information": Noul(
                instructions="Is there enough information to select a useful next capability without inventing missing facts?",
            ),
            "safe_to_automate": Noul(
                instructions=(
                    "Would it be safe for software to perform the next consequential action automatically "
                    "without explicit human approval, under ordinary least-privilege permissions?"
                ),
            ),
            "needs_human_review": Noul(
                instructions="Should an accountable or qualified human review the situation before consequential action is taken?",
            ),
            "affected_groups_present": Noul(
                instructions="Does the decision materially affect people beyond the person asking?",
            ),
            "contested_values_present": Noul(
                instructions=(
                    "Does this situation contain legitimate value trade-offs where reasonable people may disagree "
                    "about goals, fairness, rights, distribution or acceptable costs?"
                ),
            ),
            "evidence_need": Score(
                instructions="How much additional evidence is needed before a consequential decision?",
                criteria=["None.", "Minor.", "Moderate.", "Substantial.", "Critical."],
            ),
            "reversibility": Score(
                instructions="How reversible is the likely next action?",
                criteria=[
                    "Effectively irreversible.",
                    "Hard to reverse.",
                    "Partly reversible.",
                    "Mostly reversible.",
                    "Fully reversible.",
                ],
            ),
            "capability": Choice(
                instructions=(
                    "What primary capability is needed next? This is routing, not a final political recommendation."
                ),
                criteria=CAPABILITY_CRITERIA,
            ),
        }

        with TypeSafeClient() as client:
            response = client.system_one(state=state, questions=questions)

        domain = response.choices["domain"]
        capability = response.choices["capability"]

        return Assessment(
            domain=domain.choice,
            urgency=float(response.scores["urgency"].score),
            high_stakes=float(response.nouls["high_stakes"].noul),
            enough_information=float(response.nouls["enough_information"].noul),
            safe_to_automate=float(response.nouls["safe_to_automate"].noul),
            needs_human_review=float(response.nouls["needs_human_review"].noul),
            affected_groups_present=float(response.nouls["affected_groups_present"].noul),
            contested_values_present=float(response.nouls["contested_values_present"].noul),
            evidence_need=float(response.scores["evidence_need"].score),
            reversibility=float(response.scores["reversibility"].score),
            capability=capability.choice,
            domain_confidence=getattr(domain, "confidence", None),
            capability_confidence=getattr(capability, "confidence", None),
            model=getattr(response, "model", None),
            input_tokens=_input_tokens(response),
        )
