from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Sequence

from src.lib.path_utils import ValidationError
from src.services.comparison import run_comparison
from src.services.validation import require_exact_three


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run three-version comparison.")
    parser.add_argument(
        "--data-folder",
        required=True,
        help="Path to the data folder (version pool).",
    )
    parser.add_argument(
        "--versions",
        nargs="+",
        required=True,
        help="Exactly three distinct versions to compare.",
    )
    parser.add_argument(
        "--result-root",
        help="Optional result root override; defaults to project result directory.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.result_root:
        os.environ["SPM_RESULT_ROOT"] = str(Path(args.result_root).resolve())

    try:
        require_exact_three(args.versions)
        result = run_comparison(Path(args.data_folder), args.versions)
    except ValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
