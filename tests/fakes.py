"""Test doubles for Plugin Manager and Verifier — no live LLM."""

from __future__ import annotations

from mcserver.models import ChangeRecord, PluginManagerResult, VerifierRunResult, VerifyResult
from mcserver.tools import stub_state


class FakePluginManager:
    """Returns a fixed PluginManagerResult; records requests."""

    def __init__(self, result: PluginManagerResult) -> None:
        self.result = result
        self.requests: list[str] = []

    def handle(self, user_request: str) -> PluginManagerResult:
        self.requests.append(user_request)
        return self.result


class FakeVerifier:
    """Returns a fixed VerifyResult; optionally delegates rollback to stub tools."""

    def __init__(
        self,
        *,
        verify_result: VerifyResult,
        use_real_rollback: bool = False,
        rollback_ok: bool = True,
    ) -> None:
        self.verify_result = verify_result
        self.use_real_rollback = use_real_rollback
        self.rollback_ok = rollback_ok
        self.verify_calls: list[ChangeRecord] = []
        self.rollback_calls: list[str] = []

    def verify(self, change_record: ChangeRecord) -> VerifierRunResult:
        self.verify_calls.append(change_record)
        return VerifierRunResult(verify_result=self.verify_result, raw_response="fake")

    def rollback(self, backup_path: str) -> dict:
        self.rollback_calls.append(backup_path)
        if self.use_real_rollback:
            return stub_state.rollback_last_change(backup_path)
        if self.rollback_ok:
            return {"ok": True}
        return {"ok": False, "error": "simulated rollback failure"}


class StubPluginManager:
    """Runs real stub install flow (backup → install → restart) without an LLM."""

    def __init__(self, install_key: str = "hangar:WorldEdit", plugin_name: str = "WorldEdit") -> None:
        self.install_key = install_key
        self.plugin_name = plugin_name
        self.requests: list[str] = []

    def handle(self, user_request: str) -> PluginManagerResult:
        self.requests.append(user_request)
        backup = stub_state.backup_plugins_dir()
        install_result = stub_state.install_plugin(self.install_key)
        if not install_result.get("ok"):
            raise RuntimeError(f"install_plugin failed: {install_result}")
        stub_state.restart_server()
        change = ChangeRecord.now(
            action="install",
            target=self.plugin_name,
            backup_path=backup["backup_path"],
            details=f"Installed {self.plugin_name}",
        )
        return PluginManagerResult(
            change_record=change,
            raw_response='{"action": "install"}',
            user_reply=f"Installed {self.plugin_name} and restarted the server.",
        )
