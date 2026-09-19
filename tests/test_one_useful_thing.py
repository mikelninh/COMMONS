from fastapi.testclient import TestClient

from commons.app import app

client = TestClient(app)


def test_home_is_the_simple_useful_flow() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Was ist kaputt?" in response.text
    assert "Meldung vorbereiten" in response.text
    assert "Nichts wird ohne dich abgeschickt." in response.text


def test_old_experiment_home_remains_available_under_lab() -> None:
    response = client.get("/lab")
    assert response.status_code == 200
    assert "COMMONS" in response.text


def test_public_space_case_can_go_prepare_handoff_receipt() -> None:
    create = client.post(
        "/civic/cases/public-space",
        json={"raw_need": "Schlagloch auf dem Radweg. Seit mehreren Tagen sichtbar."},
    )
    assert create.status_code == 200
    case_id = create.json()["case_id"]

    patch = client.patch(
        f"/civic/cases/public-space/{case_id}",
        json={
            "district": "Mitte",
            "street": "Beispielstraße",
            "house_number": "12",
            "subject": "Schlagloch auf dem Radweg",
            "description": "Deutliches Schlagloch im Radweg vor Hausnummer 12.",
            "wants_status_updates": False,
        },
    )
    assert patch.status_code == 200
    assert patch.json()["status"] == "ready"

    prepared = client.post(f"/civic/cases/public-space/{case_id}/prepare")
    assert prepared.status_code == 200
    packet = prepared.json()
    assert packet["ready"] is True
    assert packet["proof_stage"] == "action_prepared"
    assert packet["what"]["subject"] == "Schlagloch auf dem Radweg"

    handoff = client.post(f"/civic/cases/public-space/{case_id}/handoff")
    assert handoff.status_code == 200
    assert handoff.json()["proof_stage"] == "action_prepared"
    assert "ordnungsamt.berlin.de" in handoff.json()["official_report_url"]

    receipt = client.post(
        f"/civic/cases/public-space/{case_id}/receipt",
        json={"report_number": "TEST-2026-123"},
    )
    assert receipt.status_code == 200
    assert receipt.json()["report_number"] == "TEST-2026-123"
    assert receipt.json()["proof_stage"] == "action_confirmed"


def test_status_updates_still_require_email() -> None:
    create = client.post(
        "/civic/cases/public-space",
        json={"raw_need": "Müll im öffentlichen Raum"},
    )
    case_id = create.json()["case_id"]

    response = client.patch(
        f"/civic/cases/public-space/{case_id}",
        json={
            "district": "Neukölln",
            "subject": "Müllablagerung",
            "wants_status_updates": True,
        },
    )
    assert response.status_code == 422
