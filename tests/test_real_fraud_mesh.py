import asyncio
import json

import httpx
from fastapi.testclient import TestClient

from commons.a2a_procurement import AgentCard, AgentInterface, AgentSkill
from commons.fraud_agents.beneficiary_bank import app as beneficiary_bank_app
from commons.fraud_agents.device import app as device_app
from commons.fraud_agents.scam_intel import app as scam_intel_app
from commons.fraud_agents.sending_bank import app as sending_bank_app
from commons.fraud_agents.telco import app as telco_app
from commons.fraud_mesh import evaluate_via_mesh
from commons.scam_intercept import (
    PaymentIntent,
    beneficiary_bank_signal,
    device_signal,
    scam_intel_signal,
    sending_bank_signal,
    telco_signal,
)


APPS = {
    "sending-bank-agent": sending_bank_app,
    "device-agent": device_app,
    "telco-agent": telco_app,
    "beneficiary-bank-agent": beneficiary_bank_app,
    "scam-intel-agent": scam_intel_app,
}

HANDLERS = {
    "sending-bank-agent": sending_bank_signal,
    "device-agent": device_signal,
    "telco-agent": telco_signal,
    "beneficiary-bank-agent": beneficiary_bank_signal,
    "scam-intel-agent": scam_intel_signal,
}

URLS = {
    "sending-bank-agent": "http://sending-bank.local",
    "device-agent": "http://device.local",
    "telco-agent": "http://telco.local",
    "beneficiary-bank-agent": "http://beneficiary-bank.local",
    "scam-intel-agent": "http://scam-intel.local",
}

HOST_TO_AGENT = {
    "sending-bank.local": "sending-bank-agent",
    "device.local": "device-agent",
    "telco.local": "telco-agent",
    "beneficiary-bank.local": "beneficiary-bank-agent",
    "scam-intel.local": "scam-intel-agent",
}


def card_for(agent_id: str) -> AgentCard:
    return AgentCard(
        agent_id=agent_id,
        name=agent_id,
        description="synthetic independent fraud-defense service",
        supported_interfaces=[AgentInterface(url="/message:send")],
        skills=[
            AgentSkill(
                skill_id="fraud_signal",
                name="Fraud signal",
                description="Return one minimized defensive assertion.",
            )
        ],
        price_eur=0.0,
    )


def payment(**updates) -> PaymentIntent:
    base = dict(
        amount_eur=8400,
        new_beneficiary=True,
        device_known=True,
        sim_swap_minutes_ago=43,
        beneficiary_independent_reports=3,
        beneficiary_relationship_years=0,
        scam_campaign_match=True,
        user_confirms_expected_payment=False,
    )
    base.update(updates)
    return PaymentIntent(**base)


def transport_with_offline(*offline_agents: str) -> httpx.MockTransport:
    offline = set(offline_agents)

    def handler(request: httpx.Request) -> httpx.Response:
        agent_id = HOST_TO_AGENT[request.url.host]
        if agent_id in offline:
            raise httpx.ConnectError("synthetic offline agent", request=request)

        if request.url.path == "/.well-known/agent-card.json":
            return httpx.Response(
                200,
                json=card_for(agent_id).model_dump(mode="json"),
            )

        if request.url.path == "/message:send":
            payload = PaymentIntent.model_validate(json.loads(request.content))
            signal = HANDLERS[agent_id](payload)
            return httpx.Response(
                200,
                json=signal.model_dump(mode="json"),
            )

        return httpx.Response(404)

    return httpx.MockTransport(handler)


def test_each_fraud_agent_is_an_independent_http_service() -> None:
    for agent_id, app in APPS.items():
        client = TestClient(app)

        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["agent_id"] == agent_id

        card = client.get("/.well-known/agent-card.json")
        assert card.status_code == 200
        assert card.json()["agent_id"] == agent_id

        signal = client.post("/message:send", json=payment().model_dump())
        assert signal.status_code == 200
        assert signal.json()["agent_id"] == agent_id


def test_real_mesh_queries_five_services_and_returns_latency_trace() -> None:
    result = asyncio.run(
        evaluate_via_mesh(
            payment(),
            agent_urls=URLS,
            transport=transport_with_offline(),
        )
    )

    assert result.responding_agents == 5
    assert result.degraded is False
    assert result.missing_agents == []
    assert result.decision.action == "HUMAN_REVIEW"
    assert all(trace.discovered for trace in result.traces)
    assert all(trace.responded for trace in result.traces)
    assert all(trace.latency_ms is not None for trace in result.traces)


def test_one_offline_agent_never_turns_missing_evidence_into_safety() -> None:
    legitimate = payment(
        amount_eur=900,
        new_beneficiary=False,
        device_known=True,
        sim_swap_minutes_ago=None,
        beneficiary_independent_reports=0,
        beneficiary_relationship_years=5,
        scam_campaign_match=False,
        user_confirms_expected_payment=True,
    )

    result = asyncio.run(
        evaluate_via_mesh(
            legitimate,
            agent_urls=URLS,
            transport=transport_with_offline("scam-intel-agent"),
        )
    )

    assert result.degraded is True
    assert result.missing_agents == ["scam-intel-agent"]
    assert result.responding_agents == 4
    assert result.decision.action == "CONFIRM"
    assert any(
        "degraded mode" in reason.lower()
        for reason in result.decision.reasons
    )


def test_too_few_agents_forces_human_review() -> None:
    result = asyncio.run(
        evaluate_via_mesh(
            payment(
                amount_eur=500,
                new_beneficiary=False,
                sim_swap_minutes_ago=None,
                beneficiary_independent_reports=0,
                scam_campaign_match=False,
            ),
            agent_urls=URLS,
            transport=transport_with_offline(
                "device-agent",
                "telco-agent",
                "scam-intel-agent",
            ),
        )
    )

    assert result.responding_agents == 2
    assert result.degraded is True
    assert result.decision.action == "HUMAN_REVIEW"
    assert result.decision.human_authority_required is True
    assert any(
        "fewer than three independent agents" in reason.lower()
        for reason in result.decision.reasons
    )


def test_mesh_page_explains_real_network_failure_mode() -> None:
    from commons.app import app

    response = TestClient(app).get("/fraud/mesh")
    assert response.status_code == 200
    assert "5 independent HTTP services" in response.text
    assert "Missing evidence is never treated as evidence of safety." in response.text
