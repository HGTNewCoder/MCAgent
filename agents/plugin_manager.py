"""Plugin Manager agent — search/install/configure/uninstall with allowlist."""

from __future__ import annotations

import json
import re
from typing import Any

from agents.base import ToolCallingAgent
from models import ChangeRecord
from tools.plugin_tools import PLUGIN_MANAGER_TOOLS, get_plugin_manager_tool_schemas

SYSTEM_PROMPT = """\
You are the Plugin Manager for a Minecraft server.

Your job: search, install, configure, or uninstall plugins based on the user request.

Rules:
1. ONLY install plugins that appear in search_plugin_repo results (allowlist / vetted repo).
2. ALWAYS call backup_plugins_dir() BEFORE any install_plugin or uninstall_plugin.
3. After install/uninstall/configure that needs a reload, call restart_server().
4. Do not invent plugins outside the allowlist.
5. When finished, respond with ONLY a JSON object (no markdown fences) matching:
   {
     "action": "install" | "uninstall" | "configure" | "noop",
     "target": "<plugin name or empty>",
     "backup_path": "<path from backup_plugins_dir, or empty if none>",
     "timestamp": "<ISO-8601 UTC if you know it, else empty — orchestrator may fill>",
     "details": "<short summary of what you did>"
   }
This JSON is the change_record for the Verifier. Do not include other prose after it.
"""


class PluginManagerAgent:
    def __init__(self) -> None:
        self._agent = ToolCallingAgent(
            name="PluginManager",
            system_prompt=SYSTEM_PROMPT,
            tools=PLUGIN_MANAGER_TOOLS,
            tool_schemas=get_plugin_manager_tool_schemas(),
        )

    def handle(self, user_request: str) -> ChangeRecord:
        """Run the agent on a user request and parse a ChangeRecord."""
        # Fresh history per request so agents don't share / leak context
        self._agent.reset_history()
        raw = self._agent.run(
            "User request:\n"
            f"{user_request}\n\n"
            "Perform the necessary tool calls, then return the change_record JSON."
        )
        return _parse_change_record(raw)


def _parse_change_record(raw: str) -> ChangeRecord:
    data = _extract_json_object(raw)
    if not data:
        return ChangeRecord.now(
            action="noop",
            target="",
            backup_path="",
            details=f"Could not parse change_record from agent output: {raw[:500]}",
        )
    record = ChangeRecord.from_dict(data)
    if not record.timestamp:
        record = ChangeRecord.now(
            action=record.action,  # type: ignore[arg-type]
            target=record.target,
            backup_path=record.backup_path,
            details=record.details,
        )
    return record


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
