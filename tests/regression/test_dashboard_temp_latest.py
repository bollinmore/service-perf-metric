from __future__ import annotations

from pathlib import Path

import pytest

import pytest

plotly = pytest.importorskip("plotly")
from src import webapp


@pytest.fixture
def restore_webapp_paths():
    original = {
        "RESULT_DIR": webapp.RESULT_DIR,
        "RESULT_BASE_DIR": webapp.RESULT_BASE_DIR,
        "SUMMARY_FILE": webapp.SUMMARY_FILE,
        "DEFAULT_DATASET_NAME": webapp.DEFAULT_DATASET_NAME,
    }
    yield
    webapp.configure_result_dirs(
        original["RESULT_DIR"], original["RESULT_BASE_DIR"], original["DEFAULT_DATASET_NAME"]
    )
    webapp.SUMMARY_FILE = original["SUMMARY_FILE"]


def test_dashboard_uses_temp_latest_summary(tmp_path: Path, restore_webapp_paths):
    result_base = tmp_path / "result"
    dataset_name = "data"
    dataset_dir = result_base / dataset_name
    latest_dir = dataset_dir / "temp" / "latest"
    latest_dir.mkdir(parents=True)

    # Latest comparison outputs
    summary = latest_dir / "summary.csv"
    summary.write_text("service,v1,v2\nsvc,1,2\n", encoding="utf-8")
    service_stats = latest_dir / "service_stats.csv"
    service_stats.write_text(
        "service,v1_avg,v1_min,v1_max,v1_median,v2_avg,v2_min,v2_max,v2_median\n"
        "svc,1,1,1,1,2,2,2,2\n",
        encoding="utf-8",
    )

    # Point webapp to the temp result root for this dataset
    webapp.configure_result_dirs(dataset_dir, result_base, dataset_name)

    with webapp.app.test_client() as client:
        resp = client.get("/api/dashboard", query_string={"dataset": dataset_name, "view": "analytics"})
        assert resp.status_code == 200
        payload = resp.get_json()
        assert payload["selectedDataset"] == dataset_name
        assert payload["versions"] == ["v1", "v2"]
        # ensure service stats are considered (compare defaults should include both versions)
        assert payload["compare"]["defaults"]["versionA"] in {"v1", "v2"}
        assert payload["compare"]["defaults"]["versionB"] in {"v1", "v2"}


def test_dashboard_with_raw_data_mapping(tmp_path: Path, restore_webapp_paths):
    raw_data_root = tmp_path / "raw_data"
    raw_data_root.mkdir()
    # simulate result root derived from raw data name
    base_result = tmp_path / "result"
    result_root = base_result / raw_data_root.name
    latest_dir = result_root / "temp" / "latest"
    latest_dir.mkdir(parents=True)
    (latest_dir / "summary.csv").write_text("service,v1,v2\nsvc,1,2\n", encoding="utf-8")
    (latest_dir / "service_stats.csv").write_text(
        "service,v1_avg,v1_min,v1_max,v1_median,v2_avg,v2_min,v2_max,v2_median\n"
        "svc,1,1,1,1,2,2,2,2\n",
        encoding="utf-8",
    )

    webapp.configure_result_dirs(result_root, base_result, raw_data_root.name)

    with webapp.app.test_client() as client:
        resp = client.get(
            "/api/dashboard",
            query_string={"dataset": raw_data_root.name, "view": "analytics"},
        )
        assert resp.status_code == 200
        payload = resp.get_json()
        assert payload["selectedDataset"] == raw_data_root.name
        assert payload["versions"] == ["v1", "v2"]


def test_dashboard_missing_summary_returns_error(tmp_path: Path, restore_webapp_paths):
    result_base = tmp_path / "result"
    dataset_name = "data"
    dataset_dir = result_base / dataset_name
    dataset_dir.mkdir(parents=True)
    # no summary/service_stats created
    webapp.configure_result_dirs(dataset_dir, result_base, dataset_name)

    with webapp.app.test_client() as client:
        resp = client.get(
            "/api/dashboard",
            query_string={"dataset": dataset_name, "view": "analytics"},
        )
        assert resp.status_code == 404


def test_run_comparison_writes_temp_latest(tmp_path: Path, restore_webapp_paths):
    # Arrange result_root with summaries only (no logs)
    result_base = (tmp_path / "result").resolve()
    result_root = result_base / "data"
    v1 = result_root / "v1"
    v2 = result_root / "v2"
    for v in (v1, v2):
        v.mkdir(parents=True, exist_ok=True)
        (v / "summary.csv").write_text("service,v\nsvc,1\n", encoding="utf-8")

    # Act
    from src.services.comparison import run_comparison

    run_comparison(result_root, ["v1", "v2"])

    # Assert temp/latest exists with summary
    latest_summary = result_root / "temp" / "latest" / "summary.csv"
    assert latest_summary.exists()
    content = latest_summary.read_text(encoding="utf-8")
    assert "v1" in content and "v2" in content
    latest_stats = result_root / "temp" / "latest" / "service_stats.csv"
    assert latest_stats.exists()
    stats_text = latest_stats.read_text(encoding="utf-8")
    assert "v1_min" in stats_text and "v2_min" in stats_text
    assert "svc" in stats_text


def test_dashboard_api_with_latest_outputs(tmp_path: Path, restore_webapp_paths):
    result_base = (tmp_path / "result").resolve()
    dataset_name = "data"
    result_root = result_base / dataset_name
    latest = result_root / "temp" / "latest"
    latest.mkdir(parents=True, exist_ok=True)
    (latest / "summary.csv").write_text("service,v1,v2\nsvc,1,2\n", encoding="utf-8")
    (latest / "service_stats.csv").write_text(
        "service,v1_min,v1_median,v1_avg,v1_max,v2_min,v2_median,v2_avg,v2_max\n"
        "svc,1,1,1,1,2,2,2,2\n",
        encoding="utf-8",
    )

    webapp.configure_result_dirs(result_root, result_base, dataset_name)

    with webapp.app.test_client() as client:
        resp = client.get(
            "/api/dashboard",
            query_string={"dataset": dataset_name, "view": "analytics"},
        )
        assert resp.status_code == 200
        payload = resp.get_json()
        assert payload["selectedDataset"] == dataset_name
        assert payload["versions"] == ["v1", "v2"]
