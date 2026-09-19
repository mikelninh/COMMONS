import pytest

from commons.civic import CivicActionPlan, CivicProofStage, validate_civic_plan


def test_civic_plan_preserves_citizen_voice() -> None:
    plan = CivicActionPlan(
        need="I want to improve my neighborhood and need to know whether public funding exists.",
        jurisdiction="Berlin / Marzahn-Hellersdorf",
        channel_name="Gebietsfonds Helle Mitte",
        channel_type="public_funding",
        official_source="https://www.berlin.de/",
        responsible_body="Bezirksamt Marzahn-Hellersdorf",
        eligibility_summary="Local actors may apply for eligible local projects.",
        deadline="2026-10-25",
        next_steps=["Check geographic eligibility", "Describe the citizen's own project idea"],
    )
    assert validate_civic_plan(plan).political_recommendation is False


def test_civic_plan_rejects_political_recommendation() -> None:
    plan = CivicActionPlan(
        need="Help me participate.",
        jurisdiction="Berlin",
        channel_name="Example",
        channel_type="participation",
        official_source="https://www.berlin.de/",
        responsible_body="Example authority",
        eligibility_summary="Example",
        next_steps=["Participate"],
        political_recommendation=True,
    )
    with pytest.raises(ValueError):
        validate_civic_plan(plan)


def test_advanced_proof_requires_external_reference() -> None:
    plan = CivicActionPlan(
        need="Help me submit this civic request.",
        jurisdiction="Berlin",
        channel_name="Example",
        channel_type="petition",
        official_source="https://www.parlament-berlin.de/",
        responsible_body="Petitionsausschuss",
        eligibility_summary="Anyone may petition.",
        next_steps=["Citizen reviews the text", "Citizen submits it"],
        proof_stage=CivicProofStage.ACTION_CONFIRMED,
    )
    with pytest.raises(ValueError):
        validate_civic_plan(plan)
