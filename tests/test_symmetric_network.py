from pathlib import Path

from fastapi.testclient import TestClient

from commons.app import app, registry
from commons.models import NeedRequest, ProviderKind
from commons.store import CaseStore

client = TestClient(app)


def test_builtin_machine_supply_is_registered() -> None:
    capabilities = {c.capability_id: c for c in registry.list_active()}
    assert "commons-need-router" in capabilities
    assert "commons-live-selector" in capabilities
    assert "commons-proof-guard" in capabilities


def test_ai_agent_can_request_a_need_without_gaining_execution_authority() -> None:
    response = client.post(
        "/needs",
        json={
            "text": "I need an independent source confirming this deadline.",
            "requester": {
                "kind": "ai",
                "display_name": "Research Agent",
            },
            "principal": {
                "kind": "person",
                "display_name": "Pilot user",
            },
            "authority_ceiling": "read",
            "requires_human_approval": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["requester"]["kind"] == "ai"
    assert body["authority_ceiling"] == "read"
    assert body["requires_human_approval"] is True


def test_machine_manifest_declares_supply_but_does_not_activate_it() -> None:
    response = client.post(
        "/machine/capabilities",
        json={
            "name": "Test Expert Agent",
            "kind": "ai",
            "interface": "http",
            "endpoint": "https://example.invalid/agent",
            "capabilities": [
                {
                    "capability_type": "translation",
                    "description": "Draft Vietnamese/German translation.",
                    "languages": ["vi", "de"],
                    "price_eur": 0.03,
                    "requested_authority": "execute_consequential",
                }
            ],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "declared_pending_verification"
    assert body["provider"]["verification_status"] == "declared"
    assert body["capabilities"][0]["active"] is False
    assert body["capabilities"][0]["authority_ceiling"] == "draft"


def test_quick_human_onboarding_needs_only_one_story() -> None:
    response = client.post(
        "/founding-capabilities/quick",
        json={
            "display_name": "M",
            "provider_kind": "person",
            "story": "People ask me to explain confusing technical and administrative problems in plain language.",
            "languages": ["de", "en"],
            "consent_to_pilot": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["review_status"] == "pending_review"
    assert body["what_people_ask_you_for"].startswith("People ask me")


def test_store_persists_machine_requested_need(tmp_path: Path) -> None:
    store = CaseStore(str(tmp_path / "needs.db"))
    need = NeedRequest(
        text="Need a verified source.",
        requester={
            "kind": ProviderKind.AI,
            "display_name": "Verifier Agent",
        },
        authority_ceiling="read",
    )
    store.save_need(need)
    rows = store.list_needs()
    assert len(rows) == 1
    assert rows[0].requester.kind is ProviderKind.AI
