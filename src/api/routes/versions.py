from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from flask import Blueprint, jsonify, request

from src.lib.path_utils import ValidationError
from src.services.version_pool import VersionStatus, list_versions

bp = Blueprint("versions", __name__, url_prefix="/versions")


def _status_to_dict(status: VersionStatus) -> Dict[str, Any]:
    return {
        "version_id": status.version_id,
        "status": status.status,
        "summary_path": str(status.summary_path),
        "message": status.message,
        "path": str(status.path),
    }


@bp.get("")
def get_versions():
    data_folder = request.args.get("data_folder")
    if not data_folder:
        return jsonify({"error": "data_folder is required"}), 400
    try:
        statuses = list_versions(Path(data_folder))
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 404

    return jsonify(
        {
            "data_folder": data_folder,
            "versions": [_status_to_dict(status) for status in statuses],
        }
    )
