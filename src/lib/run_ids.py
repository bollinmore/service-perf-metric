from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4


def generate_run_id(prefix: str = "cmp") -> str:
    """Generate a unique run identifier for comparison executions."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{prefix}-{ts}-{uuid4().hex[:8]}"
