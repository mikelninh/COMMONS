from __future__ import annotations

from argparse import ArgumentParser
from datetime import date, timedelta
import json
from pathlib import Path

from commons.hypothesis_lab import POINTS, run_backtest, save_report


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
        points=POINTS[:3],
    )

    hydro_path = Path("public/world-model/hydrology-report.json")
    if hydro_path.exists():
        hydro = json.loads(hydro_path.read_text(encoding="utf-8"))
        h6 = hydro.get("hypothesis") or {}
        if h6.get("id") == "H6":
            report["hypotheses"] = [
                item for item in report["hypotheses"] if item.get("id") != "H6"
            ]
            report["hypotheses"].append(
                {
                    "id": "H6",
                    "claim": h6.get("claim"),
                    "status": h6.get("status"),
                    "effect": (
                        f"mean AUC gain {h6.get('mean_auc_gain')}; "
                        f"mean precision gain {h6.get('mean_precision_gain_pct')}%"
                    ),
                    "update": h6.get("product_update"),
                }
            )
            report.setdefault("headline_metrics", {})
            report["headline_metrics"]["h6_mean_auc_gain"] = h6.get("mean_auc_gain")
            report["headline_metrics"]["h6_mean_precision_gain_pct"] = h6.get(
                "mean_precision_gain_pct"
            )
            report["headline_metrics"]["h6_basin_results"] = {
                item["id"]: {
                    "auc_gain": item.get("auc_gain_vs_recent_rain"),
                    "precision_gain_pct": item.get(
                        "precision_gain_vs_recent_rain_pct"
                    ),
                }
                for item in hydro.get("points", [])
            }

    report["next_hypotheses"] = [
        {
            "id": "H7",
            "claim": "Basin-context rainfall outperforms a single point for river-risk estimation.",
            "signals": ["center point", "surrounding grid", "GloFAS discharge"],
            "test": "Compare point rainfall vs spatially averaged rainfall.",
        },
        {
            "id": "H8",
            "claim": "A forecast revision sustained across multiple runs is more useful than a one-run jump.",
            "signals": ["6-hour archived snapshots", "forecast deltas", "later verification"],
            "test": "Compare one-run changes with 2- and 3-run persistent changes.",
        },
        {
            "id": "H9",
            "claim": "Direction agreement is more useful than raw spread.",
            "signals": ["model revision direction", "later ERA5 precipitation"],
            "test": "Compare 2/3 models revising upward with raw disagreement magnitude.",
        },
        {
            "id": "H10",
            "claim": "River percentile plus validated basin context can produce a low-false-alarm attention rule.",
            "signals": ["river percentile", "basin skill", "later discharge"],
            "test": "Optimize precision, miss rate and lead time without human-impact labels.",
        },
        {
            "id": "H11",
            "claim": "We can predict where catchment wetness is useful enough to include.",
            "signals": ["basin climate", "wetness skill", "river-response lag"],
            "test": "Cluster basins by regime and validate wetness features out-of-sample.",
        },
    ]

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
