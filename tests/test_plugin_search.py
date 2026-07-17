"""Tests for web-based plugin search and install."""

from __future__ import annotations

from mcserver import config
from mcserver.tools import stub_state
from mcserver.tools.plugins import hangar, modrinth, resolver, spigot
from mcserver.tools.plugins.models import PluginCandidate


HANGAR_SEARCH = {
    "result": [
        {
            "namespace": {"name": "EngineHub"},
            "name": "WorldEdit",
            "description": "In-game world editor",
            "stats": {"downloads": 50000},
        }
    ]
}

MODRINTH_SEARCH = {
    "hits": [
        {
            "slug": "worldedit",
            "title": "WorldEdit",
            "description": "World editing plugin",
            "downloads": 100000,
        }
    ]
}

SPIGET_SEARCH = [
    {
        "id": 9208,
        "name": "WorldEdit",
        "tag": "World editing",
        "downloads": 200000,
        "premium": False,
        "external": False,
    }
]

HANGAR_RESOLVE_PROJECT = {
    "namespace": {"name": "EngineHub"},
    "name": "WorldEdit",
    "description": "In-game world editor",
    "stats": {"downloads": 50000},
}

HANGAR_VERSIONS = [{"name": "7.3.0", "platforms": {"PAPER": ["1.21", "1.20"]}}]

HANGAR_VERSION_DETAIL = {
    "downloads": {
        "PAPER": {
            "downloadUrl": "https://hangarcdn.papermc.io/plugins/WorldEdit.jar",
        }
    }
}


def test_search_merges_sources(isolated_server, monkeypatch) -> None:
    def fake_search_all(query: str) -> dict:
        return {
            "ok": True,
            "query": query,
            "matches": [m.to_match_dict() for m in hangar_results() + modrinth_results()],
            "source_errors": [],
            "note": "test",
        }

    monkeypatch.setattr("mcserver.tools.plugins.resolver.search_all", fake_search_all)

    result = stub_state.search_plugin_repo("world edit")

    assert result["ok"] is True
    assert len(result["matches"]) >= 2
    names = {m["name"] for m in result["matches"]}
    assert "WorldEdit" in names
    keys = {m["install_key"] for m in result["matches"]}
    assert "hangar:WorldEdit" in keys


def test_install_stub_mode_uses_install_key(isolated_server, monkeypatch) -> None:
    monkeypatch.setattr(config, "MC_PROCESS_MODE", "stub")

    result = stub_state.install_plugin("hangar:WorldEdit")

    assert result["ok"] is True
    assert result["note"] == "stub"
    assert (config.PLUGINS_DIR / "WorldEdit.jar").exists()


def test_install_blocklisted_rejected(isolated_server, monkeypatch) -> None:
    monkeypatch.setattr(config, "MC_PROCESS_MODE", "stub")
    monkeypatch.setattr(config, "PLUGIN_BLOCKLIST", frozenset({"worldedit"}))

    result = stub_state.install_plugin("hangar:WorldEdit")

    assert result["ok"] is False
    assert "blocklist" in result["error"].lower()


def test_resolve_install_key_hangar(isolated_server, monkeypatch) -> None:
    monkeypatch.setattr("mcserver.tools.plugins.hangar.fetch_json", _mock_fetch_json)

    candidate, err = resolver.resolve_install_key("hangar:WorldEdit")

    assert err is None
    assert candidate is not None
    assert candidate.download_url.endswith("WorldEdit.jar")
    assert candidate.source == "hangar"


def test_spigot_premium_rejected(isolated_server, monkeypatch) -> None:
    monkeypatch.setattr(
        "mcserver.tools.plugins.spigot.fetch_json",
        lambda url: {"id": 1, "name": "PremiumPlugin", "premium": True},
    )

    candidate, err = spigot.resolve("1")

    assert candidate is None
    assert "premium" in (err or "").lower()


def hangar_results():
    return [
        PluginCandidate(
            install_key="hangar:WorldEdit",
            name="WorldEdit",
            slug="WorldEdit",
            source="hangar",
            description="In-game world editor",
            downloads=50000,
        )
    ]


def modrinth_results():
    return [
        PluginCandidate(
            install_key="modrinth:worldedit",
            name="WorldEdit",
            slug="worldedit",
            source="modrinth",
            description="World editing plugin",
            downloads=100000,
        )
    ]


def spigot_results():
    return [
        PluginCandidate(
            install_key="spigot:9208",
            name="WorldEdit",
            slug="9208",
            source="spigot",
            description="World editing",
            downloads=200000,
        )
    ]


def _mock_fetch_json(url: str):
    if url.endswith("/projects/WorldEdit"):
        return HANGAR_RESOLVE_PROJECT
    if url.endswith("/projects/WorldEdit/versions") and "/versions/" not in url.split("WorldEdit")[-1]:
        return HANGAR_VERSIONS
    if "/versions/7.3.0" in url:
        return HANGAR_VERSION_DETAIL
    raise AssertionError(f"Unexpected URL: {url}")
