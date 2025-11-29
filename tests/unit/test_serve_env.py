from __future__ import annotations

import os
import sys
import types
from pathlib import Path

from spm import serve_webapp


def test_serve_webapp_sets_data_folder_env(monkeypatch, tmp_path: Path):
    data_root = tmp_path / "raw_data"
    result_root = tmp_path / "result" / data_root.name
    base_result = tmp_path / "result"
    data_root.mkdir(parents=True)
    result_root.mkdir(parents=True)

    # Dummy Flask app to avoid running a server
    class DummyApp:
        def run(self, *args, **kwargs):
            return None

    dummy_webapp = types.ModuleType("src.webapp")
    dummy_webapp.app = DummyApp()

    def fake_configure_result_dirs(*args, **kwargs):
        return None

    dummy_webapp.configure_result_dirs = fake_configure_result_dirs

    # Inject dummy module so serve_webapp imports it
    dummy_src = types.ModuleType("src")
    dummy_src.webapp = dummy_webapp
    monkeypatch.setitem(sys.modules, "src", dummy_src)
    monkeypatch.setitem(sys.modules, "src.webapp", dummy_webapp)

    # Ensure env does not already include the target var
    monkeypatch.delenv("SPM_DATA_FOLDER", raising=False)

    serve_webapp("127.0.0.1", 0, True, data_root, result_root, base_result)

    assert os.environ.get("SPM_DATA_FOLDER") == str(data_root)
