"""Shared data models for the two-agent Minecraft management flow."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Literal


Action = Literal["install", "uninstall", "configure", "noop"]
RunMode = Literal["info", "change"]


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
class PluginManagerResult:
    """Plugin Manager agent output: structured change + full text reply."""

    change_record: ChangeRecord
    raw_response: str
    user_reply: str


@dataclass
class VerifierRunResult:
    """Verifier agent output: structured verdict + full text reply."""

    verify_result: VerifyResult
    raw_response: str


@dataclass
class OrchestratorResult:
    """Final report returned to the user by the plain-code orchestrator."""

    success: bool
    message: str
    mode: RunMode
    change_record: ChangeRecord | None
    verify_result: VerifyResult | None
    plugin_manager_reply: str = ""
    verifier_reply: str = ""
    rolled_back: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "message": self.message,
            "mode": self.mode,
            "change_record": self.change_record.to_dict() if self.change_record else None,
            "verify_result": self.verify_result.to_dict() if self.verify_result else None,
            "plugin_manager_reply": self.plugin_manager_reply,
            "verifier_reply": self.verifier_reply,
            "rolled_back": self.rolled_back,
        }
