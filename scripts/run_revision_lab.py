from __future__ import annotations

from argparse import ArgumentParser
import json
from pathlib import Path

from commons.revision_lab import run_revision_backtest


def main() -> int:
    parser = ArgumentParser(description="Backtest World Model forecast revision signals.")
    parser.add_argument("--start-date", default="2026-07-01")
    parser.add_argument("--end-date", default="2026-09-05")
    parser.add_argument("--output", default="public/world-model/revision-report.json")
    args = parser.parse_args()

    report = run_revision_backtest(
        start_date=args.start_date,
        end_date=args.end_date,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print("Revision Lab")
    print(f"period: {args.start_date} → {args.end_date}")
    print(f"paths: {report['summary']['paths']}")
    print(f"source errors: {len(report['source_errors'])}")
    for hypothesis in report["hypotheses"]:
        print(
            f"{hypothesis['id']} {hypothesis['status'].upper()}: "
            f"{hypothesis['claim']} | {hypothesis['effect']}"
        )
        print(f"  update: {hypothesis['product_update']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
