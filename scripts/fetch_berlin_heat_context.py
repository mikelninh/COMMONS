from __future__ import annotations

import argparse
import json
from pathlib import Path

from commons.berlin_heat_context import (
    fetch_context,
    run_cross_domain_heat,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build one official cross-domain Berlin heat "
            "decision-support snapshot."
        )
    )
    parser.add_argument(
        "--lon",
        type=float,
        default=13.4132,
    )
    parser.add_argument(
        "--lat",
        type=float,
        default=52.5219,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "public/data/semantic-city/"
            "berlin-heat-context.json"
        ),
    )
    args = parser.parse_args()

    context = fetch_context(
        longitude=args.lon,
        latitude=args.lat,
    )
    payload = run_cross_domain_heat(context)
    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    args.output.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        "CROSS_DOMAIN_HEAT="
        + json.dumps(
            {
                "planning_area": (
                    context.justice.planning_area_name
                ),
                "multiple_burden": (
                    context.justice.multiple_burden
                ),
                "bioclimate": (
                    context.justice.bioclimate
                ),
                "green_provision": (
                    context.justice.green_provision
                ),
                "nearest_green": {
                    "name": context.nearest_green.name,
                    "distance_m": (
                        context.nearest_green.distance_m
                    ),
                },
                "nearest_hospital": {
                    "name": (
                        context.nearest_hospital.name
                    ),
                    "distance_m": (
                        context.nearest_hospital.distance_m
                    ),
                },
                "validation": payload["validation"],
                "triples": payload[
                    "graph_stats"
                ]["triples"],
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
