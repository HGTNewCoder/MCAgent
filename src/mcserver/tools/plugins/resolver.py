"""Unified plugin search and install-key resolution."""

from __future__ import annotations

import re

from mcserver import config
from mcserver.tools.plugins import hangar, modrinth, spigot
from mcserver.tools.plugins.models import PluginCandidate

_SOURCE_ORDER = ("hangar", "modrinth", "spigot")
_RESOLVERS = {
    "hangar": hangar.resolve,
    "modrinth": modrinth.resolve,
    "spigot": spigot.resolve,
}
_SEARCHERS = {
    "hangar": hangar.search,
    "modrinth": modrinth.search,
    "spigot": spigot.search,
}


def parse_install_key(install_key: str) -> tuple[str, str]:
    key = install_key.strip()
    if ":" not in key:
        raise ValueError(
            f"Invalid install_key '{install_key}'. Expected format: source:slug_or_id"
        )
    source, identifier = key.split(":", 1)
    source = source.lower().strip()
    identifier = identifier.strip()
    if not source or not identifier:
        raise ValueError(f"Invalid install_key '{install_key}'")
    return source, identifier


def is_blocklisted(candidate: PluginCandidate) -> bool:
    blocklist = config.PLUGIN_BLOCKLIST
    if not blocklist:
        return False
    keys = {
        candidate.name.lower(),
        candidate.slug.lower(),
        candidate.install_key.lower(),
    }
    return bool(keys & blocklist)


def search_all(query: str) -> dict:
    """Search all allowed sources and return merged matches for the agent."""
    q = query.strip()
    if not q:
        return {"ok": False, "error": "Search query must not be empty", "matches": []}

    all_matches: list[PluginCandidate] = []
    source_errors: list[dict[str, str]] = []

    for source in _SOURCE_ORDER:
        if source not in config.PLUGIN_ALLOWED_SOURCES:
            continue
        search_fn = _SEARCHERS[source]
        matches, err = search_fn(q)
        if err:
            source_errors.append({"source": source, "error": err})
        all_matches.extend(matches)

    ranked = _merge_and_rank(all_matches, q)
    return {
        "ok": True,
        "query": q,
        "matches": [m.to_match_dict() for m in ranked],
        "source_errors": source_errors,
        "note": "Results from Hangar, Modrinth, and SpigotMC. Use install_key with install_plugin.",
    }


def resolve_install_key(install_key: str) -> tuple[PluginCandidate | None, str | None]:
    try:
        source, identifier = parse_install_key(install_key)
    except ValueError as exc:
        return None, str(exc)

    if source not in config.PLUGIN_ALLOWED_SOURCES:
        return None, f"Source '{source}' is not allowed. Allowed: {sorted(config.PLUGIN_ALLOWED_SOURCES)}"

    resolver = _RESOLVERS.get(source)
    if resolver is None:
        return None, f"Unknown source '{source}'"

    candidate, err = resolver(identifier)
    if err or candidate is None:
        return None, err or f"Could not resolve {install_key}"

    if is_blocklisted(candidate):
        return None, f"Plugin '{candidate.name}' is on the blocklist. Refusing install."

    return candidate, None


def stub_candidate_from_key(install_key: str) -> tuple[PluginCandidate | None, str | None]:
    """Build a minimal candidate for stub mode without network I/O."""
    try:
        source, identifier = parse_install_key(install_key)
    except ValueError as exc:
        return None, str(exc)

    if source not in config.PLUGIN_ALLOWED_SOURCES:
        return None, f"Source '{source}' is not allowed."

    name = identifier if source != "spigot" else f"Spigot-{identifier}"
    candidate = PluginCandidate(
        install_key=f"{source}:{identifier}",
        name=name,
        slug=identifier,
        source=source,
        description="",
    )
    if is_blocklisted(candidate):
        return None, f"Plugin '{name}' is on the blocklist."
    return candidate, None


def _merge_and_rank(candidates: list[PluginCandidate], query: str) -> list[PluginCandidate]:
    q = query.lower()
    seen: dict[str, PluginCandidate] = {}

    for candidate in candidates:
        norm = _normalize_name(candidate.name)
        existing = seen.get(norm)
        if existing is None or _score(candidate, q) > _score(existing, q):
            seen[norm] = candidate

    ranked = sorted(seen.values(), key=lambda c: _score(c, q), reverse=True)
    return ranked[: config.PLUGIN_SEARCH_LIMIT * len(_SOURCE_ORDER)]


def _normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def _score(candidate: PluginCandidate, query: str) -> float:
    name = candidate.name.lower()
    q = query.lower()
    score = float(candidate.downloads)
    if name == q:
        score += 1_000_000
    elif name.startswith(q):
        score += 500_000
    elif q in name:
        score += 250_000
    if q in candidate.description.lower():
        score += 50_000
    if candidate.source == "hangar":
        score += 10_000
    return score
