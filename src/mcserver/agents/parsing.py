"""Parse agent text responses: JSON contracts + user-facing prose."""

from __future__ import annotations

import json
import re
from typing import Any

_FENCED_JSON_TAIL = re.compile(
    r"```(?:json)?\s*\{[\s\S]*?\}\s*```\s*$",
    re.IGNORECASE,
)
_BARE_JSON_TAIL = re.compile(r"\{[\s\S]*\}\s*$")


def extract_json_object(text: str) -> dict[str, Any] | None:
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


def extract_prose_before_json(text: str) -> str:
    """Return human-readable text with trailing change_record JSON removed."""
    text = text.strip()
    if not text:
        return ""
    # Remove fenced ```json { ... } ``` at end (common model habit).
    text = _FENCED_JSON_TAIL.sub("", text).strip()
    # Remove bare { ... } change_record at end.
    text = _BARE_JSON_TAIL.sub("", text).strip()
    return text
