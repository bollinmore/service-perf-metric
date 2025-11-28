from __future__ import annotations

from pathlib import Path

import pytest

import spm


def _write_log(dir_path: Path, service: str = "svc", ms: int = 10) -> None:
    dir_path.mkdir(parents=True, exist_ok=True)
    (dir_path / "sample.log").write_text(f"00:00:00.000 {service} - loading_time: {ms} ms\n")


def test_generate_only_per_version(tmp_path: Path):
    data_root = tmp_path / "data"
    result_root = tmp_path / "result"
    version_dir = data_root / "v1" / "PerformanceLog"
    _write_log(version_dir, "svc1", 10)

    spm.generate_reports(data_root, result_root)

    per_version_summary = result_root / "v1" / "summary.csv"
    assert per_version_summary.exists()

    # Cross-version artifacts should not be created
    assert not (result_root / "summary.csv").exists()
    assert not (result_root / "summary_stats.csv").exists()
    assert not (result_root / "service_stats.csv").exists()
