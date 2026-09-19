from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from commons.civic import CivicProofStage
from commons.civic_case import (
    CivicReceiptInput,
    CivicSubmissionPacket,
    PublicSpaceCase,
    PublicSpaceCaseCreate,
    PublicSpaceCasePatch,
    PublicSpaceCaseStatus,
    prepare_submission_packet,
)
from commons.civic_router import CivicActionResult, CivicNeedInput, route_civic_need
from commons.models import (
    ActorRef,
    CapabilityMatch,
    CapabilityOffer,
    CapabilityRequirement,
    CapabilitySelectionRequest,
    CaseRecord,
    FoundingCapabilitySubmission,
    MachineCapabilityManifest,
    MachineOnboardingResult,
    NeedRequest,
    OutcomeInput,
    OutcomeRecord,
    ProblemInput,
    ProofRecord,
    QuickCapabilityIntake,
    LiveCapabilitySelection,
    ProviderProfile,
)
from commons.builtins import seed_builtin_capabilities
from commons.proof import ProofLedger
from commons.registry import CapabilityRegistry
from commons.selector import JevCapabilitySelector
from commons.service import CommonsService
from commons.store import CaseStore

app = FastAPI(
    title="COMMONS",
    version="0.3.0-alpha",
    description="Accountable intelligence-to-action infrastructure.",
)

analysis_service = CommonsService(persist=False)
_persistent_service: CommonsService | None = None
_demo_path = Path(__file__).parent / "static" / "index.html"
_join_path = Path(__file__).parent / "static" / "join.html"
_civic_path = Path(__file__).parent / "static" / "civic.html"
_civic_report_path = Path(__file__).parent / "static" / "civic_report.html"
registry = CapabilityRegistry()
seed_builtin_capabilities(registry)
proof_ledger = ProofLedger()
capability_selector = JevCapabilitySelector()
founding_store = CaseStore()


def persistent_service() -> CommonsService:
    global _persistent_service
    if _persistent_service is None:
        _persistent_service = CommonsService()
    return _persistent_service


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def demo() -> HTMLResponse:
    return HTMLResponse(_demo_path.read_text(encoding="utf-8"))


@app.get("/join", response_class=HTMLResponse, include_in_schema=False)
def join_capabilities() -> HTMLResponse:
    return HTMLResponse(_join_path.read_text(encoding="utf-8"))


@app.get("/civic", response_class=HTMLResponse, include_in_schema=False)
def civic_action_os() -> HTMLResponse:
    return HTMLResponse(_civic_path.read_text(encoding="utf-8"))


@app.post("/civic/action", response_model=CivicActionResult)
def civic_action(need: CivicNeedInput) -> CivicActionResult:
    return route_civic_need(need)


@app.get("/civic/report", response_class=HTMLResponse, include_in_schema=False)
def civic_public_space_report() -> HTMLResponse:
    return HTMLResponse(_civic_report_path.read_text(encoding="utf-8"))


@app.post("/civic/cases/public-space", response_model=PublicSpaceCase)
def create_public_space_case(payload: PublicSpaceCaseCreate) -> PublicSpaceCase:
    record = PublicSpaceCase(raw_need=payload.raw_need)
    return founding_store.save_public_space_case(record)


@app.get("/civic/cases/public-space/{case_id}", response_model=PublicSpaceCase)
def get_public_space_case(case_id: str) -> PublicSpaceCase:
    record = founding_store.get_public_space_case(case_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Civic case not found.")
    return record


@app.patch("/civic/cases/public-space/{case_id}", response_model=PublicSpaceCase)
def patch_public_space_case(case_id: str, patch: PublicSpaceCasePatch) -> PublicSpaceCase:
    record = founding_store.get_public_space_case(case_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Civic case not found.")

    updates = patch.model_dump(exclude_unset=True)
    candidate = record.model_copy(
        update={
            **updates,
            "updated_at": datetime.now(timezone.utc),
        }
    )
    # Re-validate cross-field constraints after model_copy.
    candidate = PublicSpaceCase.model_validate(candidate.model_dump())
    packet = prepare_submission_packet(candidate)
    candidate.status = (
        PublicSpaceCaseStatus.READY if packet.ready else PublicSpaceCaseStatus.DRAFT
    )
    return founding_store.save_public_space_case(candidate)


@app.post(
    "/civic/cases/public-space/{case_id}/prepare",
    response_model=CivicSubmissionPacket,
)
def prepare_public_space_submission(case_id: str) -> CivicSubmissionPacket:
    record = founding_store.get_public_space_case(case_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Civic case not found.")
    packet = prepare_submission_packet(record)
    record.status = PublicSpaceCaseStatus.READY if packet.ready else PublicSpaceCaseStatus.DRAFT
    record.updated_at = datetime.now(timezone.utc)
    founding_store.save_public_space_case(record)
    return packet


@app.post(
    "/civic/cases/public-space/{case_id}/handoff",
    response_model=CivicSubmissionPacket,
)
def handoff_public_space_submission(case_id: str) -> CivicSubmissionPacket:
    record = founding_store.get_public_space_case(case_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Civic case not found.")
    packet = prepare_submission_packet(record)
    if not packet.ready:
        raise HTTPException(status_code=400, detail={"blockers": packet.blockers})
    record.status = PublicSpaceCaseStatus.HANDED_OFF
    record.updated_at = datetime.now(timezone.utc)
    record.proof_notes.append("Official Ordnungsamt-Online handoff opened; submission not yet proven.")
    founding_store.save_public_space_case(record)
    return prepare_submission_packet(record)


@app.post(
    "/civic/cases/public-space/{case_id}/receipt",
    response_model=PublicSpaceCase,
)
def record_public_space_receipt(
    case_id: str,
    receipt: CivicReceiptInput,
) -> PublicSpaceCase:
    record = founding_store.get_public_space_case(case_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Civic case not found.")
    record.report_number = receipt.report_number
    record.official_receipt_ref = receipt.official_receipt_ref
    record.status = PublicSpaceCaseStatus.SUBMITTED
    record.updated_at = datetime.now(timezone.utc)
    record.proof_stage = CivicProofStage.ACTION_CONFIRMED
    record.proof_notes.append(
        "Citizen supplied the official Meldungsnummer after submission. External status verification is still pending."
    )
    return founding_store.save_public_space_case(record)


@app.post("/founding-capabilities", response_model=FoundingCapabilitySubmission)
def submit_founding_capability(
    submission: FoundingCapabilitySubmission,
) -> FoundingCapabilitySubmission:
    if not submission.consent_to_pilot:
        raise HTTPException(status_code=400, detail="Pilot consent is required.")
    return founding_store.save_founding_capability(submission)


@app.post("/needs", response_model=NeedRequest)
def submit_need(need: NeedRequest) -> NeedRequest:
    """Any actor may express a need. Requesting never grants execution authority."""
    return founding_store.save_need(need)


@app.post("/founding-capabilities/quick", response_model=FoundingCapabilitySubmission)
def submit_quick_capability(
    intake: QuickCapabilityIntake,
) -> FoundingCapabilitySubmission:
    if not intake.consent_to_pilot:
        raise HTTPException(status_code=400, detail="Pilot consent is required.")

    submission = FoundingCapabilitySubmission(
        display_name=intake.display_name,
        provider_kind=intake.provider_kind,
        what_people_ask_you_for=intake.story,
        problems_you_enjoy_helping_with=intake.story,
        what_you_can_deliver=intake.story,
        location=intake.location,
        languages=intake.languages,
        compensation=intake.compensation,
        consent_to_pilot=True,
    )
    return founding_store.save_founding_capability(submission)


@app.post("/machine/capabilities", response_model=MachineOnboardingResult)
def onboard_machine_capabilities(
    manifest: MachineCapabilityManifest,
) -> MachineOnboardingResult:
    """One machine-readable manifest declares a machine and its capabilities.

    Machine supply is inactive until a later verification/approval step.
    """
    provider = registry.register_provider(
        ProviderProfile(
            name=manifest.name,
            kind=manifest.kind,
            description=manifest.description,
            location=manifest.location,
            languages=manifest.languages,
        )
    )

    offers: list[CapabilityOffer] = []
    for spec in manifest.capabilities:
        offer = registry.register_capability(
            CapabilityOffer(
                provider_id=provider.provider_id,
                capability_type=spec.capability_type,
                description=spec.description,
                tags=spec.tags,
                languages=spec.languages or manifest.languages,
                location=manifest.location,
                unit=spec.unit,
                capacity_available=spec.capacity_available,
                price_eur=spec.price_eur,
                authority_ceiling=spec.requested_authority,
                active=False,
            )
        )
        offers.append(offer)

    return MachineOnboardingResult(provider=provider, capabilities=offers)


@app.get("/health")
def health() -> dict[str, str | bool]:
    return {
        "status": "ok",
        "version": "0.3.0-alpha",
        "jev_configured": bool(os.getenv("TYPESAFE_API_KEY")),
        "release_gate": "private-redteam",
        "public_ready": False,
    }


@app.post("/analyse", response_model=CaseRecord)
def analyse(problem: ProblemInput) -> CaseRecord:
    """Stateless analysis: no local database required."""
    return analysis_service.analyse(problem)


@app.post("/cases", response_model=CaseRecord)
def create_case(problem: ProblemInput) -> CaseRecord:
    """Persistent local/pilot path for outcome tracking."""
    return persistent_service().assess(problem)


@app.post("/cases/{case_id}/outcome", response_model=OutcomeRecord)
def record_outcome(case_id: str, outcome: OutcomeInput) -> OutcomeRecord:
    try:
        return persistent_service().record_outcome(case_id, outcome)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Case not found") from exc


@app.post("/network/providers", response_model=ProviderProfile)
def register_provider(provider: ProviderProfile) -> ProviderProfile:
    """Declare a provider. Declaration does not grant execution authority."""
    return registry.register_provider(provider)


@app.post("/network/capabilities", response_model=CapabilityOffer)
def register_capability(offer: CapabilityOffer) -> CapabilityOffer:
    """Declare a capability; unverified supply is automatically authority-capped."""
    try:
        return registry.register_capability(offer)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/network/capabilities", response_model=list[CapabilityOffer])
def list_capabilities() -> list[CapabilityOffer]:
    return registry.list_active()


@app.post("/network/match", response_model=list[CapabilityMatch])
def match_capabilities(requirement: CapabilityRequirement) -> list[CapabilityMatch]:
    return registry.match(requirement)


@app.post("/network/select", response_model=LiveCapabilitySelection)
def select_live_capability(request: CapabilitySelectionRequest) -> LiveCapabilitySelection:
    """Choose only among capabilities that deterministic filtering says are feasible."""
    candidates = registry.match(request.requirement, limit=request.max_candidates)
    if not candidates:
        raise HTTPException(status_code=404, detail="No feasible live capability found.")
    try:
        return capability_selector.choose(
            request.need,
            candidates,
            context=request.context,
            providers=registry.providers,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/proof", response_model=ProofRecord)
def record_proof(proof: ProofRecord) -> ProofRecord:
    try:
        return proof_ledger.record(proof)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/proof/{case_id}", response_model=list[ProofRecord])
def get_proof(case_id: str) -> list[ProofRecord]:
    return proof_ledger.for_case(case_id)
