"""Verifier tool registry (schemas + callables). Read-mostly + rollback only."""

from __future__ import annotations

from typing import Any, Callable

from mcserver.tools.stub import state as stub_state

ToolFn = Callable[..., dict[str, Any]]

VERIFIER_TOOLS: dict[str, ToolFn] = {
    "read_server_log": stub_state.read_server_log,
    "check_process_alive": stub_state.check_process_alive,
    "check_plugin_loaded": stub_state.check_plugin_loaded,
    "run_smoke_test": stub_state.run_smoke_test,
    "rollback_last_change": stub_state.rollback_last_change,
}


def get_verifier_tool_schemas() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "read_server_log",
                "description": "Read the last N lines of the server console log.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lines": {
                            "type": "integer",
                            "description": "Number of trailing log lines (default 50).",
                        }
                    },
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "check_process_alive",
                "description": "Check whether the Minecraft server process is running.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "check_plugin_loaded",
                "description": "Check whether a named plugin is loaded by the server.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Plugin name to check.",
                        }
                    },
                    "required": ["name"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "run_smoke_test",
                "description": (
                    "Smoke test: server boots and no fatal console error within N seconds."
                ),
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "rollback_last_change",
                "description": (
                    "Restore plugins from backup_path and restart the server. "
                    "Only use when the orchestrator asks you to roll back, or when "
                    "you are explicitly instructed to remediate an unhealthy state."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "backup_path": {
                            "type": "string",
                            "description": "Path from change_record.backup_path.",
                        }
                    },
                    "required": ["backup_path"],
                },
            },
        },
    ]
