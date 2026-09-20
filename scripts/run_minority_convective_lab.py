from __future__ import annotations

from argparse import ArgumentParser
import json
from pathlib import Path

from commons.minority_convective_lab import run_minority_convective_lab


def main() -> int:
    parser = ArgumentParser(description="Run H24/H25 minority trust and convective blindness tests.")
    parser.add_argument("--miss-report", default="public/world-model/miss-report.json")
    parser.add_argument("--output", default="public/world-model/minority-convective-report.json")
    args = parser.parse_args()

    miss_report = json.loads(Path(args.miss_report).read_text(encoding="utf-8"))
    report = run_minority_convective_lab(miss_report)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    for key in ("h24", "h25"):
        h = report[key]["hypothesis"]
        print(h["id"], h["status"].upper(), h["effect"])
        print("update:", h["product_update"])
    print("convective health:", report["convective_evidence_health"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
