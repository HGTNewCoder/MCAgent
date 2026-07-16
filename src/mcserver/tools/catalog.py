"""Static tool catalog for info-mode fallback answers."""

from __future__ import annotations

from mcserver.tools.registry.plugin import get_plugin_manager_tool_schemas
from mcserver.tools.registry.verifier import get_verifier_tool_schemas


def _names(schemas: list) -> list[str]:
    return [s["function"]["name"] for s in schemas]


def format_tool_catalog() -> str:
    pm = _names(get_plugin_manager_tool_schemas())
    vf = _names(get_verifier_tool_schemas())
    lines = [
        "Plugin Manager tools:",
        *[f"  - {n}" for n in pm],
        "",
        "Verifier tools:",
        *[f"  - {n}" for n in vf],
    ]
    return "\n".join(lines)
