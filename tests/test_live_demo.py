from fastapi.testclient import TestClient

from commons.app import app

client = TestClient(app)


def test_cinematic_live_demo_is_available() -> None:
    response = client.get("/live")
    assert response.status_code == 200
    assert "COMMONS / LIVE" in response.text
    assert "DEMO MODE · SYNTHETIC EVENTS" in response.text
    assert "Intention → verified action." in response.text
    assert "Citizen Approval" in response.text
    assert "Proof Ledger" in response.text


def test_live_demo_makes_synthetic_status_explicit() -> None:
    response = client.get("/live")
    assert "SYNTHETIC EVENTS" in response.text
    assert "reality &gt; model opinion" in response.text
