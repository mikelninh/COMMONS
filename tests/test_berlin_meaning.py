from pathlib import Path
import shutil
import subprocess


def test_meaning_engine_has_twelve_source_context_pack() -> None:
    sources = Path("public/berlin-meaning-sources.js").read_text(encoding="utf-8")
    expected = (
        "weather", "air", "transit", "trees", "green", "buildingAge",
        "wall", "heat", "justice", "hospitals", "sports", "bathing",
    )
    for key in expected:
        assert f"{key}:" in sources
    for endpoint in (
        "baumbestand", "gruenanlagen", "ua_gebaeudealter", "berlinermauer",
        "ua_klimaanalyse_2022", "ua_umweltgerechtigkeit2023",
        "krankenhaeuser", "sportstandorte", "badegewaesser",
    ):
        assert endpoint in sources


def test_meaning_engine_ranks_meaning_instead_of_exposing_layer_toggles() -> None:
    page = Path("public/berlin-meaning.html").read_text(encoding="utf-8")
    engine = Path("public/berlin-meaning-engine.js").read_text(encoding="utf-8")

    assert "Tap Berlin." in page
    assert "See what matters here." in page
    assert "VISITING" in page
    assert "I LIVE HERE" in page
    assert "SURPRISE ME" in page
    assert "BEST OF" in page
    for lens in ("NOW", "LIFE", "HISTORY", "INFRA", "NATURE"):
        assert lens in page

    assert "E.score=" in engine
    assert "E.select=" in engine
    assert "lensCounts" in engine
    assert "surpriseNearby" in engine
    assert "runTest" in engine
    assert "Context" not in page or "layer toggle" not in page.lower()


def test_meaning_engine_keeps_evidence_classes_and_caveats_visible() -> None:
    sources = Path("public/berlin-meaning-sources.js").read_text(encoding="utf-8")
    engine = Path("public/berlin-meaning-engine.js").read_text(encoding="utf-8")

    for kind in ("modeled", "live", "structural", "historical"):
        assert f"kind:'{kind}'" in sources
    assert "not a current building survey" in sources
    assert "not today’s measured temperature" in sources
    assert "does not invent its own morality score" in sources
    assert "not a local measurement station" in engine
    assert "not the same as capacity" in engine
    assert "feature count is not canopy" in sources.lower()


def test_meaning_engine_has_human_rating_and_sampling_harness() -> None:
    page = Path("public/berlin-meaning.html").read_text(encoding="utf-8")
    engine = Path("public/berlin-meaning-engine.js").read_text(encoding="utf-8")
    core = Path("public/berlin-meaning-core.js").read_text(encoding="utf-8")

    assert "Run 12-place test" in page
    assert "Useful" in engine
    assert "Surprising" in engine
    assert "Skip" in engine
    assert "meaning-card-ratings" in core
    assert "2+ meaningful candidates" in engine
    assert "Average candidate count" in engine
    assert "2+ lenses represented" in engine


def test_meaning_engine_browser_javascript_syntax() -> None:
    node = shutil.which("node")
    if node is None:
        return
    for path in (
        "public/berlin-meaning-sources.js",
        "public/berlin-meaning-core.js",
        "public/berlin-meaning-engine.js",
        "scripts/browser-meaning-smoke.mjs",
    ):
        subprocess.run([node, "--check", path], check=True)


def test_meaning_engine_design_a_keeps_primary_view_readable() -> None:
    page = Path("public/berlin-meaning.html").read_text(encoding="utf-8")
    css = Path("public/berlin-meaning.css").read_text(encoding="utf-8")
    engine = Path("public/berlin-meaning-engine.js").read_text(encoding="utf-8")

    assert "brand-mark" in page
    assert "meaningMore" in page
    assert "data-jump-lens" in page
    assert "meaning-card-visual" in engine
    assert "why this matters" in engine
    assert "Math.min(4,M.current.length)" in engine
    assert ".meaning-card-visual" in css
    assert ".why-button" in css
    assert "why this?" not in engine
