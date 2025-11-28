from __future__ import annotations

from pathlib import Path
from typing import Dict

from src.lib.path_utils import ValidationError
from src.services.comparison import get_latest_comparison


def fetch_latest_outputs(data_folder: Path) -> Dict[str, str]:
    """
    Return paths to the latest comparison outputs for visualization/download.

    Raises ValidationError if no comparison exists.
    """
    latest = get_latest_comparison(data_folder)
    return latest["outputs"]
