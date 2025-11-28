from __future__ import annotations

from pathlib import Path

from flask import Blueprint, jsonify, request, send_file

from src.lib.path_utils import ValidationError
from src.services.comparison import get_latest_comparison

bp = Blueprint("downloads", __name__, url_prefix="/downloads")


@bp.get("/comparison")
def download_comparison():
    data_folder = request.args.get("data_folder")
    file_key = request.args.get("file", "summary")
    if not data_folder:
        return jsonify({"error": "data_folder is required"}), 400

    if file_key not in {"summary", "summary_stats", "service_stats"}:
        return jsonify({"error": "file must be one of summary, summary_stats, service_stats"}), 400

    try:
        latest = get_latest_comparison(Path(data_folder))
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 404

    target_path = Path(latest["outputs"][file_key])
    if not target_path.exists():
        return jsonify({"error": f"{file_key} not found; rerun comparison."}), 404

    return send_file(target_path, as_attachment=True)
