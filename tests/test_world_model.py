from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

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


def test_world_model_public_surface_explains_limits_and_learning_loop() -> None:
    page = Path("public/world-model.html").read_text(encoding="utf-8")
    js = Path("public/world-model.js").read_text(encoding="utf-8")

    assert "Forecast what may happen." in page
    assert "Models may disagree. COMMONS must show that." in page
    assert "Not a probability" in page
    assert "History is not destiny" in page
    assert "Backtest everything" in page
    assert "COMMONS should remember its own predictions." in page
    assert "NOT YET FOR SALE" in page
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
    assert "Deploy to GitHub Pages" in workflow


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
