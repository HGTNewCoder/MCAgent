"""HTTP helpers for plugin catalog APIs (stdlib only)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from mcserver import config


def fetch_json(url: str, *, timeout: float = 15.0) -> Any:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": config.PLUGIN_HTTP_USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_bytes(url: str, *, timeout: float = 60.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": config.PLUGIN_HTTP_USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def http_error_message(exc: urllib.error.HTTPError) -> str:
    try:
        body = exc.read().decode("utf-8", errors="replace")[:200]
    except Exception:
        body = ""
    return f"HTTP {exc.code} for {exc.url}" + (f": {body}" if body else "")
