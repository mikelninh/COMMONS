import shutil
import subprocess
from pathlib import Path


def test_world_pulse_v2_public_contract() -> None:
    page = Path("public/index.html").read_text(encoding="utf-8")
    styles = Path("public/styles.css").read_text(encoding="utf-8")
    app = Path("public/app.js").read_text(encoding="utf-8")

    assert "COMMONS / WORLD PULSE" in page
    assert "Earth, <em>with a pulse.</em>" in page
    assert "Watch Action 001" in page
    assert "Explore Earth" in page
    assert "Evidence / trust" in page
    assert "shareCanvas" in page

    assert "globe.gl@2.46.2" in page
    assert "earth-night.jpg" in app
    assert "night-sky.png" in app
    assert "showAtmosphere(true)" in app
    assert "prefers-reduced-motion" in styles
    assert "film-grain" in styles


def test_action_001_is_a_reusable_cinematic_story() -> None:
    app = Path("public/app.js").read_text(encoding="utf-8")

    assert 'id: "nepal-flash-floods-2026"' in app
    assert 'id: "signal"' in app
    assert 'id: "impact"' in app
    assert 'id: "verify"' in app
    assert 'id: "response"' in app
    assert 'id: "outcome"' in app
    assert 'id: "clinic"' in app
    assert 'id: "you"' in app

    assert "~93,000" in app
    assert "CHF 25M" in app
    assert "~2,000" in app
    assert "100/day" in app
    assert "The loop is still open." in app

    assert "startActionStory" in app
    assert "renderScene" in app
    assert "sceneMarkup" in app
    assert "progressTrack" in Path("public/index.html").read_text(encoding="utf-8")


def test_trust_layer_preserves_uncertainty_and_provenance() -> None:
    app = Path("public/app.js").read_text(encoding="utf-8")

    assert "not a final affected-population count" in app
    assert "We do not claim every affected person has been reached." in app
    assert "We do not show a funding percentage without a current authoritative source." in app
    assert "We do not imply that a specific user's donation caused the displayed outcomes." in app
    assert "Historical facts retain their original date." in app

    assert "Primary evidence · IFRC" in app
    assert "Outcome evidence · IFRC" in app
    assert "Responder identity" in app

    assert "Primary source:" in app
    assert "Surfaced because:" in app


def test_sharing_creates_story_and_visual_artifact() -> None:
    app = Path("public/app.js").read_text(encoding="utf-8")

    assert "drawShareCard" in app
    assert "shareCardImage" in app
    assert "shareAction" in app
    assert "world-pulse-nepal.png" in app
    assert "SIGNAL  →  RESPONSE  →  OUTCOME" in app
    assert 'u.searchParams.set("action",ACTION.id)' in app
    assert 'u.searchParams.set("scene","signal")' in app


def test_live_world_sources_remain_explicit_about_freshness() -> None:
    app = Path("public/app.js").read_text(encoding="utf-8")

    assert '"USGS": {' in app
    assert 'freshness: "LIVE"' in app
    assert '"NASA EONET": {' in app
    assert 'freshness: "NEAR-REAL-TIME"' in app
    assert '"GDACS": {' in app
    assert "Magnitude is not a measure of human impact." in app
    assert "not a complete census" in app
    assert "An alert is not itself a casualty or need estimate." in app


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
    assert 'path: public' in pages
    assert "actions/deploy-pages@v4" in pages
