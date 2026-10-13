"""Render command handler. Resolves a plugin, builds context, runs pipeline."""

from __future__ import annotations

from pathlib import Path

from config.schema import HostConfig
from core.pipeline import Pipeline
from plugins.contracts import RenderContext
from plugins.registry import PluginRegistry
from utils.logging import get_logger

log = get_logger("handlers.render")


class RenderHandler:
    def __init__(
        self,
        registry: PluginRegistry,
        cfg: HostConfig,
        *,
        allow_network: bool = True,
    ) -> None:
        self._registry = registry
        self._cfg = cfg
        self._allow_network = allow_network

    def _pick_plugin_id(self, forced: str | None) -> str:
        if forced is not None:
            return forced
        entries = self._registry.describe()
        if not entries:
            raise RuntimeError("no plugins discovered")
        if self._allow_network:
            return entries[0].plugin_id
        offline = [e for e in entries if not e.requires_network]
        if not offline:
            raise RuntimeError("no offline plugins available")
        return offline[0].plugin_id

    def run(
        self,
        *,
        face: Path,
        audio: Path,
        out: Path,
        forced: str | None,
    ) -> int:
        for p in (face, audio):
            if not p.exists():
                log.error("input missing: %s", p)
                return 5
        out.parent.mkdir(parents=True, exist_ok=True)

        pid = self._pick_plugin_id(forced)
        try:
            entry = self._registry.get(pid)
        except KeyError as exc:
            log.error("%s", exc)
            return 4

        if entry.requires_network and not self._allow_network:
            log.error("plugin %s requires network, but --no-network was set", pid)
            return 4

        r = self._cfg.render
        ctx = RenderContext(
            face_video=face,
            audio_path=audio,