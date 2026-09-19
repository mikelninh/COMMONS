from fastapi.testclient import TestClient

from commons.app import app
from commons.civic_router import CivicNeedInput, route_civic_need

client = TestClient(app)


def test_helle_mitte_project_finds_live_fund_and_participation() -> None:
    result = route_civic_need(
        CivicNeedInput(
            text="I have a project idea in Helle Mitte to improve the neighborhood.",
            location="Berlin",
        )
    )
    ids = {channel.channel_id for channel in result.channels}
    assert "berlin-helle-mitte-fund-2026" in ids
    assert "berlin-meinberlin" in ids
    fund = next(c for c in result.channels if c.channel_id == "berlin-helle-mitte-fund-2026")
    assert fund.deadline == "2026-10-25"
    assert result.political_recommendation is False
    assert result.citizen_voice_required is True


def test_public_space_problem_routes_to_ordnungsamt() -> None:
    result = route_civic_need(
        CivicNeedInput(
            text="There is rubbish and road damage in public space near my street.",
            location="Berlin",
        )
    )
    ids = {channel.channel_id for channel in result.channels}
    assert "berlin-ordnungsamt-online" in ids
    channel = next(c for c in result.channels if c.channel_id == "berlin-ordnungsamt-online")
    assert any("immediate" in caveat for caveat in channel.caveats)


def test_formal_authority_decision_keeps_legal_remedy_warning() -> None:
    result = route_civic_need(
        CivicNeedInput(
            text="A Berlin authority sent me a Bescheid and I do not understand the decision.",
            location="Berlin",
        )
    )
    ids = {channel.channel_id for channel in result.channels}
    assert "berlin-petitionsausschuss" in ids
    assert any("Rechtsbehelfsbelehrung" in warning for warning in result.missing_information)
    petition = next(c for c in result.channels if c.channel_id == "berlin-petitionsausschuss")
    assert any("not a substitute" in caveat for caveat in petition.caveats)


def test_unknown_need_falls_back_without_inventing_authority() -> None:
    result = route_civic_need(
        CivicNeedInput(text="I want to do something useful but I am not sure what.", location="Berlin")
    )
    assert [c.channel_id for c in result.channels] == ["berlin-meinberlin"]
    assert result.missing_information


def test_civic_page_and_api_are_live() -> None:
    page = client.get("/civic")
    assert page.status_code == 200
    assert "What would you like to change, understand, or make happen?" in page.text

    response = client.post(
        "/civic/action",
        json={"text": "There is rubbish in public space and I want to report it.", "location": "Berlin"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["political_recommendation"] is False
    assert any(c["channel_id"] == "berlin-ordnungsamt-online" for c in body["channels"])


def test_civic_result_explains_how_it_reached_the_route() -> None:
    result = route_civic_need(
        CivicNeedInput(
            text="There is rubbish and road damage in public space near me.",
            location="Berlin",
        )
    )
    assert result.primary_channel_id == "berlin-ordnungsamt-online"
    assert result.checked_channels == 4
    assert "public-space problem language" in result.matched_signals
    assert [step.step for step in result.routing_trace] == [1, 2, 3, 4, 5]
    assert result.routing_trace[-1].label == "Choose the clearest next path"


def test_civic_ui_explains_that_routing_is_not_submission() -> None:
    page = client.get("/civic")
    assert page.status_code == 200
    assert "What happens when you click?" in page.text
    assert "Find a path ≠ send to government." in page.text
    assert "What COMMONS just did" in page.text
    assert "Proof ladder" in page.text
