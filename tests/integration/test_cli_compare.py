from __future__ import annotations

import json
from pathlib import Path

from src.cli.commands.compare import main


def test_cli_compare_creates_outputs(monkeypatch, temp_data_folder: Path, temp_result_root: Path, capsys):
    monkeypatch.setenv("SPM_RESULT_ROOT", str(temp_result_root))
    exit_code = main(
        [
            "--data-folder",
            str(temp_data_folder),
            "--versions",
            "v1",
            "v2",
            "v3",
        ]
    )
    captured = capsys.readouterr()
    assert exit_code == 0
    data = json.loads(captured.out)
    run_dir = Path(data["temp_location"])
    latest = Path(data["latest_pointer"])
    assert run_dir.exists()
    assert (run_dir / "summary.csv").exists()
    assert (run_dir / "summary_stats.csv").exists()
    assert (run_dir / "service_stats.csv").exists()
    assert latest.exists()
