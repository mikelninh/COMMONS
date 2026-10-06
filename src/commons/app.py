from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from commons.berlin_heat_wfs import WFSFetchError, fetch_record, run_official_heat
from commons.cologne_tree_wfs import (
    CologneWFSFetchError,
    fetch_record as fetch_cologne_tree,
    run_official_tree,
)
from commons.models import CaseRecord, OutcomeInput, OutcomeRecord, ProblemInput
from commons.semantic_city import list_scenarios, run_scenario
from commons.semantic_interop import berlin_heat_ngsi_ld
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


@app.get("/semantic-city/berlin/heat")
def semantic_city_berlin_heat(
    lon: float = 13.4132,
    lat: float = 52.5219,
    radius_m: float = 25.0,
) -> dict[str, object]:
    """Fetch official Berlin structural heat evidence for one point."""
    if radius_m <= 0 or radius_m > 500:
        raise HTTPException(
            status_code=400,
            detail="radius_m must be > 0 and <= 500",
        )
    try:
        record = fetch_record(
            longitude=lon,
            latitude=lat,
            radius_m=radius_m,
            allow_fallback=False,
        )
        return {
            "status": "official_structural_record",
            "truth_boundary": (
                "Klimaanalysekarten 2022 are structural modeled "
                "evidence, not current weather."
            ),
            "record": record.to_dict(),
            "scenario": run_official_heat(record),
        }
    except WFSFetchError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Berlin WFS evidence unavailable: {exc}",
        ) from exc


@app.get("/semantic-city/berlin/heat/ngsi-ld")
def semantic_city_berlin_heat_ngsi_ld(\n    lon: float = 13.4132,\n    lat: float = 52.5219,\n    radius_m: float = 25.0,\n) -> list[dict[str, object]]:\n    """Return official Berlin heat evidence as NGSI-LD."""\n    if radius_m <= 0 or radius_m > 500:\n        raise HTTPException(\n            status_code=400,\n            detail="radius_m must be > 0 and <= 500",\n        )\n    try:\n        record = fetch_record(\n            longitude=lon,\n            latitude=lat,\n            radius_m=radius_m,\n            allow_fallback=False,\n        )\n        return berlin_heat_ngsi_ld(record)\n    except WFSFetchError as exc:\n        raise HTTPException(\n            status_code=502,\n            detail=f"Berlin WFS evidence unavailable: {exc}",\n        ) from exc\n

@app.get("/semantic-city/cologne/tree")
def semantic_city_cologne_tree() -> dict[str, object]:
    """Fetch one official Cologne tree-cadastre record."""
    try:
        record = fetch_cologne_tree()
        return {
            "status": "official_municipal_record",
            "truth_boundary": (
                "The Cologne cadastre covers city-managed trees "
                "only and does not replace an official site survey."
            ),
            "record": record.to_dict(),
            "scenario": run_official_tree(record),
        }
    except CologneWFSFetchError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Cologne WFS evidence unavailable: {exc}",
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
