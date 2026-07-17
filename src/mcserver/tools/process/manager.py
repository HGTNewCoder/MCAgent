"""Real Minecraft server process control (start / stop / restart).

Owns the Java subprocess lifecycle. Tracks PID on disk so later tool calls
(and a new Python process) can still stop or inspect the server.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from mcserver import config
from mcserver.tools.process import rcon

# Kept so stop can send the graceful "stop" command on stdin.
_managed: subprocess.Popen[str] | None = None


def _pid_path() -> Path:
    return config.SERVER_DIR / "mcserver.pid"


def _jar_path() -> Path:
    return config.SERVER_DIR / config.MC_SERVER_JAR


def jar_available() -> bool:
    return _jar_path().is_file()


def resolve_java_bin() -> str | None:
    """Return a usable Java executable path, or None if none was found."""
    configured = config.MC_JAVA_BIN
    if Path(configured).is_file():
        return configured
    found = shutil.which(configured)
    if found:
        return found

    java_home = os.environ.get("JAVA_HOME", "").strip()
    if java_home:
        name = "java.exe" if sys.platform == "win32" else "java"
        candidate = Path(java_home) / "bin" / name
        if candidate.is_file():
            return str(candidate)

    if sys.platform == "win32":
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        java_root = Path(program_files) / "Java"
        if java_root.is_dir():
            jdks = sorted(java_root.glob("jdk*/bin/java.exe"), reverse=True)
            if jdks:
                return str(jdks[0])

    return None


def java_available() -> bool:
    return resolve_java_bin() is not None


def use_real_process() -> bool:
    """Whether process tools should drive a real Java server."""
    mode = config.MC_PROCESS_MODE
    if mode == "stub":
        return False
    if mode == "real":
        return True
    # auto
    return jar_available()


def _read_pid() -> int | None:
    path = _pid_path()
    if not path.exists():
        return None
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def _write_pid(pid: int) -> None:
    config.SERVER_DIR.mkdir(parents=True, exist_ok=True)
    _pid_path().write_text(f"{pid}\n", encoding="utf-8")


def _clear_pid() -> None:
    path = _pid_path()
    if path.exists():
        path.unlink()


def is_alive(pid: int | None = None) -> bool:
    target = pid if pid is not None else _read_pid()
    if target is None:
        return False
    try:
        os.kill(target, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but we may not signal it — treat as alive.
        return True
    except OSError:
        return False
    # On Windows, os.kill(pid, 0) may succeed for exited processes in some cases;
    # also check via tasklist-like OpenProcess if needed. Use WaitForSingleObject
    # style via subprocess query.
    if sys.platform == "win32":
        return _windows_pid_alive(target)
    return True


def _windows_pid_alive(pid: int) -> bool:
    try:
        import ctypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(  # type: ignore[attr-defined]
            PROCESS_QUERY_LIMITED_INFORMATION, False, pid
        )
        if not handle:
            return False
        exit_code = ctypes.c_ulong()
        ok = ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))  # type: ignore[attr-defined]
        ctypes.windll.kernel32.CloseHandle(handle)  # type: ignore[attr-defined]
        # STILL_ACTIVE = 259
        return bool(ok) and exit_code.value == 259
    except Exception:  # noqa: BLE001
        return False


def check_process_alive() -> dict[str, Any]:
    pid = _read_pid()
    alive = is_alive(pid)
    if pid is not None and not alive:
        _clear_pid()
        pid = None
    return {"ok": True, "alive": alive, "pid": pid}


def start_server() -> dict[str, Any]:
    global _managed

    if not jar_available():
        return {
            "ok": False,
            "error": f"Server jar not found: {_jar_path()}",
        }

    existing = check_process_alive()
    if existing.get("alive"):
        return {
            "ok": True,
            "already_running": True,
            "pid": existing.get("pid"),
            "note": "Server was already running.",
        }

    java = resolve_java_bin()
    if java is None:
        return {
            "ok": False,
            "error": (
                f"Java not found: {config.MC_JAVA_BIN}. "
                "Set MC_JAVA_BIN in .env or add Java to PATH."
            ),
        }

    cmd = [java, *config.MC_JAVA_ARGS, "-jar", config.MC_SERVER_JAR, "nogui"]
    config.SERVER_DIR.mkdir(parents=True, exist_ok=True)
    config.SERVER_LOG.parent.mkdir(parents=True, exist_ok=True)

    log_file = config.SERVER_LOG.open("a", encoding="utf-8")
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(config.SERVER_DIR),
            stdin=subprocess.PIPE,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            creationflags=creationflags,
        )
    except FileNotFoundError:
        log_file.close()
        return {"ok": False, "error": f"Java not found: {java}"}
    except OSError as exc:
        log_file.close()
        return {"ok": False, "error": f"Failed to start server: {exc}"}

    _managed = proc
    _write_pid(proc.pid)
    # Give the JVM a moment to fail fast (bad jar / OOM).
    time.sleep(1.0)
    if proc.poll() is not None:
        _clear_pid()
        _managed = None
        return {
            "ok": False,
            "error": f"Server exited immediately with code {proc.returncode}",
            "pid": proc.pid,
        }

    return {
        "ok": True,
        "already_running": False,
        "pid": proc.pid,
        "cwd": str(config.SERVER_DIR),
        "command": cmd,
    }


def stop_server() -> dict[str, Any]:
    global _managed

    pid = _read_pid()
    if pid is None:
        rcon_stop = _try_rcon_stop(pid=None)
        if rcon_stop["attempted"] and rcon_stop["ok"]:
            _managed = None
            return {
                "ok": True,
                "already_stopped": False,
                "pid": None,
                "graceful": True,
                "graceful_method": "rcon",
                "rcon": rcon_stop,
                "error": None,
            }
        if rcon_stop["attempted"] and rcon_stop.get("kind") == "connection":
            _clear_pid()
            _managed = None
            return {
                "ok": True,
                "already_stopped": True,
                "pid": None,
                "graceful": False,
                "graceful_method": None,
                "rcon": rcon_stop,
                "error": None,
            }
        if rcon_stop["attempted"] and rcon_stop["error"]:
            return {
                "ok": False,
                "already_stopped": False,
                "pid": None,
                "graceful": False,
                "graceful_method": None,
                "rcon": rcon_stop,
                "error": rcon_stop["error"],
            }
        _clear_pid()
        _managed = None
        return {"ok": True, "already_stopped": True, "pid": None}

    if not is_alive(pid):
        _clear_pid()
        _managed = None
        return {"ok": True, "already_stopped": True, "pid": None}

    graceful = _try_graceful_stop(pid)
    if is_alive(pid):
        _force_kill(pid)

    still = is_alive(pid)
    if not still:
        _clear_pid()
        _managed = None

    return {
        "ok": not still,
        "already_stopped": False,
        "pid": pid if still else None,
        "graceful": bool(graceful["ok"]),
        "graceful_method": graceful["method"],
        "rcon": graceful.get("rcon"),
        "error": None if not still else f"Process {pid} still alive after kill",
    }


def restart_server() -> dict[str, Any]:
    stopped = stop_server()
    if not stopped.get("ok"):
        return {
            "ok": False,
            "error": f"Stop failed before restart: {stopped.get('error')}",
            "stop": stopped,
        }
    # Brief pause so ports (25565) can release on Windows.
    time.sleep(config.MC_RESTART_PAUSE_SECONDS)
    started = start_server()
    return {
        "ok": bool(started.get("ok")),
        "stop": stopped,
        "start": started,
        "error": started.get("error"),
    }


def _try_graceful_stop(pid: int) -> dict[str, Any]:
    """Try graceful stop over stdin first, then RCON."""
    global _managed
    proc = _managed
    if proc is not None and proc.pid == pid and proc.stdin is not None:
        try:
            proc.stdin.write("stop\n")
            proc.stdin.flush()
        except OSError:
            pass
        else:
            try:
                proc.wait(timeout=config.MC_STOP_TIMEOUT_SECONDS)
                return {"ok": True, "method": "stdin", "rcon": None}
            except subprocess.TimeoutExpired:
                pass

    rcon_stop = _try_rcon_stop(pid=pid)
    if rcon_stop["attempted"] and rcon_stop["ok"]:
        return {"ok": True, "method": "rcon", "rcon": rcon_stop}
    return {
        "ok": False,
        "method": None,
        "rcon": rcon_stop if rcon_stop["attempted"] else None,
    }


def _try_rcon_stop(pid: int | None) -> dict[str, Any]:
    if not config.MC_RCON_ENABLED:
        return {"attempted": False, "ok": False, "error": None}
    if not config.MC_RCON_PASSWORD:
        return {
            "attempted": True,
            "ok": False,
            "kind": "configuration",
            "error": "MC_RCON_PASSWORD is not set.",
        }

    try:
        response = rcon.run_command(
            host=config.MC_RCON_HOST,
            port=config.MC_RCON_PORT,
            password=config.MC_RCON_PASSWORD,
            timeout=config.MC_RCON_TIMEOUT_SECONDS,
            command="stop",
        )
    except OSError as exc:
        return {
            "attempted": True,
            "ok": False,
            "kind": "connection",
            "error": f"RCON connection failed: {exc}",
        }
    except rcon.RconError as exc:
        return {"attempted": True, "ok": False, "kind": "rcon", "error": str(exc)}

    stopped = _wait_for_rcon_stop(pid)
    return {
        "attempted": True,
        "ok": stopped,
        "kind": None,
        "error": None if stopped else "Server did not stop after RCON command.",
        "response": response,
    }


def _wait_for_rcon_stop(pid: int | None) -> bool:
    deadline = time.time() + config.MC_STOP_TIMEOUT_SECONDS
    if pid is not None:
        while time.time() < deadline:
            if not is_alive(pid):
                return True
            time.sleep(0.25)
        return False

    # No PID means the server was probably started outside this app. After
    # sending `stop`, treat RCON becoming unavailable as evidence it stopped.
    while time.time() < deadline:
        time.sleep(0.5)
        try:
            rcon.run_command(
                host=config.MC_RCON_HOST,
                port=config.MC_RCON_PORT,
                password=config.MC_RCON_PASSWORD,
                timeout=config.MC_RCON_TIMEOUT_SECONDS,
                command="list",
            )
        except (OSError, rcon.RconError):
            return True
    return False


def _force_kill(pid: int) -> None:
    global _managed
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            check=False,
        )
    else:
        try:
            os.kill(pid, signal.SIGTERM)
            deadline = time.time() + config.MC_STOP_TIMEOUT_SECONDS
            while time.time() < deadline and is_alive(pid):
                time.sleep(0.25)
            if is_alive(pid):
                os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if _managed is not None and _managed.pid == pid:
        _managed = None
