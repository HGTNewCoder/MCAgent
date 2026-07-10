"""Deterministic orchestrator — plain code, not an LLM router.

Flow:
  user request → Plugin Manager → change_record → Verifier →
    healthy  → success report
    unhealthy → rollback + restart → failure report
"""

from __future__ import annotations

from agents.plugin_manager import PluginManagerAgent
from agents.verifier import VerifierAgent
from models import OrchestratorResult
from tools import stub_state


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
        print("[Orchestrator] 1/4 Plugin Manager…")
        change = self.plugin_manager.handle(user_request)
        print(f"[Orchestrator] change_record={change.to_dict()}")

        print("[Orchestrator] 2/4 Verifier…")
        verify = self.verifier.verify(change)
        print(f"[Orchestrator] verify={verify.to_dict()}")

        if verify.healthy:
            summary = (
                f"Success. {change.details or change.action} "
                f"(target={change.target or 'n/a'}). "
                f"Verifier: {verify.reason}"
            )
            return OrchestratorResult(
                success=True,
                message=summary,
                change_record=change,
                verify_result=verify,
                rolled_back=False,
            )

        # Unhealthy → rollback + restart, then report
        print("[Orchestrator] 3/4 unhealthy — rolling back…")
        rolled_back = False
        if change.backup_path:
            rb = self.verifier.rollback(change.backup_path)
            rolled_back = bool(rb.get("ok"))
            # Explicit restart after rollback (rollback stub already restarts;
            # keep an extra restart for the real-tool path later).
            stub_state.restart_server()
        else:
            print("[Orchestrator] no backup_path; skipping rollback")

        print("[Orchestrator] 4/4 reporting failure")
        message = (
            f"Failure after change ({change.action} {change.target}). "
            f"Reason: {verify.reason}. "
            f"{'Rolled back and restarted.' if rolled_back else 'No backup available to roll back.'}"
        )
        return OrchestratorResult(
            success=False,
            message=message,
            change_record=change,
            verify_result=verify,
            rolled_back=rolled_back,
        )
