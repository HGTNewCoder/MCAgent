"""Integration tests for rollback against a real Paper server.

Run explicitly (touches ./server, starts Java):

    uv run pytest -m integration -v
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from mcserver import config
from mcserver.models import ChangeRecord, PluginManagerResult, VerifyResult
from mcserver.orchestrator import Orchestrator
from mcserver.tools import stub_state
from mcserver.tools.process import manager as process
from tests.conftest import BAD_JAR_NAME
from tests.fakes import FakePluginManager, FakeVerifier

pytestmark = pytest.mark.integration


def _bad_jar_path() -> Path:
    return config.PLUGINS_DIR / f"{BAD_JAR_NAME}.jar"


def _install_corrupt_jar() -> None:
    config.PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
    _bad_jar_path().write_bytes(b"NOT-A-VALID-JAR")


def test_rollback_removes_bad_jar_from_plugins_dir(real_server) -> None:
    """Filesystem rollback: backup → corrupt jar → restore removes the jar."""
    backup = stub_state.backup_plugins_dir()
    before = {p.name for p in config.PLUGINS_DIR.iterdir() if p.is_file() and p.suffix == ".jar"}

    _install_corrupt_jar()
    assert _bad_jar_path().exists()

    result = stub_state.rollback_last_change(backup["backup_path"])

    assert result["ok"] is True
    assert not _bad_jar_path().exists()
    after = {p.name for p in config.PLUGINS_DIR.iterdir() if p.is_file() and p.suffix == ".jar"}
    assert before <= after


def test_bad_jar_restart_then_orchestrator_rollback(real_server) -> None:
    """Full flow: corrupt jar → restart → unhealthy verdict → rollback → healthy server."""
    backup = stub_state.backup_plugins_dir()
    backup_path = backup["backup_path"]

    _install_corrupt_jar()
    restart = stub_state.restart_server()
    assert restart.get("ok") is True, restart

    # Give Paper time to attempt plugin loading and write to latest.log.
    time.sleep(config.SMOKE_TEST_SECONDS)

    log = stub_state.read_server_log(lines=120)
    log_text = "\n".join(log.get("lines", [])).lower()
    # Corrupt jar should error in log; server may still stay up (no FATAL).
    assert (
        BAD_JAR_NAME.lower() in log_text
        or "invalid" in log_text
        or "error" in log_text
        or "exception" in log_text
        or "failed" in log_text
    )

    pm = FakePluginManager(
        PluginManagerResult(
            change_record=ChangeRecord.now(
                "install",
                BAD_JAR_NAME,
                backup_path,
                f"Installed corrupt plugin {BAD_JAR_NAME}",
            ),
            raw_response="install",
            user_reply=f"Installed {BAD_JAR_NAME}.",
        )
    )
    verifier = FakeVerifier(
        verify_result=VerifyResult(
            healthy=False,
            reason=f"{BAD_JAR_NAME} failed to load; errors in server log",
        ),
        use_real_rollback=True,
    )

    result = Orchestrator(plugin_manager=pm, verifier=verifier).handle(
        f"Install {BAD_JAR_NAME}"
    )

    assert result.success is False
    assert result.rolled_back is True
    assert not _bad_jar_path().exists()

    post_smoke = stub_state.run_smoke_test()
    alive = process.check_process_alive()
    assert alive.get("alive") is True
    assert post_smoke.get("passed") is True
