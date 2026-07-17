"""Remote plugin catalog: search Hangar, Modrinth, and SpigotMC; download jars."""

from mcserver.tools.plugins.models import PluginCandidate
from mcserver.tools.plugins.resolver import resolve_install_key, search_all

__all__ = ["PluginCandidate", "resolve_install_key", "search_all"]
