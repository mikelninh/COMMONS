from __future__ import annotations

from argparse import ArgumentParser
from datetime import datetime, timezone
import json
from pathlib import Path

from commons.trust import evaluate_registry, load_registry


def parse_args():
    parser = ArgumentParser(description="Evaluate the public COMMONS trust registry.")
    parser.add_argument(
        "--registry",
        default="public/trust-registry.json",
        help="Path to the public trust registry JSON.",
    )
    parser.add_argument(
        "--at",
        default=None,
        help="Evaluate at an ISO-8601 timestamp instead of the current time.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    registry = load_registry(Path(args.registry))
    now = None
    if args.at:
        now = datetime.fromisoformat(args.at.replace("Z", "+00:00"))
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

    report = evaluate_registry(registry, now=now)
    compact = {
        "status": report["status"],
        "evaluated_at": report["evaluated_at"],
        "provenance_coverage": report["provenance_coverage"],
        "stale_critical_claims": [
            claim["id"] for claim in report["stale_critical_claims"]
        ],
        "missing_sources": report["missing_sources"],
        "unresolved_conflicts": [
            item.get("id") for item in report["unresolved_conflicts"]
        ],
        "open_high_incidents": [
            item.get("id") for item in report["open_high_incidents"]
        ],
        "checks": report["checks"],
    }
    print(json.dumps(compact, indent=2))
    return 0 if report["status"] == "HEALTHY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
