from __future__ import annotations

import os
from typing import Literal

from pydantic import BaseModel, Field
from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

from commons.world_pulse import SignalCluster, WorldPulseResponse, WorldSignal


class PulseActionNode(BaseModel):
    node_id: str
    label: str
    kind: Literal["observe", "verify", "reason", "impact", "capability", "human"]
    status: Literal["done", "active", "waiting", "skipped"]
    detail: str


class WorldBriefItem(BaseModel):
    subject_id: str
    subject_type: Literal["signal", "cluster"]
    status: Literal["wake", "review", "watch"]
    title: str
    source_label: str
    why: list[str] = Field(default_factory=list)
    next_step: str


class WorldPulseBrief(BaseModel):
    headline: str
    summary: str
    items: list[WorldBriefItem] = Field(default_factory=list)


class WorldPulseLiveEnvelope(BaseModel):
    pulse: WorldPulseResponse
    decisions: "PulseDecisionBatch"
    brief: WorldPulseBrief


class PulseDecisionBatch(BaseModel):
    jev_enabled: bool
    changed_subjects: int
    auto_wakes: list["PulseWakeDecision"] = Field(default_factory=list)
    review_candidates: list["PulseWakeDecision"] = Field(default_factory=list)


class PulseWakeDecision(BaseModel):
    subject_id: str
    subject_type: Literal["signal", "cluster"]
    wake: bool
    mode: Literal["deterministic", "jev"]
    confidence: float | None = None
    next_capability: Literal["monitor", "verify", "reason", "coordinate"] = "monitor"
    reasons: list[str] = Field(default_factory=list)
    action_graph: list[PulseActionNode] = Field(default_factory=list)


def pulse_jev_enabled() -> bool:
    return bool(os.getenv("TYPESAFE_API_KEY")) and os.getenv("PULSE_JEV_ENABLED") == "1"


def _signal_prefilter(signal: WorldSignal) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    changed = signal.state in {"new", "updated"}
    if changed:
        reasons.append(f"signal is {signal.state} since the previous observation")
    if signal.attention_reasons:
        reasons.extend(signal.attention_reasons)

    wake = changed and bool(signal.attention_reasons)
    return wake, reasons


def _cluster_prefilter(cluster: SignalCluster) -> tuple[bool, list[str]]:
    reasons = [
        f"{len(cluster.sources)} independent sources overlap",
        f"signals are within {cluster.distance_km:.0f} km",
        "correlation is not confirmation",
    ]
    # Cross-source proximity is enough to warrant verification, not to assert a causal event.
    return len(cluster.sources) >= 2, reasons


def _graph(
    *,
    wake: bool,
    next_capability: str,
    reasons: list[str],
) -> list[PulseActionNode]:
    return [
        PulseActionNode(
            node_id="observe",
            label="Observe live world state",
            kind="observe",
            status="done",
            detail="Public feeds were normalized into a common event model.",
        ),
        PulseActionNode(
            node_id="verify",
            label="Verify the signal",
            kind="verify",
            status="active" if wake else "waiting",
            detail=(
                "Check source provenance and look for independent corroboration."
                if wake
                else "No verification wake-up required yet."
            ),
        ),
        PulseActionNode(
            node_id="reason",
            label="Wake deeper reasoning",
            kind="reason",
            status="active" if wake and next_capability == "reason" else "waiting",
            detail=(
                "A deeper reasoning agent may inspect context, uncertainty, and plausible implications."
                if wake
                else "Deep reasoning remains asleep."
            ),
        ),
        PulseActionNode(
            node_id="impact",
            label="Assess possible human impact",
            kind="impact",
            status="waiting" if wake else "skipped",
            detail="Estimate exposure only from explicit evidence; do not infer human impact from event size alone.",
        ),
        PulseActionNode(
            node_id="capability",
            label="Find relevant capabilities",
            kind="capability",
            status="waiting" if wake and next_capability in {"reason", "coordinate", "verify"} else "skipped",
            detail="Find available data, institutions, experts, tools, or responders only if the event merits escalation.",
        ),
        PulseActionNode(
            node_id="human",
            label="Human / institution decision",
            kind="human",
            status="waiting",
            detail="COMMONS may surface options; accountable humans and institutions retain consequential authority.",
        ),
    ]


def _jev_signal_decision(signal: WorldSignal, base_reasons: list[str]) -> PulseWakeDecision:
    state = {
        "event": signal.model_dump(mode="json"),
        "transparent_prefilter_reasons": base_reasons,
        "purpose": (
            "COMMONS WORLD PULSE. Decide whether this changed live signal merits deeper analysis. "
            "Do not exaggerate severity, infer casualties, or claim causal relationships that the sources do not establish."
        ),
    }
    with TypeSafeClient() as client:
        result = client.system_one(
            state=state,
            questions={
                "wake": Noul(
                    instructions=(
                        "Should COMMONS spend additional intelligence on this signal now, "
                        "rather than merely continue monitoring it?"
                    )
                ),
                "priority": Score(
                    instructions="How strongly does this signal justify additional analysis right now?",
                    criteria=[
                        "No additional analysis needed.",
                        "Low priority; monitor.",
                        "Some reason to verify.",
                        "Strong reason for deeper analysis.",
                        "Immediate strong reason to wake deeper analysis.",
                    ],
                ),
                "next_capability": Choice(
                    instructions="What is the best next capability?",
                    criteria={
                        "monitor": "Keep observing the source without extra analysis.",
                        "verify": "Check provenance, corroboration, and whether independent evidence agrees.",
                        "reason": "Use deeper reasoning to understand context, uncertainty, and possible implications.",
                        "coordinate": "Explore relevant capabilities or institutions because coordination may be needed.",
                    },
                ),
            },
        )

    wake_answer = result.nouls["wake"]
    next_answer = result.choices["next_capability"]
    wake_probability = float(wake_answer.noul)
    next_capability = next_answer.choice

    return PulseWakeDecision(
        subject_id=signal.signal_id,
        subject_type="signal",
        wake=wake_probability >= 0.5,
        mode="jev",
        confidence=getattr(wake_answer, "confidence", None),
        next_capability=next_capability,
        reasons=[
            *base_reasons,
            f"Jev wake probability {wake_probability:.2f}",
        ],
        action_graph=_graph(
            wake=wake_probability >= 0.5,
            next_capability=next_capability,
            reasons=base_reasons,
        ),
    )


def decide_signal(signal: WorldSignal) -> PulseWakeDecision:
    wake, reasons = _signal_prefilter(signal)
    if not wake:
        return PulseWakeDecision(
            subject_id=signal.signal_id,
            subject_type="signal",
            wake=False,
            mode="deterministic",
            next_capability="monitor",
            reasons=reasons or ["no material change rule fired"],
            action_graph=_graph(wake=False, next_capability="monitor", reasons=reasons),
        )

    if pulse_jev_enabled():
        return _jev_signal_decision(signal, reasons)

    next_capability: Literal["verify", "reason"] = (
        "reason"
        if any(
            marker in " ".join(reasons).lower()
            for marker in ("magnitude ≥ 6.0", "red alert", "multi-source")
        )
        else "verify"
    )
    return PulseWakeDecision(
        subject_id=signal.signal_id,
        subject_type="signal",
        wake=True,
        mode="deterministic",
        next_capability=next_capability,
        reasons=reasons,
        action_graph=_graph(wake=True, next_capability=next_capability, reasons=reasons),
    )


def decide_cluster(cluster: SignalCluster) -> PulseWakeDecision:
    wake, reasons = _cluster_prefilter(cluster)
    return PulseWakeDecision(
        subject_id=cluster.cluster_id,
        subject_type="cluster",
        wake=wake,
        mode="deterministic",
        next_capability="verify" if wake else "monitor",
        reasons=reasons,
        action_graph=_graph(wake=wake, next_capability="verify", reasons=reasons),
    )



def build_decision_batch(pulse: WorldPulseResponse) -> PulseDecisionBatch:
    signal_by_id = {signal.signal_id: signal for signal in pulse.signals}

    auto_wakes: list[PulseWakeDecision] = []
    review_candidates: list[PulseWakeDecision] = []

    for signal in pulse.signals:
        decision = decide_signal(signal)
        if decision.wake:
            auto_wakes.append(decision)
        elif signal.attention_reasons:
            review_candidates.append(
                PulseWakeDecision(
                    subject_id=signal.signal_id,
                    subject_type="signal",
                    wake=False,
                    mode="deterministic",
                    next_capability="monitor",
                    reasons=[
                        *signal.attention_reasons,
                        "attention rule matched, but no new/updated state requires an automatic wake",
                    ],
                    action_graph=_graph(
                        wake=False,
                        next_capability="monitor",
                        reasons=signal.attention_reasons,
                    ),
                )
            )

    for cluster in pulse.clusters:
        member_states = [
            signal_by_id[signal_id].state
            for signal_id in cluster.signal_ids
            if signal_id in signal_by_id
        ]
        cluster_decision = decide_cluster(cluster)
        if cluster_decision.wake and any(state in {"new", "updated"} for state in member_states):
            auto_wakes.append(cluster_decision)
        else:
            review_candidates.append(
                cluster_decision.model_copy(
                    update={
                        "wake": False,
                        "reasons": [
                            *cluster_decision.reasons,
                            "cluster is visible for review, but no member changed since the previous observation",
                        ],
                        "action_graph": _graph(
                            wake=False,
                            next_capability="monitor",
                            reasons=cluster_decision.reasons,
                        ),
                    }
                )
            )

    return PulseDecisionBatch(
        jev_enabled=pulse_jev_enabled(),
        changed_subjects=pulse.stats.new_signals + pulse.stats.updated_signals,
        auto_wakes=auto_wakes,
        review_candidates=review_candidates,
    )



def build_world_brief(
    pulse: WorldPulseResponse,
    decisions: PulseDecisionBatch,
) -> WorldPulseBrief:
    signal_by_id = {signal.signal_id: signal for signal in pulse.signals}
    cluster_by_id = {cluster.cluster_id: cluster for cluster in pulse.clusters}
    items: list[WorldBriefItem] = []

    def next_step(decision: PulseWakeDecision) -> str:
        return {
            "monitor": "Keep monitoring; no extra intelligence needed yet.",
            "verify": "Check provenance and independent corroboration.",
            "reason": "Wake deeper reasoning for context and uncertainty.",
            "coordinate": "Explore relevant capabilities or institutions.",
        }[decision.next_capability]

    for decision in decisions.auto_wakes:
        if decision.subject_type == "signal":
            signal = signal_by_id.get(decision.subject_id)
            if signal is None:
                continue
            items.append(
                WorldBriefItem(
                    subject_id=decision.subject_id,
                    subject_type="signal",
                    status="wake",
                    title=signal.title,
                    source_label=signal.source,
                    why=decision.reasons,
                    next_step=next_step(decision),
                )
            )
        else:
            cluster = cluster_by_id.get(decision.subject_id)
            if cluster is None:
                continue
            items.append(
                WorldBriefItem(
                    subject_id=decision.subject_id,
                    subject_type="cluster",
                    status="wake",
                    title="Possible multi-source event cluster",
                    source_label=" + ".join(cluster.sources),
                    why=decision.reasons,
                    next_step=next_step(decision),
                )
            )
        if len(items) >= 3:
            break

    if len(items) < 3:
        for decision in decisions.review_candidates:
            if len(items) >= 3:
                break
            if decision.subject_type == "signal":
                signal = signal_by_id.get(decision.subject_id)
                if signal is None:
                    continue
                items.append(
                    WorldBriefItem(
                        subject_id=decision.subject_id,
                        subject_type="signal",
                        status="review",
                        title=signal.title,
                        source_label=signal.source,
                        why=decision.reasons,
                        next_step=next_step(decision),
                    )
                )
            else:
                cluster = cluster_by_id.get(decision.subject_id)
                if cluster is None:
                    continue
                items.append(
                    WorldBriefItem(
                        subject_id=decision.subject_id,
                        subject_type="cluster",
                        status="review",
                        title="Possible multi-source event cluster",
                        source_label=" + ".join(cluster.sources),
                        why=decision.reasons,
                        next_step=next_step(decision),
                    )
                )

    if decisions.auto_wakes:
        headline = f"{len(decisions.auto_wakes)} live change{'s' if len(decisions.auto_wakes) != 1 else ''} woke intelligence."
        summary = (
            f"COMMONS observed {pulse.stats.total_signals} live signals and found "
            f"{decisions.changed_subjects} changed subject{'s' if decisions.changed_subjects != 1 else ''}. "
            "Only changed signals that crossed transparent wake rules triggered deeper attention."
        )
    elif pulse.baseline_observation:
        headline = "Baseline established. Intelligence stayed asleep."
        summary = (
            f"COMMONS observed {pulse.stats.total_signals} live signals. "
            "This first observation creates the baseline; no event is falsely labeled new."
        )
    else:
        headline = "Nothing crossed the wake gate."
        summary = (
            f"COMMONS observed {pulse.stats.total_signals} live signals and "
            f"{decisions.changed_subjects} changed subject{'s' if decisions.changed_subjects != 1 else ''}. "
            "No changed signal justified an automatic intelligence wake."
        )

    return WorldPulseBrief(
        headline=headline,
        summary=summary,
        items=items,
    )
