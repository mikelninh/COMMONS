from __future__ import annotations

import argparse
import json
from pathlib import Path

from commons.berlin_heat_wfs import fetch_record, run_official_heat


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch one official Berlin climate WFS record and transform it through Semantic City.")
    parser.add_argument("--lon", type=float, default=13.4132)
    parser.add_argument("--lat", type=float, default=52.5219)
    parser.add_argument("--radius-m", type=float, default=20.0)
    parser.add_argument("--output", type=Path, default=Path("public/data/semantic-city/berlin-heat-latest.json"))
    parser.add_argument("--strict-point", action="store_true")
    args = parser.parse_args()

    record = fetch_record(longitude=args.lon, latitude=args.lat, radius_m=args.radius_m)
    if args.strict_point and record.match_mode != "point_bbox":
        raise SystemExit(f"Expected point_bbox match, got {record.match_mode}")

    payload = {
        "status": "official_structural_record",
        "truth_boundary": (
            "Fetched live from Berlin's official WFS, but the underlying Klimaanalysekarten 2022 "
            "are structural modeled evidence for a representative summer day, not current weather."
        ),
        "record": record.to_dict(),
        "scenario": run_official_heat(record),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("OFFICIAL_RECORD_JSON=" + json.dumps({
        "feature_type": record.feature_type,
        "feature_id": record.feature_id,
        "match_mode": record.match_mode,
        "properties": record.properties,
        "retrieved_at": record.retrieved_at,
        "validation": payload["scenario"]["validation"],
    }, ensure_ascii=False, separators=(",", ":")))
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
