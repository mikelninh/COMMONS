from __future__ import annotations

import argparse

from commons.models import ProblemInput
from commons.service import CommonsService


def main() -> None:
    parser = argparse.ArgumentParser(description="Route a real-world problem through COMMONS.")
    parser.add_argument("problem", help="Describe what you are trying to solve.")
    parser.add_argument("--language", default=None)
    args = parser.parse_args()

    record = CommonsService().assess(
        ProblemInput(text=args.problem, language=args.language)
    )
    print(record.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
