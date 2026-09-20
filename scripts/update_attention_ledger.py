from __future__ import annotations

from argparse import ArgumentParser
import json
from pathlib import Path

from commons.attention_ledger import load_ledger, update_attention_ledger


def main() -> int:
    parser = ArgumentParser(description="Update the COMMONS live attention outcome ledger.")
    parser.add_argument("--brief", required=True)
    parser.add_argument("--ledger", required=True)
    args = parser.parse_args()

    brief = json.loads(Path(args.brief).read_text(encoding="utf-8"))
    ledger = load_ledger(args.ledger)
    ledger = update_attention_ledger(brief, ledger)

    output = Path(args.ledger)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(ledger, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": "ok", **ledger["summary"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
