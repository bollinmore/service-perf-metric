from __future__ import annotations

from pathlib import Path
from typing import Dict

from src.lib.path_utils import ValidationError
from src.services.visualization import fetch_latest_outputs


def render_comparison(data_folder: Path) -> Dict[str, str] | Dict[str, str]:
    """
    Return data for UI rendering of comparison outputs.

    If no comparison exists, raise ValidationError to prompt selection of three versions.
    """
    return fetch_latest_outputs(data_folder)
