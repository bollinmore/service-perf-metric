from __future__ import annotations

from pathlib import Path

from src.services.comparison import run_comparison


def test_comparison_runs_isolate_and_prune(monkeypatch, temp_data_folder: Path, temp_result_root: Path):
    monkeypatch.setenv("SPM_RESULT_ROOT", str(temp_result_root))

    first = run_comparison(temp_data_folder, ["v1", "v2", "v3"])
    second = run_comparison(temp_data_folder, ["v1", "v3", "v2"])

    first_run_dir = Path(first["temp_location"])
    second_run_dir = Path(second["temp_location"])
    latest_pointer = Path(second["latest_pointer"])

    assert latest_pointer.resolve() == second_run_dir
    assert second_run_dir.exists()
    # Prior run should be pruned
    assert not first_run_dir.exists()
