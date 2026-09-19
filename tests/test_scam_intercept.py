from fastapi.testclient import TestClient

from commons.app import app
from commons.scam_intercept import (
    PaymentIntent,
    compare_established_recipient,
    evaluate_payment,
)

client = TestClient(app)


def scam_payment() -> PaymentIntent:
    return PaymentIntent(
        amount_eur=8400,
        new_beneficiary=True,
        device_known=True,
        sim_swap_minutes_ago=43,
        beneficiary_independent_reports=3,
        beneficiary_relationship_years=0,
        scam_campaign_match=True,
        user_confirms_expected_payment=False,
    )


def test_fraud_lab_page_exists_and_is_explicitly_synthetic() -> None:
    response = client.get("/fraud")
    assert response.status_code == 200
    assert "One payment." in response.text
    assert "synthetic defense lab" in response.text
    assert "No agent gets to call someone a fraudster." in response.text


def test_fraud_agents_are_discoverable() -> None:
    response = client.get("/fraud/agents")
    assert response.status_code == 200
    ids = {card["agent_id"] for card in response.json()}
    assert ids == {
        "sending-bank-agent",
        "device-agent",
        "telco-agent",
        "beneficiary-bank-agent",
        "scam-intel-agent",
    }


def test_impersonation_scenario_pauses_or_escalates_based_on_corroboration() -> None:
    decision = evaluate_payment(scam_payment())

    assert decision.action == "HUMAN_REVIEW"
    assert set(decision.high_concern_agents) == {
        "sending-bank-agent",
        "telco-agent",
        "beneficiary-bank-agent",
        "scam-intel-agent",
    }
    assert decision.human_authority_required is True
    assert decision.reversible is True


def test_legitimate_new_landlord_is_not_automatically_blocked() -> None:
    payment = PaymentIntent(
        amount_eur=6500,
        new_beneficiary=True,
        device_known=True,
        sim_swap_minutes_ago=None,
        beneficiary_independent_reports=0,
        beneficiary_relationship_years=0,
        scam_campaign_match=False,
        user_confirms_expected_payment=True,
    )
    decision = evaluate_payment(payment)

    assert decision.action == "CONFIRM"
    assert "HUMAN_REVIEW" != decision.action
    assert "PAUSE_AND_VERIFY" != decision.action


def test_established_recipient_evidence_can_deescalate() -> None:
    payment = PaymentIntent(
        amount_eur=9000,
        new_beneficiary=True,
        device_known=False,
        sim_swap_minutes_ago=100,
        beneficiary_independent_reports=3,
        beneficiary_relationship_years=0,
        scam_campaign_match=False,
        user_confirms_expected_payment=False,
    )

    comparison = compare_established_recipient(payment)

    assert comparison.before.action == "PAUSE_AND_VERIFY"
    assert comparison.after.action == "CONFIRM"
    assert (
        comparison.after.signals[3].agent_id == "beneficiary-bank-agent"
        and comparison.after.signals[3].concern == "clear"
    )


def test_single_adverse_signal_only_requires_confirmation() -> None:
    payment = PaymentIntent(
        amount_eur=1200,
        new_beneficiary=False,
        device_known=True,
        sim_swap_minutes_ago=30,
        beneficiary_independent_reports=0,
        beneficiary_relationship_years=4,
        scam_campaign_match=False,
        user_confirms_expected_payment=False,
    )
    decision = evaluate_payment(payment)

    assert decision.action == "CONFIRM"
    assert decision.high_concern_agents == ["telco-agent"]


def test_http_evaluate_returns_minimized_signal_evidence() -> None:
    response = client.post("/fraud/evaluate", json=scam_payment().model_dump())
    assert response.status_code == 200
    body = response.json()

    assert body["action"] == "HUMAN_REVIEW"
    assert len(body["signals"]) == 5
    for signal in body["signals"]:
        assert "data_shared" in signal
        assert signal["data_shared"]
        assert "raw customer history" not in signal["data_shared"]


def test_scenarios_include_fraud_and_legitimate_cases() -> None:
    response = client.get("/fraud/scenarios")
    assert response.status_code == 200
    outcomes = {row["expected_outcome"] for row in response.json()}
    assert {"fraud", "legitimate"} <= outcomes
