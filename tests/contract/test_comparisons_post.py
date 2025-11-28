from __future__ import annotations

from pathlib import Path

import pytest

from src.api import create_app


@pytest.fixture
def client(monkeypatch, temp_data_folder: Path, temp_result_root: Path):
    monkeypatch.setenv("SPM_RESULT_ROOT", str(temp_result_root))
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_create_comparison_success(client, temp_data_folder: Path, temp_result_root: Path):
    payload = {"data_folder": str(temp_data_folder), "versions": ["v1", "v2", "v3"]}
    resp = client.post("/comparisons", json=payload)
    assert resp.status_code == 201
    data = resp.get_json()
    assert set(data["selected_versions"]) == {"v1", "v2", "v3"}

    run_dir = Path(data["temp_location"])
    assert run_dir.exists()
    assert (run_dir / "summary.csv").exists()
    assert (run_dir / "summary_stats.csv").exists()
    assert (run_dir / "service_stats.csv").exists()

    latest_pointer = Path(data["latest_pointer"])
    assert latest_pointer.exists()


def test_create_comparison_invalid_count(client, temp_data_folder: Path):
    payload = {"data_folder": str(temp_data_folder), "versions": ["v1", "v2"]}
    resp = client.post("/comparisons", json=payload)
    assert resp.status_code == 400
    assert "Exactly three versions" in resp.get_json()["error"]


def test_create_comparison_missing_version(client, temp_data_folder: Path):
    payload = {"data_folder": str(temp_data_folder), "versions": ["v1", "v4", "v3"]}
    resp = client.post("/comparisons", json=payload)
    assert resp.status_code == 400
    assert "Requested versions not available" in resp.get_json()["error"]


def test_create_comparison_missing_artifact(client, temp_data_folder: Path):
    missing_summary = temp_data_folder / "v2" / "summary.csv"
    missing_summary.unlink()
    payload = {"data_folder": str(temp_data_folder), "versions": ["v1", "v2", "v3"]}
    resp = client.post("/comparisons", json=payload)
    assert resp.status_code == 400
    assert "Requested versions not available" in resp.get_json()["error"]
