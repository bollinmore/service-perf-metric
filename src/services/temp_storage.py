from __future__ import annotations

import os
import shutil
from pathlib import Path

from src.config.paths import (
    LATEST_POINTER_NAME,
    latest_pointer,
    run_dir,
    temp_root_for_data_folder,
)


def init_run_dirs(data_folder: str | Path, run_id: str) -> dict:
    """Create temp directories for a comparison run and return key paths."""
    temp_root = temp_root_for_data_folder(data_folder)
    run_path = run_dir(temp_root, run_id)
    run_path.mkdir(parents=True, exist_ok=True)
    temp_root.mkdir(parents=True, exist_ok=True)
    return {
        "temp_root": temp_root,
        "run_dir": run_path,
        "summary": run_path / "summary.csv",
        "summary_stats": run_path / "summary_stats.csv",
        "service_stats": run_path / "service_stats.csv",
    }


def promote_latest(temp_root: Path, run_dir_path: Path) -> Path:
    """
    Point the temp/latest to the provided run directory.

    Uses a symlink when possible; falls back to copying if symlinks are not permitted.
    """
    latest_path = latest_pointer(temp_root)
    if latest_path.exists() or latest_path.is_symlink():
        if latest_path.is_dir() and not latest_path.is_symlink():
            shutil.rmtree(latest_path, ignore_errors=True)
        else:
            latest_path.unlink(missing_ok=True)

    try:
        latest_path.symlink_to(run_dir_path, target_is_directory=True)
    except (OSError, NotImplementedError):
        # Fallback: copytree to maintain a stable latest pointer
        shutil.copytree(run_dir_path, latest_path, dirs_exist_ok=True)
    return latest_path


def prune_previous_runs(temp_root: Path, keep_run_id: str | None = None) -> None:
    """
    Remove previous temp run folders except the one to keep.

    This does not remove the 'latest' pointer; it focuses on numbered run directories.
    """
    if not temp_root.exists():
        return
    for child in temp_root.iterdir():
        if child.name == LATEST_POINTER_NAME:
            continue
        if keep_run_id and child.name == keep_run_id:
            continue
        if child.is_dir():
            shutil.rmtree(child, ignore_errors=True)
        else:
            child.unlink(missing_ok=True)
