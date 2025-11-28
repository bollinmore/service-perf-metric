from __future__ import annotations

import zipfile
from pathlib import Path
from typing import List

from src.lib.path_utils import ValidationError


def validate_upload(zip_path: Path) -> str:
    """Validate a single zip contains `<tool-version>/PerformanceLog/*.log`."""
    if not zip_path.exists():
        raise ValidationError(f"Upload not found: {zip_path}")
    if not zipfile.is_zipfile(zip_path):
        raise ValidationError("Upload must be a zip file.")

    with zipfile.ZipFile(zip_path, "r") as zf:
        top_levels = set()
        has_log = False
        for name in zf.namelist():
            parts = Path(name).parts
            if not parts:
                continue
            top_levels.add(parts[0])
            if len(parts) >= 3 and parts[1] == "PerformanceLog" and parts[-1].endswith(".log"):
                has_log = True
        if len(top_levels) != 1:
            raise ValidationError("Upload must contain exactly one top-level version folder.")
        if not has_log:
            raise ValidationError("Upload must include PerformanceLog/*.log files.")
        return next(iter(top_levels))
