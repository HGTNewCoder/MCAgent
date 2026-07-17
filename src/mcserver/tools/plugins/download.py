"""Download plugin jars from remote catalogs."""

from __future__ import annotations

import shutil
from pathlib import Path

from mcserver import config
from mcserver.tools.plugins.http import fetch_bytes
from mcserver.tools.plugins.models import PluginCandidate

MIN_JAR_BYTES = 1000
ZIP_MAGIC = b"PK"


def cache_path(candidate: PluginCandidate) -> Path:
    safe_slug = candidate.slug.replace("/", "_").replace("\\", "_")
    return config.PLUGIN_CACHE_DIR / f"{candidate.source}_{safe_slug}.jar"


def plugins_jar_path(candidate: PluginCandidate) -> Path:
    safe_name = _safe_jar_stem(candidate.name)
    return config.PLUGINS_DIR / f"{safe_name}.jar"


def download_to_cache(candidate: PluginCandidate) -> tuple[Path | None, str | None]:
    if not candidate.download_url:
        return None, "No download URL for plugin"

    config.PLUGIN_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    dest = cache_path(candidate)

    try:
        data = fetch_bytes(candidate.download_url)
    except Exception as exc:
        return None, f"Download failed: {exc}"

    err = validate_jar_bytes(data)
    if err:
        return None, err

    dest.write_bytes(data)
    return dest, None


def install_from_cache(candidate: PluginCandidate, cached: Path) -> Path:
    config.PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
    dest = plugins_jar_path(candidate)
    shutil.copy2(cached, dest)
    return dest


def validate_jar_bytes(data: bytes) -> str | None:
    if len(data) < MIN_JAR_BYTES:
        return f"Downloaded file too small ({len(data)} bytes)"
    if not data.startswith(ZIP_MAGIC):
        return "Downloaded file is not a valid JAR (missing ZIP header)"
    return None


def _safe_jar_stem(name: str) -> str:
    stem = "".join(c for c in name if c.isalnum() or c in ("-", "_", "+", "."))
    return stem or "plugin"
