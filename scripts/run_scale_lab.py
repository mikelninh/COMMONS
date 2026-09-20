from __future__ import annotations

from argparse import ArgumentParser
from datetime import date, timedelta
import json
from pathlib import Path

from commons.scale_lab import run_scale_backtest


def main() -> int:
    parser = ArgumentParser(description="Run the COMMONS 30-location scale backtest.")
    parser.add_argument("--start-date", default=None)
    parser.add_argument("--end-date", default=None)
    parser.add_argument("--output", default="public/world-model/scale-report.json")
    args = parser.parse_args()

    end = date.fromisoformat(args.end_date) if args.end_date else date.today() - timedelta(days=10)
    start = date.fromisoformat(args.start_date) if args.start_date else end - timedelta(days=60)
    report = run_scale_backtest(start_date=start.isoformat(), end_date=end.isoformat())
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(report["hypothesis"]["effect"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
