from __future__ import annotations

import asyncio
import os
from time import perf_counter

import httpx
from pydantic import BaseModel, Field

from commons.a2a_procurement import AgentCard
from commons.scam_intercept import FraudDecision, FraudSignal, PaymentIntent, evaluate_signals


DEFAULT_AGENT_URLS = {
    "sending-bank-agent": "http://127.0.0.1:8101",
    "device-agent": "http://127.0.0.1:8102",
    "telco-agent": "http://127.0.0.1:8103",
    "beneficiary-bank-agent": "http://127.0.0.1:8104",
    "scam-intel-agent": "http://127.0.0.1:8105",
}

ENV_KEYS = {
    "sending-bank-agent": "FRAUD_SENDING_BANK_URL",
    "device-agent": "FRAUD_DEVICE_URL",
    "telco-agent": "FRAUD_TELCO_URL",
    "beneficiary-bank-agent": "FRAUD_BENEFICIARY_BANK_URL",
    "scam-intel-agent": "FRAUD_SCAM_INTEL_URL",
}


class FraudMeshTrace(BaseModel):
    agent_id: str
    base_url: str
    discovered: bool
    responded: bool
    latency_ms: float | None = None
    card: AgentCard | None = None
    signal: FraudSignal | None = None
    error: str | None = None


class FraudMeshResult(BaseModel):
    payment_id: str
    decision: FraudDecision
    traces: list[FraudMeshTrace]
    responding_agents: int = Field(ge=0)
    missing_agents: list[str] = Field(default_factory=list)
    degraded: bool
    total_latency_ms: float = Field(ge=0)


def configured_agent_urls() -> dict[str, str]:
    return {
        agent_id: os.getenv(ENV_KEYS[agent_id], default).rstrip("/")
        for agent_id, default in DEFAULT_AGENT_URLS.items()
    }


async def _query_agent(
    client: httpx.AsyncClient,
    agent_id: str,
    base_url: str,
    payment: PaymentIntent,
) -> FraudMeshTrace:
    started = perf_counter()
    card: AgentCard | None = None
    try:
        card_response = await client.get(f"{base_url}/.well-known/agent-card.json")
        card_response.raise_for_status()
        card = AgentCard.model_validate(card_response.json())
        if card.agent_id != agent_id:
            raise ValueError(
                f"Agent Card identity mismatch: expected {agent_id}, got {card.agent_id}"
            )

        message_response = await client.post(
            f"{base_url}/message:send",
            json=payment.model_dump(mode="json"),
        )
        message_response.raise_for_status()
        signal = FraudSignal.model_validate(message_response.json())
        if signal.agent_id != agent_id:
            raise ValueError(
                f"Signal identity mismatch: expected {agent_id}, got {signal.agent_id}"
            )

        return FraudMeshTrace(
            agent_id=agent_id,
            base_url=base_url,
            discovered=True,
            responded=True,
            latency_ms=round((perf_counter() - started) * 1000, 2),
            card=card,
            signal=signal,
        )
    except Exception as exc:
        return FraudMeshTrace(
            agent_id=agent_id,
            base_url=base_url,
            discovered=card is not None,
            responded=False,
            latency_ms=round((perf_counter() - started) * 1000, 2),
            card=card,
            error=f"{type(exc).__name__}: {exc}",
        )


async def evaluate_via_mesh(
    payment: PaymentIntent,
    *,
    agent_urls: dict[str, str] | None = None,
    timeout_seconds: float = 1.5,
) -> FraudMeshResult:
    urls = agent_urls or configured_agent_urls()
    started = perf_counter()

    timeout = httpx.Timeout(timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout) as client:
        traces = await asyncio.gather(
            *[
                _query_agent(client, agent_id, base_url, payment)
                for agent_id, base_url in urls.items()
            ]
        )

    signals = [trace.signal for trace in traces if trace.signal is not None]
    missing = [trace.agent_id for trace in traces if not trace.responded]

    decision = evaluate_signals(payment, signals)
    degraded = bool(missing)

    if len(signals) < 3:
        decision = decision.model_copy(
            update={
                "action": "HUMAN_REVIEW",
                "reversible": True,
                "human_authority_required": True,
                "reasons": [
                    *decision.reasons,
                    "Fewer than three independent agents responded; COMMONS will not treat missing evidence as evidence of safety.",
                ],
            }
        )
    elif missing and decision.action == "ALLOW":
        decision = decision.model_copy(
            update={
                "action": "CONFIRM",
                "reversible": True,
                "reasons": [
                    *decision.reasons,
                    "At least one expected defense agent was unavailable; degraded mode requires confirmation before treating the payment as routine.",
                ],
            }
        )

    return FraudMeshResult(
        payment_id=payment.payment_id,
        decision=decision,
        traces=list(traces),
        responding_agents=len(signals),
        missing_agents=missing,
        degraded=degraded,
        total_latency_ms=round((perf_counter() - started) * 1000, 2),
    )
