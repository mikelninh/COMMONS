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

    revision_path = Path("public/world-model/revision-report.json")
    if revision_path.exists():
        revision = json.loads(revision_path.read_text(encoding="utf-8"))
        for item in revision.get("hypotheses", []):
            report["hypotheses"] = [
                existing
                for existing in report["hypotheses"]
                if existing.get("id") != item.get("id")
            ]
            report["hypotheses"].append(
                {
                    "id": item.get("id"),
                    "claim": item.get("claim"),
                    "status": item.get("status"),
                    "effect": item.get("effect"),
                    "update": item.get("product_update"),
                }
            )
        report.setdefault("headline_metrics", {})
        summary = revision.get("summary") or {}
        report["headline_metrics"]["h8_persistent_direction_accuracy_pct"] = (
            round(100 * summary.get("persistent_direction_accuracy"), 1)
            if summary.get("persistent_direction_accuracy") is not None
            else None
        )
        report["headline_metrics"]["h9_majority_direction_accuracy_pct"] = (
            round(100 * summary.get("majority_direction_accuracy"), 1)
            if summary.get("majority_direction_accuracy") is not None
            else None
        )

    river_path = Path("public/world-model/river-attention-report.json")
    if river_path.exists():
        river = json.loads(river_path.read_text(encoding="utf-8"))
        h10 = river.get("hypothesis") or {}
        if h10.get("id") == "H10":
            report["hypotheses"] = [
                existing
                for existing in report["hypotheses"]
                if existing.get("id") != "H10"
            ]
            report["hypotheses"].append(
                {
                    "id": "H10",
                    "claim": h10.get("claim"),
                    "status": h10.get("status"),
                    "effect": (
                        f"mean AUC gain {h10.get('mean_auc_gain')}; "
                        f"mean precision gain {h10.get('mean_precision_gain_pct')}%"
                    ),
                    "update": h10.get("product_update"),
                }
            )
            report.setdefault("headline_metrics", {})
            report["headline_metrics"]["h10_mean_auc_gain"] = h10.get("mean_auc_gain")
            report["headline_metrics"]["h10_mean_precision_gain_pct"] = h10.get(
                "mean_precision_gain_pct"
            )

    report["next_hypotheses"] = [
        {
            "id": "H7",
            "claim": "Basin-context rainfall outperforms a single point for river-risk estimation.",
            "signals": ["center point", "surrounding grid", "GloFAS discharge"],
            "test": "Compare point rainfall with spatially averaged upstream rainfall.",
        },
        {
            "id": "H11",
            "claim": "We can predict which basins benefit from antecedent-wetness features.",
            "signals": ["basin climate", "wetness skill", "river-response lag"],
            "test": "Cluster basin regimes and validate wetness features out-of-sample.",
        },
        {
            "id": "H12",
            "claim": "A material-change rule can beat fixed hazard thresholds on useful-alert precision.",
            "signals": ["validated revisions", "river percentile", "horizon skill"],
            "test": "Compare rule precision, miss rate and lead time against fixed percentile alerts.",
        },
        {
            "id": "H13",
            "claim": "Adding exposure changes which physical hazards deserve human attention first.",
            "signals": ["population", "settlements", "critical infrastructure", "hazard state"],
            "test": "Compare hazard-only ranking with exposure-aware ranking against historical impact records.",
        },
        {
            "id": "H14",
            "claim": "Official warning changes provide a useful external benchmark for COMMONS attention changes.",
            "signals": ["official warnings", "COMMONS change signals", "timing"],
            "test": "Measure agreement, earlier/later detection and false alarms without treating official warnings as perfect ground truth.",
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
