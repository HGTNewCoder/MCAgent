"""SpigotMC plugin catalog client (Spiget search + XenForo metadata)."""

from __future__ import annotations

import base64
import html
import re
import urllib.error
import urllib.parse

from mcserver import config
from mcserver.tools.plugins.http import fetch_json, http_error_message
from mcserver.tools.plugins.models import PluginCandidate

SPIGET_BASE = "https://api.spiget.org/v2"
SPIGOT_API_BASE = "https://api.spigotmc.org/simple/0.2/index.php"


def _install_key(resource_id: int | str) -> str:
    return f"spigot:{resource_id}"


def search(query: str, *, limit: int | None = None) -> tuple[list[PluginCandidate], str | None]:
    limit = limit or config.PLUGIN_SEARCH_LIMIT
    q = urllib.parse.quote(query.strip())
    url = f"{SPIGET_BASE}/search/resources/{q}?field=name&size={limit}"
    try:
        data = fetch_json(url)
    except urllib.error.HTTPError as exc:
        return [], http_error_message(exc)
    except urllib.error.URLError as exc:
        return [], str(exc.reason)

    results: list[PluginCandidate] = []
    for item in data if isinstance(data, list) else []:
        resource_id = item.get("id")
        name = item.get("name", "")
        if resource_id is None or not name:
            continue
        if item.get("premium") or item.get("external"):
            continue
        description = _plain_description(item.get("tag") or "")
        results.append(
            PluginCandidate(
                install_key=_install_key(resource_id),
                name=name,
                slug=str(resource_id),
                source="spigot",
                description=description[:500],
                downloads=int(item.get("downloads", 0) or 0),
                page_url=f"https://www.spigotmc.org/resources/{resource_id}/",
                platforms=["SPIGOT", "PAPER"],
            )
        )
    return results, None


def resolve(resource_id: str) -> tuple[PluginCandidate | None, str | None]:
    try:
        rid = int(resource_id)
    except ValueError:
        return None, f"Invalid Spigot resource id: {resource_id}"

    spiget_url = f"{SPIGET_BASE}/resources/{rid}"
    try:
        resource = fetch_json(spiget_url)
    except urllib.error.HTTPError as exc:
        return None, http_error_message(exc)
    except urllib.error.URLError as exc:
        return None, str(exc.reason)

    if resource.get("premium"):
        return None, f"Spigot resource {rid} is premium — cannot auto-install"
    if resource.get("external"):
        return None, f"Spigot resource {rid} uses external download — cannot auto-install"

    name = resource.get("name") or str(rid)
    description = _plain_description(resource.get("tag") or "")

    xen_url = f"{SPIGOT_API_BASE}?action=getResource&id={rid}"
    downloads = int(resource.get("downloads", 0) or 0)
    try:
        meta = fetch_json(xen_url)
        if meta.get("description"):
            description = _plain_description(meta["description"])[:500]
        downloads = int(meta.get("stats", {}).get("downloads", downloads) or downloads)
    except (urllib.error.HTTPError, urllib.error.URLError):
        pass

    download_url = f"{SPIGET_BASE}/resources/{rid}/download"
    version = ""
    try:
        latest = fetch_json(f"{SPIGET_BASE}/resources/{rid}/versions/latest")
        version = str(latest.get("name", "") or latest.get("id", ""))
    except (urllib.error.HTTPError, urllib.error.URLError):
        pass

    return (
        PluginCandidate(
            install_key=_install_key(rid),
            name=name,
            slug=str(rid),
            source="spigot",
            description=description[:500],
            downloads=downloads,
            page_url=f"https://www.spigotmc.org/resources/{rid}/",
            download_url=download_url,
            platforms=["SPIGOT", "PAPER"],
            version=version,
        ),
        None,
    )


def _plain_description(raw: str) -> str:
    text = raw.strip()
    if not text:
        return ""
    try:
        if re.fullmatch(r"[A-Za-z0-9+/=\s]+", text.replace("\n", "")):
            text = base64.b64decode(text).decode("utf-8", errors="replace")
    except Exception:
        pass
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()
