from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from commons.models import (
    CapabilityMatch,
    CapabilityOffer,
    CapabilityRequirement,
    CapabilitySelectionRequest,
    CaseRecord,
    OutcomeInput,
    OutcomeRecord,
    ProblemInput,
    ProofRecord,
    LiveCapabilitySelection,
    ProviderProfile,
)
from commons.proof import ProofLedger
from commons.registry import CapabilityRegistry
from commons.selector import JevCapabilitySelector
from commons.service import CommonsService

app = FastAPI(
    title="COMMONS",
    version="0.3.0-alpha",
    description="Accountable intelligence-to-action infrastructure.",
)

analysis_service = CommonsService(persist=False)
_persistent_service: CommonsService | None = None
_demo_path = Path(__file__).parent / "static" / "index.html"
registry = CapabilityRegistry()
proof_ledger = ProofLedger()
capability_selector = JevCapabilitySelector()


def persistent_service() -> CommonsService:
    global _persistent_service
    if _persistent_service is None:
        _persistent_service = CommonsService()
    return _persistent_service


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def demo() -> HTMLResponse:
    return HTMLResponse(_demo_path.read_text(encoding="utf-8"))


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
