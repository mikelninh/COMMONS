from fastapi.testclient import TestClient

from commons.app import app

client = TestClient(app)


def create_case() -> dict:
    response = client.post(
        "/civic/cases/public-space",
        json={"raw_need": "There is bulky waste blocking the pavement near me."},
    )
    assert response.status_code == 200
    return response.json()


def test_real_civic_case_starts_as_persistent_draft() -> None:
    case = create_case()
    assert case["status"] == "draft"
    fetched = client.get(f"/civic/cases/public-space/{case['case_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["raw_need"].startswith("There is bulky waste")


def test_case_becomes_ready_only_with_official_minimum_fields() -> None:
    case = create_case()
    case_id = case["case_id"]

    empty_packet = client.post(f"/civic/cases/public-space/{case_id}/prepare")
    assert empty_packet.status_code == 200
    assert empty_packet.json()["ready"] is False
    assert len(empty_packet.json()["blockers"]) >= 2

    patched = client.patch(
        f"/civic/cases/public-space/{case_id}",
        json={
            "district": "Neukölln",
            "street": "Sonnenallee",
            "subject": "Bulky waste blocking pavement",
            "description": "Two mattresses are blocking most of the pavement.",
        },
    )
    assert patched.status_code == 200
    assert patched.json()["status"] == "ready"

    packet = client.post(f"/civic/cases/public-space/{case_id}/prepare")
    assert packet.status_code == 200
    assert packet.json()["ready"] is True
    assert packet.json()["where"]["district"] == "Neukölln"
    assert packet.json()["what"]["subject"] == "Bulky waste blocking pavement"


def test_photo_submission_requires_rights_confirmation() -> None:
    case = create_case()
    response = client.patch(
        f"/civic/cases/public-space/{case['case_id']}",
        json={"has_photo": True, "photo_rights_confirmed": False},
    )
    assert response.status_code == 422


def test_status_updates_require_email() -> None:
    case = create_case()
    response = client.patch(
        f"/civic/cases/public-space/{case['case_id']}",
        json={"wants_status_updates": True},
    )
    assert response.status_code == 422


def test_handoff_is_not_recorded_as_submission() -> None:
    case = create_case()
    case_id = case["case_id"]
    client.patch(
        f"/civic/cases/public-space/{case_id}",
        json={"district": "Mitte", "subject": "Illegal rubbish"},
    )

    handoff = client.post(f"/civic/cases/public-space/{case_id}/handoff")
    assert handoff.status_code == 200
    stored = client.get(f"/civic/cases/public-space/{case_id}").json()
    assert stored["status"] == "handed_off"
    assert stored["proof_stage"] == "source_verified"
    assert stored["report_number"] is None


def test_official_report_number_advances_only_to_action_confirmed() -> None:
    case = create_case()
    case_id = case["case_id"]
    client.patch(
        f"/civic/cases/public-space/{case_id}",
        json={"district": "Mitte", "subject": "Illegal rubbish"},
    )
    client.post(f"/civic/cases/public-space/{case_id}/handoff")

    receipt = client.post(
        f"/civic/cases/public-space/{case_id}/receipt",
        json={"report_number": "OA-TEST-123"},
    )
    assert receipt.status_code == 200
    body = receipt.json()
    assert body["status"] == "submitted"
    assert body["proof_stage"] == "action_confirmed"
    assert body["report_number"] == "OA-TEST-123"
    assert any("External status verification is still pending" in note for note in body["proof_notes"])


def test_real_report_workspace_is_available() -> None:
    page = client.get("/civic/report")
    assert page.status_code == 200
    assert "Report a real public-space problem." in page.text
    assert "Meldungsnummer" in page.text
