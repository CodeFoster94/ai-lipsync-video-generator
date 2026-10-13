"""Config loader: TOML file -> HostConfig, with env overrides."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

from pydantic import ValidationError

from config.schema import HostConfig, SCHEMA_VERSION


class ConfigError(RuntimeError):
    """Raised for any user-facing config problem."""


def _default_path() -> Path:
    return Path.cwd() / "config" / "default.toml"


def _apply_env(cfg: HostConfig) -> HostConfig:
    if (lv := os.environ.get("LIPSYNC_LOG_LEVEL")) is not None:
        cfg = cfg.model_copy(update={"log_level": lv.upper()})  # type: ignore[arg-type]
    if (pp := os.environ.get("LIPSYNC_PLUGIN_PATHS")) is not None:
        extra = [Path(p) for p in pp.split(os.pathsep) if p]
        cfg = cfg.model_copy(update={"plugin_paths": [*cfg.plugin_paths, *extra]})
    return cfg


def load_config(path: Path | None) -> HostConfig:
    target = path or _default_path()
    if not target.exists():
        return _apply_env(HostConfig())

    raw = tomllib.loads(target.read_text(encoding="utf-8"))
    version = int(raw.get("schema_version", 0))
    if version > SCHEMA_VERSION:
        raise ConfigError(
            f"config schema {version} is newer than host schema {SCHEMA_VERSION}"
        )

    try:
        cfg = HostConfig.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(str(exc)) from exc

    return _apply_env(cfg)