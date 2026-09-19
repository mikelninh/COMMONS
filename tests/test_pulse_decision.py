from datetime import datetime, timezone

from fastapi.testclient import TestClient

from commons.app import app
from commons.pulse_decision import build_decision_batch, decide_signal, pulse_jev_enabled
from commons.world_pulse import SourceState, WorldPulseResponse, WorldPulseStats, WorldSignal

client = TestClient(app)


def quake(*, state: str, magnitude: float, attention: list[str]) -> WorldSignal:
    now = datetime.now(timezone.utc)
    return WorldSignal(
        signal_id="usgs:test",
        source="USGS",
        source_event_id="test",
        kind="earthquake",
        title="M6.4 test earthquake",
        latitude=1.0,
        longitude=2.0,
        occurred_at=now,
        updated_at=now,
        magnitude=magnitude,
        state=state,
        attention_reasons=attention,
    )


def pulse_with(signal: WorldSignal) -> WorldPulseResponse:
    return WorldPulseResponse(
        generated_at=datetime.now(timezone.utc),
        baseline_observation=False,
        source_states=[
            SourceState(
                source="USGS",
                ok=True,
                fetched_at=datetime.now(timezone.utc),
                count=1,
            )
        ],
        stats=WorldPulseStats(
            total_signals=1,
            new_signals=1 if signal.state == "new" else 0,
            updated_signals=1 if signal.state == "updated" else 0,
            attention_signals=1 if signal.attention_reasons else 0,
            possible_multi_source_clusters=0,
        ),
        signals=[signal],
        clusters=[],
    )


def test_jev_requires_explicit_pulse_opt_in(monkeypatch) -> None:
    monkeypatch.setenv("TYPESAFE_API_KEY", "present-but-not-used")
    monkeypatch.delenv("PULSE_JEV_ENABLED", raising=False)
    assert pulse_jev_enabled() is False

    monkeypatch.setenv("PULSE_JEV_ENABLED", "1")
    assert pulse_jev_enabled() is True


def test_changed_high_signal_wakes_without_paid_jev_by_default(monkeypatch) -> None:
    monkeypatch.delenv("PULSE_JEV_ENABLED", raising=False)
    signal = quake(
        state="new",
        magnitude=6.4,
        attention=["earthquake magnitude ≥ 6.0"],
    )

    decision = decide_signal(signal)

    assert decision.wake is True
    assert decision.mode == "deterministic"
    assert decision.next_capability == "reason"
    assert any(node.kind == "reason" for node in decision.action_graph)


def test_unchanged_high_signal_does_not_auto_wake() -> None:
    signal = quake(
        state="known",
        magnitude=6.4,
        attention=["earthquake magnitude ≥ 6.0"],
    )

    decision = decide_signal(signal)

    assert decision.wake is False
    assert decision.mode == "deterministic"
    assert decision.next_capability == "monitor"


def test_batch_keeps_unchanged_attention_as_review_not_auto_spend(monkeypatch) -> None:
    monkeypatch.delenv("PULSE_JEV_ENABLED", raising=False)
    signal = quake(
        state="known",
        magnitude=6.4,
        attention=["earthquake magnitude ≥ 6.0"],
    )

    batch = build_decision_batch(pulse_with(signal))

    assert batch.jev_enabled is False
    assert batch.auto_wakes == []
    assert len(batch.review_candidates) == 1
    assert batch.review_candidates[0].wake is False


def test_world_ui_explains_zero_cost_sleep_state() -> None:
    response = client.get("/world")

    assert response.status_code == 200
    assert "intelligence stayed asleep" in response.text
    assert "0 inference calls" in response.text
    assert "TRACE DECISION" in response.text


def test_world_brief_explains_sleep_state_without_inventing_importance() -> None:
    signal = quake(
        state="known",
        magnitude=6.4,
        attention=["earthquake magnitude ≥ 6.0"],
    )
    pulse = pulse_with(signal)
    decisions = build_decision_batch(pulse)

    from commons.pulse_decision import build_world_brief

    brief = build_world_brief(pulse, decisions)

    assert "Nothing crossed the wake gate." in brief.headline
    assert brief.items
    assert brief.items[0].status == "review"
    assert "Keep monitoring" in brief.items[0].next_step


def test_world_ui_contains_brief_filters_and_shareable_focus() -> None:
    response = client.get("/world")

    assert response.status_code == 200
    assert "WORLD BRIEF" in response.text
    assert 'data-filter="changed"' in response.text
    assert "COPY FOCUS LINK" in response.text
