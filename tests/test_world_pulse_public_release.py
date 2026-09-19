import re
import shutil
import subprocess
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
    assert 'PAID AI <b id="paidAI">OFF' in page


def test_netlify_release_is_zero_backend() -> None:
    config = Path("netlify.toml").read_text(encoding="utf-8")
    assert 'publish = "public"' in config
    assert 'from = "/world"' in config


def test_world_pulse_sharing_preserves_provenance() -> None:
    page = Path("public/index.html").read_text(encoding="utf-8")

    assert "function sharePayload()" in page
    assert "Primary source:" in page
    assert "Surfaced because:" in page
    assert "provenance travels with the signal" in page
    assert "PROVENANCE COPIED" in page


def test_action_card_closes_the_first_real_world_loop() -> None:
    page = Path("public/index.html").read_text(encoding="utf-8")

    assert "COMMONS / ACTION 001" in page
    assert "Nepal: Flash Floods 2026" in page
    assert "ACT · 1 VERIFIED LOOP" in page
    assert "~93,000 people may have been affected" in page
    assert "CHF 25M Emergency Appeal" in page
    assert "safe drinking water restored for around" in page
    assert "2,000 people" in page
    assert "100 patients/day" in page
    assert "LOOP STATUS · OPEN" in page
    assert "SUPPORT VIA IFRC" in page
    assert "VERIFY THE EVIDENCE" in page
    assert "SEE LATEST OUTCOME" in page
    assert 'id:"nepal-flash-floods-2026"' in page
    assert "function actionSharePayload()" in page
    assert "Watch the loop:" in page


def test_inline_javascript_parses_with_node(tmp_path: Path) -> None:
    node = shutil.which("node")
    if node is None:
        return

    page = Path("public/index.html").read_text(encoding="utf-8")
    inline_scripts = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", page, flags=re.DOTALL)
    script = "\n".join(part for part in inline_scripts if part.strip())
    target = tmp_path / "world-pulse.js"
    target.write_text(script, encoding="utf-8")

    result = subprocess.run(
        [node, "--check", str(target)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
