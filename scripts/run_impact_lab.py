from __future__ import annotations

from argparse import ArgumentParser
import json
from pathlib import Path

from commons.impact_lab import run_impact_v0


def _load_optional(path: str | None):
    if not path:
        return None
    target = Path(path)
    if not target.exists():
        return None
    return json.loads(target.read_text(encoding="utf-8"))


def main() -> int:
    parser = ArgumentParser(description="Build COMMONS Impact v0.")
    parser.add_argument(
        "--exposure-report",
        default="public/world-model/exposure-report.json",
    )
    parser.add_argument(
        "--output",
        default="public/world-model/impact-report.json",
    )
    parser.add_argument("--history-start", default=None)
    parser.add_argument("--history-end", default=None)
    args = parser.parse_args()

    report = run_impact_v0(
        exposure_report=_load_optional(args.exposure_report),
        history_start=args.history_start,
        history_end=args.history_end,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    h = report["benchmark"]["hypothesis"]
    print("Impact v0", h["status"].upper(), h["effect"])
    print("EM-DAT coverage:", report["source_health"]["emdat_coverage"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
