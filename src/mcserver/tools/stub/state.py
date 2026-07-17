"""In-memory mock Minecraft server state for stub tool implementations.

Replace these stubs with real subprocess / RCON / filesystem calls later.
The agents only decide which tools to call; this module executes them.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mcserver import config


def _using_real_log() -> bool:
    from mcserver.tools.process import manager as process

    return process.use_real_process()


def ensure_mock_layout() -> None:
    """Create mock server directories and a starter log if missing."""
    config.PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
    config.BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    config.SERVER_LOG.parent.mkdir(parents=True, exist_ok=True)
    state_path = _state_path()
    if not state_path.exists():
        initial = {
            "process_alive": True,
            "loaded_plugins": ["Vault"],
            "plugin_configs": {},
            "log_lines": [
                "[INFO] Starting mock Minecraft server",
                '[INFO] Done (1.234s)! For help, type "help"',
            ],
            "last_backup": "",
            "force_unhealthy": False,
        }
        _write_state(initial)
        if not _using_real_log():
            _write_log_lines(initial["log_lines"])
    elif not config.SERVER_LOG.exists() and not _using_real_log():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        _write_log_lines(state.get("log_lines", []))


def _state_path() -> Path:
    return config.SERVER_DIR / "stub_state.json"


def _read_state() -> dict[str, Any]:
    ensure_mock_layout()
    return json.loads(_state_path().read_text(encoding="utf-8"))


def _write_state(state: dict[str, Any]) -> None:
    config.SERVER_DIR.mkdir(parents=True, exist_ok=True)
    _state_path().write_text(json.dumps(state, indent=2), encoding="utf-8")


def _write_log_lines(lines: list[str]) -> None:
    config.SERVER_LOG.parent.mkdir(parents=True, exist_ok=True)
    config.SERVER_LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _flush_log_from_state() -> None:
    state = json.loads(_state_path().read_text(encoding="utf-8"))
    _write_log_lines(state.get("log_lines", []))


def _append_log(line: str) -> None:
    state = _read_state()
    stamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
    entry = f"[{stamp}] {line}"
    state.setdefault("log_lines", []).append(entry)
    _write_state(state)
    if not _using_real_log():
        _write_log_lines(state["log_lines"])


def set_force_unhealthy(value: bool) -> None:
    """Test helper: make smoke_test / health checks fail until cleared."""
    state = _read_state()
    state["force_unhealthy"] = value
    _write_state(state)


def list_plugins_info() -> dict[str, Any]:
    """Installed plugin summary for the web API."""
    ensure_mock_layout()
    state = _read_state()
    loaded = list(state.get("loaded_plugins", []))
    jars: list[str] = []
    if config.PLUGINS_DIR.is_dir():
        jars = sorted(p.stem for p in config.PLUGINS_DIR.glob("*.jar") if p.is_file())
    return {
        "ok": True,
        "allowed_sources": sorted(config.PLUGIN_ALLOWED_SOURCES),
        "blocklist": sorted(config.PLUGIN_BLOCKLIST),
        "loaded": loaded,
        "jars": jars,
    }


# --- Plugin Manager stubs -------------------------------------------------


def search_plugin_repo(query: str) -> dict[str, Any]:
    from mcserver.tools.plugins.resolver import search_all

    return search_all(query)


def backup_plugins_dir() -> dict[str, Any]:
    ensure_mock_layout()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = config.BACKUPS_DIR / f"plugins_{stamp}"
    if backup_path.exists():
        shutil.rmtree(backup_path)
    shutil.copytree(config.PLUGINS_DIR, backup_path)

    # Also snapshot stub state for rollback
    meta = {
        "state": _read_state(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (backup_path / "_stub_meta.json").write_text(
        json.dumps(meta, indent=2),
        encoding="utf-8",
    )

    state = _read_state()
    state["last_backup"] = str(backup_path)
    _write_state(state)
    _append_log(f"[STUB] Backed up plugins to {backup_path}")
    return {"ok": True, "backup_path": str(backup_path)}


def install_plugin(install_key: str) -> dict[str, Any]:
    from mcserver.tools.plugins import download as plugin_download
    from mcserver.tools.plugins.resolver import resolve_install_key, stub_candidate_from_key
    from mcserver.tools.process import manager as process

    ensure_mock_layout()

    if process.use_real_process():
        candidate, err = resolve_install_key(install_key)
        if err or candidate is None:
            return {"ok": False, "error": err or "Could not resolve plugin", "install_key": install_key}

        cached, dl_err = plugin_download.download_to_cache(candidate)
        if dl_err or cached is None:
            return {
                "ok": False,
                "error": dl_err or "Download failed",
                "install_key": install_key,
                "plugin": candidate.name,
            }

        dest = plugin_download.install_from_cache(candidate, cached)
        note = f"Downloaded from {candidate.source}"
        if candidate.warning:
            note = f"{note} ({candidate.warning})"
    else:
        candidate, err = stub_candidate_from_key(install_key)
        if err or candidate is None:
            return {"ok": False, "error": err or "Invalid install_key", "install_key": install_key}

        dest = config.PLUGINS_DIR / f"{plugin_download._safe_jar_stem(candidate.name)}.jar"
        dest.write_text(f"stub-jar:{candidate.name}\n", encoding="utf-8")
        cached = None
        note = "stub"

    state = _read_state()
    loaded = set(state.get("loaded_plugins", []))
    loaded.add(candidate.name)
    state["loaded_plugins"] = sorted(loaded)
    _write_state(state)
    _append_log(f"[INSTALL] Installed plugin {candidate.name} ({note})")
    return {
        "ok": True,
        "plugin": candidate.name,
        "install_key": install_key,
        "path": str(dest),
        "source": candidate.source,
        "version": candidate.version,
        "bytes": dest.stat().st_size,
        "note": note,
        "warning": candidate.warning or None,
        "cache_path": str(cached) if cached else None,
    }


def uninstall_plugin(name: str) -> dict[str, Any]:
    state = _read_state()
    jar = config.PLUGINS_DIR / f"{name}.jar"
    if jar.exists():
        jar.unlink()
    loaded = [p for p in state.get("loaded_plugins", []) if p != name]
    state["loaded_plugins"] = loaded
    state.get("plugin_configs", {}).pop(name, None)
    _write_state(state)
    _append_log(f"[STUB] Uninstalled plugin {name}")
    return {"ok": True, "plugin": name}


def configure_plugin(name: str, key: str, value: str) -> dict[str, Any]:
    state = _read_state()
    if name not in state.get("loaded_plugins", []):
        return {"ok": False, "error": f"Unknown plugin '{name}'."}
    configs = state.setdefault("plugin_configs", {})
    plugin_cfg = configs.setdefault(name, {})
    plugin_cfg[key] = value
    _write_state(state)
    _append_log(f"[STUB] Configured {name}: {key}={value}")
    return {"ok": True, "plugin": name, "key": key, "value": value}


def start_server() -> dict[str, Any]:
    from mcserver.tools.process import manager as process

    if process.use_real_process():
        result = process.start_server()
        if result.get("ok"):
            state = _read_state()
            state["process_alive"] = True
            _write_state(state)
            _append_log(f"[PROCESS] Started server pid={result.get('pid')}")
        return result

    state = _read_state()
    state["process_alive"] = True
    _write_state(state)
    _append_log("[STUB] Server started")
    return {"ok": True, "already_running": False, "pid": None, "note": "stub"}


def stop_server() -> dict[str, Any]:
    from mcserver.tools.process import manager as process

    if process.use_real_process():
        result = process.stop_server()
        if result.get("ok"):
            state = _read_state()
            state["process_alive"] = False
            _write_state(state)
            _append_log("[PROCESS] Stopped server")
        return result

    state = _read_state()
    state["process_alive"] = False
    _write_state(state)
    _append_log("[STUB] Server stopped")
    return {"ok": True, "already_stopped": False, "pid": None, "note": "stub"}


def restart_server() -> dict[str, Any]:
    from mcserver.tools.process import manager as process

    if process.use_real_process():
        result = process.restart_server()
        state = _read_state()
        state["process_alive"] = bool(result.get("ok"))
        if state.get("force_unhealthy"):
            state["process_alive"] = False
            _append_log("[FATAL] Simulated fatal error after restart")
        elif result.get("ok"):
            _append_log(f"[PROCESS] Restarted server pid={result.get('start', {}).get('pid')}")
        _write_state(state)
        return result

    state = _read_state()
    state["process_alive"] = True
    if state.get("force_unhealthy"):
        _append_log("[FATAL] Simulated fatal error after restart")
        state["process_alive"] = False
    else:
        _append_log("[INFO] Server restart complete")
        _append_log('[INFO] Done (0.500s)! For help, type "help"')
    _write_state(state)
    return {
        "ok": True,
        "process_alive": state["process_alive"],
        "note": "stub",
    }


# --- Verifier stubs -------------------------------------------------------


def read_server_log(lines: int = 50) -> dict[str, Any]:
    from mcserver.tools.process import manager as process

    ensure_mock_layout()
    if not process.use_real_process():
        _flush_log_from_state()
    if not config.SERVER_LOG.exists():
        return {"ok": True, "lines": []}
    content = config.SERVER_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
    n = max(1, int(lines))
    return {"ok": True, "lines": content[-n:]}


def check_process_alive() -> dict[str, Any]:
    from mcserver.tools.process import manager as process

    if process.use_real_process():
        result = process.check_process_alive()
        state = _read_state()
        if state.get("force_unhealthy"):
            result = {**result, "alive": False, "forced_unhealthy": True}
        return result

    state = _read_state()
    alive = bool(state.get("process_alive", False)) and not state.get(
        "force_unhealthy", False
    )
    return {"ok": True, "alive": alive, "pid": None}


def check_plugin_loaded(name: str) -> dict[str, Any]:
    from mcserver.tools.process import manager as process

    if process.use_real_process():
        loaded = False
        if config.SERVER_LOG.exists():
            log = config.SERVER_LOG.read_text(encoding="utf-8", errors="replace").lower()
            name_lower = name.lower()
            loaded = f"enabling {name_lower}" in log or f"enabled {name_lower}" in log
        state = _read_state()
        if state.get("force_unhealthy"):
            loaded = False
        return {"ok": True, "plugin": name, "loaded": loaded}

    state = _read_state()
    loaded = name in state.get("loaded_plugins", [])
    if state.get("force_unhealthy"):
        loaded = False
    return {"ok": True, "plugin": name, "loaded": loaded}


def _log_health_issues(log: str) -> dict[str, Any]:
    """Detect log lines that should fail a smoke test."""
    upper = log.upper()
    patterns = ("FATAL", "ERROR", "SEVERE", "EXCEPTION", "FAILED TO LOAD")
    matched = [pattern for pattern in patterns if pattern in upper]
    return {
        "unhealthy": bool(matched),
        "fatal_seen": "FATAL" in matched,
        "error_seen": any(pattern != "FATAL" for pattern in matched),
        "matched_patterns": matched,
    }


def run_smoke_test() -> dict[str, Any]:
    """Server boots and log stays free of fatal/error signals."""
    from mcserver.tools.process import manager as process

    state = _read_state()
    if process.use_real_process():
        alive_info = process.check_process_alive()
        alive = bool(alive_info.get("alive"))
        log_path = config.SERVER_LOG
        log = ""
        if log_path.exists():
            log = "\n".join(log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-30:])
        issues = _log_health_issues(log)
        unhealthy = issues["unhealthy"] or state.get("force_unhealthy", False)
        if state.get("force_unhealthy"):
            alive = False
        return {
            "ok": True,
            "passed": alive and not unhealthy,
            "seconds": config.SMOKE_TEST_SECONDS,
            "fatal_seen": issues["fatal_seen"] or state.get("force_unhealthy", False),
            "error_seen": issues["error_seen"],
            "matched_patterns": issues["matched_patterns"],
            "process_alive": alive,
            "pid": alive_info.get("pid"),
        }

    log = "\n".join(state.get("log_lines", [])[-30:])
    issues = _log_health_issues(log)
    unhealthy = issues["unhealthy"] or state.get("force_unhealthy", False)
    alive = bool(state.get("process_alive", False)) and not unhealthy
    return {
        "ok": True,
        "passed": alive and not unhealthy,
        "seconds": config.SMOKE_TEST_SECONDS,
        "fatal_seen": issues["fatal_seen"] or state.get("force_unhealthy", False),
        "error_seen": issues["error_seen"],
        "matched_patterns": issues["matched_patterns"],
        "process_alive": alive,
    }


def rollback_last_change(backup_path: str) -> dict[str, Any]:
    path = Path(backup_path)
    if not path.exists():
        return {"ok": False, "error": f"Backup not found: {backup_path}"}

    meta_file = path / "_stub_meta.json"
    if meta_file.exists():
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        restored = meta.get("state", {})
        restored["process_alive"] = True
        restored["force_unhealthy"] = False
        _write_state(restored)

    # Restore plugin jars from backup (ignore meta file)
    if config.PLUGINS_DIR.exists():
        shutil.rmtree(config.PLUGINS_DIR)
    config.PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
    for item in path.iterdir():
        if item.name == "_stub_meta.json":
            continue
        dest = config.PLUGINS_DIR / item.name
        if item.is_dir():
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)

    _append_log(f"[STUB] Rolled back plugins from {backup_path}")
    restart = restart_server()
    return {
        "ok": True,
        "backup_path": backup_path,
        "restart": restart,
    }
