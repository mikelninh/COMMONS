from fastapi.testclient import TestClient

from commons.app import app

client = TestClient(app)


def test_cinematic_live_demo_is_available() -> None:
    response = client.get("/live")
    assert response.status_code == 200
    assert "COMMONS</b> / LIVE" in response.text
    assert "REAL MODE" in response.text
    assert "On-device Vision" in response.text
    assert "Citizen Approval" in response.text
    assert "Persistent Civic Case" in response.text


def test_real_live_demo_keeps_photo_local_and_separates_synthetic_mode() -> None:
    response = client.get("/live")
    assert "Your photo stays in this browser." in response.text
    assert "photo sent to server?" in response.text
    assert "NO" in response.text
    assert "watch synthetic walkthrough" in response.text
    assert "SYNTHETIC WALKTHROUGH" in response.text


def test_real_live_demo_connects_to_real_civic_case_api() -> None:
    response = client.get("/live")
    assert '"/civic/action"' in response.text
    assert '"/civic/cases/public-space"' in response.text
    assert '"/prepare"' in response.text
    assert '"/receipt"' in response.text
    assert "Meldungsnummer" in response.text
