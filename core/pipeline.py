"""Frame pipeline. Owns the loop, the writer, and plugin dispatch.

Contract with plugins:
  * plugins never touch the writer
  * plugins receive (frame, audio_window) and return a new frame
  * plugin exceptions abort the render with a clear message
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from plugins.contracts import FramePacket, LipSyncPlugin, RenderContext
from services.media_io import VideoReader, VideoWriter, AudioReader
from utils.timing import RateMeter
from utils.logging import get_logger

log = get_logger("core.pipeline")


@dataclass(slots=True)
class PipelineStats:
    frames_in: int
    frames_out: int
    duration_s: float
    mean_fps: float


class Pipeline:
    def __init__(self, plugin: LipSyncPlugin, ctx: RenderContext) -> None:
        self._plugin = plugin
        self._ctx = ctx

    def run(self) -> PipelineStats:
        ctx = self._ctx
        reader = VideoReader(ctx.face_video, fps=ctx.fps)
        audio = AudioReader(ctx.audio_path, target_rate=ctx.sample_rate)
        writer = VideoWriter(
            ctx.out_path,
            fps=ctx.fps,
            size=(ctx.width, ctx.height),
        )

        self._plugin.prepare(ctx)
        meter = RateMeter()
        frames_in = 0
        frames_out = 0

        try:
            for idx, (ts, rgb) in enumerate(reader.frames()):
                frames_in += 1
                window = audio.window_at(ts, seconds=1.0 / ctx.fps)
                packet = FramePacket(
                    index=idx,
                    timestamp_s=ts,
                    rgb=rgb,
                    audio_window=window,
                )
                try:
                    out = self._plugin.process_frame(packet, ctx)
                except Exception as exc:  # noqa: BLE001
                    log.error("plugin %s failed at frame %d: %r", self._plugin.plugin_id, idx, exc)
                    raise

                if out.shape[:2] != (ctx.height, ctx.width):
                    out = _resize_nearest(out, (ctx.height, ctx.width))

                writer.write(out)
                frames_out += 1
                meter.tick()
        finally:
            writer.close()
            reader.close()
            audio.close()

        self._plugin.finalize(ctx)
        stats = PipelineStats(
            frames_in=frames_in,
            frames_out=frames_out,
            duration_s=frames_out / max(ctx.fps, 1),
            mean_fps=meter.mean_rate(),
        )
        log.info(
            "render complete: %d/%d frames, %.2fs, %.1f fps",
            stats.frames_out,
            stats.frames_in,
            stats.duration_s,
            stats.mean_fps,
        )
        return stats


def _resize_nearest(frame: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    h, w = size
    ys = np.linspace(0, frame.shape[0] - 1, h).astype(int)
    xs = np.linspace(0, frame.shape[1] - 1, w).astype(int)
    return frame[ys][:, xs]