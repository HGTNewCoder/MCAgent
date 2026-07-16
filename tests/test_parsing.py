"""Tests for agent response parsing."""

from mcserver.agents.parsing import extract_json_object, extract_prose_before_json
from mcserver.orchestrator.routing import is_info_request


def test_extract_prose_strips_fenced_json() -> None:
    raw = "Hello tools\n\n```json\n{\"action\": \"noop\"}\n```"
    assert extract_prose_before_json(raw) == "Hello tools"
    assert extract_json_object(raw)["action"] == "noop"


def test_is_info_request() -> None:
    assert is_info_request("List all tools that you have access to")
    assert not is_info_request("Install WorldEdit")
