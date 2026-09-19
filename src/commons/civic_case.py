from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, EmailStr, Field, model_validator

from commons.civic import CivicProofStage


OFFICIAL_REPORT_URL = "https://ordnungsamt.berlin.de/frontend/meldungNeu/wo"
OFFICIAL_STATUS_URL = "https://ordnungsamt.berlin.de/frontend/aktuelleMeldungen"


class PublicSpaceCaseStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    HANDED_OFF = "handed_off"
    SUBMITTED = "submitted"
    CLOSED = "closed"


class PublicSpaceCase(BaseModel):
    case_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: PublicSpaceCaseStatus = PublicSpaceCaseStatus.DRAFT

    raw_need: str = Field(min_length=1, max_length=4000)

    district: str | None = Field(default=None, max_length=120)
    street: str | None = Field(default=None, max_length=300)
    house_number: str | None = Field(default=None, max_length=40)
    location_notes: str | None = Field(default=None, max_length=1000)

    subject: str | None = Field(default=None, max_length=240)
    description: str | None = Field(default=None, max_length=3000)

    has_photo: bool = False
    photo_rights_confirmed: bool = False

    wants_status_updates: bool = False
    email: EmailStr | None = None
    available_for_questions: bool = False

    official_report_url: str = OFFICIAL_REPORT_URL
    official_status_url: str = OFFICIAL_STATUS_URL

    report_number: str | None = Field(default=None, max_length=120)
    official_receipt_ref: str | None = Field(default=None, max_length=1000)

    proof_stage: CivicProofStage = CivicProofStage.SOURCE_VERIFIED
    proof_notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def contact_consistency(self) -> "PublicSpaceCase":
        if self.wants_status_updates and not self.email:
            raise ValueError("An email address is required for automatic status updates.")
        if self.has_photo and not self.photo_rights_confirmed:
            raise ValueError("Photo rights must be confirmed before preparing a photo submission.")
        return self


class PublicSpaceCaseCreate(BaseModel):
    raw_need: str = Field(min_length=1, max_length=4000)


class PublicSpaceCasePatch(BaseModel):
    district: str | None = Field(default=None, max_length=120)
    street: str | None = Field(default=None, max_length=300)
    house_number: str | None = Field(default=None, max_length=40)
    location_notes: str | None = Field(default=None, max_length=1000)
    subject: str | None = Field(default=None, max_length=240)
    description: str | None = Field(default=None, max_length=3000)
    has_photo: bool | None = None
    photo_rights_confirmed: bool | None = None
    wants_status_updates: bool | None = None
    email: EmailStr | None = None
    available_for_questions: bool | None = None


class CivicSubmissionPacket(BaseModel):
    case_id: str
    ready: bool
    blockers: list[str] = Field(default_factory=list)
    where: dict[str, str | None]
    what: dict[str, str | None]
    who: dict[str, str | bool | None]
    official_report_url: str
    official_status_url: str
    proof_stage: CivicProofStage
    important_notices: list[str]


class CivicReceiptInput(BaseModel):
    report_number: str = Field(min_length=1, max_length=120)
    official_receipt_ref: str | None = Field(default=None, max_length=1000)


def prepare_submission_packet(case: PublicSpaceCase) -> CivicSubmissionPacket:
    blockers: list[str] = []
    if not case.district:
        blockers.append("Choose one of Berlin's 12 districts.")
    if not case.subject:
        blockers.append("Add a short subject describing one public-space issue.")
    if case.wants_status_updates and not case.email:
        blockers.append("Add an email address if you want automatic status updates.")
    if case.has_photo and not case.photo_rights_confirmed:
        blockers.append("Confirm that you hold the rights to any photo you plan to upload.")

    notices = [
        "COMMONS prepares the data but does not submit the government form for you.",
        "Use one issue per report; the official portal may reject or edit unsuitable content.",
        "Do not use this route for emergencies or matters requiring immediate intervention.",
    ]
    if case.has_photo:
        notices.append(
            "Berlin's terms grant participating administrations a simple usage right to uploaded photos, including possible publication."
        )

    return CivicSubmissionPacket(
        case_id=case.case_id,
        ready=not blockers,
        blockers=blockers,
        where={
            "district": case.district,
            "street": case.street,
            "house_number": case.house_number,
            "location_notes": case.location_notes,
        },
        what={
            "subject": case.subject,
            "description": case.description,
        },
        who={
            "wants_status_updates": case.wants_status_updates,
            "email": str(case.email) if case.email else None,
            "available_for_questions": case.available_for_questions,
        },
        official_report_url=case.official_report_url,
        official_status_url=case.official_status_url,
        proof_stage=case.proof_stage,
        important_notices=notices,
    )
