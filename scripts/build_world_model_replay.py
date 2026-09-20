from __future__ import annotations

from argparse import ArgumentParser
import json
from pathlib import Path

from commons.world_model_replay import build_replay


def main() -> int:
    parser = ArgumentParser(description="Build a lightweight World Model replay file.")
    parser.add_argument("--snapshots", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--limit", type=int, default=48)
    args = parser.parse_args()

    replay = build_replay(Path(args.snapshots), limit=args.limit)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(replay, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"frames": replay["frame_count"], "output": str(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
