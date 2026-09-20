from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from commons.world_model_eval import score_loop_snapshot

from commons.world_model import (
    OpenMeteoClient,
    WATCHPOINTS,
    WorldModelError,
    build_flood_signal,
    build_forecast_council,
    build_snapshot,
    build_weather_memory,
)


class FakeClient:
    provider_shift = {"ecmwf": 0.0, "gfs": 1.5, "icon": -0.8}

    def __init__(self) -> None:
        self.history_calls = 0
        self.flood_history_calls = 0
        self.flood_forecast_calls = 0

    def forecast(self, provider, point):
        shift = self.provider_shift[provider]
        return {
            "daily": {
                "time": [
                    "2026-09-20",
                    "2026-09-21",
                    "2026-09-22",
                    "2026-09-23",
                ],
                "precipitation_sum": [10 + shift, 14 + shift, 8 + shift, 2],
                "temperature_2m_max": [22 + shift / 3, 24, 21, 20],
                "temperature_2m_min": [12, 13, 11, 10],
                "wind_gusts_10m_max": [40, 46 + shift, 38, 30],
            }
        }

    def era5_history(self, point, **kwargs):
        self.history_calls += 1
        return {
            "daily": {
                "time": [
                    "2020-09-18", "2020-09-19", "2020-09-20",
                    "2021-09-18", "2021-09-19", "2021-09-20",
                    "2022-09-18", "2022-09-19", "2022-09-20",
                    "2023-09-18", "2023-09-19", "2023-09-20",
                ],
                "precipitation_sum": [
                    4, 5, 6,
                    10, 12, 8,
                    18, 15, 14,
                    7, 8, 9,
                ],
                "temperature_2m_max": [20] * 12,
            }
        }

    def flood_history(self, point, **kwargs):
        self.flood_history_calls += 1
        return {
            "daily": {
                "time": [
                    "2018-09-18",
                    "2019-09-18",
                    "2020-09-18",
                    "2021-09-18",
                    "2022-07-31",
                ],
                "river_discharge": [20, 30, 40, 50, 60],
            }
        }

    def flood_forecast(self, point, **kwargs):
        self.flood_forecast_calls += 1
        return {
            "daily": {
                "time": [
                    "2026-09-20",
                    "2026-09-21",
                    "2026-09-22",
                    "2026-09-23",
                ],
                "river_discharge": [35, 55, 70, 48],
            }
        }


def test_forecast_council_preserves_independent_members_and_labels_agreement() -> None:
    council = build_forecast_council(WATCHPOINTS[0], FakeClient())

    assert [item["provider"] for item in council["members"]] == [
        "ecmwf",
        "gfs",
        "icon",
    ]
    assert council["consensus"]["precip_72h_mm_median"] is not None
    assert council["consensus"]["precip_agreement"] in {"high", "medium", "low"}
    assert "not a calibrated probability" in council["interpretation"]


def test_weather_memory_uses_only_consecutive_three_day_windows() -> None:
    memory = build_weather_memory(
        FakeClient().era5_history(WATCHPOINTS[0]),
        target_precip_72h_mm=32.0,
        target_start_date="2026-09-20",
    )

    assert memory["status"] == "ok"
    assert 0 <= memory["seasonal_percentile"] <= 100
    starts = {item["start_date"] for item in memory["analogues"]}
    assert starts <= {
        "2020-09-18",
        "2021-09-18",
        "2022-09-18",
        "2023-09-18",
    }
    assert "do not imply similar human impact" in memory["limitation"]


def test_flood_signal_compares_live_forecast_with_cached_history() -> None:
    client = FakeClient()
    signal = build_flood_signal(
        client.flood_history(WATCHPOINTS[0]),
        client.flood_forecast(WATCHPOINTS[0]),
        now=datetime(2026, 9, 20, tzinfo=timezone.utc).date(),
    )

    assert signal["status"] == "ok"
    assert signal["forecast_peak_date"] == "2026-09-22"
    assert signal["forecast_peak_discharge_m3s"] == 70.0
    assert signal["historical_percentile"] == 100.0
    assert "not a local warning" in signal["limitation"]


def test_snapshot_contains_all_ten_loops_but_only_claims_enabled_layers() -> None:
    snapshot = build_snapshot(
        FakeClient(),
        now=datetime(2026, 9, 20, 12, tzinfo=timezone.utc),
    )

    assert len(snapshot["loops"]) == 10
    assert snapshot["mode"] == "research"
    flood = next(loop for loop in snapshot["loops"] if loop["id"] == "water-rises")
    outbreak = next(loop for loop in snapshot["loops"] if loop["id"] == "stop-an-outbreak")

    assert flood["forecast_council"]["members"]
    assert flood["weather_memory"]["status"] == "ok"
    assert flood["flood_signal"]["status"] == "ok"
    assert outbreak["physical_context"] == "not_applicable"
    assert "commercial" in snapshot["source_contract"]["licensing_note"].lower()


def test_expensive_historical_baselines_are_cached_across_refreshes() -> None:
    client = FakeClient()
    cache: dict = {}

    build_snapshot(
        client,
        now=datetime(2026, 9, 20, 0, tzinfo=timezone.utc),
        memory_cache=cache,
    )
    build_snapshot(
        client,
        now=datetime(2026, 9, 20, 6, tzinfo=timezone.utc),
        memory_cache=cache,
    )

    assert client.history_calls == 1
    assert client.flood_history_calls == 1
    assert client.flood_forecast_calls == 2
    assert "water-rises" in cache["era5"]
    assert "water-rises" in cache["flood_history"]


def test_commercial_mode_fails_closed_without_customer_configuration(monkeypatch) -> None:
    monkeypatch.delenv("OPEN_METEO_API_KEY", raising=False)
    for key in ("ECMWF", "GFS", "ICON", "ARCHIVE", "FLOOD"):
        monkeypatch.delenv(f"OPEN_METEO_{key}_URL", raising=False)

    with pytest.raises(WorldModelError, match="Commercial mode requires OPEN_METEO_API_KEY"):
        OpenMeteoClient(commercial=True)


def test_ten_loop_registry_is_emotional_and_honest_about_coverage() -> None:
    catalog = json.loads(
        Path("public/world-model/loops.json").read_text(encoding="utf-8")
    )
    loops = catalog["loops"]

    assert len(loops) == 10
    assert [loop["order"] for loop in loops] == list(range(1, 11))
    assert {loop["human_anchor"] for loop in loops} == {
        "home",
        "shelter",
        "body",
        "land",
        "breath",
        "water",
        "health",
        "ground",
        "food",
        "hope",
    }
    assert sum(loop["coverage"] == "live_pilot" for loop in loops) == 1
    assert any(loop["coverage"] == "story_layer_only" for loop in loops)


def test_seed_state_never_fabricates_live_weather() -> None:
    seed = json.loads(Path("public/world-model/seed.json").read_text(encoding="utf-8"))

    assert seed["generated_at"] is None
    assert seed["status"] == "waiting_for_first_live_snapshot"
    assert seed["loops"] == []


def test_world_model_public_surface_is_story_first_and_truth_preserving() -> None:
    page = Path("public/world-model.html").read_text(encoding="utf-8")
    js = Path("public/world-model.js").read_text(encoding="utf-8")

    assert "Something is changing." in page
    assert "Three models." in page
    assert "Has the sky looked like this before?" in page
    assert "The gap is the clue." in page
    assert "What did we believe" in page
    assert "Inspect the machine." in page
    assert "Not a probability." in page
    assert "History is not destiny." in page
    assert "Backtest everything." in page
    assert "COMMONS should remember its own predictions." in page
    assert "NOT YET FOR SALE" in page
    assert "raw.githubusercontent.com/mikelninh/COMMONS/world-model-data/data/world-model/latest.json" in js
    assert "./world-model/latest.json" in js
    assert "./world-model/seed.json" in js


def test_snapshot_workflow_runs_every_six_hours_archives_and_reuses_history() -> None:
    workflow = Path(".github/workflows/world-model.yml").read_text(encoding="utf-8")

    assert 'cron: "17 */6 * * *"' in workflow
    assert "python scripts/build_world_model.py" in workflow
    assert "--cache-in /tmp/world-model-cache.json" in workflow
    assert "--cache-out /tmp/world-model-cache-out.json" in workflow
    assert "memory-cache.json" in workflow
    assert "world-model-data" in workflow
    assert "actions/upload-artifact@v4" in workflow
    assert 'group: "world-model-snapshot"' in workflow
    assert "Deploy to GitHub Pages" not in workflow
    assert "pages: write" not in workflow


def test_public_home_links_to_world_model() -> None:
    page = Path("public/index.html").read_text(encoding="utf-8")

    assert 'href="./world-model.html"' in page
    assert "World model" in page


def test_monetization_plan_keeps_emergency_information_public() -> None:
    plan = Path("docs/MONETIZATION_V1.md").read_text(encoding="utf-8")

    assert "Commercial capability subsidizes a useful public commons." in plan
    assert "paywalling emergency information" in plan
    assert "€500–1,500 / month" in plan
    assert "These are hypotheses, not current published prices." in plan
    assert "Do not activate paid customer revenue" in plan
    assert "3 organizations × one useful watchlist × recurring monthly payment" in plan


def test_backtest_scores_each_provider_and_consensus_without_claiming_calibration() -> None:
    client = FakeClient()
    snapshot = build_snapshot(
        client,
        now=datetime(2026, 9, 20, 12, tzinfo=timezone.utc),
    )
    flood = next(loop for loop in snapshot["loops"] if loop["id"] == "water-rises")
    result = score_loop_snapshot(
        flood,
        {
            "precip_72h_mm": 34.0,
            "temp_max_72h_c": 24.0,
            "gust_max_72h_kmh": 45.0,
        },
    )

    assert len(result["members"]) == 3
    assert result["consensus"]["precip_abs_error_mm"] is not None
    assert "not probabilistic calibration" in result["note"]


def test_backtest_cli_exists_for_archived_snapshots() -> None:
    script = Path("scripts/backtest_world_model.py").read_text(encoding="utf-8")

    assert "--snapshot" in script
    assert "--observed" in script
    assert "Brier score and CRPS require ensemble forecasts" in script


def test_world_model_browser_javascript_parses() -> None:
    node = shutil.which("node")
    if node is None:
        return
    result = subprocess.run(
        [node, "--check", "public/world-model.js"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_world_model_public_surface_has_required_data_attribution() -> None:
    page = Path("public/world-model.html").read_text(encoding="utf-8")

    assert "Weather, ERA5 and GloFAS access via" in page
    assert "https://open-meteo.com/" in page
    assert "CC BY 4.0" in page
    assert "source-specific terms" in page


def test_live_data_plane_is_independent_from_pages_deploys() -> None:
    js = Path("public/world-model.js").read_text(encoding="utf-8")
    pages = Path(".github/workflows/pages.yml").read_text(encoding="utf-8")
    workflow = Path(".github/workflows/world-model.yml").read_text(encoding="utf-8")

    assert "world-model-data/data/world-model/latest.json" in js
    assert 'group: "pages"' in pages
    assert 'group: "world-model-snapshot"' in workflow


def test_world_model_experience_has_five_visual_scenes_and_lab_mode() -> None:
    page = Path("public/world-model.html").read_text(encoding="utf-8")
    styles = Path("public/world-model.css").read_text(encoding="utf-8")
    js = Path("public/world-model.js").read_text(encoding="utf-8")

    for index in range(5):
        assert f'data-scene="{index}"' in page

    assert 'id="storyModeBtn"' in page
    assert 'id="labModeBtn"' in page
    assert 'id="openLabBtn"' in page
    assert 'id="replaySlider"' in page

    assert ".world-orb" in styles
    assert ".radial-meter" in styles
    assert ".council-bars" in styles
    assert ".memory-line" in styles
    assert ".tension-visual" in styles
    assert ".replay-stage" in styles

    assert "function renderSignal" in js
    assert "function renderCouncilVisual" in js
    assert "function renderMemoryVisual" in js
    assert "function renderReplayFrame" in js
    assert "function setMode" in js


def test_replay_builder_extracts_real_archived_world_model_frames(tmp_path) -> None:
    from commons.world_model_replay import build_replay

    snapshots = tmp_path / "snapshots"
    snapshots.mkdir()
    client = FakeClient()
    first = build_snapshot(
        client,
        now=datetime(2026, 9, 20, 0, tzinfo=timezone.utc),
    )
    second = build_snapshot(
        client,
        now=datetime(2026, 9, 20, 6, tzinfo=timezone.utc),
    )
    (snapshots / "a.json").write_text(json.dumps(first), encoding="utf-8")
    (snapshots / "b.json").write_text(json.dumps(second), encoding="utf-8")

    replay = build_replay(snapshots, limit=48)

    assert replay["loop_id"] == "water-rises"
    assert replay["frame_count"] == 2
    assert len(replay["frames"][0]["members"]) == 3
    assert "historical_percentile" in replay["frames"][0]["flood_signal"]


def test_snapshot_workflow_publishes_replay_file() -> None:
    workflow = Path(".github/workflows/world-model.yml").read_text(encoding="utf-8")

    assert "build_world_model_replay.py" in workflow
    assert "data/world-model/replay.json" in workflow
    assert "--limit 48" in workflow


def test_replay_ui_reads_independent_data_plane_and_falls_back_gracefully() -> None:
    js = Path("public/world-model.js").read_text(encoding="utf-8")

    assert "world-model-data/data/world-model/replay.json" in js
    assert "return [];" in js
    assert "replayFrames=[{" in js
    assert "first archived frame" in js


def test_scroll_cinema_uses_damped_visual_timeline() -> None:
    styles = Path("public/world-model.css").read_text(encoding="utf-8")
    js = Path("public/world-model.js").read_text(encoding="utf-8")

    assert "#storyExperience .scene-frame" in styles
    assert "position:sticky" in styles
    assert "height:156svh" in styles
    assert "--story-progress" in styles

    assert "function setupScrollCinema" in js
    assert "function cinemaTick" in js
    assert "requestAnimationFrame(cinemaTick)" in js
    assert "cinema.smoothY+=(cinema.targetY-cinema.smoothY)*alpha" in js
    assert "Math.pow(0.00008,dt/1000)" in js


def test_scroll_cinema_choreographs_each_scene_instead_of_only_smoothing_page_scroll() -> None:
    styles = Path("public/world-model.css").read_text(encoding="utf-8")
    js = Path("public/world-model.js").read_text(encoding="utf-8")

    assert "--orb-scale" in js
    assert "--bar-reveal" in js
    assert "--memory-reveal" in js
    assert "--tension-scale" in js
    assert "--replay-tilt" in js

    assert "var(--orb-scale,1)" in styles
    assert "var(--bar-reveal,1)" in styles
    assert "var(--memory-reveal,1)" in styles
    assert "var(--tension-scale,1)" in styles
    assert "var(--replay-tilt,0deg)" in styles


def test_scroll_cinema_keeps_reduced_motion_and_lab_mode_safe() -> None:
    styles = Path("public/world-model.css").read_text(encoding="utf-8")
    js = Path("public/world-model.js").read_text(encoding="utf-8")

    assert "prefers-reduced-motion: reduce" in styles
    assert "const reduceMotion=" in js
    assert "function setupReducedMotionStory" in js
    assert 'document.body.classList.toggle("lab-mode",!story)' in js
    assert 'if(reduceMotion)' in js


def test_scene_frames_are_created_runtime_without_losing_existing_semantics() -> None:
    page = Path("public/world-model.html").read_text(encoding="utf-8")
    js = Path("public/world-model.js").read_text(encoding="utf-8")

    assert 'data-scene="0"' in page
    assert 'data-scene="4"' in page
    assert "function wrapSceneFrames" in js
    assert 'frame.className="scene-frame"' in js
    assert "while(scene.firstChild)frame.appendChild(scene.firstChild)" in js


def test_hypothesis_lab_surfaces_falsification_and_rule_update() -> None:
    page = Path("public/world-model.html").read_text(encoding="utf-8")
    js = Path("public/world-model.js").read_text(encoding="utf-8")
    styles = Path("public/world-model.css").read_text(encoding="utf-8")
    report = json.loads(
        Path("public/world-model/hypothesis-report.json").read_text(encoding="utf-8")
    )

    assert "HYPOTHESIS LAB · BACKTESTED" in page
    assert "Reality gets a vote." in page
    assert 'id="hypothesisGrid"' in page
    assert 'id="confidenceRule"' in page

    assert "function renderHypothesisLab" in js
    assert "function loadHypothesisReport" in js
    assert "./world-model/hypothesis-report.json" in js

    assert ".hypothesis-card.not_supported" in styles
    assert ".rule-update" in styles
    assert ".next-test-grid" in styles

    h2 = next(item for item in report["hypotheses"] if item["id"] == "H2")
    h4 = next(item for item in report["hypotheses"] if item["id"] == "H4")
    evidence_health = (report.get("data_quality") or {}).get("status", "healthy")
    if evidence_health == "healthy":
        assert h2["status"] == "not_supported"
        assert h4["status"] == "mixed"
    else:
        assert h2["status"] == "insufficient"
        assert h4["status"] == "insufficient"
    h2_update = h2.get("update") or h2.get("product_update") or ""
    h4_update = h4.get("update") or h4.get("product_update") or ""
    assert "confidence penalty" in h2_update
    assert "disagreement" in h4_update.lower()


def test_hypothesis_report_records_supported_council_and_horizon_findings() -> None:
    report = json.loads(
        Path("public/world-model/hypothesis-report.json").read_text(encoding="utf-8")
    )
    h1 = next(item for item in report["hypotheses"] if item["id"] == "H1")
    h3 = next(item for item in report["hypotheses"] if item["id"] == "H3")
    h5 = next(item for item in report["hypotheses"] if item["id"] == "H5")

    # The weekly report is live research output. Source outages can change sample count;
    # tests should verify enough evidence exists, not freeze one historical run.
    assert report["records"] >= 100
    evidence_health = (report.get("data_quality") or {}).get("status", "healthy")
    expected_status = "supported" if evidence_health == "healthy" else "insufficient"
    assert h1["status"] == expected_status
    assert h3["status"] == expected_status
    assert h5["status"] == expected_status
    lead = report["summary_by_lead"]
    assert all(
        lead[str(day)]["council_improvement_vs_average_model_pct"] > 0
        for day in (1, 3, 5)
    )
    assert all(
        lead[str(day)]["council_heavy_rain_improvement_pct"] > 0
        for day in (1, 3, 5)
    )
    assert lead["1"]["council_median_mae_mm"] < lead["5"]["council_median_mae_mm"]


def test_hypothesis_engine_normalizes_disagreement_before_confidence_claims() -> None:
    source = Path("src/commons/hypothesis_lab.py").read_text(encoding="utf-8")

    assert "symmetric_percentage_error" in source
    assert "relative_spread" in source
    assert "heavy_rain_relative_spread_vs_normalized_error_correlation" in source
    assert "error_reduction_if_abstain_top_disagreement_quartile_pct" in source
    assert "do not convert it into a confidence penalty yet" in source.lower() or "do not treat disagreement" in source.lower()


def test_hypothesis_lab_reruns_weekly_instead_of_freezing_one_result() -> None:
    workflow = Path(".github/workflows/hypothesis-lab.yml").read_text(encoding="utf-8")

    assert 'cron: "41 5 * * 0"' in workflow
    assert 'branches: ["main"]' in workflow
    assert "run_hypothesis_lab.py" in workflow
    assert "hypothesis lab weekly backtest" in workflow
    assert 'group: "world-model-hypothesis-lab"' in workflow


def test_next_hypotheses_focus_on_hydrology_and_persistence() -> None:
    report = json.loads(
        Path("public/world-model/hypothesis-report.json").read_text(encoding="utf-8")
    )
    ids = {item["id"] for item in report["next_hypotheses"]}

    assert {"H7", "H11", "H13", "H14", "H16"} <= ids
    assert "H6" not in ids
    h11 = next(item for item in report["next_hypotheses"] if item["id"] == "H11")
    assert any("basin" in signal.lower() for signal in h11["signals"])
    assert "out-of-sample" in h11["test"]


def test_h6_is_mixed_and_basin_specific_not_global() -> None:
    report = json.loads(
        Path("public/world-model/hypothesis-report.json").read_text(encoding="utf-8")
    )
    hydro = json.loads(
        Path("public/world-model/hydrology-report.json").read_text(encoding="utf-8")
    )

    h6 = next(item for item in report["hypotheses"] if item["id"] == "H6")
    assert h6["status"] == "mixed"
    assert "per basin" in h6["update"]

    assert hydro["hypothesis"]["status"] == "mixed"
    points = {item["id"]: item for item in hydro["points"]}
    assert points["warsaw"]["auc_gain_vs_recent_rain"] > 0.20
    assert points["nuwakot"]["auc_gain_vs_recent_rain"] < 0.03
    assert points["niamey"]["auc_gain_vs_recent_rain"] < 0


def test_weekly_report_composes_hydrology_result_instead_of_erasing_it() -> None:
    script = Path("scripts/run_hypothesis_lab.py").read_text(encoding="utf-8")

    assert 'hydro_path = Path("public/world-model/hydrology-report.json")' in script
    assert '"id": "H6"' in script
    assert '"next_hypotheses"' in script
    assert '"H11"' in script


def test_council_ui_does_not_present_disagreement_as_confidence() -> None:
    page = Path("public/world-model.html").read_text(encoding="utf-8")

    assert "visible context · not a confidence score" in page


def test_revision_hypotheses_are_promoted_and_river_momentum_is_rejected() -> None:
    report = json.loads(
        Path("public/world-model/hypothesis-report.json").read_text(encoding="utf-8")
    )
    by_id = {item["id"]: item for item in report["hypotheses"]}

    assert by_id["H8"]["status"] == "supported"
    assert by_id["H9"]["status"] == "supported"
    assert by_id["H10"]["status"] == "not_supported"
    assert "material-change signal" in by_id["H8"]["update"]
    assert "2/3 models revised upward/downward" in by_id["H9"]["update"]
    assert "current river percentile" in by_id["H10"]["update"].lower()


def test_live_revision_signal_is_visible_but_not_overclaimed() -> None:
    page = Path("public/world-model.html").read_text(encoding="utf-8")
    js = Path("public/world-model.js").read_text(encoding="utf-8")

    assert 'id="liveRevisionSignal"' in page
    assert "EARLY WATCH · OBSERVATIONAL" in page
    assert "function revisionDirectionBetween" in js
    assert "function renderLiveRevisionSignal" in js
    assert "2/3 models" not in page  # live value must be derived from data
    assert "six-hour persistence is still being evaluated" in js
    assert "WATCH only — alert gate unchanged." in js
    assert "Raw disagreement remains visible context, not a confidence penalty." in js


def test_weekly_lab_retests_revision_and_river_rules() -> None:
    workflow = Path(".github/workflows/hypothesis-lab.yml").read_text(encoding="utf-8")

    assert "run_revision_lab.py" in workflow
    assert "run_river_attention_lab.py" in workflow
    assert "revision-report.json" in workflow
    assert "river-attention-report.json" in workflow


def test_revision_lab_requires_both_direction_and_error_improvement() -> None:
    source = Path("src/commons/revision_lab.py").read_text(encoding="utf-8")

    assert "p_acc >= o_acc + 0.05" in source
    assert "p_improve >= o_improve + 0.05" in source
    assert "majority_acc >= 0.60" in source
    assert "majority_improve >= 0.55" in source


def test_river_trajectory_hypothesis_failed_in_all_three_test_basins() -> None:
    report = json.loads(
        Path("public/world-model/river-attention-report.json").read_text(encoding="utf-8")
    )

    assert report["hypothesis"]["status"] == "not_supported"
    assert report["hypothesis"]["mean_auc_gain"] < 0
    assert report["hypothesis"]["mean_precision_gain_pct"] < 0
    assert all(item["auc_gain"] < 0 for item in report["points"])


def test_next_hypotheses_move_toward_attention_quality_and_external_validation() -> None:
    report = json.loads(
        Path("public/world-model/hypothesis-report.json").read_text(encoding="utf-8")
    )
    ids = {item["id"] for item in report["next_hypotheses"]}

    assert {"H7", "H11", "H13", "H14", "H16"} <= ids
    h16 = next(item for item in report["next_hypotheses"] if item["id"] == "H16")
    h14 = next(item for item in report["next_hypotheses"] if item["id"] == "H14")
    assert "WATCH" in h16["claim"]
    assert "monitoring time, ignored watches, useful catches and perceived interruption burden" in h16["test"]
    assert "official warnings" in h14["signals"]


def test_attention_rule_only_uses_lower_threshold_when_revision_is_upward() -> None:
    from commons.attention_rule_lab import first_alert_lead

    upward = {
        "council": {5: 10.0, 3: 17.0, 1: 21.0},
        "revision_5_to_3": 1,
        "revision_3_to_1": 1,
    }
    downward = {
        "council": {5: 10.0, 3: 17.0, 1: 21.0},
        "revision_5_to_3": -1,
        "revision_3_to_1": -1,
    }

    assert first_alert_lead(upward, 20.0, policy="strict") == 1
    assert first_alert_lead(upward, 20.0, policy="loose") == 3
    assert first_alert_lead(upward, 20.0, policy="revision_aware") == 3
    assert first_alert_lead(downward, 20.0, policy="revision_aware") == 1


def test_attention_rule_benchmark_includes_strict_and_loose_controls() -> None:
    source = Path("src/commons/attention_rule_lab.py").read_text(encoding="utf-8")

    assert 'policy="strict"' in source
    assert 'policy="loose"' in source
    assert 'policy="revision_aware"' in source
    assert "LOOSE_FACTOR = 0.80" in source
    assert "revision_beats_strict" in source
    assert "revision_beats_loose" in source


def test_attention_rule_requires_precision_recall_tradeoff_not_engagement() -> None:
    source = Path("src/commons/attention_rule_lab.py").read_text(encoding="utf-8")

    assert "precision" in source
    assert "recall" in source
    assert "miss_rate" in source
    assert "mean_true_alert_lead_days" in source
    assert "false_alerts_per_100_days" in source


def test_h12_keeps_alert_gate_strict_and_revision_signal_watch_only() -> None:
    report = json.loads(
        Path("public/world-model/attention-rule-report.json").read_text(encoding="utf-8")
    )
    h12 = report["hypothesis"]

    assert h12["status"] == "not_supported"
    assert report["policies"]["revision_aware"]["recall"] > report["policies"]["strict"]["recall"]
    assert report["policies"]["revision_aware"]["precision"] < report["policies"]["strict"]["precision"]
    # H12 is rejected by its declared support threshold, not by an exact weekly F1 delta.
    assert h12["f1_gain_vs_strict"] < 0.03
    assert "fixed thresholds" in h12["product_update"].lower()


def test_weekly_lab_retests_h12_attention_rule() -> None:
    workflow = Path(".github/workflows/hypothesis-lab.yml").read_text(encoding="utf-8")
    script = Path("scripts/run_hypothesis_lab.py").read_text(encoding="utf-8")

    assert "run_attention_rule_lab.py" in workflow
    assert "attention-rule-report.json" in workflow
    assert 'attention_path = Path("public/world-model/attention-rule-report.json")' in script
    assert '"id": "H12"' in script


def test_h15_status_follows_measured_watch_value_and_burden() -> None:
    report = json.loads(
        Path("public/world-model/watch-alert-report.json").read_text(encoding="utf-8")
    )
    h15 = report["hypothesis"]

    expected_supported = (
        report["extra_recall"] >= 0.03
        and report["watch_only_precision"] >= 0.20
        and report["watch_burden_per_100_days"] <= 3.0
    )

    assert (h15["status"] == "supported") is expected_supported
    assert report["watch_recall"] >= report["alert_recall"]
    if expected_supported:
        assert "two-tier attention model" in h15["product_update"]
    else:
        assert "do not add a separate watch tier yet" in h15["product_update"].lower()


def test_weekly_lab_retests_watch_alert_architecture() -> None:
    workflow = Path(".github/workflows/hypothesis-lab.yml").read_text(encoding="utf-8")
    script = Path("scripts/run_hypothesis_lab.py").read_text(encoding="utf-8")

    assert "run_watch_alert_lab.py" in workflow
    assert "watch-alert-report.json" in workflow
    assert 'watch_path = Path("public/world-model/watch-alert-report.json")' in script
    assert '"id": "H15"' in script


def test_next_step_is_human_usefulness_not_more_automatic_confidence() -> None:
    report = json.loads(
        Path("public/world-model/hypothesis-report.json").read_text(encoding="utf-8")
    )
    h16 = next(item for item in report["next_hypotheses"] if item["id"] == "H16")

    assert "monitoring time" in h16["claim"].lower()
    assert "perceived noise" in h16["claim"].lower()
    assert "human pilot" in h16["test"].lower()


def test_hypothesis_http_retries_transient_failures(monkeypatch) -> None:
    import commons.hypothesis_lab as lab

    calls = {"count": 0}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"daily":{"time":[]}}'

    def flaky_urlopen(request, timeout):
        calls["count"] += 1
        if calls["count"] < 3:
            raise TimeoutError("temporary handshake timeout")
        return Response()

    monkeypatch.setattr(lab, "urlopen", flaky_urlopen)
    monkeypatch.setattr(lab, "sleep", lambda seconds: None)

    payload = lab._request_json(
        "https://example.test/data",
        {"x": 1},
        attempts=3,
        backoff_seconds=0,
    )

    assert calls["count"] == 3
    assert payload["daily"]["time"] == []


def test_hypothesis_data_quality_blocks_learning_from_partial_sources() -> None:
    from commons.hypothesis_lab import BacktestPoint, evaluate_data_quality

    point = BacktestPoint("x", "X", "Test", 0.0, 0.0)
    full_records = [
        {
            "point_id": "x",
            "predictions_mm": {"ecmwf": 1.0, "gfs": 1.0, "icon": 1.0},
        }
        for _ in range(60)
    ]
    partial_records = [
        {
            "point_id": "x",
            "predictions_mm": {"ecmwf": 1.0, "gfs": 1.0},
        }
        for _ in range(60)
    ]

    healthy = evaluate_data_quality(
        full_records,
        start_date="2026-09-01",
        end_date="2026-09-20",
        points=(point,),
    )
    degraded = evaluate_data_quality(
        partial_records,
        start_date="2026-09-01",
        end_date="2026-09-20",
        points=(point,),
    )

    assert healthy["status"] == "healthy"
    assert healthy["temporal_coverage"] == 1.0
    assert healthy["full_council_ratio"] == 1.0
    assert degraded["status"] == "degraded"
    assert degraded["temporal_coverage"] == 1.0
    assert degraded["full_council_ratio"] < 0.9
