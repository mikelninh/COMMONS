from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def extract_frame(snapshot: dict[str, Any]) -> dict[str, Any] | None:
    loop = next(
        (item for item in snapshot.get("loops", []) if item.get("id") == "water-rises"),
        None,
    )
    if not loop:
        return None
    council = loop.get("forecast_council") or {}
    flood = loop.get("flood_signal") or {}
    memory = loop.get("weather_memory") or {}
    return {
        "generated_at": snapshot.get("generated_at"),
        "watchpoint": loop.get("watchpoint"),
        "members": council.get("members") or [],
        "consensus": council.get("consensus") or {},
        "source_errors": council.get("source_errors") or [],
        "weather_memory": {
            "status": memory.get("status"),
            "seasonal_percentile": memory.get("seasonal_percentile"),
        },
        "flood_signal": {
            "status": flood.get("status"),
            "forecast_peak_date": flood.get("forecast_peak_date"),
            "forecast_peak_discharge_m3s": flood.get("forecast_peak_discharge_m3s"),
            "historical_percentile": flood.get("historical_percentile"),
        },
    }


def build_replay(root: Path, limit: int = 48) -> dict[str, Any]:
    files = sorted(root.rglob("*.json"))[-limit:]
    frames = []
    for path in files:
        try:
            snapshot = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        frame = extract_frame(snapshot)
        if frame and frame.get("generated_at"):
            frames.append(frame)
    return {
        "schema_version": "0.1",
        "loop_id": "water-rises",
        "frame_count": len(frames),
        "frames": frames,
        "note": "Archived research snapshots. Frames show what COMMONS knew at each collection time.",
    }
