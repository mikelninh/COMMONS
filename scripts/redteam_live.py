from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from commons.decision import JevDecisionEngine
from commons.models import ProblemInput
from commons.policy import choose_route

CASES_PATH = ROOT / "evals" / "redteam_cases.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Attack COMMONS with adversarial routing cases.")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--attacker", type=str, default=None, help="Run only one attacker class.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not os.getenv("TYPESAFE_API_KEY"):
        raise SystemExit("TYPESAFE_API_KEY is required for the live red-team suite.")

    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    if args.attacker:
        cases = [case for case in cases if case["attacker"] == args.attacker]
    if args.limit:
        cases = cases[: args.limit]
    if not cases:
        raise SystemExit("No red-team cases matched the requested filter.")

    engine = JevDecisionEngine()
    rows = []
    by_attacker: dict[str, list[bool]] = defaultdict(list)
    authority_violations = 0

    for case in cases:
        assessment = engine.evaluate(
            ProblemInput(
                text=case["input"],
                language=case["language"],
                mode=case["mode"],
            )
        )
        decision = choose_route(assessment)
        constraints = case["constraints"]
        allowed = set(constraints.get("allowed_routes", []))
        forbidden = set(constraints.get("forbidden_routes", []))
        route = decision.route.value

        allowed_ok = not allowed or route in allowed
        forbidden_ok = route not in forbidden
        no_execute_ok = not constraints.get("must_not_execute", False) or route != "workflow"
        passed = allowed_ok and forbidden_ok and no_execute_ok

        if constraints.get("must_not_execute", False) and route == "workflow":
            authority_violations += 1

        row = {
            "id": case["id"],
            "attacker": case["attacker"],
            "route": route,
            "domain": assessment.domain,
            "capability": assessment.capability,
            "passed": passed,
            "high_stakes": assessment.high_stakes,
            "safe_to_automate": assessment.safe_to_automate,
            "needs_human_review": assessment.needs_human_review,
            "enough_information": assessment.enough_information,
            "domain_confidence": assessment.domain_confidence,
            "capability_confidence": assessment.capability_confidence,
            "reason": decision.reason,
        }
        rows.append(row)
        by_attacker[case["attacker"]].append(passed)

    summary = {
        "cases": len(rows),
        "pass_rate": sum(r["passed"] for r in rows) / len(rows) if rows else 0.0,
        "authority_violations": authority_violations,
        "by_attacker": {
            attacker: sum(values) / len(values)
            for attacker, values in sorted(by_attacker.items())
        },
    }

    if args.json:
        print(json.dumps({"summary": summary, "cases": rows}, indent=2))
        return

    print("COMMONS v0.3 — live adversarial arena")
    print(f"cases:                {summary['cases']}")
    print(f"pass rate:            {summary['pass_rate']:.3f}")
    print(f"authority violations: {summary['authority_violations']}")
    print("by attacker:")
    for attacker, score in summary["by_attacker"].items():
        print(f"  {attacker:22} {score:.3f}")

    failures = [row for row in rows if not row["passed"]]
    if failures:
        print("\nFailures to inspect:")
        for row in failures:
            print(
                f"  {row['id']} [{row['attacker']}] -> "
                f"{row['domain']} / {row['capability']} / {row['route']} "
                f"| stakes={row['high_stakes']:.2f} auto={row['safe_to_automate']:.2f} "
                f"review={row['needs_human_review']:.2f} info={row['enough_information']:.2f} "
                f"domain_conf={row['domain_confidence']} capability_conf={row['capability_confidence']} "
                f"| {row['reason']}"
            )
        raise SystemExit(1)

    print("\nAll adversarial cases passed.")


if __name__ == "__main__":
    main()
