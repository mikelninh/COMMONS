from __future__ import annotations

from argparse import ArgumentParser
import json
from pathlib import Path

from commons.exposure_lab import run_exposure_context


def main() -> int:
    parser = ArgumentParser(description="Build WorldPop exposure context for COMMONS.")
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--radius-km", type=float, default=20.0)
    parser.add_argument("--output", default="public/world-model/exposure-report.json")
    args = parser.parse_args()

    report = run_exposure_context(year=args.year, radius_km=args.radius_km)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(report["hypothesis"]["effect"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
