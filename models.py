"""Shared data models for the two-agent Minecraft management flow."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Literal


Action = Literal["install", "uninstall", "configure", "noop"]


@dataclass
class ChangeRecord:
    """Produced by Plugin Manager; consumed by Verifier."""

    action: Action
    target: str
    backup_path: str
    timestamp: str
    details: str = ""

    @classmethod
    def now(
        cls,
        action: Action,
        target: str,
        backup_path: str,
        details: str = "",
    ) -> ChangeRecord:
        return cls(
            action=action,
            target=target,
            backup_path=backup_path,
            timestamp=datetime.now(timezone.utc).isoformat(),
            details=details,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChangeRecord:
        return cls(
            action=data.get("action", "noop"),
            target=data.get("target", ""),
            backup_path=data.get("backup_path", ""),
            timestamp=data.get("timestamp", ""),
            details=data.get("details", ""),
        )


@dataclass
class VerifyResult:
    """Produced by Verifier after independent health checks."""

    healthy: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OrchestratorResult:
    """Final report returned to the user by the plain-code orchestrator."""

    success: bool
    message: str
    change_record: ChangeRecord | None
    verify_result: VerifyResult | None
    rolled_back: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "message": self.message,
            "change_record": self.change_record.to_dict() if self.change_record else None,
            "verify_result": self.verify_result.to_dict() if self.verify_result else None,
            "rolled_back": self.rolled_back,
        }
