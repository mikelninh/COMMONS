from __future__ import annotations

from argparse import ArgumentParser
import json
from pathlib import Path

from commons.model_dropout_lab import run_model_dropout_backtest


def main() -> int:
    parser = ArgumentParser(description="Stress-test COMMONS attention ranking under model dropout.")
    parser.add_argument("--train-start", default="2026-07-01")
    parser.add_argument("--train-end", default="2026-08-10")
    parser.add_argument("--test-start", default="2026-08-11")
    parser.add_argument("--test-end", default="2026-09-10")
    parser.add_argument("--output", default="public/world-model/model-dropout-report.json")
    args = parser.parse_args()

    report = run_model_dropout_backtest(
        train_start=args.train_start,
        train_end=args.train_end,
        test_start=args.test_start,
        test_end=args.test_end,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    h = report["hypothesis"]
    print("Model Dropout Lab")
    print(f"test cases: {report['test_cases']} · heavy events: {report['heavy_events']}")
    for provider, result in report["dropouts"].items():
        print(provider, "alert agreement", result["alert_agreement"], result["budgets"])
    print(h["id"], h["status"].upper(), h["effect"])
    print("update:", h["product_update"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
