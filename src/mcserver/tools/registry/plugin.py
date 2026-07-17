"""Plugin Manager tool registry (schemas + callables)."""

from __future__ import annotations

from typing import Any, Callable

from mcserver.tools.stub import state as stub_state

ToolFn = Callable[..., dict[str, Any]]

PLUGIN_MANAGER_TOOLS: dict[str, ToolFn] = {
    "search_plugin_repo": stub_state.search_plugin_repo,
    "backup_plugins_dir": stub_state.backup_plugins_dir,
    "install_plugin": stub_state.install_plugin,
    "uninstall_plugin": stub_state.uninstall_plugin,
    "configure_plugin": stub_state.configure_plugin,
    "start_server": stub_state.start_server,
    "stop_server": stub_state.stop_server,
    "restart_server": stub_state.restart_server,
}


def get_plugin_manager_tool_schemas() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "search_plugin_repo",
                "description": (
                    "Search Hangar, Modrinth, and SpigotMC for plugins matching the query. "
                    "Returns install_key handles for install_plugin."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": (
                                "Search query — use keywords from user intent "
                                "(e.g. 'world edit', 'permissions', 'economy')."
                            ),
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
                    "Install a plugin by install_key from search_plugin_repo results "
                    "(format: source:slug_or_id, e.g. hangar:WorldEdit). "
                    "Downloads the jar from the catalog in real server mode. "
                    "Call backup_plugins_dir first."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "install_key": {
                            "type": "string",
                            "description": (
                                "Install key from search results, e.g. hangar:WorldEdit, "
                                "modrinth:worldedit, spigot:9208."
                            ),
                        }
                    },
                    "required": ["install_key"],
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
                "name": "start_server",
                "description": "Start the Minecraft server process if it is not already running.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "stop_server",
                "description": "Stop the Minecraft server process gracefully (then force-kill if needed).",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "restart_server",
                "description": (
                    "Restart the Minecraft server process (stop then start). "
                    "Use after install/uninstall/configure that needs a reload."
                ),
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
    ]
