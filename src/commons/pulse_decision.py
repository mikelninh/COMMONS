from __future__ import annotations

import os
from typing import Literal

from pydantic import BaseModel, Field
from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

from commons.world_pulse import SignalCluster, WorldSignal


class PulseActionNode(BaseModel):
    node_id: str
    label: str
    kind: Literal["observe", "verify", "reason", "impact", "capability", "human"]
    status: Literal["done", "active", "waiting", "skipped"]
    detail: str


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
