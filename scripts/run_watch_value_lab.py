from __future__ import annotations

from argparse import ArgumentParser
import json
from pathlib import Path

from commons.watch_value_lab import run_watch_value_backtest


def main() -> int:
    parser = ArgumentParser(description="Backtest whether revisions help rank WATCH candidates.")
    parser.add_argument("--start-date", default="2026-07-01")
    parser.add_argument("--end-date", default="2026-09-05")
    parser.add_argument("--near-threshold-factor", type=float, default=0.60)
    parser.add_argument("--output", default="public/world-model/watch-value-report.json")
    args = parser.parse_args()

    report = run_watch_value_backtest(
        start_date=args.start_date,
        end_date=args.end_date,
        near_threshold_factor=args.near_threshold_factor,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    h = report["hypothesis"]
    print("WATCH Value Lab")
    print(f"near-threshold cases: {report['near_threshold_cases']}")
    print(h["id"], h["status"].upper(), h["effect"])
    print("update:", h["product_update"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
