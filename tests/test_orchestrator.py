"""Integration tests for Orchestrator — fake agents, real stub tools."""

from __future__ import annotations

from mcserver import config
from mcserver.models import ChangeRecord, PluginManagerResult, VerifyResult
from mcserver.orchestrator import Orchestrator
from tests.fakes import FakePluginManager, FakeVerifier, StubPluginManager


def test_info_mode_skips_verifier(isolated_server) -> None:
    pm = FakePluginManager(
        PluginManagerResult(
            change_record=ChangeRecord.now("noop", "", "", "No changes made."),
            raw_response="noop",
            user_reply="Allowed sources: hangar, modrinth, spigot. Search finds plugins by intent.",
        )
    )
    verifier = FakeVerifier(verify_result=VerifyResult(healthy=True, reason="should not run"))

    result = Orchestrator(plugin_manager=pm, verifier=verifier).handle(
        "What plugins are allowed on this server?"
    )

    assert result.success is True
    assert result.mode == "info"
    assert result.verify_result is None
    assert result.rolled_back is False
    assert pm.requests == ["What plugins are allowed on this server?"]
    assert verifier.verify_calls == []


def test_healthy_change_succeeds(isolated_server, monkeypatch) -> None:
    monkeypatch.setattr(config, "MC_PROCESS_MODE", "stub")
    pm = StubPluginManager("hangar:WorldEdit", "WorldEdit")
    verifier = FakeVerifier(
        verify_result=VerifyResult(healthy=True, reason="process alive; plugin loaded; smoke test passed")
    )

    result = Orchestrator(plugin_manager=pm, verifier=verifier).handle("Install WorldEdit")

    assert result.success is True
    assert result.mode == "change"
    assert result.verify_result is not None
    assert result.verify_result.healthy is True
    assert result.rolled_back is False
    jars = list(config.PLUGINS_DIR.glob("*.jar"))
    assert jars, f"No plugin jars in {config.PLUGINS_DIR}"
    assert jars[0].stem == "WorldEdit"
    assert len(verifier.verify_calls) == 1
    assert verifier.verify_calls[0].action == "install"
    assert verifier.verify_calls[0].target == "WorldEdit"
    assert verifier.rollback_calls == []


def test_unhealthy_change_rolls_back(isolated_server, monkeypatch) -> None:
    monkeypatch.setattr(config, "MC_PROCESS_MODE", "stub")
    pm = StubPluginManager("hangar:WorldEdit", "WorldEdit")
    verifier = FakeVerifier(
        verify_result=VerifyResult(healthy=False, reason="FATAL in server log"),
        use_real_rollback=True,
    )

    result = Orchestrator(plugin_manager=pm, verifier=verifier).handle("Install WorldEdit")

    assert result.success is False
    assert result.mode == "change"
    assert result.rolled_back is True
    assert result.verify_result is not None
    assert result.verify_result.healthy is False
    assert not (config.PLUGINS_DIR / "WorldEdit.jar").exists()
    assert len(verifier.rollback_calls) == 1
    assert result.change_record is not None
    assert verifier.rollback_calls[0] == result.change_record.backup_path


def test_unhealthy_without_backup_skips_rollback(isolated_server) -> None:
    pm = FakePluginManager(
        PluginManagerResult(
            change_record=ChangeRecord.now("install", "WorldEdit", "", "Install without backup"),
            raw_response="install",
            user_reply="Installed WorldEdit.",
        )
    )
    verifier = FakeVerifier(
        verify_result=VerifyResult(healthy=False, reason="smoke test failed"),
    )

    result = Orchestrator(plugin_manager=pm, verifier=verifier).handle("Install WorldEdit")

    assert result.success is False
    assert result.rolled_back is False
    assert "No backup available" in result.message
    assert verifier.rollback_calls == []
