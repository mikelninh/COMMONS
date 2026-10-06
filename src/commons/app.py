from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from commons.models import CaseRecord, OutcomeInput, OutcomeRecord, ProblemInput
from commons.semantic_city import list_scenarios, run_scenario
from commons.service import CommonsService

app = FastAPI(
    title="COMMONS",
    version="0.2.0",
    description="Accountable intelligence-to-action infrastructure.",
)

analysis_service = CommonsService(persist=False)
_persistent_service: CommonsService | None = None
_demo_path = Path(__file__).parent / "static" / "index.html"


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
        "version": "0.2.0",
        "jev_configured": bool(os.getenv("TYPESAFE_API_KEY")),
    }


@app.get("/semantic-city/scenarios")
def semantic_city_scenarios() -> dict[str, object]:
    """List the deterministic Semantic City application scenarios."""
    return {
        "status": "demo_fixture",
        "truth_boundary": (
            "Numeric values and dependency topology are illustrative "
            "until replaced by live official ingestion."
        ),
        "scenarios": list_scenarios(),
    }


@app.get("/semantic-city/scenarios/{scenario_id}")
def semantic_city_scenario(
    scenario_id: str,
) -> dict[str, object]:
    """Run one SPARQL-backed scenario with explicit authority metadata."""
    try:
        return run_scenario(scenario_id).to_dict()
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


@app.post("/analyse", response_model=CaseRecord)
def analyse(problem: ProblemInput) -> CaseRecord:
    """Stateless civic/demo analysis: no local database required."""
    return analysis_service.analyse(problem)


@app.post("/cases", response_model=CaseRecord)
def create_case(problem: ProblemInput) -> CaseRecord:
    """Persistent local/pilot path for outcome tracking."""
    return persistent_service().assess(problem)


@app.post(
    "/cases/{case_id}/outcome",
    response_model=OutcomeRecord,
)
def record_outcome(
    case_id: str,
    outcome: OutcomeInput,
) -> OutcomeRecord:
    try:
        return persistent_service().record_outcome(
            case_id,
            outcome,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail="Case not found",
        ) from exc
