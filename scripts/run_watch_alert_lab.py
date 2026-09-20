from __future__ import annotations

from argparse import ArgumentParser
import json
from pathlib import Path

from commons.watch_alert_lab import run_watch_alert_backtest


def main() -> int:
    parser=ArgumentParser(description="Backtest WATCH vs ALERT attention tiers.")
    parser.add_argument("--start-date",default="2026-07-01")
    parser.add_argument("--end-date",default="2026-09-05")
    parser.add_argument("--output",default="public/world-model/watch-alert-report.json")
    args=parser.parse_args()

    report=run_watch_alert_backtest(
        start_date=args.start_date,
        end_date=args.end_date,
    )
    output=Path(args.output)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")

    print("WATCH ALERT Lab")
    print(f"paths: {report['paths']} heavy events: {report['heavy_events']}")
    print(
        f"alert recall={report['alert_recall']} watch recall={report['watch_recall']} "
        f"extra recall={report['extra_recall']}"
    )
    print(
        f"watch-only precision={report['watch_only_precision']} "
        f"burden/100d={report['watch_burden_per_100_days']} "
        f"earlier={report['mean_earlier_watch_days']}d"
    )
    h=report["hypothesis"]
    print(f"{h['id']} {h['status'].upper()}: {h['claim']}")
    print(f"  update: {h['product_update']}")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
