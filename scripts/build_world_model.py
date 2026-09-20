from __future__ import annotations

from argparse import ArgumentParser
import json
import os
from pathlib import Path

from commons.world_model import OpenMeteoClient, build_snapshot, load_fixture


def parse_args():
    parser = ArgumentParser(description="Build the COMMONS World Model v0 snapshot.")
    parser.add_argument(
        "--output",
        default="public/world-model/latest.json",
        help="Output JSON path.",
    )
    parser.add_argument(
        "--fixture",
        default=None,
        help="Optional fixture JSON for deterministic/offline builds.",
    )
    parser.add_argument(
        "--commercial",
        action="store_true",
        help="Require commercial-safe provider configuration.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    commercial = args.commercial or os.getenv("COMMONS_COMMERCIAL_MODE", "0") == "1"

    if args.fixture:
        client = load_fixture(args.fixture)
    else:
        client = OpenMeteoClient(commercial=commercial)

    snapshot = build_snapshot(client)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "ok",
                "output": str(output),
                "generated_at": snapshot["generated_at"],
                "loops": len(snapshot["loops"]),
                "commercial_mode": commercial,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
