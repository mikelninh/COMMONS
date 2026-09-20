from __future__ import annotations

from argparse import ArgumentParser
import json
from pathlib import Path

from commons.deep_miss_lab import run_deep_miss_killer


def main() -> int:
    parser = ArgumentParser(description="Run H23 deep-miss recovery experiments.")
    parser.add_argument(
        "--miss-report",
        default="public/world-model/miss-report.json",
    )
    parser.add_argument(
        "--output",
        default="public/world-model/deep-miss-report.json",
    )
    args = parser.parse_args()

    miss_report = json.loads(Path(args.miss_report).read_text(encoding="utf-8"))
    report = run_deep_miss_killer(miss_report)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    h = report["hypothesis"]
    print("H23 Deep Miss Killer")
    print(h["status"].upper(), h["effect"])
    print("update:", h["product_update"])
    print("live semantics:", report["live_semantics_correction"])
    print("failure taxonomy:", report["failure_taxonomy"]["counts"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
