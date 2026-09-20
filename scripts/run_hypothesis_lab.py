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

    # Keep one stable public schema even when individual research modules use
    # the internal key name "product_update".
    for hypothesis in report.get("hypotheses", []):
        if "update" not in hypothesis and "product_update" in hypothesis:
            hypothesis["update"] = hypothesis.pop("product_update")

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

    attention_path = Path("public/world-model/attention-rule-report.json")
    if attention_path.exists():
        attention = json.loads(attention_path.read_text(encoding="utf-8"))
        h12 = attention.get("hypothesis") or {}
        if h12.get("id") == "H12":
            report["hypotheses"] = [
                existing
                for existing in report["hypotheses"]
                if existing.get("id") != "H12"
            ]
            report["hypotheses"].append(
                {
                    "id": "H12",
                    "claim": h12.get("claim"),
                    "status": h12.get("status"),
                    "effect": (
                        f"F1 gain {h12.get('f1_gain_vs_strict')}; "
                        f"recall gain {h12.get('recall_gain_vs_strict')}; "
                        f"precision change {h12.get('precision_change_vs_strict')}; "
                        f"lead gain {h12.get('lead_gain_days_vs_strict')}d"
                    ),
                    "update": h12.get("product_update"),
                }
            )
            report.setdefault("headline_metrics", {})
            policies = attention.get("policies") or {}
            report["headline_metrics"]["h12_strict_f1"] = (
                policies.get("strict") or {}
            ).get("f1")
            report["headline_metrics"]["h12_revision_f1"] = (
                policies.get("revision_aware") or {}
            ).get("f1")
            report["headline_metrics"]["h12_revision_recall"] = (
                policies.get("revision_aware") or {}
            ).get("recall")
            report["headline_metrics"]["h12_revision_precision"] = (
                policies.get("revision_aware") or {}
            ).get("precision")

    watch_path = Path("public/world-model/watch-alert-report.json")
    if watch_path.exists():
        watch = json.loads(watch_path.read_text(encoding="utf-8"))
        h15 = watch.get("hypothesis") or {}
        if h15.get("id") == "H15":
            report["hypotheses"] = [
                existing
                for existing in report["hypotheses"]
                if existing.get("id") != "H15"
            ]
            report["hypotheses"].append(
                {
                    "id": "H15",
                    "claim": h15.get("claim"),
                    "status": h15.get("status"),
                    "effect": (
                        f"alert recall {watch.get('alert_recall')}; "
                        f"watch recall {watch.get('watch_recall')}; "
                        f"watch-only precision {watch.get('watch_only_precision')}; "
                        f"burden {watch.get('watch_burden_per_100_days')}/100d"
                    ),
                    "update": h15.get("product_update"),
                }
            )
            report.setdefault("headline_metrics", {})
            report["headline_metrics"]["h15_alert_recall"] = watch.get("alert_recall")
            report["headline_metrics"]["h15_watch_recall"] = watch.get("watch_recall")
            report["headline_metrics"]["h15_watch_burden_per_100_days"] = watch.get(
                "watch_burden_per_100_days"
            )

    watch_value_path = Path("public/world-model/watch-value-report.json")
    if watch_value_path.exists():
        watch_value = json.loads(watch_value_path.read_text(encoding="utf-8"))
        h17 = watch_value.get("hypothesis") or {}
        if h17.get("id") == "H17":
            report["hypotheses"] = [
                existing
                for existing in report["hypotheses"]
                if existing.get("id") != "H17"
            ]
            report["hypotheses"].append(
                {
                    "id": "H17",
                    "claim": h17.get("claim"),
                    "status": h17.get("status"),
                    "effect": h17.get("effect"),
                    "update": h17.get("product_update"),
                }
            )
            report.setdefault("headline_metrics", {})
            report["headline_metrics"]["h17_revision_up_heavy_rate"] = (
                watch_value.get("revision_up") or {}
            ).get("heavy_event_rate")
            report["headline_metrics"]["h17_revision_not_up_heavy_rate"] = (
                watch_value.get("revision_not_up") or {}
            ).get("heavy_event_rate")
            report["headline_metrics"]["h17_heavy_rate_lift"] = watch_value.get(
                "heavy_event_rate_lift"
            )

    budget_path = Path("public/world-model/attention-budget-report.json")
    if budget_path.exists():
        budget = json.loads(budget_path.read_text(encoding="utf-8"))
        h18 = budget.get("hypothesis") or {}
        if h18.get("id") == "H18":
            report["hypotheses"] = [
                existing
                for existing in report["hypotheses"]
                if existing.get("id") != "H18"
            ]
            report["hypotheses"].append(
                {
                    "id": "H18",
                    "claim": h18.get("claim"),
                    "status": h18.get("status"),
                    "effect": h18.get("effect"),
                    "update": h18.get("product_update"),
                }
            )
            comparison = budget.get("comparison") or {}
            report.setdefault("headline_metrics", {})
            report["headline_metrics"]["h18_average_precision_gain"] = comparison.get(
                "average_precision_gain"
            )
            report["headline_metrics"]["h18_ndcg_gain"] = comparison.get("ndcg_gain")
            report["headline_metrics"]["h18_improved_budgets"] = comparison.get(
                "improved_budgets"
            )

    dropout_path = Path("public/world-model/model-dropout-report.json")
    if dropout_path.exists():
        dropout = json.loads(dropout_path.read_text(encoding="utf-8"))
        h19 = dropout.get("hypothesis") or {}
        if h19.get("id") == "H19":
            report["hypotheses"] = [
                existing
                for existing in report["hypotheses"]
                if existing.get("id") != "H19"
            ]
            report["hypotheses"].append(
                {
                    "id": "H19",
                    "claim": h19.get("claim"),
                    "status": h19.get("status"),
                    "effect": h19.get("effect"),
                    "update": h19.get("product_update"),
                }
            )
            summary = dropout.get("summary") or {}
            report.setdefault("headline_metrics", {})
            report["headline_metrics"]["h19_min_top_k_retention"] = summary.get(
                "min_top_k_retention"
            )
            report["headline_metrics"]["h19_min_alert_agreement"] = summary.get(
                "min_alert_agreement"
            )
            report["headline_metrics"]["h19_max_heavy_event_catch_loss"] = summary.get(
                "max_heavy_event_catch_loss"
            )

    scale_path = Path("public/world-model/scale-report.json")
    if scale_path.exists():
        scale = json.loads(scale_path.read_text(encoding="utf-8"))
        h20 = scale.get("hypothesis") or {}
        if h20.get("id") == "H20":
            report["hypotheses"] = [
                item for item in report["hypotheses"] if item.get("id") != "H20"
            ]
            report["hypotheses"].append(
                {
                    "id": "H20",
                    "claim": h20.get("claim"),
                    "status": h20.get("status"),
                    "effect": h20.get("effect"),
                    "update": h20.get("product_update"),
                }
            )
            report.setdefault("headline_metrics", {})
            report["headline_metrics"]["h20_council_win_rate"] = (
                scale.get("summary") or {}
            ).get("council_win_rate")
            report["headline_metrics"]["h20_median_improvement_pct"] = (
                scale.get("summary") or {}
            ).get("median_improvement_pct")

    miss_path = Path("public/world-model/miss-report.json")
    if miss_path.exists():
        miss = json.loads(miss_path.read_text(encoding="utf-8"))
        h21 = miss.get("hypothesis") or {}
        if h21.get("id") == "H21":
            report["hypotheses"] = [
                item for item in report["hypotheses"] if item.get("id") != "H21"
            ]
            report["hypotheses"].append(
                {
                    "id": "H21",
                    "claim": h21.get("claim"),
                    "status": h21.get("status"),
                    "effect": h21.get("effect"),
                    "update": h21.get("product_update"),
                }
            )
            report.setdefault("headline_metrics", {})
            report["headline_metrics"]["h21_misses"] = miss.get("misses")
            report["headline_metrics"]["h21_near_threshold_share"] = miss.get(
                "near_threshold_share"
            )

    exposure_path = Path("public/world-model/exposure-report.json")
    if exposure_path.exists():
        exposure = json.loads(exposure_path.read_text(encoding="utf-8"))
        h13 = exposure.get("hypothesis") or {}
        if h13.get("id") == "H13":
            report["hypotheses"] = [
                item for item in report["hypotheses"] if item.get("id") != "H13"
            ]
            report["hypotheses"].append(
                {
                    "id": "H13",
                    "claim": h13.get("claim"),
                    "status": h13.get("status"),
                    "effect": h13.get("effect"),
                    "update": h13.get("product_update"),
                }
            )
            report.setdefault("headline_metrics", {})
            report["headline_metrics"]["h13_exposure_usable_points"] = exposure.get(
                "usable_points"
            )
            report["headline_metrics"]["h13_exposure_coverage_status"] = exposure.get(
                "coverage_status"
            )

    external_path = Path("public/world-model/external-alert-report.json")
    if external_path.exists():
        external = json.loads(external_path.read_text(encoding="utf-8"))
        h22 = external.get("hypothesis") or {}
        if h22.get("id") == "H22":
            report["hypotheses"] = [
                item for item in report["hypotheses"] if item.get("id") != "H22"
            ]
            report["hypotheses"].append(
                {
                    "id": "H22",
                    "claim": h22.get("claim"),
                    "status": h22.get("status"),
                    "effect": h22.get("effect"),
                    "update": h22.get("product_update"),
                }
            )
            report.setdefault("headline_metrics", {})
            report["headline_metrics"]["h22_gdacs_matched_point_days"] = external.get(
                "matched_point_days"
            )
            report["headline_metrics"]["h22_gdacs_overlap_rate"] = external.get(
                "overlap_rate"
            )

    deep_miss_path = Path("public/world-model/deep-miss-report.json")
    if deep_miss_path.exists():
        deep_miss = json.loads(deep_miss_path.read_text(encoding="utf-8"))
        h23 = deep_miss.get("hypothesis") or {}
        if h23.get("id") == "H23":
            report["hypotheses"] = [
                item for item in report["hypotheses"] if item.get("id") != "H23"
            ]
            report["hypotheses"].append(
                {
                    "id": "H23",
                    "claim": h23.get("claim"),
                    "status": h23.get("status"),
                    "effect": h23.get("effect"),
                    "update": h23.get("product_update"),
                }
            )
            report.setdefault("headline_metrics", {})
            test = deep_miss.get("test") or {}
            selected = test.get("selected") or {}
            comparison = test.get("comparison") or {}
            semantics = deep_miss.get("live_semantics_correction") or {}
            report["headline_metrics"]["h23_selected_strategy"] = test.get(
                "selected_strategy"
            )
            report["headline_metrics"]["h23_deep_miss_recovery_rate"] = selected.get(
                "deep_miss_recovery_rate"
            )
            report["headline_metrics"]["h23_incremental_false_alerts_per_100"] = comparison.get(
                "incremental_false_alerts_per_100"
            )
            report["headline_metrics"]["h23_precision_change"] = comparison.get(
                "precision_change"
            )
            report["headline_metrics"]["h23_live_window_resolved_exact_day_deep"] = semantics.get(
                "no_longer_deep_under_live_72h_window"
            )

    minority_convective_path = Path("public/world-model/minority-convective-report.json")
    if minority_convective_path.exists():
        minority_convective = json.loads(
            minority_convective_path.read_text(encoding="utf-8")
        )
        for section_key in ("h24", "h25"):
            section = minority_convective.get(section_key) or {}
            hypothesis = section.get("hypothesis") or {}
            hypothesis_id = hypothesis.get("id")
            if not hypothesis_id:
                continue
            report["hypotheses"] = [
                item
                for item in report["hypotheses"]
                if item.get("id") != hypothesis_id
            ]
            report["hypotheses"].append(
                {
                    "id": hypothesis_id,
                    "claim": hypothesis.get("claim"),
                    "status": hypothesis.get("status"),
                    "effect": hypothesis.get("effect"),
                    "update": hypothesis.get("product_update"),
                }
            )

        report.setdefault("headline_metrics", {})
        h24 = minority_convective.get("h24") or {}
        h24_test = h24.get("test") or {}
        report["headline_metrics"]["h24_selected_rule"] = h24_test.get(
            "selected_rule"
        ) or (h24.get("development") or {}).get("selected_rule")
        report["headline_metrics"]["h24_deep_miss_recovery_rate"] = (
            (h24_test.get("selected") or {}).get("target_recovery_rate")
        )
        report["headline_metrics"]["h24_incremental_false_alerts_per_100"] = (
            (h24_test.get("comparison") or {}).get(
                "incremental_false_alerts_per_100"
            )
        )

        h25 = minority_convective.get("h25") or {}
        h25_test = h25.get("test") or {}
        report["headline_metrics"]["h25_selected_rule"] = h25_test.get(
            "selected_rule"
        ) or (h25.get("development") or {}).get("selected_rule")
        report["headline_metrics"]["h25_blind_miss_recovery_rate"] = (
            (h25_test.get("selected") or {}).get("target_recovery_rate")
        )
        report["headline_metrics"]["h25_blind_test_misses"] = (
            (h25_test.get("baseline") or {}).get("target_misses")
        )
        report["headline_metrics"]["h25_convective_evidence_status"] = (
            minority_convective.get("convective_evidence_health") or {}
        ).get("status")

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
            "id": "H14",
            "claim": "Source-specific official warning archives improve external validation beyond the global GDACS benchmark.",
            "signals": ["national warning archives", "COMMONS attention state", "timing", "geography"],
            "test": "Add authority-specific adapters where archive access is available; keep GDACS separate from official local warning ground truth.",
        },
        {
            "id": "H16",
            "claim": "A PRIORITY queue reduces analyst monitoring time without creating perceived noise.",
            "signals": ["priority rank", "alert state", "analyst actions", "time-to-orientation"],
            "test": "Run a human pilot measuring monitoring time, unnecessary reviews, useful catches and perceived noise.",
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
        print(f"  update: {hypothesis.get('update') or hypothesis.get('product_update')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
