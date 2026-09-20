from __future__ import annotations

from argparse import ArgumentParser

from commons.hydrology_lab import run_hydrology_backtest, save_report


def main() -> int:
    parser = ArgumentParser(description="Run COMMONS hydrology hypothesis backtest.")
    parser.add_argument("--start-date", default="2019-01-01")
    parser.add_argument("--end-date", default="2022-07-31")
    parser.add_argument("--output", default="public/world-model/hydrology-report.json")
    args = parser.parse_args()

    report = run_hydrology_backtest(
        start_date=args.start_date,
        end_date=args.end_date,
    )
    save_report(report, args.output)

    h = report["hypothesis"]
    print("Hydrology Lab")
    print(f"period: {args.start_date} → {args.end_date}")
    print(f"source errors: {len(report['source_errors'])}")
    for point in report["points"]:
        print(
            f"{point['name']}: AUC gain={point.get('auc_gain_vs_recent_rain')} "
            f"precision gain={point.get('precision_gain_vs_recent_rain_pct')}%"
        )
    print(
        f"{h['id']} {h['status'].upper()}: {h['claim']} | "
        f"mean AUC gain={h['mean_auc_gain']} | "
        f"mean precision gain={h['mean_precision_gain_pct']}%"
    )
    print(f"  update: {h['product_update']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
