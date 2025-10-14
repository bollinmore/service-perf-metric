from __future__ import annotations

import argparse
import csv
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = BASE_DIR / "data"
DEFAULT_RESULT_DIR = BASE_DIR / "result"


def result_root_for_data(data_root: Path) -> Path:
    """Return the result directory that corresponds to the given data folder."""
    return DEFAULT_RESULT_DIR / data_root.name


# Allow imports from src.*
sys.path.insert(0, str(BASE_DIR))

try:
    from src import extract
except ModuleNotFoundError as exc:  # pragma: no cover - import guard
    raise SystemExit(f"Failed to import project modules: {exc}") from exc


def _resolve_path(path_str: str, default: Path) -> Path:
    """Resolve a user-supplied path against the project root when relative."""
    raw = Path(path_str) if path_str else default
    return raw if raw.is_absolute() else (BASE_DIR / raw)


def clean_results(result_dir: Path) -> None:
    """Remove the entire result directory."""
    if not result_dir.exists():
        print(f"[clean] Nothing to remove at {result_dir}")
        return
    shutil.rmtree(result_dir)
    print(f"[clean] Removed {result_dir}")


def _collect_log_dirs(data_root: Path) -> List[Tuple[str, Path]]:
    """Return list of (dataset_name, log_dir) pairs under the data root."""
    datasets: List[Tuple[str, Path]] = []
    if not data_root.exists():
        raise FileNotFoundError(f"Data folder not found: {data_root}")

    for candidate in sorted(data_root.iterdir()):
        if not candidate.is_dir():
            continue
        # Prefer a direct PerformanceLog folder, but fall back to any child match
        log_dir = candidate / "PerformanceLog"
        if log_dir.is_dir():
            datasets.append((candidate.name, log_dir))
            continue
        matching = list(candidate.rglob("PerformanceLog"))
        if matching:
            datasets.append((candidate.name, matching[0]))
    return datasets


def _determine_pattern(log_dir: Path) -> str:
    """Pick a glob pattern for log files, skipping login logs when possible."""
    loading_logs = list(log_dir.glob("*loading.log"))
    if loading_logs:
        return "*loading.log"
    return "*.log"


def _combine_summaries(summary_map: Dict[str, Path], output_path: Path) -> None:
    """Combine per-dataset summaries into result/summary.csv."""
    if not summary_map:
        print("[generate] No summaries to combine")
        return

    service_order: List[str] = []
    seen_services: set[str] = set()
    per_dataset_values: Dict[str, Dict[str, List[int]]] = {}

    for dataset in sorted(summary_map.keys()):
        csv_path = summary_map[dataset]
        per_dataset_values[dataset] = {}
        if not csv_path.exists():
            print(f"[generate] Skipping missing summary: {csv_path}")
            continue
        with csv_path.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.reader(fh)
            header = next(reader, None)
            if not header or header[0] != "service":
                print(f"[generate] Invalid summary header in {csv_path}")
                continue
            for row in reader:
                if len(row) < 2:
                    continue
                service = row[0].strip()
                try:
                    value = int(row[1])
                except (TypeError, ValueError):
                    continue
                if service not in per_dataset_values[dataset]:
                    per_dataset_values[dataset][service] = []
                per_dataset_values[dataset][service].append(value)
                if service not in seen_services:
                    service_order.append(service)
                    seen_services.add(service)

    if not service_order:
        print("[generate] No service rows collected; skip combined summary")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    datasets = sorted(per_dataset_values.keys())

    with output_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["service", *datasets])
        for service in service_order:
            max_rows = 0
            per_service_rows: List[List[int]] = []
            for dataset in datasets:
                values = per_dataset_values[dataset].get(service, [])
                per_service_rows.append(values)
                max_rows = max(max_rows, len(values))
            for idx in range(max_rows):
                row = [service]
                for values in per_service_rows:
                    row.append(values[idx] if idx < len(values) else "")
                writer.writerow(row)

    print(f"[generate] Wrote combined summary to {output_path}")


def generate_reports(data_root: Path, result_root: Path) -> None:
    """Parse logs under data_root and produce CSV summaries in result_root."""
    result_root.mkdir(parents=True, exist_ok=True)

    summary_marker = result_root / "summary.csv"
    if summary_marker.exists():
        print(
            f"[generate] Existing outputs detected for '{data_root.name}' at {result_root}; "
            "reusing previous artifacts for charts"
        )
        return

    datasets = _collect_log_dirs(data_root)
    if not datasets:
        print(f"[generate] No PerformanceLog folders found under {data_root}")
        return

    summary_paths: Dict[str, Path] = {}
    total_rows = 0

    for dataset_name, log_dir in datasets:
        if not log_dir.exists():
            continue
        pattern = _determine_pattern(log_dir)
        out_path = result_root / dataset_name / "summary.csv"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        rows = extract.process_dir(log_dir, pattern, out_path=out_path)
        if rows > 0:
            summary_paths[dataset_name] = out_path
            total_rows += rows
            print(f"[generate] {dataset_name}: wrote {rows} rows to {out_path}")
        else:
            print(f"[generate] {dataset_name}: no matches (pattern {pattern})")

    if not summary_paths:
        print("[generate] No summaries generated")
        return

    combined_path = summary_marker
    _combine_summaries(summary_paths, combined_path)

    env = os.environ.copy()
    env["SPM_RESULT_ROOT"] = str(result_root)

    try:
        subprocess.run(
            [sys.executable, str(BASE_DIR / "src" / "report.py")],
            check=True,
            cwd=BASE_DIR,
            env=env,
        )
    except subprocess.CalledProcessError as exc:
        print(f"[generate] report.py failed: {exc}")
        raise SystemExit(exc.returncode) from exc

    print(f"[generate] Completed report generation ({total_rows} total rows)")


def _merge_single_source(
    source_dir: Path, dest_dir: Path, overwrite: bool
) -> Tuple[int, int, int]:
    """Copy files from one data source into destination.

    Returns (copied, skipped, overwritten).
    """
    copied = skipped = overwritten = 0
    for root, _, files in os.walk(source_dir):
        root_path = Path(root)
        relative = root_path.relative_to(source_dir)
        target_root = dest_dir / relative
        target_root.mkdir(parents=True, exist_ok=True)
        for filename in files:
            src_file = root_path / filename
            dst_file = target_root / filename
            if dst_file.exists():
                if overwrite:
                    shutil.copy2(src_file, dst_file)
                    overwritten += 1
                else:
                    skipped += 1
                continue
            shutil.copy2(src_file, dst_file)
            copied += 1
    return copied, skipped, overwritten


def merge_data_folders(
    source_paths: Iterable[Path], dest_path: Path, overwrite: bool = False
) -> None:
    """Merge multiple data folders into a destination data folder."""
    dest_path.mkdir(parents=True, exist_ok=True)
    total_copied = total_skipped = total_overwritten = 0

    for source in source_paths:
        if not source.exists():
            print(f"[merge] Skip missing source: {source}")
            continue
        if source.resolve() == dest_path.resolve():
            print(f"[merge] Skip destination itself: {source}")
            continue
        print(f"[merge] Merging {source} -> {dest_path}")
        copied, skipped, overwritten = _merge_single_source(source, dest_path, overwrite)
        total_copied += copied
        total_skipped += skipped
        total_overwritten += overwritten

    print(
        "[merge] Done "
        f"(copied={total_copied}, skipped={total_skipped}, overwritten={total_overwritten})"
    )


def serve_webapp(host: str, port: int, debug: bool, result_root: Path, base_result_dir: Path) -> None:
    """Start the Flask web application."""
    os.environ["SPM_RESULT_ROOT"] = str(result_root)
    os.environ["SPM_RESULT_BASE"] = str(base_result_dir)
    dataset_name = result_root.name if result_root.parent == base_result_dir else ""
    if dataset_name:
        os.environ["SPM_DEFAULT_DATASET"] = dataset_name
    else:
        os.environ.pop("SPM_DEFAULT_DATASET", None)
    from src import webapp

    configure = getattr(webapp, "configure_result_dirs", None)
    if callable(configure):
        configure(result_root, base_result_dir, dataset_name or None)
    else:
        webapp.RESULT_DIR = result_root
        webapp.SUMMARY_FILE = result_root / "summary.csv"

    try:
        webapp.app.run(host=host, port=port, debug=debug)
    except KeyboardInterrupt:
        print("\n[serve] Shutting down")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Service Performance Metric helper CLI"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    clean_parser = subparsers.add_parser("clean", help="Remove generated result files")
    clean_parser.add_argument(
        "--result",
        default=str(DEFAULT_RESULT_DIR),
        help="Result folder to clean (default: result)",
    )
    clean_parser.set_defaults(func=cmd_clean)

    generate_parser = subparsers.add_parser(
        "generate", help="Parse logs and build reports"
    )
    generate_parser.add_argument(
        "--data",
        default=str(DEFAULT_DATA_DIR),
        help="Data folder containing version folders (default: data)",
    )
    generate_parser.set_defaults(func=cmd_generate)

    serve_parser = subparsers.add_parser(
        "serve", help="Build reports (optional) and start the web app"
    )
    serve_parser.add_argument(
        "--data",
        default=str(DEFAULT_DATA_DIR),
        help="Data folder containing version folders (default: data)",
    )
    serve_parser.add_argument(
        "data_dir",
        nargs="?",
        help="Optional positional data folder (equivalent to --data)",
    )
    serve_parser.add_argument(
        "--host", default="0.0.0.0", help="Host interface for the web server"
    )
    serve_parser.add_argument(
        "--port", default=8000, type=int, help="Port for the web server (default: 8000)"
    )
    serve_parser.add_argument(
        "--debug", action="store_true", help="Run the Flask app in debug mode"
    )
    serve_parser.add_argument(
        "--no-build",
        action="store_true",
        help="Skip report generation before launching the web app",
    )
    serve_parser.set_defaults(func=cmd_serve)

    merge_parser = subparsers.add_parser(
        "merge", help="Combine multiple data folders into one destination"
    )
    merge_parser.add_argument(
        "sources",
        nargs="+",
        help="One or more source data folders to merge",
    )
    merge_parser.add_argument(
        "--into",
        default=str(DEFAULT_DATA_DIR),
        help="Destination data folder (default: data)",
    )
    merge_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite duplicate files in destination (default: skip)",
    )
    merge_parser.set_defaults(func=cmd_merge)

    return parser


def cmd_clean(args: argparse.Namespace) -> None:
    result_dir = _resolve_path(args.result, DEFAULT_RESULT_DIR)
    clean_results(result_dir)


def cmd_generate(args: argparse.Namespace) -> None:
    data_root = _resolve_path(args.data, DEFAULT_DATA_DIR)
    result_root = result_root_for_data(data_root)
    generate_reports(data_root, result_root)


def cmd_serve(args: argparse.Namespace) -> None:
    data_arg = args.data_dir or args.data
    data_root = _resolve_path(data_arg, DEFAULT_DATA_DIR)
    result_root = result_root_for_data(data_root)
    if not args.no_build:
        generate_reports(data_root, result_root)
    serve_webapp(args.host, args.port, args.debug, result_root, DEFAULT_RESULT_DIR)


def cmd_merge(args: argparse.Namespace) -> None:
    sources = [_resolve_path(src, DEFAULT_DATA_DIR) for src in args.sources]
    dest = _resolve_path(args.into, DEFAULT_DATA_DIR)
    merge_data_folders(sources, dest, overwrite=args.overwrite)


def main(argv: List[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
