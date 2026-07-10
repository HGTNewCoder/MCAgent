"""Runtime configuration for the Minecraft management agents."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent

# DeepSeek (OpenAI-compatible)
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# Stub / future real server paths
SERVER_DIR = Path(os.getenv("MC_SERVER_DIR", ROOT / "mock_server"))
PLUGINS_DIR = SERVER_DIR / "plugins"
BACKUPS_DIR = SERVER_DIR / "backups"
SERVER_LOG = SERVER_DIR / "logs" / "latest.log"

# Only these plugins may be installed (allowlist / vetted repo)
PLUGIN_ALLOWLIST: frozenset[str] = frozenset(
    {
        "EssentialsX",
        "WorldEdit",
        "LuckPerms",
        "Vault",
        "CoreProtect",
        "Dynmap",
    }
)

# Smoke-test window (seconds) — used by stub and future real checks
SMOKE_TEST_SECONDS = int(os.getenv("SMOKE_TEST_SECONDS", "5"))

# Max tool-calling rounds per agent turn
MAX_AGENT_STEPS = int(os.getenv("MAX_AGENT_STEPS", "12"))

# Per-run agent output logs (YYYY-MM-DD_HH-MM-SS.log)
RUN_LOGS_DIR = Path(os.getenv("RUN_LOGS_DIR", ROOT / "logs"))
