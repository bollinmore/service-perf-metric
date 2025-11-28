from __future__ import annotations

from pathlib import Path

from src.services.temp_storage import prune_previous_runs


def test_prune_previous_runs(tmp_path: Path):
    temp_root = tmp_path / "temp"
    keep = temp_root / "keep"
    old = temp_root / "old"
    latest = temp_root / "latest"

    keep.mkdir(parents=True, exist_ok=True)
    old.mkdir(parents=True, exist_ok=True)
    latest.mkdir(parents=True, exist_ok=True)

    prune_previous_runs(temp_root, keep_run_id="keep")

    assert keep.exists()
    assert not old.exists()
    assert latest.exists()
