from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from commons.a2a_procurement import AgentCard, AgentInterface, AgentSkill


Concern = Literal["clear", "watch", "high"]
Action = Literal["ALLOW", "CONFIRM", "PAUSE_AND_VERIFY", "HUMAN_REVIEW"]


class PaymentIntent(BaseModel):
    payment_id: str = Field(default_factory=lambda: str(uuid4()))
    amount_eur: float = Field(ge=0)
    new_beneficiary: bool
    device_known: bool
    sim_swap_minutes_ago: int | None = Field(default=None, ge=0)
    beneficiary_independent_reports: int = Field(default=0, ge=0)
    beneficiary_relationship_years: float = Field(default=0.0, ge=0)
    scam_campaign_match: bool = False
    user_confirms_expected_payment: bool = False


class FraudSignal(BaseModel):
    signal_id: str = Field(default_factory=lambda: str(uuid4()))
    agent_id: str
    concern: Concern
    claim: str
    evidence: list[str] = Field(default_factory=list)
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data_shared: list[str] = Field(default_factory=list)


class FraudDecision(BaseModel):
    payment_id: str
    action: Action
    reasons: list[str]
    high_concern_agents: list[str]
    watch_agents: list[str]
    independent_signal_count: int
    reversible: bool
    human_authority_required: bool
    signals: list[FraudSignal]
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FraudScenario(BaseModel):
    scenario_id: str
    name: str
    description: str
    payment: PaymentIntent
    expected_outcome: Literal["fraud", "legitimate", "uncertain"]


class ScenarioComparison(BaseModel):
    before: FraudDecision
    after: FraudDecision
    changed_field: str
    explanation: str


def _card(
    agent_id: str,
    name: str,
    description: str,
    skill_id: str,
    skill_name: str,
) -> AgentCard:
    return AgentCard(
        agent_id=agent_id,
        name=name,
        description=description,
        supported_interfaces=[
            AgentInterface(url=f"/fraud/agents/{agent_id}/message:send")
        ],
        skills=[
            AgentSkill(
                skill_id=skill_id,
                name=skill_name,
                description=description,
            )
        ],
        price_eur=0.0,
    )


FRAUD_AGENT_CARDS = [
    _card(
        "sending-bank-agent",
        "Sending Bank Agent",
        "Shares narrow payment-context assertions such as amount and whether the beneficiary is new.",
        "payment_context",
        "Payment context",
    ),
    _card(
        "device-agent",
        "Device Trust Agent",
        "Reports whether the transaction comes from a previously known device.",
        "device_trust",
        "Device trust",
    ),
    _card(
        "telco-agent",
        "Telco Change Agent",
        "Reports recent high-risk account changes such as a SIM swap without exposing unrelated telco history.",
        "sim_change",
        "SIM change",
    ),
    _card(
        "beneficiary-bank-agent",
        "Beneficiary Bank Agent",
        "Returns minimized receiving-account evidence such as independent scam reports or established relationship context.",
        "beneficiary_context",
        "Beneficiary context",
    ),
    _card(
        "scam-intel-agent",
        "Scam Intelligence Agent",
        "Checks whether the described payment context matches a known scam campaign pattern.",
        "campaign_match",
        "Scam campaign match",
    ),
]


def list_fraud_agent_cards() -> list[AgentCard]:
    return [card.model_copy(deep=True) for card in FRAUD_AGENT_CARDS]


def sending_bank_signal(payment: PaymentIntent) -> FraudSignal:
    evidence = [f"amount €{payment.amount_eur:,.2f}"]
    if payment.new_beneficiary:
        evidence.append("beneficiary is new")
    if payment.user_confirms_expected_payment:
        evidence.append("user says the payment is expected")

    concern: Concern = "clear"
    claim = "Payment context looks routine."
    if payment.new_beneficiary and payment.amount_eur >= 5000:
        concern = "high"
        claim = "Large payment to a new beneficiary deserves verification."
    elif payment.new_beneficiary or payment.amount_eur >= 5000:
        concern = "watch"
        claim = "Payment context contains one unusual element."

    if payment.user_confirms_expected_payment and concern == "watch":
        concern = "clear"
        claim = "User confirmation reduces concern, but other independent signals still matter."

    return FraudSignal(
        agent_id="sending-bank-agent",
        concern=concern,
        claim=claim,
        evidence=evidence,
        data_shared=["amount band", "new-beneficiary flag", "user confirmation flag"],
    )


def device_signal(payment: PaymentIntent) -> FraudSignal:
    if payment.device_known:
        return FraudSignal(
            agent_id="device-agent",
            concern="clear",
            claim="Transaction comes from a known device.",
            evidence=["known device"],
            data_shared=["device familiarity assertion"],
        )
    return FraudSignal(
        agent_id="device-agent",
        concern="watch",
        claim="Transaction comes from an unrecognized device.",
        evidence=["device not previously known"],
        data_shared=["device familiarity assertion"],
    )


def telco_signal(payment: PaymentIntent) -> FraudSignal:
    minutes = payment.sim_swap_minutes_ago
    if minutes is None:
        return FraudSignal(
            agent_id="telco-agent",
            concern="clear",
            claim="No recent SIM-change signal was supplied.",
            evidence=["no recent SIM swap asserted"],
            data_shared=["recent SIM-change assertion"],
        )
    if minutes <= 180:
        return FraudSignal(
            agent_id="telco-agent",
            concern="high",
            claim="A SIM swap occurred shortly before the payment.",
            evidence=[f"SIM swap {minutes} minutes ago"],
            data_shared=["minutes since SIM change"],
        )
    if minutes <= 1440:
        return FraudSignal(
            agent_id="telco-agent",
            concern="watch",
            claim="A SIM change occurred within the last day.",
            evidence=[f"SIM swap {minutes} minutes ago"],
            data_shared=["minutes since SIM change"],
        )
    return FraudSignal(
        agent_id="telco-agent",
        concern="clear",
        claim="The SIM change is not recent enough to trigger the current rule.",
        evidence=[f"SIM swap {minutes} minutes ago"],
        data_shared=["minutes since SIM change"],
    )


def beneficiary_bank_signal(payment: PaymentIntent) -> FraudSignal:
    reports = payment.beneficiary_independent_reports
    years = payment.beneficiary_relationship_years

    if years >= 2 and reports == 0:
        return FraudSignal(
            agent_id="beneficiary-bank-agent",
            concern="clear",
            claim="Receiving account has established legitimate relationship context and no independent scam reports.",
            evidence=[f"relationship history {years:g} years", "0 independent scam reports"],
            data_shared=["relationship-age band", "independent-report count"],
        )
    if reports >= 3:
        return FraudSignal(
            agent_id="beneficiary-bank-agent",
            concern="high",
            claim="Receiving account has multiple independent scam reports.",
            evidence=[f"{reports} independent scam reports"],
            data_shared=["independent-report count"],
        )
    if reports > 0:
        return FraudSignal(
            agent_id="beneficiary-bank-agent",
            concern="watch",
            claim="Receiving account has at least one scam report but corroboration is limited.",
            evidence=[f"{reports} independent scam report(s)"],
            data_shared=["independent-report count"],
        )
    return FraudSignal(
        agent_id="beneficiary-bank-agent",
        concern="clear",
        claim="No receiving-account concern is currently asserted.",
        evidence=["0 independent scam reports"],
        data_shared=["independent-report count", "relationship-age band"],
    )


def scam_intel_signal(payment: PaymentIntent) -> FraudSignal:
    if payment.scam_campaign_match:
        return FraudSignal(
            agent_id="scam-intel-agent",
            concern="high",
            claim="Payment context matches a known scam-campaign pattern.",
            evidence=["current campaign-pattern match"],
            data_shared=["campaign-match assertion"],
        )
    return FraudSignal(
        agent_id="scam-intel-agent",
        concern="clear",
        claim="No current scam-campaign pattern match.",
        evidence=["no campaign match"],
        data_shared=["campaign-match assertion"],
    )


def evaluate_payment(payment: PaymentIntent) -> FraudDecision:
    signals = [
        sending_bank_signal(payment),
        device_signal(payment),
        telco_signal(payment),
        beneficiary_bank_signal(payment),
        scam_intel_signal(payment),
    ]

    high = [signal.agent_id for signal in signals if signal.concern == "high"]
    watch = [signal.agent_id for signal in signals if signal.concern == "watch"]
    reasons: list[str] = []

    large_new = payment.new_beneficiary and payment.amount_eur >= 5000
    established_recipient = (
        payment.beneficiary_relationship_years >= 2
        and payment.beneficiary_independent_reports == 0
    )

    if established_recipient:
        reasons.append("Receiving bank reports established relationship context with no scam reports.")

    if len(high) >= 3:
        action: Action = "HUMAN_REVIEW"
        reasons.append("Three or more independent agents supplied high-concern signals.")
    elif large_new and len(high) >= 2:
        action = "PAUSE_AND_VERIFY"
        reasons.append("Large new-beneficiary payment plus at least two independent high-concern signals.")
    elif len(high) >= 2:
        action = "PAUSE_AND_VERIFY"
        reasons.append("At least two independent high-concern signals require reversible verification.")
    elif len(high) == 1 or len(watch) >= 2:
        action = "CONFIRM"
        reasons.append("Concern exists, but evidence is not sufficiently corroborated for a pause.")
    else:
        action = "ALLOW"
        reasons.append("No corroborated high-concern pattern crossed the intervention rule.")

    if established_recipient and action == "PAUSE_AND_VERIFY" and len(high) < 3:
        action = "CONFIRM"
        reasons.append("Established recipient context de-escalates the intervention from pause to confirmation.")

    if payment.user_confirms_expected_payment and action == "CONFIRM" and len(high) == 0:
        action = "ALLOW"
        reasons.append("User confirmation plus no high-concern signals permits the payment under this demo policy.")

    return FraudDecision(
        payment_id=payment.payment_id,
        action=action,
        reasons=reasons,
        high_concern_agents=high,
        watch_agents=watch,
        independent_signal_count=len(high) + len(watch),
        reversible=action in {"CONFIRM", "PAUSE_AND_VERIFY", "HUMAN_REVIEW"},
        human_authority_required=action in {"PAUSE_AND_VERIFY", "HUMAN_REVIEW"},
        signals=signals,
    )


SCENARIOS = [
    FraudScenario(
        scenario_id="bank-impersonation",
        name="Bank impersonation scam",
        description="Large payment to a new beneficiary shortly after a SIM swap, with receiving-bank reports and a campaign match.",
        payment=PaymentIntent(
            amount_eur=8400,
            new_beneficiary=True,
            device_known=True,
            sim_swap_minutes_ago=43,
            beneficiary_independent_reports=3,
            beneficiary_relationship_years=0,
            scam_campaign_match=True,
            user_confirms_expected_payment=False,
        ),
        expected_outcome="fraud",
    ),
    FraudScenario(
        scenario_id="new-landlord",
        name="Legitimate new landlord",
        description="Large new-beneficiary transfer from a known device with no SIM change, no reports, and no scam-campaign match.",
        payment=PaymentIntent(
            amount_eur=6500,
            new_beneficiary=True,
            device_known=True,
            sim_swap_minutes_ago=None,
            beneficiary_independent_reports=0,
            beneficiary_relationship_years=0,
            scam_campaign_match=False,
            user_confirms_expected_payment=True,
        ),
        expected_outcome="legitimate",
    ),
    FraudScenario(
        scenario_id="known-recipient",
        name="Established recipient",
        description="A high-value payment that initially looks unusual, but the receiving bank confirms a long-established relationship.",
        payment=PaymentIntent(
            amount_eur=9000,
            new_beneficiary=False,
            device_known=False,
            sim_swap_minutes_ago=600,
            beneficiary_independent_reports=0,
            beneficiary_relationship_years=5,
            scam_campaign_match=False,
            user_confirms_expected_payment=True,
        ),
        expected_outcome="legitimate",
    ),
]


def list_scenarios() -> list[FraudScenario]:
    return [scenario.model_copy(deep=True) for scenario in SCENARIOS]


def compare_established_recipient(payment: PaymentIntent) -> ScenarioComparison:
    before = evaluate_payment(payment)
    changed = payment.model_copy(
        update={
            "beneficiary_independent_reports": 0,
            "beneficiary_relationship_years": 5.0,
        }
    )
    after = evaluate_payment(changed)
    return ScenarioComparison(
        before=before,
        after=after,
        changed_field="beneficiary context",
        explanation=(
            "The receiving-bank agent changed from adverse/unknown context to an established "
            "five-year relationship with zero independent scam reports. COMMONS recomputed the "
            "recommended action rather than preserving the earlier intervention."
        ),
    )
