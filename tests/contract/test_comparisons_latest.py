from __future__ import annotations

from pathlib import Path

import pytest

from src.api import create_app
from src.services.comparison import run_comparison


@pytest.fixture
def client(monkeypatch, temp_data_folder: Path, temp_result_root: Path):
    monkeypatch.setenv("SPM_RESULT_ROOT", str(temp_result_root))
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_get_latest_not_found(client, temp_data_folder: Path):
    resp = client.get("/comparisons/latest", query_string={"data_folder": str(temp_data_folder)})
    assert resp.status_code == 404
    assert "select three versions" in resp.get_json()["error"]


def test_get_latest_success(monkeypatch, client, temp_data_folder: Path, temp_result_root: Path):
    # Create a comparison run directly
    monkeypatch.setenv("SPM_RESULT_ROOT", str(temp_result_root))
    run_comparison(temp_data_folder, ["v1", "v2", "v3"])

    resp = client.get("/comparisons/latest", query_string={"data_folder": str(temp_data_folder)})
    assert resp.status_code == 200
    data = resp.get_json()
    assert set(data["selected_versions"]) == {"v1", "v2", "v3"}
    for key in ["summary", "summary_stats", "service_stats"]:
        assert Path(data["outputs"][key]).exists()
