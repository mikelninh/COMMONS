from datetime import datetime, timezone

from commons import pulse
from commons.pulse import PulseSignal, PulseSnapshot


def sample_signal(signal_id: str = "test") -> PulseSignal:
    return PulseSignal(
        id=signal_id,
        category="planet",
        label="Test signal",
        value=1.0,
        unit="events",
        display_value="1",
        freshness="live",
        confidence="high",
        as_of="2026-09-19",
        source_name="Test source",
        source_url="https://example.com",
        methodology="Test methodology.",
    )


def test_fresh_snapshot_degrades_when_one_source_fails(monkeypatch) -> None:
    def good():
        return [sample_signal()]

    def bad():
        raise RuntimeError("upstream down")

    monkeypatch.setattr(pulse, "_producers", lambda: [("good", good), ("bad", bad)])
    snapshot = pulse._fresh_snapshot()

    assert [signal.id for signal in snapshot.signals] == ["test"]
    assert snapshot.warnings == ["bad unavailable: RuntimeError"]


def test_snapshot_cache_avoids_refetch(monkeypatch) -> None:
    calls = 0

    def fresh():
        nonlocal calls
        calls += 1
        return PulseSnapshot(
            generated_at=datetime.now(timezone.utc),
            signals=[sample_signal()],
        )

    monkeypatch.setattr(pulse, "_fresh_snapshot", fresh)
    monkeypatch.setattr(pulse, "_cache_snapshot", None)
    monkeypatch.setattr(pulse, "_cache_until", 0.0)

    first = pulse.build_snapshot()
    second = pulse.build_snapshot()

    assert calls == 1
    assert first.signals[0].id == second.signals[0].id
    assert first is not second
