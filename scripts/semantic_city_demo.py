from __future__ import annotations

import argparse
import json

from commons.semantic_city import (
    export_turtle,
    list_scenarios,
    run_scenario,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the COMMONS Semantic City demo fixture."
    )
    parser.add_argument(
        "--scenario",
        choices=[item["id"] for item in list_scenarios()],
        default="heat",
    )
    parser.add_argument(
        "--format",
        choices=["json", "turtle"],
        default="json",
    )
    args = parser.parse_args()

    if args.format == "turtle":
        print(export_turtle())
        return

    print(
        json.dumps(
            run_scenario(args.scenario).to_dict(),
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
