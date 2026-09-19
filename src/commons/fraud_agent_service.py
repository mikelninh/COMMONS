from __future__ import annotations

from fastapi import FastAPI, HTTPException

from commons.a2a_procurement import AgentCard, AgentInterface, AgentSkill
from commons.scam_intercept import (
    FraudSignal,
    PaymentIntent,
    beneficiary_bank_signal,
    device_signal,
    scam_intel_signal,
    sending_bank_signal,
    telco_signal,
)

_HANDLERS = {
    "sending-bank-agent": (
        "Sending Bank Agent",
        "payment_context",
        "Shares minimized payment-context assertions.",
        sending_bank_signal,
    ),
    "device-agent": (
        "Device Trust Agent",
        "device_trust",
        "Reports only device familiarity needed for the decision.",
        device_signal,
    ),
    "telco-agent": (
        "Telco Change Agent",
        "sim_change",
        "Reports only recent SIM-change timing needed for the decision.",
        telco_signal,
    ),
    "beneficiary-bank-agent": (
        "Beneficiary Bank Agent",
        "beneficiary_context",
        "Reports minimized receiving-account context and independent-report counts.",
        beneficiary_bank_signal,
    ),
    "scam-intel-agent": (
        "Scam Intelligence Agent",
        "campaign_match",
        "Reports whether the scenario matches a current scam pattern.",
        scam_intel_signal,
    ),
}


def create_agent_app(agent_id: str) -> FastAPI:
    if agent_id not in _HANDLERS:
        raise KeyError(agent_id)

    name, skill_id, description, handler = _HANDLERS[agent_id]
    app = FastAPI(title=name, version="1.0.0")

    @app.get("/.well-known/agent-card.json", response_model=AgentCard)
    def card() -> AgentCard:
        return AgentCard(
            agent_id=agent_id,
            name=name,
            description=description,
            supported_interfaces=[
                AgentInterface(url="/message:send")
            ],
            skills=[
                AgentSkill(
                    skill_id=skill_id,
                    name=skill_id.replace("_", " ").title(),
                    description=description,
                )
            ],
            price_eur=0.0,
        )

    @app.post("/message:send", response_model=FraudSignal)
    def message_send(payment: PaymentIntent) -> FraudSignal:
        try:
            return handler(payment)
        except Exception as exc:  # keep boundary explicit for service callers
            raise HTTPException(status_code=500, detail="Agent evaluation failed.") from exc

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "agent_id": agent_id}

    return app
