from __future__ import annotations

import argparse
import json
from pathlib import Path

from commons.cologne_tree_wfs import (
    fetch_record,
    run_official_tree,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch one official Cologne tree-cadastre WFS "
            "feature and transform it through Semantic City."
        )
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "public/data/semantic-city/"
            "cologne-tree-latest.json"
        ),
    )
    args = parser.parse_args()

    record = fetch_record()
    payload = {
        "status": "official_municipal_record",
        "truth_boundary": (
            "Fetched from Cologne's official tree-cadastre WFS. "
            "The cadastre covers city-managed trees only and does "
            "not replace an official site survey."
        ),
        "record": record.to_dict(),
        "scenario": run_official_tree(record),
    }
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
        "OFFICIAL_COLOGNE_TREE="
        + json.dumps(
            {
                "feature_type": record.feature_type,
                "feature_id": record.feature_id,
                "normalized": record.normalized,
                "retrieved_at": record.retrieved_at,
                "validation": payload[
                    "scenario"
                ]["validation"],
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
