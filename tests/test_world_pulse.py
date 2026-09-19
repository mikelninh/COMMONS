from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from commons import world_pulse
from commons.app import app
from commons.world_pulse import WorldSignal

client = TestClient(app)


def signal(
    signal_id: str,
    source: str,
    *,
    lat: float,
    lon: float,
    kind: str = "earthquake",
    title: str = "test",
    hours_ago: int = 0,
    magnitude: float | None = None,
) -> WorldSignal:
    now = datetime.now(timezone.utc)
    return WorldSignal(
        signal_id=signal_id,
        source=source,
        source_event_id=signal_id,
        kind=kind,
        title=title,
        latitude=lat,
        longitude=lon,
        occurred_at=now - timedelta(hours=hours_ago),
        updated_at=now - timedelta(hours=hours_ago),
        magnitude=magnitude,
    )


def test_world_pulse_page_is_shareable() -> None:
    response = client.get("/world")
    assert response.status_code == 200
    assert "COMMONS</b> / WORLD PULSE" in response.text
    assert "Most of Earth is quiet." in response.text
    assert "Correlation does not become confirmation." in response.text


def test_first_observation_is_baseline_not_fake_change() -> None:
    world_pulse._previous_fingerprints.clear()
    signals = [
        signal("usgs:1", "USGS", lat=10, lon=10),
        signal("gdacs:1", "GDACS", lat=20, lon=20),
    ]

    baseline = world_pulse._apply_change_state(signals)

    assert baseline is True
    assert all(item.state == "known" for item in signals)


def test_second_observation_marks_only_real_changes() -> None:
    world_pulse._previous_fingerprints.clear()
    first = [signal("usgs:1", "USGS", lat=10, lon=10, title="original")]
    assert world_pulse._apply_change_state(first) is True

    second = [
        signal("usgs:1", "USGS", lat=10, lon=10, title="updated"),
        signal("usgs:2", "USGS", lat=30, lon=30, title="new"),
    ]
    baseline = world_pulse._apply_change_state(second)

    assert baseline is False
    by_id = {item.signal_id: item for item in second}
    assert by_id["usgs:1"].state == "updated"
    assert by_id["usgs:2"].state == "new"


def test_multi_source_cluster_requires_different_sources_and_proximity() -> None:
    near_usgs = signal("usgs:1", "USGS", lat=35.0, lon=139.0, hours_ago=1)
    near_gdacs = signal("gdacs:1", "GDACS", lat=35.4, lon=139.2, hours_ago=2)
    far_nasa = signal("eonet:1", "NASA EONET", lat=-20.0, lon=-60.0, hours_ago=1)

    clusters = world_pulse._clusters([near_usgs, near_gdacs, far_nasa])

    assert len(clusters) == 1
    assert set(clusters[0].sources) == {"USGS", "GDACS"}
    assert clusters[0].distance_km < 250
    assert "Correlation is not proof" in clusters[0].reason


def test_large_quake_has_visible_attention_reason() -> None:
    quake = signal(
        "usgs:large",
        "USGS",
        lat=0,
        lon=0,
        magnitude=6.2,
    )
    reasons = world_pulse._attention_for(quake)
    assert "earthquake magnitude ≥ 6.0" in reasons


def test_source_states_expose_freshness_and_scope(monkeypatch) -> None:
    assert world_pulse.SourceState(
        source="USGS",
        ok=True,
        fetched_at=datetime.now(timezone.utc),
        count=1,
        freshness="live",
        cadence="feed updated about every minute",
        source_url="https://earthquake.usgs.gov/earthquakes/feed/",
        scope_note="Rolling earthquake feed.",
    ).freshness == "live"
