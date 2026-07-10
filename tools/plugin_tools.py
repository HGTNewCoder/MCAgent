"""Plugin Manager tool registry (schemas + callables)."""

from __future__ import annotations

from typing import Any, Callable

from tools import stub_state

ToolFn = Callable[..., dict[str, Any]]

PLUGIN_MANAGER_TOOLS: dict[str, ToolFn] = {
    "search_plugin_repo": stub_state.search_plugin_repo,
    "backup_plugins_dir": stub_state.backup_plugins_dir,
    "install_plugin": stub_state.install_plugin,
    "uninstall_plugin": stub_state.uninstall_plugin,
    "configure_plugin": stub_state.configure_plugin,
    "restart_server": stub_state.restart_server,
}


def get_plugin_manager_tool_schemas() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "search_plugin_repo",
                "description": (
                    "Search the vetted plugin allowlist/repo. "
                    "Only allowlisted plugins can be installed."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (plugin name fragment).",
                        }
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "backup_plugins_dir",
                "description": (
                    "Backup the plugins directory. MUST be called before any "
                    "install or uninstall."
                ),
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "install_plugin",
                "description": (
                    "Install an allowlisted plugin by exact name. "
                    "Call backup_plugins_dir first."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Exact plugin name from the allowlist.",
                        }
                    },
                    "required": ["name"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "uninstall_plugin",
                "description": (
                    "Uninstall a plugin by name. Call backup_plugins_dir first."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Plugin name to uninstall.",
                        }
                    },
                    "required": ["name"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "configure_plugin",
                "description": "Set a configuration key/value for a plugin.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Plugin name."},
                        "key": {"type": "string", "description": "Config key."},
                        "value": {"type": "string", "description": "Config value."},
                    },
                    "required": ["name", "key", "value"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "restart_server",
                "description": "Restart the Minecraft server process after changes.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
    ]
