from pathlib import Path


def test_cinematic_world_pulse_public_contract() -> None:
    page = Path("public/world/index.html").read_text(encoding="utf-8")

    assert "COMMONS</b> / WORLD PULSE" in page
    assert "Most of Earth is quiet." in page
    assert "Globe()" in page
    assert "WORLD SPOTLIGHT" in page
    assert "TRACE WHAT WAKES" in page
    assert "COMMONS ACTION GRAPH" in page
    assert "PAUSE STORY" in page
    assert "EXPLORE" in page
    assert "SHARE" in page
    assert "possible multi-source overlap" in page
    assert "Reality > model opinion." in page
    assert "PAID AI <b id=\"paidAI\">OFF" in page


def test_cinematic_world_pulse_keeps_transparent_live_rules() -> None:
    page = Path("public/world/index.html").read_text(encoding="utf-8")

    assert "USGS magnitude ≥ 6.0" in page
    assert "USGS magnitude ≥ 5.0" in page
    assert "GDACS red alert" in page
    assert "GDACS orange alert" in page
    assert "First observation is a baseline, not a fake burst" in page
    assert "Correlation does not become confirmation." in page
