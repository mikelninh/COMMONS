from fastapi import FastAPI, HTTPException

from commons.models import CaseRecord, OutcomeInput, OutcomeRecord, ProblemInput
from commons.service import CommonsService

app = FastAPI(
    title="COMMONS",
    version="0.1.0",
    description="Accountable intelligence-to-action infrastructure.",
)

service = CommonsService()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/cases", response_model=CaseRecord)
def create_case(problem: ProblemInput) -> CaseRecord:
    return service.assess(problem)


@app.post("/cases/{case_id}/outcome", response_model=OutcomeRecord)
def record_outcome(case_id: str, outcome: OutcomeInput) -> OutcomeRecord:
    try:
        return service.record_outcome(case_id, outcome)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Case not found") from exc
