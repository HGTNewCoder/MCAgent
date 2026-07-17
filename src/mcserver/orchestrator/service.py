"""Deterministic orchestrator — plain code, not an LLM router.

Flow:
  user request → Plugin Manager → change_record →
    info request → report answer (skip Verifier)
    change request → Verifier → healthy / rollback
"""

from __future__ import annotations

from mcserver.agents.plugin_manager import PluginManagerAgent
from mcserver.agents.verifier import VerifierAgent
from mcserver.models import OrchestratorResult
from mcserver.orchestrator.routing import is_info_request
from mcserver.tools import stub_state
from mcserver.tools.catalog import format_tool_catalog


class Orchestrator:
    def __init__(
        self,
        plugin_manager: PluginManagerAgent | None = None,
        verifier: VerifierAgent | None = None,
    ) -> None:
        stub_state.ensure_mock_layout()
        self.plugin_manager = plugin_manager or PluginManagerAgent()
        self.verifier = verifier or VerifierAgent()

    def handle(self, user_request: str) -> OrchestratorResult:
        info_mode = is_info_request(user_request)

        print("[Orchestrator] Plugin Manager…")
        pm = self.plugin_manager.handle(user_request)
        change = pm.change_record

        if info_mode:
            print("[Orchestrator] info mode — skipping Verifier")
            reply = pm.user_reply.strip()
            if not reply or len(reply) < 40:
                reply = format_tool_catalog()
            return OrchestratorResult(
                success=True,
                message=reply,
                mode="info",
                change_record=change,
                verify_result=None,
                rolled_back=False,
            )

        print("[Orchestrator] Verifier…")
        vr = self.verifier.verify(change)
        verify = vr.verify_result

        if verify.healthy:
            summary = (
                f"Success. {change.details or change.action} "
                f"(target={change.target or 'n/a'}). "
                f"Verifier: {verify.reason}"
            )
            return OrchestratorResult(
                success=True,
                message=summary,
                mode="change",
                change_record=change,
                verify_result=verify,
                plugin_manager_reply=pm.user_reply,
                rolled_back=False,
            )

        print("[Orchestrator] unhealthy — rolling back…")
        rolled_back = False
        rollback_note = "No backup available to roll back."
        if change.backup_path:
            rb = self.verifier.rollback(change.backup_path)
            rolled_back = bool(rb.get("ok"))
            if rolled_back:
                stub_state.restart_server()
                rollback_note = "Rolled back and restarted."
            else:
                err = rb.get("error") or rb
                print(f"[Orchestrator] rollback failed: {err}")
                rollback_note = f"Rollback failed: {err}."
        else:
            print("[Orchestrator] no backup_path; skipping rollback")

        message = (
            f"Failure after change ({change.action} {change.target}). "
            f"Reason: {verify.reason}. "
            f"{rollback_note}"
        )
        return OrchestratorResult(
            success=False,
            message=message,
            mode="change",
            change_record=change,
            verify_result=verify,
            plugin_manager_reply=pm.user_reply,
            rolled_back=rolled_back,
        )
