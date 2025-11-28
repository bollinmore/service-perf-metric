from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from src.config.paths import temp_root_for_data_folder


@pytest.fixture
def temp_data_folder(tmp_path: Path) -> Path:
    """Temporary data folder with three version directories."""
    base = tmp_path / "data_pool"
    base.mkdir(parents=True, exist_ok=True)
    for name in ["v1", "v2", "v3"]:
        version_dir = base / name
        version_dir.mkdir()
        (version_dir / "PerformanceLog").mkdir()
        (version_dir / "PerformanceLog" / f"{name}.log").write_text("log")
        (version_dir / "summary.csv").write_text("summary")
    return base


@pytest.fixture
def temp_result_root(tmp_path: Path) -> Path:
    """Temporary result root matching the data folder name for comparisons."""
    return tmp_path / "result"


@pytest.fixture(autouse=True)
def cleanup_tmp(temp_result_root: Path) -> None:
    yield
    if temp_result_root.exists():
        shutil.rmtree(temp_result_root, ignore_errors=True)


@pytest.fixture
def temp_paths(temp_data_folder: Path, temp_result_root: Path) -> dict:
    """Precomputed paths for temp storage tests."""
    temp_root = temp_root_for_data_folder(temp_data_folder.name)
    return {
        "data_folder": temp_data_folder,
        "result_root": temp_result_root,
        "temp_root": temp_root,
    }
