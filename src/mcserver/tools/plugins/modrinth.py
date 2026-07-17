"""Modrinth plugin catalog client."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse

from mcserver import config
from mcserver.tools.plugins.http import fetch_json, http_error_message
from mcserver.tools.plugins.models import PluginCandidate

MODRINTH_BASE = "https://api.modrinth.com/v2"


def _install_key(slug: str) -> str:
    return f"modrinth:{slug}"


def search(query: str, *, limit: int | None = None) -> tuple[list[PluginCandidate], str | None]:
    limit = limit or config.PLUGIN_SEARCH_LIMIT
    facets = json.dumps([["project_type:plugin"], ["categories:paper"]])
    q = urllib.parse.quote(query.strip())
    url = f"{MODRINTH_BASE}/search?query={q}&limit={limit}&facets={urllib.parse.quote(facets)}"
    try:
        data = fetch_json(url)
    except urllib.error.HTTPError as exc:
        return [], http_error_message(exc)
    except urllib.error.URLError as exc:
        return [], str(exc.reason)

    results: list[PluginCandidate] = []
    for hit in data.get("hits", []):
        slug = hit.get("slug") or hit.get("project_id", "")
        if not slug:
            continue
        results.append(
            PluginCandidate(
                install_key=_install_key(slug),
                name=hit.get("title") or slug,
                slug=slug,
                source="modrinth",
                description=(hit.get("description") or "")[:500],
                downloads=int(hit.get("downloads", 0) or 0),
                page_url=f"https://modrinth.com/plugin/{slug}",
                platforms=["PAPER"],
            )
        )
    return results, None


def resolve(slug: str) -> tuple[PluginCandidate | None, str | None]:
    project_url = f"{MODRINTH_BASE}/project/{urllib.parse.quote(slug)}"
    try:
        project = fetch_json(project_url)
    except urllib.error.HTTPError as exc:
        return None, http_error_message(exc)
    except urllib.error.URLError as exc:
        return None, str(exc.reason)

    name = project.get("title") or slug
    page_url = f"https://modrinth.com/plugin/{slug}"
    mc = config.MC_MINECRAFT_VERSION

    versions_url = (
        f"{MODRINTH_BASE}/project/{urllib.parse.quote(slug)}/version"
        f"?loaders=[\"paper\",\"spigot\"]&game_versions=[\"{mc}\"]"
    )
    try:
        versions = fetch_json(versions_url)
    except urllib.error.HTTPError:
        versions_url = f"{MODRINTH_BASE}/project/{urllib.parse.quote(slug)}/version"
        try:
            versions = fetch_json(versions_url)
        except urllib.error.HTTPError as exc:
            return None, http_error_message(exc)
        except urllib.error.URLError as exc:
            return None, str(exc.reason)
    except urllib.error.URLError as exc:
        return None, str(exc.reason)

    if not versions:
        return None, f"No Modrinth versions found for '{slug}'"

    warning = ""
    version = versions[0]
    if mc not in (version.get("game_versions") or []):
        warning = f"No Modrinth version matched MC {mc}; using {version.get('version_number', '?')}"

    files = version.get("files") or []
    download_url = files[0].get("url", "") if files else ""
    if not download_url:
        return None, f"No download file for Modrinth {slug}"

    return (
        PluginCandidate(
            install_key=_install_key(slug),
            name=name,
            slug=slug,
            source="modrinth",
            description=(project.get("description") or "")[:500],
            downloads=int(project.get("downloads", 0) or 0),
            page_url=page_url,
            download_url=download_url,
            platforms=["PAPER"],
            version=version.get("version_number", ""),
            warning=warning,
        ),
        None,
    )
