from __future__ import annotations

from argparse import ArgumentParser
import json
from pathlib import Path

from commons.attention_rule_lab import run_attention_backtest


def main() -> int:
    parser=ArgumentParser(description="Backtest COMMONS material-change attention rule.")
    parser.add_argument("--start-date",default="2026-07-01")
    parser.add_argument("--end-date",default="2026-09-05")
    parser.add_argument("--output",default="public/world-model/attention-rule-report.json")
    args=parser.parse_args()

    report=run_attention_backtest(
        start_date=args.start_date,
        end_date=args.end_date,
    )
    output=Path(args.output)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")

    print("Attention Rule Lab")
    print(f"period: {args.start_date} → {args.end_date}")
    print(f"paths: {report['paths']}")
    print(f"source errors: {len(report['source_errors'])}")
    for name,policy in report["policies"].items():
        print(
            f"{name}: precision={policy['precision']} recall={policy['recall']} "
            f"f1={policy['f1']} lead={policy['mean_true_alert_lead_days']} "
            f"false/100d={policy['false_alerts_per_100_days']}"
        )
    h=report["hypothesis"]
    print(
        f"{h['id']} {h['status'].upper()}: {h['claim']} | "
        f"F1 gain={h['f1_gain_vs_strict']} recall gain={h['recall_gain_vs_strict']} "
        f"precision change={h['precision_change_vs_strict']} "
        f"lead gain={h['lead_gain_days_vs_strict']}"
    )
    print(f"  update: {h['product_update']}")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
