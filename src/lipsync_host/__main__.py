"""CLI bootstrap for the lip-sync plugin host.

Responsibilities:
  * parse argv
  * resolve config (file + env + flags)
  * build the plugin registry from declared search paths
  * dispatch to a handler (list / render / inspect)

Exit codes:
  0 success, 2 bad args, 3 config error, 4 plugin load failure,
  5 render failure.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from config.loader import load_config, ConfigError
from handlers.render_handler import RenderHandler
from handlers.inspect_handler import InspectHandler
from plugins.loader import PluginLoader, PluginLoadError
from plugins.registry import PluginRegistry
from utils.logging import configure_logging, get_logger


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="lipsync-host",
        description="Plugin-host for AI lip-sync video generation.",
    )
    p.add_argument("--config", type=Path, default=None, help="Path to config TOML.")
    p.add_argument("--plugin-path", action="append", default=[], help="Extra plugin dir.")
    p.add_argument("--list-plugins", action="store_true", help="List discovered plugins.")
    p.add_argument("--inspect", type=Path, default=None, help="Inspect a plugin folder.")
    p.add_argument("--face", type=Path, default=None, help="Driving face video/image.")
    p.add_argument("--audio", type=Path, default=None, help="Driving audio track.")
    p.add_argument("--out", type=Path, default=None, help="Output video path.")
    p.add_argument("--plugin", default=None, help="Force a specific plugin id.")
    p.add_argument("--no-network", action="store_true", help="Refuse plugins that need net.")
    p.add_argument("-v", "--verbose", action="count", default=0)
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    configure_logging(verbose=args.verbose)
    log = get_logger("lipsync_host")

    try:
        cfg = load_config(args.config)
    except ConfigError as exc:
        log.error("config error: %s", exc)
        return 3

    loader = PluginLoader(search_paths=[*cfg.plugin_paths, *args.plugin_path])
    registry = PluginRegistry(loader)

    try:
        registry.discover()
    except PluginLoadError as exc:
        log.error("plugin load failure: %s", exc)
        return 4

    if args.list_plugins:
        for entry in registry.describe():
            print(f"{entry.plugin_id:<28} api={entry.api:<6} {entry.summary}")
        return 0

    if args.inspect is not None:
        return InspectHandler(registry).run(args.inspect)

    if not (args.face and args.audio and args.out):
        log.error("render requires --face, --audio, --out")
        return 2

    handler = RenderHandler(registry, cfg, allow_network=not args.no_network)
    return handler.run(face=args.face, audio=args.audio, out=args.out, forced=args.plugin)


if __name__ == "__main__":
    sys.exit(main())