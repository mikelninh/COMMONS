from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class Route(StrEnum):
    REQUEST_INFO = "request_info"
    RETRIEVE = "retrieve"
    CALCULATE = "calculate"
    REASON = "reason"
    DELIBERATE = "deliberate"
    TRANSLATE = "translate"
    VERIFY = "verify"
    SPECIALIST = "specialist"
    WORKFLOW = "workflow"
    HUMAN = "human"


class OutcomeStatus(StrEnum):
    RESOLVED = "resolved"
    PARTIAL = "partial"
    UNRESOLVED = "unresolved"
    HARMFUL = "harmful"
    UNKNOWN = "unknown"


class AuthorityLevel(StrEnum):
    READ = "read"
    EXPLAIN = "explain"
    TRANSLATE = "translate"
    DRAFT = "draft"
    EXECUTE_REVERSIBLE = "execute_reversible"
    EXECUTE_CONSEQUENTIAL = "execute_consequential"
    PROHIBITED = "prohibited"


class ProviderKind(StrEnum):
    PERSON = "person"
    BUSINESS = "business"
    NONPROFIT = "nonprofit"
    PUBLIC_SERVICE = "public_service"
    AI = "ai"
    SOFTWARE = "software"
    COMPUTE = "compute"
    RESOURCE = "resource"


class VerificationStatus(StrEnum):
    DECLARED = "declared"
    BASIC = "basic"
    VERIFIED = "verified"
    SUSPENDED = "suspended"


class ProofLevel(StrEnum):
    DECLARED = "declared"
    ACTIONED = "actioned"
    COUNTERPARTY_CONFIRMED = "counterparty_confirmed"
    EXTERNALLY_VERIFIED = "externally_verified"
    DURABLE = "durable"


class ProblemInput(BaseModel):
    text: str = Field(min_length=1, max_length=8000)
    language: str | None = None
    mode: Literal["citizen", "official", "community"] = "citizen"
    context: dict[str, Any] = Field(default_factory=dict)


class Assessment(BaseModel):
    domain: str
    urgency: float = Field(ge=0, le=4)
    high_stakes: float = Field(ge=0, le=1)
    enough_information: float = Field(ge=0, le=1)
    safe_to_automate: float = Field(ge=0, le=1)
    needs_human_review: float = Field(ge=0, le=1)
    capability: str
    affected_groups_present: float = Field(default=0.0, ge=0, le=1)
    contested_values_present: float = Field(default=0.0, ge=0, le=1)
    evidence_need: float = Field(default=0.0, ge=0, le=4)
    reversibility: float = Field(default=4.0, ge=0, le=4)
    domain_confidence: float | None = Field(default=None, ge=0, le=1)
    capability_confidence: float | None = Field(default=None, ge=0, le=1)
    model: str | None = None
    input_tokens: int | None = Field(default=None, ge=0)


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
    time_to_resolution_seconds: float | None = Field(default=None, ge=0)
    intelligence_cost_eur: float | None = Field(default=None, ge=0)
    user_benefit: int | None = Field(default=None, ge=1, le=5)
    agency_rating: int | None = Field(default=None, ge=1, le=5)
    recurrence: bool | None = None
    notes: str | None = None


class OutcomeRecord(OutcomeInput):
    case_id: str
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ProviderProfile(BaseModel):
    provider_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(min_length=1, max_length=200)
    kind: ProviderKind
    description: str | None = Field(default=None, max_length=2000)
    location: str | None = Field(default=None, max_length=300)
    languages: list[str] = Field(default_factory=list)
    verification_status: VerificationStatus = VerificationStatus.DECLARED
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CapabilityOffer(BaseModel):
    capability_id: str = Field(default_factory=lambda: str(uuid4()))
    provider_id: str
    capability_type: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=2000)
    tags: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    location: str | None = Field(default=None, max_length=300)
    unit: str = Field(default="task", max_length=80)
    capacity_available: float = Field(default=1.0, ge=0)
    price_eur: float | None = Field(default=None, ge=0)
    authority_ceiling: AuthorityLevel = AuthorityLevel.DRAFT
    verification_status: VerificationStatus = VerificationStatus.DECLARED
    evidence_refs: list[str] = Field(default_factory=list)
    active: bool = True
    success_count: int = Field(default=0, ge=0)
    failure_count: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CapabilityRequirement(BaseModel):
    capability_type: str = Field(min_length=1, max_length=120)
    tags: list[str] = Field(default_factory=list)
    language: str | None = None
    location: str | None = None
    max_price_eur: float | None = Field(default=None, ge=0)
    required_authority: AuthorityLevel = AuthorityLevel.READ
    require_verified_provider: bool = False
    allowed_provider_kinds: list[ProviderKind] = Field(default_factory=list)
    preferred_provider_kinds: list[ProviderKind] = Field(default_factory=list)


class CapabilityMatch(BaseModel):
    capability: CapabilityOffer
    score: float = Field(ge=0, le=1)
    reasons: list[str] = Field(default_factory=list)


class ProofRecord(BaseModel):
    proof_id: str = Field(default_factory=lambda: str(uuid4()))
    case_id: str
    capability_id: str | None = None
    provider_id: str | None = None
    verifier_id: str | None = None
    level: ProofLevel
    evidence_ref: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=2000)
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ResourceBudget(BaseModel):
    max_cost_eur: float = Field(ge=0)
    max_capabilities: int = Field(default=5, ge=1, le=50)
    prefer_verified: bool = True
    selection_mode: Literal["best_fit", "cost_efficiency"] = "best_fit"


class CapabilityPlan(BaseModel):
    requirements: list[CapabilityRequirement]
    matches: list[CapabilityMatch]
    total_cost_eur: float = Field(ge=0)
    unresolved_requirements: list[CapabilityRequirement] = Field(default_factory=list)
    within_budget: bool
