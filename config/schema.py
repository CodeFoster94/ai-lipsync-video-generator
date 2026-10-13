"""Typed config schema for the host.

SCHEMA_VERSION is bumped whenever a field is added/removed/renamed.
The loader refuses to start if the on-disk version is newer than this.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

SCHEMA_VERSION: int = 4


class RenderConfig(BaseModel):
    fps: int = Field(25, ge=1, le=120)
    width: int = Field(1280, ge=64, le=7680)
    height: int = Field(720, ge=64, le=4320)
    codec: Literal["h264", "h265", "vp9"] = "h264"
    bitrate_kbps: int = Field(8000, ge=500, le=120_000)
    audio_sample_rate: int = Field(16_000, ge=8_000, le=48_000)


class ModelConfig(BaseModel):
    runtime: Literal["onnx", "torch"] = "onnx"
    device: Literal["auto", "cpu", "cuda", "dml"] = "auto"
    face_detector: str = "s3fd"
    phoneme_model: str = "wav2vec2-lite"
    max_frames_per_batch: int = Field(16, ge=1, le=256)


class HostConfig(BaseModel):
    schema_version: int = SCHEMA_VERSION
    plugin_paths: list[Path] = Field(default_factory=list)
    render: RenderConfig = Field(default_factory=RenderConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"