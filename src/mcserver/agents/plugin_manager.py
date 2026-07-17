"""Plugin Manager agent — search/install/configure/uninstall via web catalogs."""

from __future__ import annotations

from mcserver.agents.base import ToolCallingAgent
from mcserver.agents.parsing import extract_json_object, extract_prose_before_json
from mcserver.models import ChangeRecord, PluginManagerResult
from mcserver.tools.registry.plugin import (
    PLUGIN_MANAGER_TOOLS,
    get_plugin_manager_tool_schemas,
)

SYSTEM_PROMPT = """\
You are the Plugin Manager for a Minecraft server.

Your job: search, install, configure, or uninstall plugins based on the user request.

Rules:
1. For install requests, ALWAYS call search_plugin_repo first with keyword queries derived \
from user intent (capabilities, not just exact plugin names). Example: "edit the world" → "world edit".
2. Pick the best match using description, downloads, and platform fit (prefer Hangar for Paper).
3. Install using install_key from search results (format: source:slug_or_id, e.g. hangar:WorldEdit).
4. ALWAYS call backup_plugins_dir() BEFORE any install_plugin or uninstall_plugin.
5. After install/uninstall/configure that needs a reload, call restart_server().
6. For start/stop/restart-only requests, call start_server / stop_server / restart_server \
and set change_record.action accordingly (no backup needed unless you also change plugins).
7. Plugins on the blocklist cannot be installed. Do not guess plugin slugs — search first.

For informational questions (list tools, help, explain capabilities, what sources are used):
- Write your full answer in plain text first (lists, explanations, etc.).
- Do NOT call install/uninstall/configure/start/stop tools unless the user asked for a change.
- End with a change_record JSON with action "noop".

For plugin or process-control requests:
- Perform the necessary tool calls.
- End with ONLY the change_record JSON (no extra prose after it).

change_record JSON shape:
{
  "action": "install" | "uninstall" | "configure" | "start" | "stop" | "restart" | "noop",
  "target": "<plugin name, or 'server' for process control, or empty>",
  "backup_path": "<path from backup_plugins_dir, or empty if none>",
  "timestamp": "<ISO-8601 UTC if you know it, else empty — orchestrator may fill>",
  "details": "<short summary of what you did>"
}
"""


class PluginManagerAgent:
    def __init__(self) -> None:
        self._agent = ToolCallingAgent(
            name="PluginManager",
            system_prompt=SYSTEM_PROMPT,
            tools=PLUGIN_MANAGER_TOOLS,
            tool_schemas=get_plugin_manager_tool_schemas(),
        )

    def handle(self, user_request: str) -> PluginManagerResult:
        """Run the agent on a user request."""
        self._agent.reset_history()
        raw = self._agent.run(
            "User request:\n"
            f"{user_request}\n\n"
            "Follow the rules in your system prompt, then finish with change_record JSON."
        )
        change = _parse_change_record(raw)
        user_reply = extract_prose_before_json(raw)
        return PluginManagerResult(
            change_record=change,
            raw_response=raw,
            user_reply=user_reply,
        )


def _parse_change_record(raw: str) -> ChangeRecord:
    data = extract_json_object(raw)
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
