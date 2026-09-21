from pathlib import Path
import shutil
import subprocess


def test_berlin_v2_lab_exposes_all_concepts() -> None:
    page = Path("public/berlin-v2-lab.html").read_text(encoding="utf-8")
    css = Path("public/berlin-v2-lab.css").read_text(encoding="utf-8")
    explore = Path("public/berlin-v2-lab-explore.js").read_text(encoding="utf-8")
    stories = Path("public/berlin-v2-lab-stories.js").read_text(encoding="utf-8")

    for label in ("Layouts", "Discover", "Why Here", "Compare", "Time", "Lab", "Share"):
        assert label in page
    for layout in ("editorial", "cinematic", "observatory"):
        assert f'data-layout="{layout}"' in page
        assert f'data-try-layout="{layout}"' in page
    assert page.count("data-share=") == 5
    assert "Show me something" in page
    assert "Choose a place on the map" in page
    assert "Pick A" in page and "Pick B" in page
    assert "Scrub the tape." in page
    assert "Questions that have to survive reality." in page
    assert "Share the insight, not the dashboard." in page
    assert ".changed-rail" in css
    assert "pointContext" in explore
    assert "Context, not a ranking." in explore
    assert "renderShare" in stories


def test_berlin_v2_lab_supports_feedback_before_selection() -> None:
    page = Path("public/berlin-v2-lab.html").read_text(encoding="utf-8")
    core = Path("public/berlin-v2-lab-core.js").read_text(encoding="utf-8")

    assert "My picks" in page
    assert "Copy feedback summary" in page
    assert "commons-v2-ratings" in core
    assert "commons-v2-layout" in core
    assert "Love" in core
    assert "Maybe" in core
    assert "Nope" in core


def test_berlin_v2_lab_javascript_syntax() -> None:
    node = shutil.which("node")
    if node is None:
        return
    for path in (
        "public/berlin-v2-lab-core.js",
        "public/berlin-v2-lab-explore.js",
        "public/berlin-v2-lab-stories.js",
        "scripts/browser-v2-lab-smoke.mjs",
    ):
        subprocess.run([node, "--check", path], check=True)
