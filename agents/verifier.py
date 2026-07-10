"""Verifier agent — independent health checks; rollback is the only write tool."""

from __future__ import annotations

import json
import re
from typing import Any

from agents.base import ToolCallingAgent
from models import ChangeRecord, VerifyResult
from tools.verifier_tools import VERIFIER_TOOLS, get_verifier_tool_schemas

SYSTEM_PROMPT = """\
You are the Verifier for a Minecraft server. You do NOT share context with the Plugin Manager.

Your job: independently decide whether the last change left the server healthy.

You have read tools plus rollback_last_change. For a normal verification pass:
1. check_process_alive()
2. read_server_log(lines) and look for FATAL / severe errors
3. If change_record.action is install/uninstall/configure and target is set,
   check_plugin_loaded(target) as appropriate (loaded after install; not loaded after uninstall)
4. run_smoke_test()
5. Do NOT call rollback_last_change unless the user/orchestrator message explicitly asks you to roll back.

When finished verifying (not rolling back), respond with ONLY a JSON object (no markdown fences):
{
  "healthy": true | false,
  "reason": "<short explanation citing what you checked>"
}
"""


class VerifierAgent:
    def __init__(self) -> None:
        self._agent = ToolCallingAgent(
            name="Verifier",
            system_prompt=SYSTEM_PROMPT,
            tools=VERIFIER_TOOLS,
            tool_schemas=get_verifier_tool_schemas(),
        )

    def verify(self, change_record: ChangeRecord) -> VerifyResult:
        self._agent.reset_history()
        payload = json.dumps(change_record.to_dict(), indent=2)
        raw = self._agent.run(
            "Verify whether this change left the server healthy.\n"
            "Do NOT roll back in this pass — only report healthy/reason.\n\n"
            f"change_record:\n{payload}"
        )
        return _parse_verify_result(raw)

    def rollback(self, backup_path: str) -> dict[str, Any]:
        """Orchestrator-driven rollback: call the rollback tool via a short agent turn."""
        self._agent.reset_history()
        raw = self._agent.run(
            "The server is unhealthy. Call rollback_last_change exactly once with "
            f'backup_path="{backup_path}", then briefly confirm what you did in plain text.'
        )
        return {"ok": True, "agent_message": raw}


def _parse_verify_result(raw: str) -> VerifyResult:
    data = _extract_json_object(raw)
    if not data:
        return VerifyResult(
            healthy=False,
            reason=f"Could not parse verifier output: {raw[:500]}",
        )
    return VerifyResult(
        healthy=bool(data.get("healthy", False)),
        reason=str(data.get("reason", "")),
    )


def _extract_json_object(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None
    try:
        obj = json.loads(match.group(0))
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None
