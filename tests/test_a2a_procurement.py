from fastapi.testclient import TestClient

from commons.a2a_procurement import ProcurementRequest, run_procurement
from commons.app import app

client = TestClient(app)


def test_a2a_lab_page_exists() -> None:
    response = client.get("/a2a")
    assert response.status_code == 200
    assert "Give the network a job." in response.text
    assert "Run the agent network" in response.text


def test_agent_cards_are_discoverable() -> None:
    response = client.get("/a2a/agents")
    assert response.status_code == 200
    cards = response.json()
    ids = {card["agent_id"] for card in cards}
    assert {"strategy-agent", "copy-agent-alpha", "copy-agent-beta", "qa-agent"} <= ids
    assert all(card["supported_interfaces"][0]["protocol_version"] == "1.0" for card in cards)

    card = client.get("/a2a/agents/qa-agent/.well-known/agent-card.json")
    assert card.status_code == 200
    assert card.json()["agent_id"] == "qa-agent"


def test_forced_failure_reroutes_and_still_verifies() -> None:
    result = run_procurement(
        ProcurementRequest(
            objective="COMMONS Care: help people turn a real need into one safe useful next action.",
            budget_eur=0.25,
            simulate_primary_failure=True,
        )
    )

    assert result.within_budget is True
    assert result.verified is True
    assert result.final_artifact is not None

    tasks = result.tasks
    assert any(
        task.agent_id == "copy-agent-alpha" and task.state == "TASK_STATE_FAILED"
        for task in tasks
    )
    assert any(
        task.agent_id == "copy-agent-beta" and task.state == "TASK_STATE_COMPLETED"
        for task in tasks
    )
    assert tasks[-1].agent_id == "qa-agent"
    assert tasks[-1].artifact is not None
    assert tasks[-1].artifact.data["independent_verifier"] is True

    landing_receipts = [
        receipt for receipt in result.handoffs if receipt.skill_id == "landing_copy"
    ]
    assert len(landing_receipts) == 2
    assert landing_receipts[0].state == "TASK_STATE_FAILED"
    assert landing_receipts[1].state == "TASK_STATE_COMPLETED"


def test_successful_primary_does_not_reroute() -> None:
    result = run_procurement(
        ProcurementRequest(
            objective="Small launch: produce a useful landing-page brief.",
            budget_eur=0.25,
            simulate_primary_failure=False,
        )
    )

    assert result.verified is True
    assert not any(task.agent_id == "copy-agent-beta" for task in result.tasks)
    assert len([r for r in result.handoffs if r.skill_id == "landing_copy"]) == 1


def test_budget_blocks_backup_when_remaining_funds_are_insufficient() -> None:
    result = run_procurement(
        ProcurementRequest(
            objective="Budget test: prove that rerouting obeys hard spending limits.",
            budget_eur=0.055,
            simulate_primary_failure=True,
        )
    )

    assert result.verified is False
    assert result.final_artifact is None
    assert result.within_budget is False
    assert "remaining budget" in result.summary.lower()
    assert not any(task.agent_id == "copy-agent-beta" for task in result.tasks)


def test_http_procurement_returns_receipts_and_artifact() -> None:
    response = client.post(
        "/a2a/procure",
        json={
            "objective": "Agent Proof: turn one objective into a verified launch artifact.",
            "budget_eur": 0.25,
            "simulate_primary_failure": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["verified"] is True
    assert body["spent_eur"] <= body["budget_eur"]
    assert body["final_artifact"]["name"] == "verified-launch-kit"
    assert len(body["handoffs"]) == 3
