from __future__ import annotations

from argparse import ArgumentParser
from datetime import date, timedelta

from commons.hypothesis_lab import run_backtest, save_report


def main() -> int:
    parser = ArgumentParser(description="Run COMMONS World Model hypothesis backtests.")
    parser.add_argument("--start-date", default=None)
    parser.add_argument("--end-date", default=None)
    parser.add_argument(
        "--output",
        default="public/world-model/hypothesis-report.json",
    )
    args = parser.parse_args()

    end = date.fromisoformat(args.end_date) if args.end_date else date.today() - timedelta(days=10)
    start = (
        date.fromisoformat(args.start_date)
        if args.start_date
        else end - timedelta(days=60)
    )

    report = run_backtest(
        start_date=start.isoformat(),
        end_date=end.isoformat(),
    )
    save_report(report, args.output)

    print("Hypothesis Lab")
    print(f"period: {start} → {end}")
    print(f"records: {report['records']}")
    print(f"source errors: {len(report['source_errors'])}")
    for hypothesis in report["hypotheses"]:
        print(
            f"{hypothesis['id']} {hypothesis['status'].upper()}: "
            f"{hypothesis['claim']} | {hypothesis.get('effect')}"
        )
        print(f"  update: {hypothesis['product_update']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
