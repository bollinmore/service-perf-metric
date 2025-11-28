from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Sequence

from src.config.paths import latest_pointer, temp_root_for_data_folder
from src.lib.logging_config import get_comparison_logger
from src.lib.path_utils import ValidationError
from src.lib.run_ids import generate_run_id
from src.services.temp_storage import init_run_dirs, promote_latest, prune_previous_runs
from src.services.validation import require_exact_three
from src.services.version_pool import list_versions, require_versions_available


def _write_summary(run_paths: dict, versions: list[str], data_folder: Path) -> None:
    summary_path = run_paths["summary"]
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["version", "source_summary"])
        for version in versions:
            writer.writerow([version, str(data_folder / version / "summary.csv")])


def _write_stub(run_paths: dict, filename_key: str, versions: list[str]) -> None:
    path = run_paths[filename_key]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        writer.writerow(["versions", ";".join(versions)])


def run_comparison(data_folder: Path, versions: Sequence[str]) -> dict:
    """
    Execute a three-version comparison.

    Validates selection, ensures required artifacts exist, writes temporary outputs,
    and promotes the latest pointer.
    """
    logger = get_comparison_logger()
    selection = require_exact_three(list(versions))
    pool = list_versions(data_folder)
    require_versions_available(selection, pool)

    run_id = generate_run_id()
    run_paths = init_run_dirs(data_folder, run_id)

    _write_summary(run_paths, selection, data_folder)
    _write_stub(run_paths, "summary_stats", selection)
    _write_stub(run_paths, "service_stats", selection)

    manifest_path = Path(run_paths["run_dir"]) / "manifest.json"
    manifest_payload = {
        "run_id": run_id,
        "data_folder": str(data_folder),
        "selected_versions": selection,
        "outputs": {
            "summary": str(run_paths["summary"]),
            "summary_stats": str(run_paths["summary_stats"]),
            "service_stats": str(run_paths["service_stats"]),
        },
    }
    manifest_path.write_text(json.dumps(manifest_payload, ensure_ascii=False))

    latest = promote_latest(run_paths["temp_root"], run_paths["run_dir"])
    prune_previous_runs(run_paths["temp_root"], keep_run_id=run_id)

    logger.info(
        "comparison.run.completed",
        extra={
            "run_id": run_id,
            "data_folder": str(data_folder),
            "versions": selection,
            "run_dir": str(run_paths["run_dir"]),
            "latest_pointer": str(latest),
        },
    )

    manifest_payload.update(
        {
            "status": "completed",
            "temp_location": str(run_paths["run_dir"]),
            "latest_pointer": str(latest),
        }
    )
    return manifest_payload


def get_latest_comparison(data_folder: Path) -> dict:
    """Return metadata for the latest comparison, or raise ValidationError if absent."""
    temp_root = temp_root_for_data_folder(data_folder)
    latest = latest_pointer(temp_root)
    if not latest.exists():
        raise ValidationError("No comparison exists; select three versions to run comparison.")

    # Resolve symlink if present
    run_dir_path = latest.resolve()
    manifest = run_dir_path / "manifest.json"
    if not manifest.exists():
        raise ValidationError("Latest comparison manifest missing; rerun comparison.")

    payload = json.loads(manifest.read_text())
    payload["latest_pointer"] = str(latest)
    payload["temp_location"] = str(run_dir_path)
    return payload
