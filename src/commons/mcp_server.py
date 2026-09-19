from __future__ import annotations

import os
from typing import Any

import httpx
from mcp.server import MCPServer


API_URL = os.getenv("COMMONS_API_URL", "http://127.0.0.1:8000").rstrip("/")
mcp = MCPServer("COMMONS Capability Network")


def _post(path: str, payload: dict[str, Any]) -> Any:
    response = httpx.post(f"{API_URL}{path}", json=payload, timeout=30.0)
    response.raise_for_status()
    return response.json()


def _get(path: str) -> Any:
    response = httpx.get(f"{API_URL}{path}", timeout=30.0)
    response.raise_for_status()
    return response.json()


@mcp.tool()
def list_capabilities() -> list[dict[str, Any]]:
    """List currently active capabilities exposed by COMMONS."""
    return _get("/network/capabilities")


@mcp.tool()
def find_capabilities(
    capability_type: str,
    tags: list[str] | None = None,
    language: str | None = None,
    location: str | None = None,
    max_price_eur: float | None = None,
    required_authority: str = "read",
    require_verified_provider: bool = False,
    allowed_provider_kinds: list[str] | None = None,
    preferred_provider_kinds: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Find feasible human, agent, business, software or resource capabilities.

    Deterministic COMMONS policy filters candidates before any model selection.
    """
    payload = {
        "capability_type": capability_type,
        "tags": tags or [],
        "language": language,
        "location": location,
        "max_price_eur": max_price_eur,
        "required_authority": required_authority,
        "require_verified_provider": require_verified_provider,
        "allowed_provider_kinds": allowed_provider_kinds or [],
        "preferred_provider_kinds": preferred_provider_kinds or [],
    }
    return _post("/network/match", payload)


@mcp.tool()
def request_help(
    text: str,
    requester_name: str = "LLM agent",
    requester_kind: str = "ai",
    principal_name: str | None = None,
    budget_eur: float | None = None,
    authority_ceiling: str = "read",
    requires_human_approval: bool = True,
) -> dict[str, Any]:
    """Submit a need to COMMONS without granting extra execution authority.

    Use principal_name when the agent is acting for a human or organization.
    """
    payload: dict[str, Any] = {
        "text": text,
        "requester": {
            "kind": requester_kind,
            "display_name": requester_name,
        },
        "budget_eur": budget_eur,
        "authority_ceiling": authority_ceiling,
        "requires_human_approval": requires_human_approval,
    }
    if principal_name:
        payload["principal"] = {
            "kind": "person",
            "display_name": principal_name,
        }
    return _post("/needs", payload)


@mcp.tool()
def choose_capability(
    need: str,
    capability_type: str,
    tags: list[str] | None = None,
    language: str | None = None,
    location: str | None = None,
    max_price_eur: float | None = None,
    required_authority: str = "read",
    require_verified_provider: bool = False,
    allowed_provider_kinds: list[str] | None = None,
    preferred_provider_kinds: list[str] | None = None,
    max_candidates: int = 8,
) -> dict[str, Any]:
    """Ask COMMONS to choose the best fit from a safe live candidate shortlist.

    This is fit selection, not permission to execute the selected capability.
    """
    payload = {
        "need": need,
        "requirement": {
            "capability_type": capability_type,
            "tags": tags or [],
            "language": language,
            "location": location,
            "max_price_eur": max_price_eur,
            "required_authority": required_authority,
            "require_verified_provider": require_verified_provider,
            "allowed_provider_kinds": allowed_provider_kinds or [],
            "preferred_provider_kinds": preferred_provider_kinds or [],
        },
        "context": {
            "caller": "COMMONS MCP",
            "selection_rule": "best fit within deterministic constraints",
        },
        "max_candidates": max_candidates,
    }
    return _post("/network/select", payload)


@mcp.resource("commons://principles")
def principles() -> str:
    """Return the core operating principles for agent callers."""
    return (
        "COMMONS principles:\n"
        "- Anything can ask. Anything can help.\n"
        "- Declaring a need or capability never grants authority.\n"
        "- Confidence is not authority.\n"
        "- Humans, agents and businesses are selected by fit, not cheapest-worker logic.\n"
        "- Consequential execution requires the applicable approval and proof gates.\n"
        "- Reality and verified outcomes outrank model opinion."
    )
