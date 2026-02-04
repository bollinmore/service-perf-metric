from __future__ import annotations

import argparse
import csv
import json
import os
import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = BASE_DIR / "data"
DEFAULT_RESULT_DIR = BASE_DIR / "result"
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
RUN_LOG = LOG_DIR / "run.log"
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
RUN_LOG = LOG_DIR / "run.log"


def result_root_for_data(data_root: Path) -> Path:
    """Return the result directory that corresponds to the given data folder."""
    return DEFAULT_RESULT_DIR / data_root.name


# Allow imports from src.*
sys.path.insert(0, str(BASE_DIR))

try:
    from src import config
    from src import extract
    from src.lib.path_utils import ValidationError, parse_versions_arg, validate_base_path
    from src.lib.logging import get_logger, log_selection, log_upload_rejection
    from src.services.comparison_service import plan_comparison, refresh_results
    from src.services.comparison import run_comparison
    from src.services.mode_service import get_mode_service
    from src.services.selection_service import validate_selection
    from src.services.version_discovery import discover_versions
    from src.services.upload_validator import validate_upload
except ModuleNotFoundError as exc:  # pragma: no cover - import guard
    raise SystemExit(f"Failed to import project modules: {exc}") from exc

ENV_PATH = config.load_env(BASE_DIR / ".env")
MODE_SERVICE = get_mode_service(BASE_DIR)
LOGGER = config.configure_logging()
FILE_LOGGER = logging.getLogger("spm.runfile")
if not FILE_LOGGER.handlers:
    fh = logging.FileHandler(RUN_LOG, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    FILE_LOGGER.addHandler(fh)
    FILE_LOGGER.setLevel(logging.INFO)
    FILE_LOGGER.propagate = False
def _resolve_path(path_str: str | None, default: Path) -> Path:
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


def _collect_log_dirs(data_root: Path, allowed_versions: List[str] | None = None) -> List[Tuple[str, Path]]:
    """Return list of (dataset_name, log_dir) pairs under the data root."""
    datasets: List[Tuple[str, Path]] = []
    if not data_root.exists():
        print(f"[generate] Data folder not found: {data_root}")
        return []

    allowed_set = set(allowed_versions) if allowed_versions else None

    for candidate in sorted(data_root.iterdir()):
        if not candidate.is_dir():
            continue
        if allowed_set and candidate.name not in allowed_set:
            continue
        # Prefer a direct PerformanceLog folder, but fall back to any child match
        log_dir = candidate / "PerformanceLog"
        if log_dir.is_dir() and any(log_dir.glob("*.log")):
            datasets.append((candidate.name, log_dir))
            continue
        matching = [path for path in candidate.glob("PerformanceLog") if path.is_dir()]
        if matching and any(matching[0].glob("*.log")):
            datasets.append((candidate.name, matching[0]))
    return datasets


def _determine_pattern(log_dir: Path) -> str:
    """Pick a glob pattern for log files, preferring loading/inquire2 primary logs."""
    if list(log_dir.glob("*loading*.log")):
        return "*loading*.log"
    if list(log_dir.glob("*inquire2.log")):
        return "*inquire2.log"
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


def generate_reports(data_root: Path, result_root: Path, allowed_versions: List[str] | None = None) -> None:
    """Parse logs under data_root and produce per-version CSV summaries in result_root.

    Cross-version outputs (summary.csv, summary_stats.csv, service_stats.csv) are NOT
    generated here; they are produced only by explicit comparison runs.
    """
    result_root.mkdir(parents=True, exist_ok=True)

    datasets = _collect_log_dirs(data_root, allowed_versions=allowed_versions)
    if not datasets:
        msg = f"No PerformanceLog folders found under {data_root}"
        print(f"[generate] {msg}")
        FILE_LOGGER.warning(msg)
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
            FILE_LOGGER.info(f"summary_written dataset={dataset_name} rows={rows} path={out_path}")
        else:
            print(f"[generate] {dataset_name}: no matches (pattern {pattern})")
            FILE_LOGGER.warning(f"summary_empty dataset={dataset_name} pattern={pattern}")

    if not summary_paths:
        print("[generate] No summaries generated")
        FILE_LOGGER.warning("No summaries generated")
        return
    print(f"[generate] Completed per-version summaries ({total_rows} total rows); cross-version reports deferred to comparison runs.")
    FILE_LOGGER.info(
        json.dumps(
            {
                "event": "per_version_summaries_complete",
                "data_root": str(data_root),
                "result_root": str(result_root),
                "versions": list(summary_paths.keys()),
                "total_rows": total_rows,
            }
        )
    )


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


def serve_webapp(host: str, port: int, debug: bool, data_root: Path, result_root: Path, base_result_dir: Path) -> None:
    """Start the Flask web application."""
    mode_status = MODE_SERVICE.current_status()
    os.environ["SPM_MODE"] = mode_status.mode
    os.environ["SPM_MODE_SOURCE"] = mode_status.source
    os.environ["SPM_DATA_FOLDER"] = str(data_root)
    if mode_status.warnings:
        for note in mode_status.warnings:
            print(f"[mode] Warning: {note}")
    print(f"[mode] Active mode: {mode_status.mode} (source={mode_status.source})")
    if mode_status.snapshot:
        print(
            "[mode] Preserved development version: "
            f"{mode_status.snapshot.id} @ {mode_status.snapshot.timestamp.isoformat()}"
        )

    os.environ["SPM_RESULT_ROOT"] = str(result_root)
    os.environ["SPM_RESULT_BASE"] = str(base_result_dir)
    dataset_name = result_root.name if result_root.parent == base_result_dir else ""
    if dataset_name:
        os.environ["SPM_DEFAULT_DATASET"] = dataset_name
    else:
        os.environ.pop("SPM_DEFAULT_DATASET", None)
    os.environ["SPM_DATA_FOLDER"] = str(data_root)
    from src import webapp

    configure = getattr(webapp, "configure_result_dirs", None)
    if callable(configure):
        configure(result_root, base_result_dir, dataset_name or None)
    else:
        webapp.RESULT_DIR = result_root
        webapp.SUMMARY_FILE = result_root / "summary.csv"

    try:
        production_requested = (
            os.environ.get("SPM_FORCE_PRODUCTION") == "1" or not debug
        )
        if production_requested:
            try:
                from waitress import serve as waitress_serve
            except ImportError:
                print(
                    "[serve] Production server requested but 'waitress' is not installed; "
                    "falling back to Flask development server"
                )
            else:
                print("[serve] Starting production WSGI server via waitress")
                waitress_serve(webapp.app, host=host, port=port)
                return

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
        "generate", help="Parse logs and build reports (requires --data-folder)"
    )
    generate_parser.add_argument(
        "--data-folder",
        required=True,
        help="Data folder containing version folders (required)",
    )
    generate_parser.add_argument(
        "--versions",
        help="Optional comma-separated list of versions to include (e.g., 2.0.1.0,2.0.1.2)",
    )
    generate_parser.add_argument(
        "--refresh",
        action="store_true",
        help="Force refresh by clearing previous results before generation",
    )
    generate_parser.add_argument(
        "--allow-conflicts",
        action="store_true",
        help="Proceed even if log filename conflicts detected across versions",
    )
    generate_parser.set_defaults(func=cmd_generate)

    serve_parser = subparsers.add_parser(
        "serve", help="Build reports (optional) and start the web app (defaults to ./data)"
    )
    serve_parser.add_argument(
        "--data-folder",
        default=None,
        help="Data folder containing version folders (default: $SPM_DATA_FOLDER or data)",
    )
    serve_parser.add_argument(
        "--versions",
        help="Optional comma-separated list of versions to include (e.g., 2.0.1.0,2.0.1.2)",
    )
    serve_parser.add_argument(
        "--host", default="0.0.0.0", help="Host interface for the web server"
    )
    serve_parser.add_argument(
        "--port", default=6231, type=int, help="Port for the web server (default: 6231)"
    )
    serve_parser.add_argument(
        "--debug", action="store_true", help="Run the Flask app in debug mode"
    )
    serve_parser.add_argument(
        "--no-build",
        action="store_true",
        help="Skip report generation before launching the web app",
    )
    serve_parser.add_argument(
        "--refresh",
        action="store_true",
        help="Force refresh by clearing previous results before serve",
    )
    serve_parser.add_argument(
        "--allow-conflicts",
        action="store_true",
        help="Proceed even if log filename conflicts detected across versions",
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

    versions_parser = subparsers.add_parser(
        "versions", help="List available versions under a data folder"
    )
    versions_parser.add_argument(
        "--data-folder",
        required=True,
        help="Data folder containing version folders (required)",
    )
    versions_parser.set_defaults(func=cmd_versions)

    compare_parser = subparsers.add_parser(
        "compare", help="Validate selected versions and generate reports"
    )
    compare_parser.add_argument(
        "--data-folder",
        required=True,
        help="Data folder containing version folders (required)",
    )
    compare_parser.add_argument(
        "--versions",
        required=True,
        help="Comma-separated list of versions to compare (2-4 required)",
    )
    compare_parser.add_argument(
        "--refresh",
        action="store_true",
        help="Force refresh by clearing previous results before comparison",
    )
    compare_parser.add_argument(
        "--allow-conflicts",
        action="store_true",
        help="Proceed even if log filename conflicts detected across versions",
    )
    compare_parser.set_defaults(func=cmd_compare)

    upload_parser = subparsers.add_parser(
        "upload", help="Validate and extract a single zip containing <tool-version>/PerformanceLog/*.log"
    )
    upload_parser.add_argument(
        "--data-folder",
        required=True,
        help="Base data folder where the version folder will be created",
    )
    upload_parser.add_argument(
        "--zip",
        required=True,
        help="Path to the zip file to upload",
    )
    upload_parser.set_defaults(func=cmd_upload)

    return parser


def cmd_clean(args: argparse.Namespace) -> None:
    result_dir = _resolve_path(args.result, DEFAULT_RESULT_DIR)
    clean_results(result_dir)


def cmd_generate(args: argparse.Namespace) -> None:
    default_data = config.resolve_data_folder(None)
    data_root = validate_base_path(_resolve_path(args.data_folder, default_data))
    versions = parse_versions_arg(args.versions)
    plan = plan_comparison(data_root, versions or None, result_root_for_data(data_root))
    if plan.conflicts and not getattr(args, "allow_conflicts", False):
        raise ValidationError("; ".join(plan.conflicts))
    log_selection(LOGGER, str(data_root), plan.selected_versions)
    if getattr(args, "refresh", False):
        refresh_results(plan, force_refresh=True)
    generate_reports(plan.base_path, plan.result_root, allowed_versions=plan.selected_versions)


def cmd_serve(args: argparse.Namespace) -> None:
    default_data = config.resolve_data_folder(None)
    data_root = validate_base_path(_resolve_path(args.data_folder, default_data))
    discovered = discover_versions(data_root, strict_missing=False)
    all_versions = sorted(v.name for v in discovered)

    result_root = result_root_for_data(data_root)
    result_root.mkdir(parents=True, exist_ok=True)
    compare_selection: List[str] = []
    if len(all_versions) >= 2:
        compare_selection = all_versions[-3:] if len(all_versions) > 3 else all_versions
    elif not all_versions:
        print(f"[serve] No versions found under {data_root}; waiting for uploads via web UI.")

    if not args.no_build and all_versions:
        def _summaries_exist(root: Path, versions: List[str]) -> bool:
            return all((root / ver / "summary.csv").exists() for ver in versions)

        if getattr(args, "refresh", False) or not _summaries_exist(result_root, all_versions):
            generate_reports(data_root, result_root, allowed_versions=all_versions)

        def _latest_matches(root: Path, selection: List[str]) -> bool:
            manifest = root / "temp" / "latest" / "manifest.json"
            if not manifest.exists():
                return False
            try:
                payload = json.loads(manifest.read_text())
                return payload.get("selected_versions") == selection
            except Exception:
                return False

        if len(compare_selection) >= 2 and not _latest_matches(result_root, compare_selection):
            try:
                run_comparison(result_root, compare_selection)
            except ValidationError as exc:
                LOGGER.error(f"[serve] comparison generation failed: {exc}")

    serve_webapp(args.host, args.port, args.debug, data_root, result_root, DEFAULT_RESULT_DIR)


def cmd_merge(args: argparse.Namespace) -> None:
    sources = [_resolve_path(src, DEFAULT_DATA_DIR) for src in args.sources]
    dest = _resolve_path(args.into, DEFAULT_DATA_DIR)
    merge_data_folders(sources, dest, overwrite=args.overwrite)


def cmd_versions(args: argparse.Namespace) -> None:
    default_data = config.resolve_data_folder(None)
    data_root = validate_base_path(_resolve_path(args.data_folder, default_data))
    versions = discover_versions(data_root)
    if not versions:
        print(f"[versions] No versions found under {data_root}")
        return
    print("[versions] Available:")
    for v in versions:
        print(f" - {v.name} ({v.log_dir})")


def cmd_compare(args: argparse.Namespace) -> None:
    default_data = config.resolve_data_folder(None)
    data_root = validate_base_path(_resolve_path(args.data_folder, default_data))
    versions = parse_versions_arg(args.versions)
    plan = plan_comparison(data_root, versions or None, result_root_for_data(data_root))
    if plan.conflicts and not getattr(args, "allow_conflicts", False):
        raise ValidationError("; ".join(plan.conflicts))
    log_selection(LOGGER, str(data_root), plan.selected_versions)
    if getattr(args, "refresh", False):
        refresh_results(plan, force_refresh=True)
    generate_reports(plan.base_path, plan.result_root, allowed_versions=plan.selected_versions)


def cmd_upload(args: argparse.Namespace) -> None:
    default_data = config.resolve_data_folder(None)
    data_root = validate_base_path(_resolve_path(args.data_folder, default_data))
    zip_path = _resolve_path(args.zip, BASE_DIR)
    try:
        version_name = validate_upload(zip_path)
    except ValidationError as exc:
        log_upload_rejection(LOGGER, str(exc))
        raise

    target_dir = data_root / version_name
    target_dir.mkdir(parents=True, exist_ok=True)

    import zipfile

    with zipfile.ZipFile(zip_path, "r") as zf:
        top_level = version_name
        for member in zf.infolist():
            parts = Path(member.filename).parts
            if not parts:
                continue
            if parts[0] != top_level:
                raise ValidationError("Upload contains mismatched top-level folder.")
            member_rel = Path(*parts[1:])
            if ".." in member_rel.parts:
                raise ValidationError("Upload contains unsafe paths.")
            if member.is_dir():
                (target_dir / member_rel).mkdir(parents=True, exist_ok=True)
                continue
            dest_file = target_dir / member_rel
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member, "r") as src, dest_file.open("wb") as dst:
                dst.write(src.read())
    print(f"[upload] Uploaded and extracted version '{version_name}' into {target_dir}")


def main(argv: List[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except ValidationError as exc:
        print(f"[error] {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
