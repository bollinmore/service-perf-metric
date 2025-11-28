from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.lib.path_utils import ValidationError
from src.services.visualization import fetch_latest_outputs


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download comparison output.")
    parser.add_argument("--data-folder", required=True, help="Path to data folder (version pool).")
    parser.add_argument(
        "--file",
        choices=["summary", "summary_stats", "service_stats"],
        default="summary",
        help="Which comparison output to download.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        outputs = fetch_latest_outputs(Path(args.data_folder))
    except ValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    target = outputs[args.file]
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
