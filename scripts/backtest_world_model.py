from __future__ import annotations

from argparse import ArgumentParser
import json
from pathlib import Path

from commons.world_model_eval import score_loop_snapshot, summarize_scores


def parse_args():
    parser = ArgumentParser(description="Backtest archived COMMONS World Model forecasts.")
    parser.add_argument("--snapshot", required=True)
    parser.add_argument(
        "--observed",
        required=True,
        help="JSON mapping loop id to observed 72h summary metrics.",
    )
    parser.add_argument("--output", default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    observed = json.loads(Path(args.observed).read_text(encoding="utf-8"))

    results = []
    for loop in snapshot.get("loops") or []:
        if loop.get("id") not in observed:
            continue
        if not loop.get("forecast_council"):
            continue
        results.append(score_loop_snapshot(loop, observed[loop["id"]]))

    report = {
        "snapshot_generated_at": snapshot.get("generated_at"),
        "results": results,
        "summary": summarize_scores(results),
        "limitations": (
            "v0 scores deterministic point summaries only. "
            "Probability calibration, Brier score and CRPS require ensemble forecasts."
        ),
    }
    encoded = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        Path(args.output).write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
