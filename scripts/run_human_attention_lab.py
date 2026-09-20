from __future__ import annotations

from argparse import ArgumentParser
import json
from pathlib import Path

from commons.human_attention_lab import build_attention_cases


def main() -> int:
    parser = ArgumentParser(description="Build the H16 human attention benchmark fixture.")
    parser.add_argument("--start-date", default="2026-07-01")
    parser.add_argument("--end-date", default="2026-09-05")
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--output", default="public/world-model/attention-cases.json")
    args = parser.parse_args()

    report = build_attention_cases(
        start_date=args.start_date,
        end_date=args.end_date,
        limit=args.limit,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print("H16 Human Attention Benchmark")
    print(f"cases: {report['case_count']} · period: {report['period']['start']} → {report['period']['end']}")
    print(f"mix: {report['case_mix']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
