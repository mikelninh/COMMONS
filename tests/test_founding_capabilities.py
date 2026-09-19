from pathlib import Path

from fastapi.testclient import TestClient

from commons.app import app
from commons.models import FoundingCapabilitySubmission, ProviderKind
from commons.store import CaseStore

client = TestClient(app)


def sample_submission(**overrides):
    data = dict(
        display_name="Founding Helper",
        provider_kind="person",
        what_people_ask_you_for="Explaining German bureaucracy in plain language.",
        problems_you_enjoy_helping_with="Helping people understand confusing letters.",
        inputs_you_need="The letter and relevant context.",
        what_you_can_deliver="A plain-language explanation and draft next step.",
        how_to_verify_it_worked="The person confirms they understand what to do next.",
        location="Berlin",
        languages=["de", "en"],
        availability="2 hours per week",
        compensation="sponsored cases",
        never_automate="Submitting anything in my name.",
        ai_can_help_with="Extracting text and finding official sources.",
        human_judgment_matters_for="Ambiguity, tone and sensitive context.",
        evidence_or_examples="Past volunteer experience.",
        consent_to_pilot=True,
    )
    data.update(overrides)
    return data


def test_join_page_is_available() -> None:
    response = client.get("/join")
    assert response.status_code == 200
    assert "What can you help the world do?" in response.text
    assert "Nobody automatically earns authority" in response.text


def test_founding_submission_requires_consent() -> None:
    response = client.post(
        "/founding-capabilities",
        json=sample_submission(consent_to_pilot=False),
    )
    assert response.status_code == 400


def test_founding_submission_stays_pending_review() -> None:
    response = client.post(
        "/founding-capabilities",
        json=sample_submission(),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["review_status"] == "pending_review"
    assert body["provider_kind"] == "person"


def test_store_persists_founding_capabilities(tmp_path: Path) -> None:
    store = CaseStore(str(tmp_path / "pilot.db"))
    submission = FoundingCapabilitySubmission(
        **sample_submission(provider_kind=ProviderKind.PERSON)
    )
    store.save_founding_capability(submission)

    rows = store.list_founding_capabilities()

    assert len(rows) == 1
    assert rows[0].submission_id == submission.submission_id
    assert rows[0].review_status == "pending_review"
