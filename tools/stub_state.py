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

import config


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
        _write_log_lines(initial["log_lines"])
    elif not config.SERVER_LOG.exists():
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
    _write_log_lines(state["log_lines"])


def set_force_unhealthy(value: bool) -> None:
    """Test helper: make smoke_test / health checks fail until cleared."""
    state = _read_state()
    state["force_unhealthy"] = value
    _write_state(state)


# --- Plugin Manager stubs -------------------------------------------------


def search_plugin_repo(query: str) -> dict[str, Any]:
    q = query.strip().lower()
    matches = [name for name in sorted(config.PLUGIN_ALLOWLIST) if q in name.lower()]
    return {
        "ok": True,
        "query": query,
        "matches": matches,
        "note": "Only allowlisted plugins are returned.",
    }


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


def install_plugin(name: str) -> dict[str, Any]:
    if name not in config.PLUGIN_ALLOWLIST:
        return {
            "ok": False,
            "error": f"Plugin '{name}' is not on the allowlist. Refusing install.",
            "allowlist": sorted(config.PLUGIN_ALLOWLIST),
        }

    state = _read_state()
    jar = config.PLUGINS_DIR / f"{name}.jar"
    jar.write_text(f"stub-jar:{name}\n", encoding="utf-8")
    loaded = set(state.get("loaded_plugins", []))
    loaded.add(name)
    state["loaded_plugins"] = sorted(loaded)
    _write_state(state)
    _append_log(f"[STUB] Installed plugin {name}")
    return {"ok": True, "plugin": name, "path": str(jar)}


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
    if name not in state.get("loaded_plugins", []) and name not in config.PLUGIN_ALLOWLIST:
        return {"ok": False, "error": f"Unknown plugin '{name}'."}
    configs = state.setdefault("plugin_configs", {})
    plugin_cfg = configs.setdefault(name, {})
    plugin_cfg[key] = value
    _write_state(state)
    _append_log(f"[STUB] Configured {name}: {key}={value}")
    return {"ok": True, "plugin": name, "key": key, "value": value}


def restart_server() -> dict[str, Any]:
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
        "note": "Stub restart — replace with real process manager later.",
    }


# --- Verifier stubs -------------------------------------------------------


def read_server_log(lines: int = 50) -> dict[str, Any]:
    ensure_mock_layout()
    _flush_log_from_state()
    content = config.SERVER_LOG.read_text(encoding="utf-8").splitlines()
    n = max(1, int(lines))
    return {"ok": True, "lines": content[-n:]}


def check_process_alive() -> dict[str, Any]:
    state = _read_state()
    alive = bool(state.get("process_alive", False)) and not state.get("force_unhealthy", False)
    return {"ok": True, "alive": alive}


def check_plugin_loaded(name: str) -> dict[str, Any]:
    state = _read_state()
    loaded = name in state.get("loaded_plugins", [])
    if state.get("force_unhealthy"):
        loaded = False
    return {"ok": True, "plugin": name, "loaded": loaded}


def run_smoke_test() -> dict[str, Any]:
    """Stub: server boots and no fatal error within N seconds."""
    state = _read_state()
    log = "\n".join(state.get("log_lines", [])[-30:])
    fatal = "FATAL" in log.upper() or state.get("force_unhealthy", False)
    alive = bool(state.get("process_alive", False)) and not fatal
    return {
        "ok": True,
        "passed": alive and not fatal,
        "seconds": config.SMOKE_TEST_SECONDS,
        "fatal_seen": fatal,
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
