"""Deterministic request routing helpers for the orchestrator."""

from __future__ import annotations

import re

# Plain-code detection for questions that should not run the Verifier.
_INFO_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\blist\b.*\btools?\b",
        r"\bwhat\b.*\btools?\b",
        r"\bwhich\b.*\btools?\b",
        r"\bshow\b.*\btools?\b",
        r"\bhelp\b",
        r"\bexplain\b",
        r"\bhow do (you|i)\b",
        r"\bwhat can you\b",
        r"\bwhat are you\b",
        r"\bwhat plugins?\b.*\b(available|allowlist|allowed)\b",
        r"\bshow\b.*\b(plugins?|allowlist)\b",
    )
)


def is_info_request(user_request: str) -> bool:
    """True when the user is asking for information, not a server change."""
    text = user_request.strip()
    if not text:
        return False
    return any(p.search(text) for p in _INFO_PATTERNS)
