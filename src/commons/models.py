from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class Route(StrEnum):
    REQUEST_INFO = "request_info"
    RETRIEVE = "retrieve"
    CALCULATE = "calculate"
    REASON = "reason"
    TRANSLATE = "translate"
    SPECIALIST = "specialist"
    WORKFLOW = "workflow"
    HUMAN = "human"


class OutcomeStatus(StrEnum):
    RESOLVED = "resolved"
    PARTIAL = "partial"
    UNRESOLVED = "unresolved"
    HARMFUL = "harmful"
    UNKNOWN = "unknown"


class ProblemInput(BaseModel):
    text: str = Field(min_length=1)
    language: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class Assessment(BaseModel):
    domain: str
    urgency: float = Field(ge=0, le=4)
    high_stakes: float = Field(ge=0, le=1)
    enough_information: float = Field(ge=0, le=1)
    safe_to_automate: float = Field(ge=0, le=1)
    needs_human_review: float = Field(ge=0, le=1)
    capability: str
    domain_confidence: float | None = Field(default=None, ge=0, le=1)
    capability_confidence: float | None = Field(default=None, ge=0, le=1)
    model: str | None = None


class RouteDecision(BaseModel):
    route: Route
    reason: str
    policy_version: str


class CaseRecord(BaseModel):
    case_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    problem: ProblemInput
    assessment: Assessment
    decision: RouteDecision


class OutcomeInput(BaseModel):
    status: OutcomeStatus
    verified: bool = False
    verification_method: str | None = None
    user_benefit: int | None = Field(default=None, ge=1, le=5)
    recurrence: bool | None = None
    notes: str | None = None


class OutcomeRecord(OutcomeInput):
    case_id: str
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
