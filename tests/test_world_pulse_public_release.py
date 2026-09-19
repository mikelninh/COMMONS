from pathlib import Path


def test_world_pulse_public_release_contract() -> None:
    page = Path("public/index.html").read_text(encoding="utf-8")

    assert "COMMONS</b> / WORLD PULSE" in page
    assert "Most of Earth is quiet." in page
    assert "LIVE + NEAR-REAL-TIME PUBLIC DATA" in page
    assert '"USGS":{freshness:"LIVE"' in page
    assert '"NASA EONET":{freshness:"NEAR-REAL-TIME"' in page
    assert '"GDACS":{freshness:"NEAR-REAL-TIME"' in page
    assert "First observation is a baseline, not a fake burst" in page
    assert "Correlation does not become confirmation." in page
    assert "globe.gl@2.46.2" in page
    assert "three-globe@2.45.2" in page
    assert "prefers-reduced-motion" in page
    assert "PAID AI <b id=\"paidAI\">OFF" in page


def test_netlify_release_is_zero_backend() -> None:
    config = Path("netlify.toml").read_text(encoding="utf-8")
    assert 'publish = "public"' in config
    assert 'from = "/world"' in config
