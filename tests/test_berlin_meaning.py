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

    assert "Berlin has layers." in page
    assert "One city. Real sources." in page
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
        "public/berlin-continuous.js",
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
    assert "fullList.slice(0,4)" in engine
    assert ".meaning-card-visual" in css
    assert ".why-button" in css
    assert "why this?" not in engine


def test_city_xray_is_the_primary_post_selection_instrument() -> None:
    page = Path("public/berlin-meaning.html").read_text(encoding="utf-8")
    engine = Path("public/berlin-meaning-engine.js").read_text(encoding="utf-8")
    xray = Path("public/berlin-xray.js").read_text(encoding="utf-8")
    css = Path("public/berlin-meaning.css").read_text(encoding="utf-8")

    assert 'id="xrayStage"' in page
    assert 'id="xrayTimeSlider"' in page
    for mode in ("live", "people", "nature", "infra", "history"):
        assert f'data-xray="{mode}"' in page

    assert "window.BerlinXray?.activate(point)" in engine
    assert "renderLive" in xray
    assert "renderPeople" in xray
    assert "renderNature" in xray
    assert "renderInfra" in xray
    assert "renderHistory" in xray
    assert "−12H" in xray
    assert "+12H" in xray
    assert "NO MODEL" in xray
    assert "No synthetic future history" in xray
    assert ".xray-rail" in css
    assert ".xray-time" in css


def test_city_xray_changes_the_map_not_only_the_copy() -> None:
    xray = Path("public/berlin-xray.js").read_text(encoding="utf-8")

    for source_id in ("xray-heat", "xray-area", "xray-line", "xray-point", "xray-transit"):
        assert source_id in xray
    for layer_id in ("xray-heat-layer", "xray-area-layer", "xray-line-layer", "xray-point-layer", "xray-transit-layer"):
        assert layer_id in xray
    assert "setPaintProperty" in xray
    assert "setLayoutProperty" in xray
    assert "setData" in xray


def test_one_continuous_berlin_unifies_place_lens_time_and_compare() -> None:
    page = Path("public/berlin-meaning.html").read_text(encoding="utf-8")
    continuous = Path("public/berlin-continuous.js").read_text(encoding="utf-8")
    css = Path("public/berlin-meaning.css").read_text(encoding="utf-8")

    assert 'id="continuousSheet"' in page
    assert 'id="continuousInsightTitle"' in page
    assert 'id="continuousCompare"' in page
    assert 'id="continuousShare"' in page
    assert 'id="continuousRepick"' in page
    assert "compat-controls" in page
    assert "tool-dock" not in page

    for key in ("place:null", "lens:'live'", "time:1", "comparison:null", "selectedInsight:null"):
        assert key in continuous
    assert "cameraBefore" in Path("scripts/browser-meaning-smoke.mjs").read_text(encoding="utf-8")
    assert "startCompare" in continuous
    assert "chooseCompare" in continuous
    assert "data-sheet-state" in css
    assert ".continuous-sheet" in css


def test_cinematic_atlas_skin_is_loaded_after_base_meaning_styles() -> None:
    page = Path("public/berlin-meaning.html").read_text(encoding="utf-8")
    cinematic = Path("public/berlin-cinematic.css").read_text(encoding="utf-8")

    assert page.index("berlin-meaning.css") < page.index("berlin-cinematic.css")
    assert "BERLIN · NOW · MEMORY" in page
    assert ".continuous-sheet" in cinematic
    assert "--atlas-serif" in cinematic
    assert "@media(max-width:900px)" in cinematic
