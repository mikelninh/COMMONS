import shutil
import subprocess
from pathlib import Path


def read_public():
    return (
        Path("public/index.html").read_text(encoding="utf-8"),
        Path("public/styles.css").read_text(encoding="utf-8"),
        Path("public/app.js").read_text(encoding="utf-8"),
    )


def test_living_atlas_identity_contract() -> None:
    page, styles, app = read_public()

    assert "WORLD PULSE · LIVING ATLAS" in page
    assert "Earth is <em>not quiet.</em>" in page
    assert "What changes." in page
    assert "What humans do next." in page

    assert "Pulse" in page
    assert "Thread" in page
    assert "Bloom" in page
    assert "timeScrubber" in page

    assert "Iowan Old Style" in styles
    assert ".scene-stage.right-whisper" in styles
    assert ".scene-stage.center-monument" in styles
    assert ".scene-stage.final-center" in styles


def test_stock_globe_texture_is_removed() -> None:
    _, _, app = read_public()

    assert "earth-night.jpg" not in app
    assert "night-sky.png" not in app
    assert "WORLD_ATLAS" in app
    assert "countries-110m.json" in app
    assert "polygonsData" in app
    assert "showGraticules(true)" in app


def test_pulse_thread_bloom_are_real_globe_states() -> None:
    _, _, app = read_public()

    assert "THREADS" in app
    assert "BLOOM" in app
    assert "ringsData" in app
    assert "arcsData" in app
    assert 'kind:"bloom"' in app
    assert "setMilestone" in app
    assert "updateAtlasLayers" in app


def test_nepal_story_is_spatial_and_temporal() -> None:
    _, _, app = read_public()

    assert 'id: "nepal-flash-floods-2026"' in app
    assert 'composition: "left-monument"' in app
    assert 'composition: "right-whisper"' in app
    assert 'composition: "center-monument"' in app
    assert 'composition: "low-left"' in app
    assert 'composition: "final-center"' in app

    assert 'id: "signal"' in app
    assert 'id: "impact"' in app
    assert 'id: "verify"' in app
    assert 'id: "response"' in app
    assert 'id: "outcome"' in app
    assert 'id: "capacity"' in app
    assert 'id: "meaning"' in app
    assert 'id: "you"' in app

    assert "TIME_SCENES" in app
    assert "scrubTime" in app
    assert "globeOffset" in app


def test_truth_contract_survives_the_art_direction() -> None:
    _, _, app = read_public()

    assert "not presented as a final affected-population count" in app
    assert "not proof that any one contribution caused the outcome" in app
    assert "not a tracked shipment route" in app

    assert "We do not claim every affected person has been reached." in app
    assert "We do not show a funding percentage without a current authoritative source." in app
    assert "We do not imply that a particular donation caused the displayed outcomes." in app
    assert "The loop remains open." in app

    assert "IFRC Emergency Appeal" in app
    assert "IFRC response update" in app
    assert "Nepal Red Cross Society" in app


def test_live_world_sources_remain_explicit_about_freshness() -> None:
    _, _, app = read_public()

    assert '"USGS": {' in app
    assert 'freshness: "LIVE"' in app
    assert '"NASA EONET": {' in app
    assert 'freshness: "NEAR-REAL-TIME"' in app
    assert '"GDACS": {' in app

    assert "Magnitude is not a measure of human impact." in app
    assert "not a complete census" in app
    assert "An alert is not itself a casualty or need estimate." in app


def test_share_artifact_uses_living_atlas_grammar() -> None:
    page, _, app = read_public()

    assert "shareCanvas" in page
    assert "drawShareCard" in app
    assert "shareCardImage" in app
    assert "shareAction" in app
    assert "world-pulse-living-atlas-nepal.png" in app
    assert "PULSE" in app
    assert "THREAD" in app
    assert "BLOOM" in app


def test_accessibility_and_reduced_motion_remain_present() -> None:
    page, styles, app = read_public()

    assert "prefers-reduced-motion" in styles
    assert "aria-label" in page
    assert "Escape" in app
    assert "ArrowRight" in app
    assert "ArrowLeft" in app


def test_static_javascript_parses_with_node() -> None:
    node = shutil.which("node")
    if node is None:
        return

    result = subprocess.run(
        [node, "--check", "public/app.js"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_pages_and_zero_backend_release_config() -> None:
    config = Path("netlify.toml").read_text(encoding="utf-8")
    pages = Path(".github/workflows/pages.yml").read_text(encoding="utf-8")

    assert 'publish = "public"' in config
    assert 'from = "/world"' in config
    assert "path: public" in pages
    assert "actions/deploy-pages@v4" in pages
