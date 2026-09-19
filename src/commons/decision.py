from __future__ import annotations

from typing import Any

from typesafe_sdk import Choice, Noul, NoulCriteria, Score, TypeSafeClient

from commons.models import Assessment, ProblemInput


DOMAIN_CRITERIA = {
    "education": "Learning, teaching, tutoring, skills or educational access.",
    "health": "Physical or mental health, healthcare or medical services.",
    "legal": "Laws, rights, legal processes or legal representation.",
    "public_services": "Government, benefits, public administration or social services.",
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
    "retrieve": "Find reliable information or evidence.",
    "calculate": "Use deterministic computation, optimisation or data processing.",
    "reason": "Perform deeper analysis, planning or synthesis.",
    "translate": "Translate or mediate language as the primary capability.",
    "specialist": "A domain specialist or specialist system is required.",
    "workflow": "Use software tools or APIs to execute a multi-step task.",
    "human": "A human expert or accountable reviewer is the appropriate next capability.",
    "other": "None of the listed capabilities clearly fits.",
}


class JevDecisionEngine:
    """Turn messy problem state into a small set of typed probabilistic judgments."""

    def evaluate(self, problem: ProblemInput) -> Assessment:
        state: dict[str, Any] = {
            "problem": problem.text,
            "language": problem.language,
            "context": problem.context,
        }

        questions = {
            "domain": Choice(
                instructions="What is the primary domain of the problem?",
                criteria=DOMAIN_CRITERIA,
            ),
            "urgency": Score(
                instructions="How time-sensitive is this problem?",
                criteria=[
                    "No meaningful time pressure.",
                    "Routine; delay is unlikely to matter.",
                    "Time-sensitive; delay could noticeably worsen the outcome.",
                    "Urgent; action should happen soon.",
                    "Immediate; delay could cause serious harm or loss.",
                ],
            ),
            "high_stakes": Noul(
                instructions=(
                    "Could a wrong next action materially affect health, safety, legal status, "
                    "rights, significant finances, or another consequential interest?"
                ),
                criteria=NoulCriteria(
                    true="A wrong action could cause meaningful harm or loss.",
                    false="The likely consequences of a wrong route are limited and recoverable.",
                ),
            ),
            "enough_information": Noul(
                instructions="Is there enough information to select a useful next capability without inventing missing facts?",
            ),
            "safe_to_automate": Noul(
                instructions=(
                    "Would it be safe for software to take the next meaningful action automatically "
                    "under ordinary least-privilege permissions?"
                ),
            ),
            "needs_human_review": Noul(
                instructions=(
                    "Should an accountable human review the situation before a consequential action is taken?"
                ),
            ),
            "capability": Choice(
                instructions="What primary capability is needed next?",
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
            capability=capability.choice,
            domain_confidence=getattr(domain, "confidence", None),
            capability_confidence=getattr(capability, "confidence", None),
            model=getattr(response, "model", None),
        )
