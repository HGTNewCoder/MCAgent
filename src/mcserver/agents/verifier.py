"""Verifier agent — independent health checks; rollback is the only write tool."""

from __future__ import annotations

import json
from typing import Any

from mcserver.agents.base import ToolCallingAgent
from mcserver.agents.parsing import extract_json_object
from mcserver.models import ChangeRecord, VerifierRunResult, VerifyResult
from mcserver.tools.registry.verifier import VERIFIER_TOOLS, get_verifier_tool_schemas

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

    def verify(self, change_record: ChangeRecord) -> VerifierRunResult:
        self._agent.reset_history()
        payload = json.dumps(change_record.to_dict(), indent=2)
        raw = self._agent.run(
            "Verify whether this change left the server healthy.\n"
            "Do NOT roll back in this pass — only report healthy/reason.\n\n"
            f"change_record:\n{payload}"
        )
        return VerifierRunResult(
            verify_result=_parse_verify_result(raw),
            raw_response=raw,
        )

    def rollback(self, backup_path: str) -> dict[str, Any]:
        """Orchestrator-driven rollback: invoke the tool directly and return its result."""
        fn = VERIFIER_TOOLS["rollback_last_change"]
        result = fn(backup_path=backup_path)
        print(f"[Verifier] rollback_last_change → {result}")
        return result


def _parse_verify_result(raw: str) -> VerifyResult:
    data = extract_json_object(raw)
    if not data:
        return VerifyResult(
            healthy=False,
            reason=f"Could not parse verifier output: {raw[:500]}",
        )
    return VerifyResult(
        healthy=bool(data.get("healthy", False)),
        reason=str(data.get("reason", "")),
    )
