from __future__ import annotations

from enum import StrEnum
from pydantic import BaseModel, Field, HttpUrl


class CivicProofStage(StrEnum):
    SOURCE_VERIFIED = "source_verified"
    ACTION_PREPARED = "action_prepared"
    ACTION_CONFIRMED = "action_confirmed"
    INSTITUTION_ACK = "institution_ack"
    OUTCOME_VERIFIED = "outcome_verified"


class CivicActionPlan(BaseModel):
    need: str = Field(min_length=1, max_length=4000)
    jurisdiction: str = Field(min_length=1, max_length=300)
    channel_name: str = Field(min_length=1, max_length=300)
    channel_type: str = Field(min_length=1, max_length=120)
    official_source: HttpUrl
    responsible_body: str = Field(min_length=1, max_length=300)
    eligibility_summary: str = Field(min_length=1, max_length=2000)
    deadline: str | None = Field(default=None, max_length=120)
    next_steps: list[str] = Field(min_length=1, max_length=12)
    citizen_voice_required: bool = True
    political_recommendation: bool = False
    proof_stage: CivicProofStage = CivicProofStage.SOURCE_VERIFIED
    proof_refs: list[str] = Field(default_factory=list)


def validate_civic_plan(plan: CivicActionPlan) -> CivicActionPlan:
    """Fail closed on civic plans that overstate proof or political authority."""
    if plan.political_recommendation:
        raise ValueError("COMMONS civic plans must not contain political recommendations.")
    if not plan.citizen_voice_required:
        raise ValueError("The citizen must retain control over their own civic position.")
    if plan.proof_stage is not CivicProofStage.SOURCE_VERIFIED and not plan.proof_refs:
        raise ValueError("Advanced civic proof stages require external proof references.")
    return plan
