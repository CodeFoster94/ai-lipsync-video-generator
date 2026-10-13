"""Registry: name -> plugin impl, with allowlist enforcement."""

from __future__ import annotations

from dataclasses import dataclass

from plugins.contracts import PLUGIN_API
from plugins.loader import LoadedPlugin, PluginLoader, PluginLoadError


@dataclass(slots=True)
class PluginEntry:
    plugin_id: str
    api: str
    summary: str
    requires_network: bool
    impl: type


class PluginRegistry:
    def __init__(self, loader: PluginLoader) -> None:
        self._loader = loader
        self._entries: dict[str, PluginEntry] = {}
        self._errors: list[str] = []

    def discover(self) -> None:
        loaded, errors = self._loader.load_all()
        self._errors = errors
        for lp in loaded:
            self._entries[lp.plugin_id] = PluginEntry(
                plugin_id=lp.plugin_id,
                api=lp.api,
                summary=lp.summary,
                requires_network=lp.requires_network,
                impl=lp.impl,
            )
        if not self._entries and errors:
            raise PluginLoadError("; ".join(errors))

    def get(self, plugin_id: str) -> PluginEntry:
        try:
            return self._entries[plugin_id]
        except KeyError as exc:
            raise KeyError(f"unknown plugin id: {plugin_id}") from exc

    def describe(self) -> list[PluginEntry]:
        return sorted(self._entries.values(), key=lambda e: e.plugin_id)

    def errors(self) -> list[str]:
        return list(self._errors)

    def api_version(self) -> str:
        return PLUGIN_API