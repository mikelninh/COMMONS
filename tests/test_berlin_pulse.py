from pathlib import Path
import shutil
import subprocess


def test_berlin_pulse_is_first_class_and_source_honest() -> None:
    page = Path("public/berlin.html").read_text(encoding="utf-8")
    pulse = Path("public/berlin-pulse.js").read_text(encoding="utf-8")
    css = Path("public/berlin-pulse.css").read_text(encoding="utf-8")

    assert "berlin-pulse.css" in page
    assert "berlin-pulse.js" in page
    assert "BERLIN PULSE" in pulse
    assert "WHAT CHANGED?" in pulse
    assert "FORECAST TEST" in pulse
    assert "WHY HERE? · V2" in pulse
    assert "HYPOTHESIS LAB" in pulse
    assert "persistence" in pulse
    assert "no forecast claim" in pulse
    assert "CAMS via Open-Meteo · modeled" in pulse
    assert "presence ≠ burden level" in pulse
    assert ".pulse-panel" in css
    assert ".pulse-hypothesis-grid" in css


def test_berlin_live_failures_fall_back_to_the_tape_without_faking_live_data() -> None:
    js = Path("public/berlin.js").read_text(encoding="utf-8")
    css = Path("public/berlin.css").read_text(encoding="utf-8")

    assert "renderTapeFallback" in js
    assert "LAST RECORDED" in js
    assert "not live." in js
    assert "friendlyFailure" in js
    assert "Try live again" in js
    assert "Live failed, so this panel is showing a clearly dated recording instead." in js
    assert ".insight.degraded" in css
    assert ".inline-retry" in css


def test_berlin_mobile_layout_keeps_navigation_and_evidence_readable() -> None:
    css = Path("public/berlin.css").read_text(encoding="utf-8")
    pulse_css = Path("public/berlin-pulse.css").read_text(encoding="utf-8")

    assert "@media(max-width:800px)" in css
    assert "top:132px" in css
    assert "bottom:116px" in css
    assert "overflow-x:auto" in css
    assert "@media(max-width:520px)" in pulse_css
    assert "max-height:calc(100vh - 142px)" in pulse_css


def test_berlin_pulse_tape_records_changes_hypotheses_and_scores_forecasts() -> None:
    collector = Path("scripts/collect_berlin_pulse.py").read_text(encoding="utf-8")
    workflow = Path(".github/workflows/berlin-pulse.yml").read_text(encoding="utf-8")

    assert "robust_anomaly" in collector
    assert "build_changes" in collector
    assert "build_hypotheses" in collector
    assert "ZoneInfo" in collector
    assert "rain-air" in collector
    assert "rain-river" in collector
    assert "transit-rhythm" in collector
    assert "4 are required" in collector
    assert "resolve_predictions" in collector
    assert "issue_prediction" in collector
    assert "candidate_abs_error" in collector
    assert "baseline_abs_error" in collector
    assert "collection missed the 90-minute scoring window" in collector
    assert "v6.vbb.transport.rest/radar" in collector
    assert "wasserportal.berlin.de/station.php" in collector
    assert "air-quality-api.open-meteo.com/v1/air-quality" in collector
    assert "cron: '17 */3 * * *'" in workflow
    assert "contents: write" in workflow
    assert "python scripts/collect_berlin_pulse.py" in workflow


def test_why_here_v2_uses_official_structural_context_without_inventing_a_score() -> None:
    pulse = Path("public/berlin-pulse.js").read_text(encoding="utf-8")

    assert "wfsAround" in pulse
    for key in ("trees", "green", "heat", "justice"):
        assert f"wfsAround('{key}'" in pulse
    assert "official mapped trees nearby" in pulse
    assert "official green-space features" in pulse
    assert "official pressure context" in pulse
    assert "Feature presence is context, not a severity score." in pulse


def test_berlin_pulse_javascript_and_python_syntax() -> None:
    node = shutil.which("node")
    if node is not None:
        subprocess.run([node, "--check", "public/berlin-pulse.js"], check=True)
        subprocess.run([node, "--check", "public/berlin.js"], check=True)

    python = shutil.which("python") or shutil.which("python3")
    if python is not None:
        subprocess.run([python, "-m", "py_compile", "scripts/collect_berlin_pulse.py"], check=True)
        subprocess.run([python, "-m", "py_compile", "tests/test_berlin_pulse.py"], check=True)
