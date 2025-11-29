from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from flask import Blueprint, jsonify, request

from src.lib.path_utils import ValidationError
from src.services.comparison import get_latest_comparison, run_comparison
from src.services.validation import require_exact_three

bp = Blueprint("comparisons", __name__, url_prefix="/comparisons")


@bp.post("")
def create_comparison():
    payload: Dict[str, Any] = request.get_json(silent=True) or {}
    data_folder = payload.get("data_folder")
    versions = payload.get("versions") or []
    if not data_folder:
        return jsonify({"error": "data_folder is required"}), 400
    try:
        require_exact_three(versions)
        result = run_comparison(Path(data_folder), versions)
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(result), 201


@bp.get("/latest")
def get_latest():
    data_folder = request.args.get("data_folder")
    if not data_folder:
        return jsonify({"error": "data_folder is required"}), 400
    try:
        latest = get_latest_comparison(Path(data_folder))
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 404

    return jsonify(latest)
