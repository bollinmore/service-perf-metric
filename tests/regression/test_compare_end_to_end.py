from __future__ import annotations

from pathlib import Path

from src.api import create_app
from src.services.comparison import run_comparison


def test_compare_end_to_end(monkeypatch, temp_data_folder: Path, temp_result_root: Path):
    monkeypatch.setenv("SPM_RESULT_ROOT", str(temp_result_root))
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        # Trigger comparison
        resp = client.post(
            "/comparisons",
            json={"data_folder": str(temp_data_folder), "versions": ["v1", "v2", "v3"]},
        )
        assert resp.status_code == 201

        # Fetch latest
        latest = client.get("/comparisons/latest", query_string={"data_folder": str(temp_data_folder)})
        assert latest.status_code == 200
        payload = latest.get_json()
        for key in ["summary", "summary_stats", "service_stats"]:
            path = Path(payload["outputs"][key])
            assert path.exists()

        # Download one file
        dl = client.get("/downloads/comparison", query_string={"data_folder": str(temp_data_folder), "file": "summary"})
        assert dl.status_code == 200
        assert dl.data
