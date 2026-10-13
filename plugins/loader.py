"""Filesystem plugin loader.

Discovers `*.py` modules under each search path, imports them in a
sandboxed namespace, and returns classes that satisfy LipSyncPlugin.

Import is done via importlib so we don't pollute sys.modules with names
that could collide with stdlib. Failures on a single plugin are
reported, not fatal — the host keeps going.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path

from plugins.contracts import LipSyncPlugin, PLUGIN_API


class PluginLoadError(RuntimeError):
    """Raised when the loader cannot proceed at all."""


@dataclass(slots=True)
class LoadedPlugin:
    plugin_id: str
    api: str
    summary: str
    requires_network: bool
    impl: type


class PluginLoader:
    def __init__(self, search_paths: list[Path]) -> None:
        self._paths = [Path(p).resolve() for p in search_paths]

    def iter_modules(self) -> list[Path]:
        found: list[Path] = []
        for root in self._paths:
            if not root.is_dir():
                continue
            found.extend(sorted(root.rglob("*.py")))
        return [p for p in found if not p.name.startswith("_")]

    def load_one(self, module_path: Path) -> list[LoadedPlugin]:
        mod_name = f"lipsync_plugin_{module_path.stem}_{abs(hash(module_path)) % 10_000}"
        spec = importlib.util.spec_from_file_location(mod_name, module_path)
        if spec is None or spec.loader is None:
            raise PluginLoadError(f"cannot build spec for {module_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception as exc:  # noqa: BLE001 — plugin code is untrusted
            sys.modules.pop(mod_name, None)
            raise PluginLoadError(f"{module_path.name}: {exc!r}") from exc

        out: list[LoadedPlugin] = []
        for attr in vars(module).values():
            if not isinstance(attr, type):
                continue
            if not issubclass(attr, object):
                continue
            if getattr(attr, "__module__", None) != mod_name:
                continue
            if not isinstance(attr(), LipSyncPlugin):  # type: ignore[call-arg]
                continue
            api = getattr(attr, "api", "?")
            if api != PLUGIN_API:
                raise PluginLoadError(
                    f"{attr.__name__} targets api {api}, host is {PLUGIN_API}"
                )
            out.append(
                LoadedPlugin(
                    plugin_id=attr.plugin_id,
                    api=api,
                    summary=getattr(attr, "summary", ""),
                    requires_network=bool(getattr(attr, "requires_network", False)),
                    impl=attr,
                )
            )
        return out

    def load_all(self) -> tuple[list[LoadedPlugin], list[str]]:
        loaded: list[LoadedPlugin] = []
        errors: list[str] = []
        for mod in self.iter_modules():
            try:
                loaded.extend(self.load_one(mod))
            except PluginLoadError as exc:
                errors.append(str(exc))
        return loaded, errors