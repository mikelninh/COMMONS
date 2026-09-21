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
    assert "FORECAST TEST" in pulse
    assert "WHY HERE?" in pulse
    assert "persistence" in pulse
    assert "no forecast claim" in pulse
    assert "CAMS via Open-Meteo · modeled" in pulse
    assert "official structural heat and environmental-justice evidence" in pulse
    assert ".pulse-panel" in css


def test_berlin_pulse_tape_records_and_scores_forecasts() -> None:
    collector = Path("scripts/collect_berlin_pulse.py").read_text(encoding="utf-8")
    workflow = Path(".github/workflows/berlin-pulse.yml").read_text(encoding="utf-8")

    assert "robust_anomaly" in collector
    assert "resolve_predictions" in collector
    assert "issue_prediction" in collector
    assert "candidate_abs_error" in collector
    assert "baseline_abs_error" in collector\n    assert "collection missed the 90-minute scoring window" in collector
    assert "v6.vbb.transport.rest/radar" in collector
    assert "wasserportal.berlin.de/station.php" in collector
    assert "air-quality-api.open-meteo.com/v1/air-quality" in collector
    assert "cron: '17 */3 * * *'" in workflow
    assert "contents: write" in workflow
    assert "python scripts/collect_berlin_pulse.py" in workflow


def test_berlin_pulse_javascript_syntax() -> None:
    node = shutil.which("node")
    if node is None:
        return
    subprocess.run([node, "--check", "public/berlin-pulse.js"], check=True)
