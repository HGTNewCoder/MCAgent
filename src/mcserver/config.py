"""Runtime configuration for the Minecraft management agents."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# src/mcserver/config.py → repo root is two levels up from package dir
PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent.parent

# Always load .env from repo root so scripts work regardless of cwd.
load_dotenv(PROJECT_ROOT / ".env")


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

# DeepSeek (OpenAI-compatible)
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# Server paths (under repo root by default). Use ./server for the real Paper install.
SERVER_DIR = Path(os.getenv("MC_SERVER_DIR", PROJECT_ROOT / "mock_server"))
if not SERVER_DIR.is_absolute():
    SERVER_DIR = (PROJECT_ROOT / SERVER_DIR).resolve()
PLUGINS_DIR = SERVER_DIR / "plugins"
BACKUPS_DIR = SERVER_DIR / "backups"
SERVER_LOG = SERVER_DIR / "logs" / "latest.log"

# Download cache for plugin jars fetched from remote catalogs.
_raw_cache = os.getenv("MC_PLUGIN_CACHE_DIR", str(PROJECT_ROOT / "plugin-cache"))
PLUGIN_CACHE_DIR = Path(_raw_cache)
if not PLUGIN_CACHE_DIR.is_absolute():
    PLUGIN_CACHE_DIR = (PROJECT_ROOT / PLUGIN_CACHE_DIR).resolve()

# Minecraft version used when picking compatible plugin builds.
MC_MINECRAFT_VERSION = os.getenv("MC_MINECRAFT_VERSION", "1.21").strip()

# Plugin catalog settings
PLUGIN_SEARCH_LIMIT = int(os.getenv("PLUGIN_SEARCH_LIMIT", "10"))
PLUGIN_HTTP_USER_AGENT = os.getenv(
    "PLUGIN_HTTP_USER_AGENT",
    "mcserver/0.1 (+https://github.com/minecraft-server)",
)

# Sources the agent may search and install from.
PLUGIN_ALLOWED_SOURCES: frozenset[str] = frozenset({"hangar", "modrinth", "spigot"})

# Prototype security: blocklist-only. Install is rejected when name/slug matches.
# TODO(security): Before production, re-enable search-session install gate and
# consider a curated allowlist — see MEMORY.md Future work [plugin-discovery].
_raw_blocklist = os.getenv("MC_PLUGIN_BLOCKLIST", "")
PLUGIN_BLOCKLIST: frozenset[str] = frozenset(
    part.strip().lower()
    for part in _raw_blocklist.split(",")
    if part.strip()
)

# Process control — real Java subprocess when jar exists (auto) or forced via MC_PROCESS_MODE
MC_PROCESS_MODE = os.getenv("MC_PROCESS_MODE", "auto").strip().lower()  # auto|stub|real
MC_JAVA_BIN = os.getenv("MC_JAVA_BIN", "java")
MC_SERVER_JAR = os.getenv("MC_SERVER_JAR", "server.jar")
_raw_java_args = os.getenv("MC_JAVA_ARGS", "-Xms1G -Xmx2G").strip()
MC_JAVA_ARGS: list[str] = _raw_java_args.split() if _raw_java_args else []
MC_STOP_TIMEOUT_SECONDS = float(os.getenv("MC_STOP_TIMEOUT_SECONDS", "30"))
MC_RESTART_PAUSE_SECONDS = float(os.getenv("MC_RESTART_PAUSE_SECONDS", "2"))

# RCON is used for graceful stop when stdin is unavailable, such as when the
# server was started outside this Python process.
MC_RCON_ENABLED = _env_bool("MC_RCON_ENABLED", False)
MC_RCON_HOST = os.getenv("MC_RCON_HOST", "127.0.0.1")
MC_RCON_PORT = int(os.getenv("MC_RCON_PORT", "25575"))
MC_RCON_PASSWORD = os.getenv("MC_RCON_PASSWORD", "")
MC_RCON_TIMEOUT_SECONDS = float(os.getenv("MC_RCON_TIMEOUT_SECONDS", "3"))

# Smoke-test window (seconds) — used by stub and future real checks
SMOKE_TEST_SECONDS = int(os.getenv("SMOKE_TEST_SECONDS", "5"))

# Max tool-calling rounds per agent turn
MAX_AGENT_STEPS = int(os.getenv("MAX_AGENT_STEPS", "12"))

# Per-run agent output logs (YYYY-MM-DD_HH-MM-SS.log)
RUN_LOGS_DIR = Path(os.getenv("RUN_LOGS_DIR", PROJECT_ROOT / "logs"))
