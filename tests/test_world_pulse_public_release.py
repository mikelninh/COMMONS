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
    assert 'id: "descent"' in app
    assert 'id: "silence"' in app
    assert 'id: "memory"' in app
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


def test_css_is_parse_safe_and_hidden_layers_are_contained() -> None:
    _, styles, _ = read_public()

    assert_css_braces_balanced(styles)
    assert ".current-arrow{font-size:17px;color:#626761;transition:.3s var(--ease)}" in styles
    assert "%3C/filter id='x'/%3E" not in styles

    # Critical visibility rules live near the top of the stylesheet so a later
    # decorative typo cannot expose raw story/drawer/explorer markup.
    assert ".story:not(.active)" in styles
    assert ".evidence:not(.open)" in styles
    assert ".look:not(.open)" in styles
    assert ".share:not(.open)" in styles
    assert "visibility:hidden" in styles


def test_auxiliary_ui_modes_are_mutually_exclusive() -> None:
    _, _, app = read_public()

    assert "function closeAuxiliaryLayers" in app
    assert 'closeAuxiliaryLayers("look")' in app
    assert 'closeAuxiliaryLayers("evidence")' in app
    assert 'closeAuxiliaryLayers("share")' in app


def test_story_mode_owns_the_viewport() -> None:
    _, styles, app = read_public()

    assert "body.story-mode .topbar" in styles
    assert "body.story-mode .legend" in styles
    assert 'document.body.classList.add("story-mode")' in app
    assert 'document.body.classList.remove("story-mode")' in app


def test_scroll_cinema_surface_and_progress_contract() -> None:
    page, styles, app = read_public()

    assert "scrollNarrative" in page
    assert "scrollFilm" in page
    assert "timeFill" in page
    assert 'id="timeScrubber" type="range" min="0" max="1"' in page

    assert "SCROLL CINEMA" in styles
    assert "html.story-mode" in styles
    assert "body.story-mode .scroll-film" in styles
    assert ".scroll-scene.is-interactive .scene" in styles
    assert ".time-fill" in styles

    assert "function syncScrollCinema" in app
    assert "function requestScrollCinema" in app
    assert "function storyProgress" in app
    assert "function jumpToScene" in app
    assert "function autoScrollTick" in app
    assert 'window.addEventListener("scroll",requestScrollCinema' in app


def test_scroll_cinema_interpolates_camera_and_semantic_layers() -> None:
    _, _, app = read_public()

    assert "const position=progress*maxIndex" in app
    assert "const cam={" in app
    assert "lat:lerp(a.camera.lat,b.camera.lat,t)" in app
    assert "lng:lerp(a.camera.lng,b.camera.lng,t)" in app
    assert "altitude:lerp(a.camera.altitude,b.camera.altitude,t)" in app
    assert "world.pointOfView(cam,0)" in app
    assert "world.globeOffset([" in app

    assert "const thread=smoothstep(2.3,3.35,position)" in app
    assert "const bloom=smoothstep(4.85,6.15,position)" in app
    assert "const memory=smoothstep(7.55,8.35,position)" in app
    assert "updateSemanticVisuals(thread,bloom,memory)" in app
    assert "threadStrength" in app
    assert "bloomStrength" in app


def test_scroll_story_crossfades_and_respects_reduced_motion() -> None:
    _, styles, app = read_public()

    assert "filter:blur(5px)" in styles
    assert "will-change:opacity,transform,filter" in styles
    assert "@media(prefers-reduced-motion:reduce)" in styles
    assert "scroll-behavior:auto" in styles

    assert "const distance=Math.abs(delta)" in app
    assert "const opacity=clamp01(1-smoothstep(.12,1.02,distance))" in app
    assert "el.style.opacity=opacity.toFixed(3)" in app
    assert 'el.setAttribute("aria-hidden",interactive?"false":"true")' in app


def test_scroll_story_manual_input_takes_control_from_auto_play() -> None:
    _, _, app = read_public()

    assert "function stopAutoScroll" in app
    assert 'window.addEventListener("wheel",()=>{if(storyPlaying)stopAutoScroll()}' in app
    assert 'window.addEventListener("touchstart",()=>{if(storyPlaying)stopAutoScroll()}' in app
    assert 'storyPlaying?"Pause":"Auto"' in app



def test_orbit_to_geographic_descent_is_real_ui_state() -> None:
    page, styles, app = read_public()

    assert 'id="descentLayer"' in page
    assert 'id="terrainSvg"' in page
    assert 'id="nepalCountry"' in page
    assert 'id="nepalClipPath"' in page
    assert 'pathLength="1"' in page
    assert "country outline is geographic" in page
    assert "relief field is stylized, not elevation data" in page

    assert ".descent-layer" in styles
    assert ".terrain-world" in styles
    assert ".terrain-country" in styles
    assert ".terrain-contours path" in styles
    assert ".terrain-thread" in styles
    assert ".terrain-bloom" in styles

    assert "function buildTerrainMap" in app
    assert "flattenCoordinateRings" in app
    assert 'String(d?.id)==="524"' in app
    assert "buildTerrainMap();" in app
    assert "terrainMix" in app
    assert '"--globe-opacity"' in app
    assert '"--terrain-opacity"' in app
    assert '"--terrain-tilt"' in app


def test_descent_is_explicitly_not_fake_topography_or_routes() -> None:
    _, _, app = read_public()

    assert "relief treatment is intentionally stylized and is not elevation data" in app
    assert "not elevation, flood extent, damage mapping, or a factual topographic model" in app
    assert "response thread is also semantic rather than a literal route" in app
    assert "not a tracked shipment route" in app


def test_scroll_depth_and_silence_moment_are_choreographed() -> None:
    _, styles, app = read_public()

    assert "--scene-depth" in styles
    assert ".scroll-scene.silence-scene" in styles
    assert "--silence-label-opacity" in styles
    assert "--cinema-chrome-opacity" in styles

    assert 'composition: "silence-scene"' in app
    assert 'id: "silence"' in app
    assert "const silenceDistance=Math.abs(position-5)" in app
    assert '"--cinema-chrome-opacity"' in app
    assert '"--scene-depth"' in app


def test_memory_of_earth_is_one_truthful_mark_not_a_score() -> None:
    page, styles, app = read_public()

    assert 'id="memoryMark"' in page
    assert "MEMORY OF EARTH" in page
    assert ".memory-mark" in styles
    assert "memoryPoint" in app
    assert 'kind:"memory"' in app
    assert "memoryStrength" in app
    assert "The memory mark represents only this documented Nepal response story." in app
    assert "not a score, rank, completion badge" in app


def test_optional_sound_is_user_initiated_and_procedural() -> None:
    page, _, app = read_public()

    assert 'id="soundBtn"' in page
    assert 'aria-pressed="false"' in page
    assert "function createAudioNodeGraph" in app
    assert "function toggleSound" in app
    assert "function updateSoundscape" in app
    assert "function soundAccent" in app
    assert "window.AudioContext||window.webkitAudioContext" in app
    assert '$("soundBtn").onclick=toggleSound' in app
    assert "soundEnabled=false" in app or "let soundEnabled = false" in app


def test_descent_returns_cleanly_to_the_planet() -> None:
    _, _, app = read_public()

    assert "function resetCinematicVisuals" in app
    assert '"--terrain-opacity"' in app
    assert '"--memory-opacity"' in app
    assert "resetCinematicVisuals();" in app
    assert 'terrain: 0,' in app
