from __future__ import annotations

import pytest

from src.lib.path_utils import ValidationError
from src.services.validation import require_exact_three, require_present
from src.services.version_pool import require_versions_available, VersionStatus


def test_require_exact_three_valid():
    assert require_exact_three(["a", "b", "c"]) == ["a", "b", "c"]


def test_require_exact_three_invalid_count():
    with pytest.raises(ValidationError):
        require_exact_three(["a", "b"])
    with pytest.raises(ValidationError):
        require_exact_three(["a", "b", "c", "d"])


def test_require_exact_three_duplicates():
    with pytest.raises(ValidationError):
        require_exact_three(["a", "a", "b"])


def test_require_present_missing():
    with pytest.raises(ValidationError):
        require_present(["a", "b"], ["a"])


def test_require_versions_available_flags_missing_artifacts():
    pool = [
        VersionStatus(version_id="a", path=None, summary_path=None, status="available"),  # type: ignore[arg-type]
        VersionStatus(version_id="b", path=None, summary_path=None, status="missing_artifacts"),  # type: ignore[arg-type]
    ]
    with pytest.raises(ValidationError):
        require_versions_available(["a", "b", "c"], pool)
