from __future__ import annotations

from argparse import ArgumentParser
from datetime import date, timedelta
import json
from pathlib import Path

from commons.external_alert_lab import run_external_alert_benchmark


def main() -> int:
    parser = ArgumentParser(description="Benchmark COMMONS against public external disaster alerts.")
    parser.add_argument("--start-date", default=None)
    parser.add_argument("--end-date", default=None)
    parser.add_argument("--output", default="public/world-model/external-alert-report.json")
    args = parser.parse_args()

    end = date.fromisoformat(args.end_date) if args.end_date else date.today() - timedelta(days=10)
    start = date.fromisoformat(args.start_date) if args.start_date else end - timedelta(days=60)
    report = run_external_alert_benchmark(
        start_date=start.isoformat(),
        end_date=end.isoformat(),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(report["hypothesis"]["effect"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
