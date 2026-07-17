"""Hangar (PaperMC) plugin catalog client."""

from __future__ import annotations

import urllib.parse
import urllib.error
from typing import Any

from mcserver import config
from mcserver.tools.plugins.http import fetch_json, http_error_message
from mcserver.tools.plugins.models import PluginCandidate

HANGAR_BASE = "https://hangar.papermc.io"


def _install_key(slug: str) -> str:
    return f"hangar:{slug}"


def _page_url(namespace: str, slug: str) -> str:
    return f"{HANGAR_BASE}/{namespace}/{slug}"


def search(query: str, *, limit: int | None = None) -> tuple[list[PluginCandidate], str | None]:
    limit = limit or config.PLUGIN_SEARCH_LIMIT
    q = urllib.parse.quote(query.strip())
    url = f"{HANGAR_BASE}/api/v1/projects?q={q}&limit={limit}&offset=0"
    try:
        data = fetch_json(url)
    except urllib.error.HTTPError as exc:
        return [], http_error_message(exc)
    except urllib.error.URLError as exc:
        return [], str(exc.reason)

    results: list[PluginCandidate] = []
    for item in data.get("result", []):
        namespace = item.get("namespace", {}).get("name", "")
        slug = item.get("name", "")
        if not slug:
            continue
        stats = item.get("stats", {})
        results.append(
            PluginCandidate(
                install_key=_install_key(slug),
                name=item.get("name", slug),
                slug=slug,
                source="hangar",
                description=(item.get("description") or "")[:500],
                downloads=int(stats.get("downloads", 0) or 0),
                page_url=_page_url(namespace, slug) if namespace else f"{HANGAR_BASE}/{slug}",
                platforms=["PAPER"],
            )
        )
    return results, None


def resolve(slug: str) -> tuple[PluginCandidate | None, str | None]:
    """Resolve latest compatible version and download URL for a Hangar project slug."""
    project_url = f"{HANGAR_BASE}/api/v1/projects/{urllib.parse.quote(slug)}"
    try:
        project = fetch_json(project_url)
    except urllib.error.HTTPError as exc:
        return None, http_error_message(exc)
    except urllib.error.URLError as exc:
        return None, str(exc.reason)

    namespace = project.get("namespace", {}).get("name", "")
    name = project.get("name", slug)
    stats = project.get("stats", {})
    page = _page_url(namespace, slug) if namespace else f"{HANGAR_BASE}/{slug}"

    versions_url = f"{HANGAR_BASE}/api/v1/projects/{urllib.parse.quote(slug)}/versions"
    try:
        versions_data = fetch_json(versions_url)
    except urllib.error.HTTPError as exc:
        return None, http_error_message(exc)
    except urllib.error.URLError as exc:
        return None, str(exc.reason)

    versions = versions_data if isinstance(versions_data, list) else versions_data.get("result", [])
    if not versions:
        return None, f"No versions found for Hangar project '{slug}'"

    mc = config.MC_MINECRAFT_VERSION
    chosen, warning = _pick_version(versions, mc)
    version_name = chosen.get("name", "")
    if not version_name:
        return None, f"Could not determine version for Hangar project '{slug}'"

    version_url = (
        f"{HANGAR_BASE}/api/v1/projects/{urllib.parse.quote(slug)}"
        f"/versions/{urllib.parse.quote(version_name)}"
    )
    try:
        version_detail = fetch_json(version_url)
    except urllib.error.HTTPError as exc:
        return None, http_error_message(exc)
    except urllib.error.URLError as exc:
        return None, str(exc.reason)

    download_url = _paper_download_url(version_detail)
    if not download_url:
        return None, f"No Paper download URL for Hangar {slug} {version_name}"

    return (
        PluginCandidate(
            install_key=_install_key(slug),
            name=name,
            slug=slug,
            source="hangar",
            description=(project.get("description") or "")[:500],
            downloads=int(stats.get("downloads", 0) or 0),
            page_url=page,
            download_url=download_url,
            platforms=["PAPER"],
            version=version_name,
            warning=warning,
        ),
        None,
    )


def _pick_version(versions: list[dict[str, Any]], mc: str) -> tuple[dict[str, Any], str]:
    """Prefer a version whose platformVersions include the configured MC version."""
    warning = ""
    for entry in reversed(versions):
        platforms = entry.get("platforms", {}) or entry.get("platformVersions", {})
        paper_versions: list[str] = []
        if isinstance(platforms, dict):
            paper_versions = list(platforms.get("PAPER", []) or platforms.get("paper", []))
        if mc in paper_versions:
            return entry, warning
    if versions:
        warning = f"No Hangar version matched MC {mc}; using latest ({versions[-1].get('name', '?')})"
        return versions[-1], warning
    return {}, warning


def _paper_download_url(version_detail: dict[str, Any]) -> str:
    downloads = version_detail.get("downloads", {})
    if isinstance(downloads, dict):
        paper = downloads.get("PAPER") or downloads.get("paper")
        if isinstance(paper, dict):
            url = paper.get("downloadUrl") or paper.get("externalUrl")
            if url:
                return str(url)
        for platform_dl in downloads.values():
            if isinstance(platform_dl, dict):
                url = platform_dl.get("downloadUrl") or platform_dl.get("externalUrl")
                if url:
                    return str(url)
    return ""
