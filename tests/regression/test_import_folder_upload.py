from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest

from src import webapp


@pytest.fixture
def isolate_webapp_paths(tmp_path: Path):
    original = {
        "DATA_BASE_DIR": webapp.DATA_BASE_DIR,
        "RESULT_DIR": webapp.RESULT_DIR,
        "RESULT_BASE_DIR": webapp.RESULT_BASE_DIR,
        "SUMMARY_FILE": webapp.SUMMARY_FILE,
        "DEFAULT_DATASET_NAME": webapp.DEFAULT_DATASET_NAME,
    }
    data_base = tmp_path / "data"
    result_base = tmp_path / "result"
    data_base.mkdir(parents=True, exist_ok=True)
    result_base.mkdir(parents=True, exist_ok=True)

    webapp.DATA_BASE_DIR = data_base
    webapp.configure_result_dirs(result_base, result_base, None)

    yield {"data_base": data_base, "result_base": result_base}

    webapp.DATA_BASE_DIR = original["DATA_BASE_DIR"]
    webapp.configure_result_dirs(
        original["RESULT_DIR"], original["RESULT_BASE_DIR"], original["DEFAULT_DATASET_NAME"]
    )
    webapp.SUMMARY_FILE = original["SUMMARY_FILE"]


def test_folder_upload_populates_dataset_and_dashboard(isolate_webapp_paths):
    paths = isolate_webapp_paths
    dataset_name = "raw"
    log_content = b"12:00:00.000 ServiceA - loading_time: 42 ms\n"

    with webapp.app.test_client() as client:
        resp = client.post(
            "/api/datasets/import",
            data={
                "datasetName": dataset_name,
                "folder": (BytesIO(log_content), f"{dataset_name}/v1/PerformanceLog/log1.log"),
            },
            content_type="multipart/form-data",
        )
        assert resp.status_code == 201
        payload = resp.get_json()
        assert payload["dataset"] == dataset_name

        dashboard = client.get(
            "/api/dashboard",
            query_string={"dataset": dataset_name, "view": "reports"},
        )
        assert dashboard.status_code == 200
        dash_payload = dashboard.get_json()
        assert dash_payload["selectedDataset"] == dataset_name
        assert "versions" in dash_payload and "v1" in dash_payload["versions"]
        assert "reports" in dash_payload

        # Analytics view should also work via fallback per-version summary
        analytics = client.get(
            "/api/dashboard",
            query_string={"dataset": dataset_name, "view": "analytics"},
        )
        assert analytics.status_code == 200

    data_root = paths["data_base"] / dataset_name
    assert (data_root / "v1" / "PerformanceLog" / "log1.log").exists()
    result_root = paths["result_base"] / dataset_name
    assert (result_root / "v1" / "summary.csv").exists()


def test_folder_upload_respects_env_data_folder(monkeypatch, tmp_path: Path):
    data_base = tmp_path / "custom_data"
    result_base = tmp_path / "result_root"
    data_base.mkdir(parents=True, exist_ok=True)
    result_base.mkdir(parents=True, exist_ok=True)

    original = {
        "DATA_BASE_DIR": webapp.DATA_BASE_DIR,
        "RESULT_DIR": webapp.RESULT_DIR,
        "RESULT_BASE_DIR": webapp.RESULT_BASE_DIR,
        "SUMMARY_FILE": webapp.SUMMARY_FILE,
        "DEFAULT_DATASET_NAME": webapp.DEFAULT_DATASET_NAME,
    }
    monkeypatch.setenv("SPM_DATA_FOLDER", str(data_base))
    webapp.configure_result_dirs(result_base, result_base, None)

    dataset_name = "raw"
    log_content = b"12:00:00.000 ServiceB - loading_time: 21 ms\n"

    try:
        with webapp.app.test_client() as client:
            resp = client.post(
                "/api/datasets/import",
                data={
                    "datasetName": dataset_name,
                    "folder": (BytesIO(log_content), f"{dataset_name}/v1/PerformanceLog/logA.log"),
                },
                content_type="multipart/form-data",
            )
            assert resp.status_code == 201

            analytics = client.get(
                "/api/dashboard",
                query_string={"dataset": dataset_name, "view": "analytics"},
            )
            assert analytics.status_code == 200

        assert (data_base / dataset_name / "v1" / "PerformanceLog" / "logA.log").exists()
    finally:
        webapp.DATA_BASE_DIR = original["DATA_BASE_DIR"]
        webapp.configure_result_dirs(
            original["RESULT_DIR"], original["RESULT_BASE_DIR"], original["DEFAULT_DATASET_NAME"]
        )
        webapp.SUMMARY_FILE = original["SUMMARY_FILE"]
