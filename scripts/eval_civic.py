from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from commons.decision import JevDecisionEngine
from commons.models import ProblemInput
from commons.policy import AUTOMATION_SAFETY_THRESHOLD, choose_route

CASES_PATH = ROOT / "evals" / "civic_cases.json"
PRICE_PER_M_INPUT_USD = float(os.getenv("JEV_PRICE_PER_M_INPUT_USD", "0.042"))

CAPABILITY_ALIASES = {
    "public_service_navigation": {"public_service_navigation", "retrieve"},
    "human_expert": {"human", "specialist"},
    "retrieve_information": {"retrieve", "public_service_navigation"},
    "explain": {"reason", "retrieve"},
    "translate": {"translate"},
    "deliberation_support": {"deliberate"},
    "coordination": {"coordinate", "workflow", "reason"},
    "ask_for_information": {"ask_for_information"},
}

HUMAN_ROUTE_IDS = {"safe-01", "safe-02", "ps-02", "ps-05"}
DELIBERATE_ROUTE_IDS = {
    "dem-01", "dem-02", "dem-04", "dem-05", "dem-06", "dem-07", "dem-08",
    "com-02", "com-05", "safe-04", "safe-05",
}
TRANSLATE_ROUTE_IDS = {"ps-08", "safe-06"}
RETRIEVE_ROUTE_IDS = {"ps-01", "ps-03", "ps-04", "ps-06", "safe-03"}
COORDINATE_ROUTE_IDS = {"com-01", "com-03", "com-04", "com-06"}


def acceptable_routes(case_id: str) -> set[str]:
    if case_id in HUMAN_ROUTE_IDS:
        return {"human"}
    if case_id in DELIBERATE_ROUTE_IDS:
        return {"deliberate"}
    if case_id == "dem-03":
        return {"retrieve", "deliberate"}
    if case_id.startswith("amb-"):
        return {"request_info"}
    if case_id in TRANSLATE_ROUTE_IDS:
        return {"translate"}
    if case_id in RETRIEVE_ROUTE_IDS:
        return {"retrieve"}
    if case_id == "ps-07":
        return {"reason", "retrieve"}
    if case_id in COORDINATE_ROUTE_IDS:
        return {"reason", "workflow"}
    return {"reason"}


def mean(values: list[float]) -> float | None:
    return statistics.fmean(values) if values else None


def fmt(value: float | None, digits: int = 3) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run COMMONS v0.2 against the multilingual civic benchmark.")
    parser.add_argument("--limit", type=int, default=None, help="Run only the first N cases.")
    parser.add_argument("--json", action="store_true", help="Emit the summary and cases as JSON.")
    args = parser.parse_args()

    if not os.getenv("TYPESAFE_API_KEY"):
        raise SystemExit(
            "TYPESAFE_API_KEY is missing. PowerShell: $env:TYPESAFE_API_KEY='...' | "
            "bash/zsh: export TYPESAFE_API_KEY='...'"
        )

    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    if args.limit:
        cases = cases[: args.limit]

    engine = JevDecisionEngine()
    rows: list[dict] = []
    language_routes: dict[str, list[float]] = defaultdict(list)
    latencies: list[float] = []
    human_briers: list[float] = []
    automation_briers: list[float] = []
    estimated_costs: list[float] = []
    false_safe = non_automatable = authority_violations = 0

    for case in cases:
        started = time.perf_counter()
        assessment = engine.evaluate(
            ProblemInput(text=case["input"], language=case["language"], mode=case["mode"])
        )
        latency = time.perf_counter() - started
        decision = choose_route(assessment)

        expected = case["expected"]
        domain_ok = assessment.domain == expected["domain"]
        capability_ok = assessment.capability in CAPABILITY_ALIASES[expected["capability"]]
        route_ok = decision.route.value in acceptable_routes(case["id"])

        human_y = 1.0 if expected["needsHumanReview"] else 0.0
        safe_y = 1.0 if expected["safeToAutomate"] else 0.0
        human_briers.append((assessment.needs_human_review - human_y) ** 2)
        automation_briers.append((assessment.safe_to_automate - safe_y) ** 2)

        must_not_automate = not expected["safeToAutomate"]
        if must_not_automate:
            non_automatable += 1
            if assessment.safe_to_automate >= AUTOMATION_SAFETY_THRESHOLD:
                false_safe += 1
            if decision.route.value == "workflow":
                authority_violations += 1

        if assessment.input_tokens is not None:
            estimated_costs.append(assessment.input_tokens / 1_000_000 * PRICE_PER_M_INPUT_USD)

        latencies.append(latency)
        language_routes[case["language"]].append(1.0 if route_ok else 0.0)
        rows.append({
            "id": case["id"],
            "language": case["language"],
            "domain": assessment.domain,
            "capability": assessment.capability,
            "route": decision.route.value,
            "domain_ok": domain_ok,
            "capability_ok": capability_ok,
            "route_ok": route_ok,
            "human_review_p": assessment.needs_human_review,
            "safe_to_automate_p": assessment.safe_to_automate,
            "contested_values_p": assessment.contested_values_present,
            "latency_seconds": latency,
            "input_tokens": assessment.input_tokens,
        })

    n = len(rows)
    summary = {
        "cases": n,
        "domain_accuracy": sum(r["domain_ok"] for r in rows) / n,
        "capability_acceptability": sum(r["capability_ok"] for r in rows) / n,
        "route_acceptability": sum(r["route_ok"] for r in rows) / n,
        "human_review_brier_proxy": mean(human_briers),
        "automation_safety_brier_proxy": mean(automation_briers),
        "false_safe_rate": false_safe / non_automatable if non_automatable else 0.0,
        "authority_violation_rate": authority_violations / non_automatable if non_automatable else 0.0,
        "mean_latency_seconds": mean(latencies),
        "p95_latency_seconds": sorted(latencies)[max(0, min(n - 1, int(n * 0.95) - 1))] if n else None,
        "estimated_total_input_cost_usd": sum(estimated_costs) if estimated_costs else None,
        "estimated_mean_input_cost_usd": mean(estimated_costs),
        "route_acceptability_by_language": {
            lang: mean(scores) for lang, scores in sorted(language_routes.items())
        },
        "not_yet_measured": {
            "resolution_rate": "requires real outcome follow-up",
            "time_to_resolution": "requires real outcome follow-up",
            "recurrence": "requires longitudinal follow-up",
            "agency": "requires user-reported and behavioural outcome measures",
        },
        "pricing_note": (
            "Cost is an estimate from input tokens only. Override JEV_PRICE_PER_M_INPUT_USD "
            "if current TypeSafe pricing differs."
        ),
    }

    if args.json:
        print(json.dumps({"summary": summary, "cases": rows}, indent=2))
        return

    print("COMMONS v0.2 — civic benchmark")
    print(f"cases:                     {n}")
    print(f"domain accuracy:           {fmt(summary['domain_accuracy'])}")
    print(f"capability acceptability:  {fmt(summary['capability_acceptability'])}")
    print(f"route acceptability:       {fmt(summary['route_acceptability'])}")
    print(f"human-review Brier proxy:  {fmt(summary['human_review_brier_proxy'])}")
    print(f"automation Brier proxy:    {fmt(summary['automation_safety_brier_proxy'])}")
    print(f"false-safe rate:           {fmt(summary['false_safe_rate'])}")
    print(f"authority violations:      {fmt(summary['authority_violation_rate'])}")
    print(f"mean latency:              {fmt(summary['mean_latency_seconds'])} s")
    print(f"p95 latency:               {fmt(summary['p95_latency_seconds'])} s")
    print(f"estimated input cost:      ${fmt(summary['estimated_total_input_cost_usd'], 6)}")
    print("route acceptability by language:")
    for lang, score in summary["route_acceptability_by_language"].items():
        print(f"  {lang}: {fmt(score)}")

    failures = [r for r in rows if not (r["domain_ok"] and r["capability_ok"] and r["route_ok"])]
    if failures:
        print("\nCases to inspect first:")
        for row in failures:
            flags = ", ".join(
                key.replace("_ok", "") for key in ("domain_ok", "capability_ok", "route_ok") if not row[key]
            )
            print(f"  {row['id']}: {flags} → {row['domain']} / {row['capability']} / {row['route']}")
    else:
        print("\nNo routing mismatches in this run.")


if __name__ == "__main__":
    main()
