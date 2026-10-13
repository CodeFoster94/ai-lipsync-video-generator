"""Shared contracts every lip-sync plugin must satisfy.

A plugin is a class decorated with @register_plugin that implements
LipSyncPlugin. The host calls hooks in a fixed order:

    prepare(ctx) -> for each frame: process_frame(frame, ctx) -> finalize(ctx)

The host owns frame pacing and the video writer; plugins only transform
frames and produce audio-aligned mouth-region tensors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import numpy as np

PLUGIN_API: str = "0.6"


@dataclass(slots=True)
class RenderContext:
    """Per-render state handed to plugins. Mutable by design."""

    face_video: Path
    audio_path: Path
    out_path: Path
    fps: int
    width: int
    height: int
    sample_rate: int
    device: str
    scratch: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class FramePacket:
    """One decoded video frame plus its audio window."""

    index: int
    timestamp_s: float
    rgb: np.ndarray  # uint8, shape (H, W, 3)
    audio_window: np.ndarray  # float32, mono, shape (N,)


@runtime_checkable
class LipSyncPlugin(Protocol):
    """Structural contract. Implement all members."""

    plugin_id: str
    api: str
    summary: str
    requires_network: bool

    def prepare(self, ctx: RenderContext) -> None: ...

    def process_frame(self, packet: FramePacket, ctx: RenderContext) -> np.ndarray: ...

    def finalize(self, ctx: RenderContext) -> None: ...


_REGISTRY: dict[str, type] = {}


def register_plugin(cls: type) -> type:
    """Class decorator. Adds the plugin to the in-process registry."""
    pid = getattr(cls, "plugin_id", None)
    if not isinstance(pid, str) or not pid:
        raise ValueError(f"{cls.__name__} must define a non-empty plugin_id")
    if pid in _REGISTRY:
        raise ValueError(f"duplicate plugin_id: {pid}")
    _REGISTRY[pid] = cls
    return cls


def in_process_registry() -> dict[str, type]:
    return dict(_REGISTRY)