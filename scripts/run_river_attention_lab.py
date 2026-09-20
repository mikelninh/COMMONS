from __future__ import annotations

from argparse import ArgumentParser
import json
from pathlib import Path

from commons.river_attention_lab import run_river_attention_backtest


def main() -> int:
    parser = ArgumentParser(description="Backtest river trajectory attention signal.")
    parser.add_argument("--start-date", default="2019-01-01")
    parser.add_argument("--end-date", default="2022-07-31")
    parser.add_argument("--output", default="public/world-model/river-attention-report.json")
    args = parser.parse_args()

    report = run_river_attention_backtest(
        start_date=args.start_date,
        end_date=args.end_date,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print("River Attention Lab")
    print(f"period: {args.start_date} → {args.end_date}")
    print(f"source errors: {len(report['source_errors'])}")
    for point in report["points"]:
        print(
            f"{point['name']}: AUC gain={point.get('auc_gain')} "
            f"precision gain={point.get('precision_gain_pct')}%"
        )
    h = report["hypothesis"]
    print(
        f"{h['id']} {h['status'].upper()}: {h['claim']} | "
        f"mean AUC gain={h['mean_auc_gain']} | "
        f"mean precision gain={h['mean_precision_gain_pct']}%"
    )
    print(f"  update: {h['product_update']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
