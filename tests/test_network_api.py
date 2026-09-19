from fastapi.testclient import TestClient

from commons.app import app

client = TestClient(app)


def test_health_marks_alpha_as_not_public_ready() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["public_ready"] is False
    assert body["release_gate"] == "private-redteam"


def test_network_onboarding_caps_unverified_authority() -> None:
    provider = client.post(
        "/network/providers",
        json={"name": "Test Driver", "kind": "person", "location": "Berlin"},
    )
    assert provider.status_code == 200
    provider_id = provider.json()["provider_id"]

    offer = client.post(
        "/network/capabilities",
        json={
            "provider_id": provider_id,
            "capability_type": "transport",
            "description": "Can drive deliveries.",
            "authority_ceiling": "execute_consequential",
        },
    )
    assert offer.status_code == 200
    assert offer.json()["authority_ceiling"] == "draft"


def test_proof_api_rejects_self_verification() -> None:
    response = client.post(
        "/proof",
        json={
            "case_id": "api-proof-case",
            "provider_id": "same-provider",
            "verifier_id": "same-provider",
            "level": "externally_verified",
        },
    )
    assert response.status_code == 400
