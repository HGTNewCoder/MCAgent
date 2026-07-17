"""Tests for plugin install (stub mode and mocked download)."""

from __future__ import annotations

from unittest.mock import patch

from mcserver import config
from mcserver.tools import stub_state
from mcserver.tools.plugins.models import PluginCandidate


def test_install_uses_stub_when_not_real(isolated_server, monkeypatch) -> None:
    monkeypatch.setattr(config, "MC_PROCESS_MODE", "stub")

    result = stub_state.install_plugin("hangar:WorldEdit")

    assert result["ok"] is True
    assert result["note"] == "stub"
    jar = config.PLUGINS_DIR / "WorldEdit.jar"
    assert jar.read_text(encoding="utf-8").startswith("stub-jar:")


def test_install_downloads_in_real_mode(isolated_server, monkeypatch) -> None:
    monkeypatch.setattr(config, "MC_PROCESS_MODE", "real")
    cache = isolated_server / "cache"
    cache.mkdir(parents=True)
    monkeypatch.setattr(config, "PLUGIN_CACHE_DIR", cache)
    (isolated_server / "server.jar").write_bytes(b"fake-paper")
    monkeypatch.setattr(config, "MC_SERVER_JAR", "server.jar")

    candidate = PluginCandidate(
        install_key="hangar:WorldEdit",
        name="WorldEdit",
        slug="WorldEdit",
        source="hangar",
        description="",
        download_url="https://example.com/WorldEdit.jar",
    )

    with patch(
        "mcserver.tools.plugins.resolver.resolve_install_key",
        return_value=(candidate, None),
    ), patch(
        "mcserver.tools.plugins.download.fetch_bytes",
        return_value=b"PK" + b"\x00" * 2000,
    ):
        result = stub_state.install_plugin("hangar:WorldEdit")

    assert result["ok"] is True
    assert "Downloaded from hangar" in result["note"]
    dest = config.PLUGINS_DIR / "WorldEdit.jar"
    assert dest.exists()
    assert dest.stat().st_size >= 1000


def test_install_fails_on_bad_download(isolated_server, monkeypatch) -> None:
    monkeypatch.setattr(config, "MC_PROCESS_MODE", "real")
    monkeypatch.setattr(config, "PLUGIN_CACHE_DIR", isolated_server / "cache")
    (isolated_server / "server.jar").write_bytes(b"fake-paper")
    monkeypatch.setattr(config, "MC_SERVER_JAR", "server.jar")

    candidate = PluginCandidate(
        install_key="hangar:WorldEdit",
        name="WorldEdit",
        slug="WorldEdit",
        source="hangar",
        description="",
        download_url="https://example.com/WorldEdit.jar",
    )

    with patch(
        "mcserver.tools.plugins.resolver.resolve_install_key",
        return_value=(candidate, None),
    ), patch(
        "mcserver.tools.plugins.download.fetch_bytes",
        return_value=b"too-small",
    ):
        result = stub_state.install_plugin("hangar:WorldEdit")

    assert result["ok"] is False
    assert "small" in result["error"].lower() or "zip" in result["error"].lower()
