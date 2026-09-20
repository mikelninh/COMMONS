from __future__ import annotations

from argparse import ArgumentParser
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from commons.morning_brief import build_morning_brief


def _load(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def find_previous_snapshot(
    snapshots_dir: str | Path | None,
    current: dict[str, Any],
) -> dict[str, Any] | None:
    if not snapshots_dir:
        return None
    root = Path(snapshots_dir)
    if not root.exists():
        return None

    current_dt = _dt(current.get("generated_at"))
    candidates: list[tuple[datetime, dict[str, Any]]] = []
    for path in root.rglob("*.json"):
        try:
            payload = _load(path)
        except (OSError, json.JSONDecodeError):
            continue
        generated = _dt(payload.get("generated_at"))
        if generated is None:
            continue
        if current_dt is not None and generated >= current_dt:
            continue
        candidates.append((generated, payload))

    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[-1][1]


def parse_args():
    parser = ArgumentParser(description="Build the COMMONS Morning Brief.")
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--snapshots", default=None)
    parser.add_argument("--attention-report", required=True)
    parser.add_argument("--hypothesis-report", required=True)
    parser.add_argument("--loops", required=True)
    parser.add_argument("--exposure-report", default=None)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    snapshot = _load(args.snapshot)
    previous = find_previous_snapshot(args.snapshots, snapshot)
    exposure = (
        _load(args.exposure_report)
        if args.exposure_report and Path(args.exposure_report).exists()
        else None
    )
    brief = build_morning_brief(
        snapshot,
        previous_snapshot=previous,
        attention_report=_load(args.attention_report),
        hypothesis_report=_load(args.hypothesis_report),
        loop_catalog=_load(args.loops),
        exposure_report=exposure,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(brief, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "ok",
                "output": str(output),
                "generated_at": brief.get("generated_at"),
                "alerts": brief["summary"]["alerts"],
                "priority": brief["summary"]["priority"],
                "evidence": brief["evidence"]["status"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
