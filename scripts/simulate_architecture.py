from __future__ import annotations

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "evals" / "civic_cases.json").read_text(encoding="utf-8"))

VERSIONS = {
    "v0.2_judgment_only": {"route": .86, "completion": .38, "verification": .10, "safety": .975, "agency": .94, "hours": 18, "cost": .01, "recurrence": .34},
    "v0.3_evidence_capabilities": {"route": .90, "completion": .68, "verification": .62, "safety": .970, "agency": .92, "hours": 7, "cost": .09, "recurrence": .22},
    "v0.4_bounded_execution": {"route": .92, "completion": .84, "verification": .86, "safety": .965, "agency": .89, "hours": 2.5, "cost": .28, "recurrence": .14},
}
LANGUAGE_FACTOR = {"en": 1.0, "de": .98, "vi": .93}


def run(version: dict[str, float], rng: random.Random, trials: int = 5000) -> dict[str, float | int]:
    resolved = verified = safe = agency = repeated = 0
    total_hours = total_cost = brier = 0.0

    for _ in range(trials):
        case = rng.choice(CASES)
        ambiguous = case["id"].startswith("amb-")
        route_p = max(.5, version["route"] * LANGUAGE_FACTOR.get(case["language"], .95) * (.82 if ambiguous else 1))
        route_ok = rng.random() < route_p
        expected = case["expected"]
        needs_human = expected["needsHumanReview"]
        should_not_auto = not expected["safeToAutomate"]

        safety_p = version["safety"] - (.006 if should_not_auto else 0) - (.004 if needs_human else 0)
        safe_run = rng.random() < safety_p
        safe += int(safe_run)

        completion_p = version["completion"] if route_ok else version["completion"] * .16
        completed = rng.random() < completion_p
        outcome = completed and safe_run
        resolved += int(outcome)
        verified += int(outcome and rng.random() < version["verification"])

        agency_p = max(.6, version["agency"] - (.01 if needs_human else 0))
        agency += int(rng.random() < agency_p)
        repeated += int(outcome and rng.random() < version["recurrence"])

        total_hours += version["hours"] * (.7 + rng.random() * .6) * (1 if route_ok else 1.8)
        total_cost += version["cost"] * (1 if route_ok else 1.4)
        brier += (route_p - int(route_ok)) ** 2

    return {
        "trials": trials,
        "simulated_resolution_rate": resolved / trials,
        "verified_resolution_rate": verified / trials,
        "mean_time_to_resolution_hours": total_hours / trials,
        "mean_intelligence_cost_eur": total_cost / trials,
        "brier_route_calibration": brier / trials,
        "safety_rate": safe / trials,
        "agency_retention_rate": agency / trials,
        "recurrence_rate": repeated / max(1, resolved),
    }


def main() -> None:
    rng = random.Random(20260919)
    print("COMMONS architecture stress simulation")
    print("ASSUMPTIONS ARE ILLUSTRATIVE, NOT MEASURED JEV PERFORMANCE OR A FORECAST.\n")
    for name, version in VERSIONS.items():
        print(name)
        print(json.dumps(run(version, rng), indent=2))


if __name__ == "__main__":
    main()
