from __future__ import annotations

import os
from pathlib import Path

from src.config import PROJECT_ROOT

TEMP_DIR_NAME = "temp"
LATEST_POINTER_NAME = "latest"


def result_root() -> Path:
    """Return the current result root, respecting environment override."""
    override = os.environ.get("SPM_RESULT_ROOT")
    if override:
        return Path(override)
    return PROJECT_ROOT / "result"


def result_root_for_data_folder(data_folder: str | Path) -> Path:
    """Resolve the result root for a given data folder name or path."""
    data_path = Path(data_folder)
    folder_name = data_path.name
    if data_path.is_absolute():
        return data_path
    return result_root() / folder_name


def temp_root_for_data_folder(data_folder: str | Path) -> Path:
    """Return the temp root under result/<data-folder>/temp."""
    return result_root_for_data_folder(data_folder) / TEMP_DIR_NAME


def run_dir(temp_root: Path, run_id: str) -> Path:
    """Return the directory path for a specific comparison run."""
    return temp_root / run_id


def latest_pointer(temp_root: Path) -> Path:
    """Return the path used as the latest pointer for comparison outputs."""
    return temp_root / LATEST_POINTER_NAME
