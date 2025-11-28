from __future__ import annotations

import pytest

from pathlib import Path

from src.api import create_app
from src.services.comparison import run_comparison
from src.services.visualization import fetch_latest_outputs
from src.lib.path_utils import ValidationError


@pytest.fixture
def client(monkeypatch, temp_result_root: Path):
    monkeypatch.setenv("SPM_RESULT_ROOT", str(temp_result_root))
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_visualization_requires_selection(temp_data_folder: Path):
    with pytest.raises(ValidationError):
        fetch_latest_outputs(temp_data_folder)


def test_visualization_after_selection(monkeypatch, temp_data_folder: Path, temp_result_root: Path):
    monkeypatch.setenv("SPM_RESULT_ROOT", str(temp_result_root))
    run_comparison(temp_data_folder, ["v1", "v2", "v3"])
    outputs = fetch_latest_outputs(temp_data_folder)
    assert "summary" in outputs
    assert Path(outputs["summary"]).exists()


def test_download_route_prompts_when_missing(client, temp_data_folder: Path):
    resp = client.get("/downloads/comparison", query_string={"data_folder": str(temp_data_folder)})
    assert resp.status_code == 404
    assert "select three versions" in resp.get_json()["error"]


def test_download_route_serves_file(monkeypatch, client, temp_data_folder: Path, temp_result_root: Path):
    monkeypatch.setenv("SPM_RESULT_ROOT", str(temp_result_root))
    run_comparison(temp_data_folder, ["v1", "v2", "v3"])
    resp = client.get("/downloads/comparison", query_string={"data_folder": str(temp_data_folder), "file": "summary"})
    assert resp.status_code == 200
    assert resp.data  # file content returned
