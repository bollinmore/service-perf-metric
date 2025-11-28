from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import os

from src import config


@dataclass
class VersionSnapshot:
    id: str
    timestamp: datetime
    notes: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "notes": self.notes or "",
        }


@dataclass
class ReadinessItem:
    name: str
    required: bool
    status: str
    message: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "required": self.required,
            "status": self.status,
            "message": self.message,
        }


@dataclass
class ReadinessStatus:
    items: List[ReadinessItem] = field(default_factory=list)

    @property
    def all_complete(self) -> bool:
        return all(
            (not item.required) or item.status == "complete" for item in self.items
        )

    def to_dict(self) -> dict:
        return {
            "items": [item.to_dict() for item in self.items],
            "allComplete": self.all_complete,
        }


@dataclass
class ModeStatus:
    mode: str
    source: str
    validated: bool
    snapshot: Optional[VersionSnapshot] = None
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        payload = {
            "mode": self.mode,
            "source": self.source,
            "validated": self.validated,
        }
        if self.snapshot:
            payload["snapshot"] = self.snapshot.to_dict()
        if self.warnings:
            payload["warnings"] = self.warnings
        return payload


class ModeService:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self._resolution = config.resolve_mode()
        config.apply_mode_env(self._resolution)
        self._status = ModeStatus(
            mode=self._resolution.mode,
            source=self._resolution.source,
            validated=False,
            snapshot=None,
            warnings=self._resolution.warnings.copy(),
        )
        self._readiness = self._build_readiness_status()

    def _build_readiness_status(self) -> ReadinessStatus:
        result_dir = Path(os.environ.get("SPM_RESULT_ROOT", self.project_root / "result"))
        summary_path = result_dir / "summary.csv"
        items = [
            ReadinessItem(
                name="Mode set to production",
                required=True,
                status="complete" if self._status.mode == "production" else "pending",
                message="Automatically complete when SPM_MODE=production is active.",
            ),
            ReadinessItem(
                name="Summary data available",
                required=True,
                status="complete" if summary_path.exists() else "pending",
                message="summary.csv must exist for production readiness.",
            ),
        ]
        return ReadinessStatus(items)

    def current_status(self) -> ModeStatus:
        return self._status

    def readiness_status(self) -> ReadinessStatus:
        self._readiness = self._build_readiness_status()
        if self._status.mode == "production":
            self._status.validated = self._readiness.all_complete
        else:
            self._status.validated = False
        return self._readiness

    @property
    def docker_forced(self) -> bool:
        return self._resolution.docker_forced

    def capture_snapshot(self, notes: str | None = None) -> VersionSnapshot:
        now = datetime.now(timezone.utc)
        snapshot_id = now.strftime("dev-%Y%m%d-%H%M%S")
        snapshot = VersionSnapshot(id=snapshot_id, timestamp=now, notes=notes)
        self._status.snapshot = snapshot
        return snapshot

    def set_mode(self, mode: str, notes: str | None = None) -> ModeStatus:
        target = (mode or "").strip().lower()
        if self._resolution.docker_forced:
            self._status.mode = "production"
            self._status.source = "docker-forced"
            self._status.warnings = ["Mode changes are locked in Docker; forcing production."]
            self.readiness_status()
            print("[mode] Docker environment detected; forcing production mode.")
            return self._status

        if target not in config.ALLOWED_MODES:
            self._status.mode = "development"
            self._status.source = "env"
            self._status.warnings = [
                "Invalid mode requested; defaulting to development."
            ]
            self.readiness_status()
            print("[mode] Invalid mode request received; falling back to development.")
            return self._status

        if target == "production":
            if not self._status.snapshot:
                self.capture_snapshot(notes)
            print("[mode] Switching to production mode with preserved development snapshot.")
        self._status.mode = target
        self._status.source = "env"
        self._status.warnings = []
        self.readiness_status()
        config.apply_mode_env(
            config.ModeResolution(
                mode=self._status.mode,
                source=self._status.source,
                warnings=self._status.warnings.copy(),
                docker_forced=False,
            )
        )
        print(f"[mode] Mode set to {self._status.mode} (source={self._status.source}).")
        return self._status

    def revert_to_development(self) -> ModeStatus:
        self._status.mode = "development"
        self._status.source = "env"
        self._status.validated = False
        self._status.warnings = []
        self.readiness_status()
        print("[mode] Reverted to development mode using preserved snapshot (if available).")
        config.apply_mode_env(
            config.ModeResolution(
                mode=self._status.mode,
                source=self._status.source,
                warnings=self._status.warnings.copy(),
                docker_forced=False,
            )
        )
        return self._status


_service: ModeService | None = None


def get_mode_service(project_root: Path) -> ModeService:
    global _service
    if _service is None:
        _service = ModeService(project_root)
    return _service
