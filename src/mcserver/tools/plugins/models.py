"""Shared types for the plugin catalog."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class PluginCandidate:
    install_key: str
    name: str
    slug: str
    source: str
    description: str
    downloads: int = 0
    page_url: str = ""
    download_url: str = ""
    platforms: list[str] = field(default_factory=list)
    version: str = ""
    warning: str = ""

    def to_match_dict(self) -> dict:
        """Shape returned to the LLM from search_plugin_repo."""
        data = asdict(self)
        data.pop("download_url", None)
        return data
