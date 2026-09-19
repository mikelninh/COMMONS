from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


TaskState = Literal[
    "TASK_STATE_SUBMITTED",
    "TASK_STATE_WORKING",
    "TASK_STATE_COMPLETED",
    "TASK_STATE_FAILED",
]


class AgentInterface(BaseModel):
    url: str
    protocol_binding: Literal["HTTP+JSON"] = "HTTP+JSON"
    protocol_version: Literal["1.0"] = "1.0"


class AgentSkill(BaseModel):
    skill_id: str
    name: str
    description: str
    input_modes: list[str] = Field(default_factory=lambda: ["application/json"])
    output_modes: list[str] = Field(default_factory=lambda: ["application/json"])


class AgentCard(BaseModel):
    agent_id: str
    name: str
    description: str
    version: str = "1.0.0"
    supported_interfaces: list[AgentInterface]
    skills: list[AgentSkill]
    price_eur: float = Field(ge=0)
    verified: bool = True


class A2AArtifact(BaseModel):
    artifact_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    data: dict[str, Any]
    produced_by: str
    requested_next_skill: str | None = None


class A2ATask(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid4()))
    context_id: str
    agent_id: str
    skill_id: str
    state: TaskState
    input: dict[str, Any]
    artifact: A2AArtifact | None = None
    error: str | None = None
    cost_eur: float = Field(default=0.0, ge=0)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None


class HandoffReceipt(BaseModel):
    receipt_id: str = Field(default_factory=lambda: str(uuid4()))
    requested_by: str
    skill_id: str
    selected_agent_id: str
    candidate_agent_ids: list[str]
    reason: str
    task_id: str
    state: TaskState


class ProcurementRequest(BaseModel):
    objective: str = Field(min_length=8, max_length=2000)
    budget_eur: float = Field(default=0.25, ge=0.01, le=100)
    simulate_primary_failure: bool = True


class ProcurementResult(BaseModel):
    context_id: str
    objective: str
    budget_eur: float
    spent_eur: float
    within_budget: bool
    agent_cards: list[AgentCard]
    tasks: list[A2ATask]
    handoffs: list[HandoffReceipt]
    final_artifact: A2AArtifact | None
    verified: bool
    summary: str


def _card(
    agent_id: str,
    name: str,
    description: str,
    skill_id: str,
    skill_name: str,
    skill_description: str,
    price_eur: float,
) -> AgentCard:
    return AgentCard(
        agent_id=agent_id,
        name=name,
        description=description,
        supported_interfaces=[
            AgentInterface(url=f"/a2a/agents/{agent_id}/message:send")
        ],
        skills=[
            AgentSkill(
                skill_id=skill_id,
                name=skill_name,
                description=skill_description,
            )
        ],
        price_eur=price_eur,
    )


AGENTS = [
    _card(
        "strategy-agent",
        "Strategy Agent",
        "Turns a product objective into a concise audience/problem/promise brief and requests the next capability.",
        "strategy_brief",
        "Strategy brief",
        "Produce audience, problem, promise, constraints, then request landing_copy.",
        0.02,
    ),
    _card(
        "copy-agent-alpha",
        "Copy Agent Alpha",
        "Primary landing-page copy provider. Intentionally failure-testable.",
        "landing_copy",
        "Landing copy",
        "Turn a strategy brief into headline, subheadline and CTA.",
        0.03,
    ),
    _card(
        "copy-agent-beta",
        "Copy Agent Beta",
        "Backup landing-page copy provider with the same declared skill.",
        "landing_copy",
        "Landing copy",
        "Turn a strategy brief into headline, subheadline and CTA.",
        0.04,
    ),
    _card(
        "qa-agent",
        "Independent QA Agent",
        "Checks whether the final launch artifact satisfies the requested structure without being the producing agent.",
        "verify_launch_kit",
        "Verify launch kit",
        "Check required strategy and landing-copy fields and return evidence.",
        0.02,
    ),
]


def list_agent_cards() -> list[AgentCard]:
    return [card.model_copy(deep=True) for card in AGENTS]


def _agent(agent_id: str) -> AgentCard:
    for card in AGENTS:
        if card.agent_id == agent_id:
            return card
    raise KeyError(agent_id)


def _candidates(skill_id: str) -> list[AgentCard]:
    return [
        card
        for card in AGENTS
        if card.verified and any(skill.skill_id == skill_id for skill in card.skills)
    ]


def _product_name(objective: str) -> str:
    cleaned = " ".join(objective.strip().split())
    if ":" in cleaned:
        prefix = cleaned.split(":", 1)[0].strip()
        if 2 <= len(prefix) <= 60:
            return prefix
    words = cleaned.split()
    return " ".join(words[:5]).rstrip(".,") or "the product"


def _run_strategy(context_id: str, objective: str) -> A2ATask:
    card = _agent("strategy-agent")
    product = _product_name(objective)
    artifact = A2AArtifact(
        name="strategy-brief",
        produced_by=card.agent_id,
        requested_next_skill="landing_copy",
        data={
            "product": product,
            "audience": "people who feel the problem described in the objective strongly enough to try a simpler solution",
            "problem": objective.strip(),
            "promise": f"{product} should make the desired outcome clearer, faster, and easier to act on.",
            "constraints": [
                "state only what the objective supports",
                "one clear primary action",
                "avoid invented proof or customer claims",
            ],
        },
    )
    return A2ATask(
        context_id=context_id,
        agent_id=card.agent_id,
        skill_id="strategy_brief",
        state="TASK_STATE_COMPLETED",
        input={"objective": objective},
        artifact=artifact,
        cost_eur=card.price_eur,
        completed_at=datetime.now(timezone.utc),
    )


def _run_copy(
    context_id: str,
    card: AgentCard,
    strategy: A2AArtifact,
    *,
    fail: bool,
) -> A2ATask:
    if fail:
        return A2ATask(
            context_id=context_id,
            agent_id=card.agent_id,
            skill_id="landing_copy",
            state="TASK_STATE_FAILED",
            input={"strategy_artifact_id": strategy.artifact_id},
            error="Simulated provider failure: agent became unavailable after accepting the task.",
            cost_eur=0.01,
            completed_at=datetime.now(timezone.utc),
        )

    product = str(strategy.data["product"])
    promise = str(strategy.data["promise"])
    artifact = A2AArtifact(
        name="landing-copy",
        produced_by=card.agent_id,
        requested_next_skill="verify_launch_kit",
        data={
            "headline": f"{product}, without the usual friction.",
            "subheadline": promise,
            "cta": "Try the simplest useful version",
        },
    )
    return A2ATask(
        context_id=context_id,
        agent_id=card.agent_id,
        skill_id="landing_copy",
        state="TASK_STATE_COMPLETED",
        input={"strategy_artifact_id": strategy.artifact_id},
        artifact=artifact,
        cost_eur=card.price_eur,
        completed_at=datetime.now(timezone.utc),
    )


def _run_qa(
    context_id: str,
    strategy: A2AArtifact,
    copy: A2AArtifact,
) -> A2ATask:
    card = _agent("qa-agent")
    required_strategy = {"product", "audience", "problem", "promise", "constraints"}
    required_copy = {"headline", "subheadline", "cta"}
    missing_strategy = sorted(required_strategy - set(strategy.data))
    missing_copy = sorted(required_copy - set(copy.data))
    independent = card.agent_id not in {strategy.produced_by, copy.produced_by}
    passed = not missing_strategy and not missing_copy and independent
    artifact = A2AArtifact(
        name="verification-report",
        produced_by=card.agent_id,
        data={
            "passed": passed,
            "independent_verifier": independent,
            "missing_strategy_fields": missing_strategy,
            "missing_copy_fields": missing_copy,
            "evidence": [
                f"strategy artifact {strategy.artifact_id}",
                f"copy artifact {copy.artifact_id}",
            ],
        },
    )
    return A2ATask(
        context_id=context_id,
        agent_id=card.agent_id,
        skill_id="verify_launch_kit",
        state="TASK_STATE_COMPLETED" if passed else "TASK_STATE_FAILED",
        input={
            "strategy_artifact_id": strategy.artifact_id,
            "copy_artifact_id": copy.artifact_id,
        },
        artifact=artifact,
        error=None if passed else "Verification failed.",
        cost_eur=card.price_eur,
        completed_at=datetime.now(timezone.utc),
    )


def run_procurement(request: ProcurementRequest) -> ProcurementResult:
    context_id = str(uuid4())
    tasks: list[A2ATask] = []
    handoffs: list[HandoffReceipt] = []
    spent = 0.0

    strategy = _run_strategy(context_id, request.objective)
    if spent + strategy.cost_eur > request.budget_eur:
        return ProcurementResult(
            context_id=context_id,
            objective=request.objective,
            budget_eur=request.budget_eur,
            spent_eur=0.0,
            within_budget=False,
            agent_cards=list_agent_cards(),
            tasks=[],
            handoffs=[],
            final_artifact=None,
            verified=False,
            summary="Budget too low to start the first delegated task.",
        )
    tasks.append(strategy)
    spent += strategy.cost_eur

    copy_candidates = sorted(_candidates("landing_copy"), key=lambda c: c.price_eur)
    if not copy_candidates:
        raise RuntimeError("No landing_copy agents available.")

    primary = copy_candidates[0]
    primary_task = _run_copy(
        context_id,
        primary,
        strategy.artifact,
        fail=request.simulate_primary_failure,
    )
    if spent + primary_task.cost_eur > request.budget_eur:
        return ProcurementResult(
            context_id=context_id,
            objective=request.objective,
            budget_eur=request.budget_eur,
            spent_eur=round(spent, 4),
            within_budget=False,
            agent_cards=list_agent_cards(),
            tasks=tasks,
            handoffs=handoffs,
            final_artifact=None,
            verified=False,
            summary="Budget exhausted before the copy delegation could be attempted.",
        )
    tasks.append(primary_task)
    spent += primary_task.cost_eur
    handoffs.append(
        HandoffReceipt(
            requested_by=strategy.agent_id,
            skill_id="landing_copy",
            selected_agent_id=primary.agent_id,
            candidate_agent_ids=[c.agent_id for c in copy_candidates],
            reason="Selected lowest-cost verified agent declaring the requested skill.",
            task_id=primary_task.task_id,
            state=primary_task.state,
        )
    )

    copy_task = primary_task
    if primary_task.state == "TASK_STATE_FAILED":
        backups = [c for c in copy_candidates if c.agent_id != primary.agent_id]
        if not backups:
            return ProcurementResult(
                context_id=context_id,
                objective=request.objective,
                budget_eur=request.budget_eur,
                spent_eur=round(spent, 4),
                within_budget=True,
                agent_cards=list_agent_cards(),
                tasks=tasks,
                handoffs=handoffs,
                final_artifact=None,
                verified=False,
                summary="Primary copy agent failed and no backup agent was available.",
            )
        backup = backups[0]
        backup_task = _run_copy(context_id, backup, strategy.artifact, fail=False)
        if spent + backup_task.cost_eur > request.budget_eur:
            return ProcurementResult(
                context_id=context_id,
                objective=request.objective,
                budget_eur=request.budget_eur,
                spent_eur=round(spent, 4),
                within_budget=False,
                agent_cards=list_agent_cards(),
                tasks=tasks,
                handoffs=handoffs,
                final_artifact=None,
                verified=False,
                summary="Primary agent failed; a backup existed but the remaining budget could not fund rerouting.",
            )
        tasks.append(backup_task)
        spent += backup_task.cost_eur
        handoffs.append(
            HandoffReceipt(
                requested_by="commons-router",
                skill_id="landing_copy",
                selected_agent_id=backup.agent_id,
                candidate_agent_ids=[c.agent_id for c in backups],
                reason="Primary task failed; rerouted to the next verified compatible agent.",
                task_id=backup_task.task_id,
                state=backup_task.state,
            )
        )
        copy_task = backup_task

    qa_candidates = _candidates("verify_launch_kit")
    qa = qa_candidates[0]
    qa_task = _run_qa(context_id, strategy.artifact, copy_task.artifact)
    if spent + qa_task.cost_eur > request.budget_eur:
        return ProcurementResult(
            context_id=context_id,
            objective=request.objective,
            budget_eur=request.budget_eur,
            spent_eur=round(spent, 4),
            within_budget=False,
            agent_cards=list_agent_cards(),
            tasks=tasks,
            handoffs=handoffs,
            final_artifact=None,
            verified=False,
            summary="The work was produced, but the budget was too low to fund independent verification.",
        )
    tasks.append(qa_task)
    spent += qa_task.cost_eur
    handoffs.append(
        HandoffReceipt(
            requested_by=copy_task.agent_id,
            skill_id="verify_launch_kit",
            selected_agent_id=qa.agent_id,
            candidate_agent_ids=[c.agent_id for c in qa_candidates],
            reason="Producing agent requested independent verification; self-verification is excluded.",
            task_id=qa_task.task_id,
            state=qa_task.state,
        )
    )

    verified = bool(qa_task.artifact and qa_task.artifact.data.get("passed"))
    final = None
    if verified:
        final = A2AArtifact(
            name="verified-launch-kit",
            produced_by="commons-router",
            data={
                "strategy": strategy.artifact.data,
                "landing_copy": copy_task.artifact.data,
                "verification": qa_task.artifact.data,
                "task_ids": [task.task_id for task in tasks],
                "handoff_receipt_ids": [receipt.receipt_id for receipt in handoffs],
            },
        )

    return ProcurementResult(
        context_id=context_id,
        objective=request.objective,
        budget_eur=request.budget_eur,
        spent_eur=round(spent, 4),
        within_budget=spent <= request.budget_eur,
        agent_cards=list_agent_cards(),
        tasks=tasks,
        handoffs=handoffs,
        final_artifact=final,
        verified=verified,
        summary=(
            "Objective completed through agent delegation, failure rerouting, and independent verification."
            if verified
            else "The agent network did not produce a verified final artifact."
        ),
    )
