import shutil
import subprocess
from pathlib import Path


def assert_css_braces_balanced(css: str) -> None:
    depth = 0
    quote = None
    escaped = False
    in_comment = False
    i = 0
    while i < len(css):
        ch = css[i]
        nxt = css[i + 1] if i + 1 < len(css) else ""

        if in_comment:
            if ch == "*" and nxt == "/":
                in_comment = False
                i += 2
                continue
            i += 1
            continue

        if quote:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
            i += 1
            continue

        if ch == "/" and nxt == "*":
            in_comment = True
            i += 2
            continue
        if ch in ("'", '"'):
            quote = ch
            i += 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            assert depth >= 0, "CSS contains an unmatched closing brace"
        i += 1

    assert quote is None, "CSS contains an unclosed quoted string"
    assert not in_comment, "CSS contains an unclosed comment"
    assert depth == 0, f"CSS contains {depth} unmatched opening brace(s)"


def read_public():
    return (
        Path("public/index.html").read_text(encoding="utf-8"),
        Path("public/styles.css").read_text(encoding="utf-8"),
        Path("public/app.js").read_text(encoding="utf-8"),
        Path("public/stories.js").read_text(encoding="utf-8"),
    )


def test_living_atlas_multi_story_identity() -> None:
    page, styles, app, stories = read_public()

    assert "WORLD PULSE · LIVING ATLAS" in page
    assert "STORIES OF RESPONSE · VOL. 01" in page
    assert "storyLibrary" in page
    assert "storyCards" in page
    assert "Stories" in page

    assert "WORLD_PULSE_STORIES" in stories
    assert "const STORIES" in app
    assert "activeStory" in app
    assert "function selectStory" in app
    assert "function enterStory" in app

    assert "STORIES OF RESPONSE — MULTI-STORY LIBRARY" in styles
    assert ".story-card" in styles


def test_launch_collection_contains_three_distinct_story_grammars() -> None:
    _, _, _, stories = read_public()

    assert 'id: "nepal-flash-floods-2026"' in stories
    assert 'title: "Water Returns"' in stories
    assert 'grammar: ["Pulse", "Thread", "Bloom"]' in stories

    assert 'id: "bhutan-rabies-elimination-2026"' in stories
    assert 'title: "The Last Transmission"' in stories
    assert 'grammar: ["Threat", "Network", "Silence"]' in stories

    assert 'id: "drc-ebola-bundibugyo-2026"' in stories
    assert 'title: "Outrunning an Epidemic"' in stories
    assert 'grammar: ["Spread", "Response", "Open loop"]' in stories


def test_catalog_uses_story_specific_country_geometry() -> None:
    page, _, app, stories = read_public()

    assert 'id="terrainCountry"' in page
    assert 'id="terrainClipPath"' in page

    assert 'countryId: "524"' in stories
    assert 'countryId: "064"' in stories
    assert 'countryId: "180"' in stories

    assert 'padStart(3,"0")===activeStory.countryId' in app
    assert '$("terrainCountry").setAttribute("d",path)' in app
    assert '$("terrainClipPath").setAttribute("d",path)' in app
    assert "buildTerrainMap()" in app


def test_home_globe_contains_story_points() -> None:
    _, _, app, _ = read_public()

    assert "const storyPoints=STORIES.map" in app
    assert 'kind:"story"' in app
    assert "enterStory(d.storyId,0)" in app
    assert "points=[...signals.slice(0,150),...storyPoints]" in app
    assert "world.ringsData(storyMode?[actionPoint]:[...surfaced,...storyPoints])" in app


def test_story_router_supports_new_and_legacy_deep_links() -> None:
    _, _, app, _ = read_public()

    assert 'params.get("story")||params.get("action")' in app
    assert 'u.searchParams.set("story",activeStory.id)' in app
    assert 'u.searchParams.delete("action")' in app
    assert "storyById" in app


def test_nepal_truth_contract_survives_catalog_refactor() -> None:
    _, _, _, stories = read_public()

    assert "~93,000 is not presented as a final affected-population count." in stories
    assert "We do not imply that a particular donation caused the displayed outcomes." in stories
    assert "Safe drinking water" in stories
    assert "~2,000" in stories
    assert "100/day" in stories


def test_bhutan_is_an_elimination_story_not_a_disaster_clone() -> None:
    _, _, _, stories = read_public()

    assert "WHO validated Bhutan" in stories
    assert "zero human deaths from dog-mediated rabies since june 2023" in stories.lower()
    assert 'value: "0"' in stories
    assert 'label: "human deaths"' in stories
    assert "Elimination is maintenance" in stories
    assert "not a claim that rabies can never reappear" in stories
    assert "continued free access to post-exposure prophylaxis" in stories


def test_drc_remains_an_open_loop_without_fake_bloom() -> None:
    _, _, app, stories = read_public()

    assert 'title: "Outrunning an Epidemic"' in stories
    assert 'value: "7,475"' in stories
    assert 'value: "3,605"' in stories
    assert 'value: "1,798"' in stories
    assert "No false Bloom" in stories
    assert "epidemic is still growing" in stories
    assert "No green resolution Bloom is shown" in stories
    assert "bloom: []" in stories

    assert "const bloom=BLOOM.length?" in app
    assert '((BLOOM.length?bloom:0)*terrainOpacity)' in app


def test_story_specific_semantic_thresholds_drive_scroll() -> None:
    _, _, app, stories = read_public()

    assert "const semantic=activeStory.semantic" in app
    assert "semantic.threadStart" in app
    assert "semantic.bloomStart" in app
    assert "semantic.memoryStart" in app
    assert "activeStory.semantic.silenceIndex" in app
    assert "activeStory.semantic.milestones" in app

    assert stories.count("threadStart:") == 3
    assert stories.count("silenceIndex:") == 3


def test_final_scene_can_continue_directly_to_next_story() -> None:
    _, _, app, _ = read_public()

    assert "function nextStory" in app
    assert 'data-action="next"' in app
    assert "following.country" in app
    assert 'enterStory(following.id,0)' in app


def test_evidence_drawer_is_catalog_driven() -> None:
    _, _, app, stories = read_public()

    assert "activeStory.evidence.map" in app
    assert "activeStory.guardrails.map" in app
    assert "activeStory.terrain.disclosure" in app
    assert "activeStory.statusLabel" in app

    assert stories.count("evidence: [") == 3
    assert stories.count("guardrails: [") == 3


def test_share_studio_is_catalog_driven() -> None:
    page, _, app, _ = read_public()

    assert "shareCanvas" in page
    assert "activeStory.share.value" in app
    assert "activeStory.share.label" in app
    assert "activeStory.share.note" in app
    assert '"world-pulse-"+activeStory.slug+".png"' in app
    assert "activeStory.grammar.join" in app


def test_scroll_cinema_still_interpolates_camera_and_depth() -> None:
    _, styles, app, _ = read_public()

    assert "function syncScrollCinema" in app
    assert "const position=progress*maxIndex" in app
    assert "lat:lerp(a.camera.lat,b.camera.lat,t)" in app
    assert "lng:lerp(a.camera.lng,b.camera.lng,t)" in app
    assert "altitude:lerp(a.camera.altitude,b.camera.altitude,t)" in app
    assert "world.pointOfView(cam,0)" in app
    assert '"--scene-depth"' in app

    assert ".scroll-scene" in styles
    assert "will-change:opacity,transform,filter" in styles


def test_orbit_to_geographic_descent_remains_explicitly_stylized() -> None:
    page, styles, app, stories = read_public()

    assert 'id="descentLayer"' in page
    assert ".descent-layer" in styles
    assert ".terrain-contours path" in styles
    assert "flattenCoordinateRings" in app
    assert "buildTerrainMap" in app

    assert "stylized, not elevation data" in stories
    assert "stylized, not outbreak-intensity data" in stories
    assert "Internal contour lines are a cinematic depth treatment" in app
    assert "Response threads are semantic rather than literal routes." in app


def test_memory_of_earth_is_status_aware_not_a_score() -> None:
    page, styles, app, stories = read_public()

    assert 'id="memoryMark"' in page
    assert "MEMORY OF EARTH" in page
    assert ".memory-mark" in styles
    assert "activeStory.statusLabel" in app
    assert "not a score, rank, completion badge" in app

    assert "memory:" in stories
    assert 'memory: "#d2b06d"' in stories


def test_optional_sound_remains_user_initiated() -> None:
    page, _, app, _ = read_public()

    assert 'id="soundBtn"' in page
    assert 'aria-pressed="false"' in page
    assert "function createAudioNodeGraph" in app
    assert "function toggleSound" in app
    assert "function updateSoundscape" in app
    assert "window.AudioContext||window.webkitAudioContext" in app
    assert '$("soundBtn").onclick=toggleSound' in app


def test_live_world_sources_keep_freshness_and_limits_visible() -> None:
    _, _, app, _ = read_public()

    assert '"USGS": {' in app
    assert 'freshness: "LIVE"' in app
    assert '"NASA EONET": {' in app
    assert 'freshness: "NEAR-REAL-TIME"' in app
    assert '"GDACS": {' in app
    assert "Magnitude is not a measure of human impact." in app
    assert "not a complete census" in app
    assert "An alert is not itself a casualty or need estimate." in app


def test_hidden_application_layers_remain_contained() -> None:
    _, styles, app, _ = read_public()

    assert_css_braces_balanced(styles)
    assert ".story:not(.active)" in styles
    assert ".evidence:not(.open)" in styles
    assert ".look:not(.open)" in styles
    assert ".share:not(.open)" in styles
    assert "visibility:hidden" in styles

    assert "function closeAuxiliaryLayers" in app
    assert 'closeAuxiliaryLayers("look")' in app
    assert 'closeAuxiliaryLayers("evidence")' in app
    assert 'closeAuxiliaryLayers("share")' in app


def test_reduced_motion_and_keyboard_controls_remain() -> None:
    page, styles, app, _ = read_public()

    assert "prefers-reduced-motion" in styles
    assert "aria-label" in page
    assert "Escape" in app
    assert "ArrowRight" in app
    assert "ArrowLeft" in app


def test_static_javascript_files_parse_with_node() -> None:
    node = shutil.which("node")
    if node is None:
        return

    for path in ("public/stories.js", "public/app.js"):
        result = subprocess.run(
            [node, "--check", path],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"{path}: {result.stderr}"


def test_pages_and_zero_backend_release_config() -> None:
    config = Path("netlify.toml").read_text(encoding="utf-8")
    pages = Path(".github/workflows/pages.yml").read_text(encoding="utf-8")

    assert 'publish = "public"' in config
    assert 'from = "/world"' in config
    assert "path: public" in pages
    assert "actions/deploy-pages@v4" in pages
