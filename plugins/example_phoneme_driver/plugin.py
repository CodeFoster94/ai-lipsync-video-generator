"""Reference plugin: maps audio windows to viseme weights.

This is the smallest non-trivial plugin we ship. It uses a tiny
lookup table (phoneme -> viseme) and a mouth-region warp. Real plugins
would call an ONNX phoneme model; this one is deterministic and offline
so it's useful as a smoke-test target for the host.
"""

from __future__ import annotations

import numpy as np

from plugins.contracts import (
    FramePacket,
    LipSyncPlugin,
    RenderContext,
    register_plugin,
)


# Coarse phoneme-class -> (mouth_open, mouth_wide, jaw_drop) weights.
_VISEME_TABLE: dict[str, tuple[float, float, float]] = {
    "sil": (0.00, 0.00, 0.00),
    "AA": (0.85, 0.30, 0.55),
    "IY": (0.35, 0.80, 0.20),
    "UW": (0.45, 0.10, 0.30),
    "EH": (0.55, 0.45, 0.35),
    "TH": (0.25, 0.35, 0.10),
    "M": (0.00, 0.15, 0.00),
}


@register_plugin
class PhonemeDriverPlugin:
    plugin_id = "example.phoneme_driver"
    api = "0.6"
    summary = "Reference phoneme->viseme driver (offline, deterministic)."
    requires_network = False

    def prepare(self, ctx: RenderContext) -> None:
        ctx.scratch["frame_count"] = 0

    def _classify_window(self, window: np.ndarray) -> str:
        # Cheap energy-based proxy for a real phoneme model.
        if window.size == 0:
            return "sil"
        rms = float(np.sqrt(np.mean(window.astype(np.float32) ** 2)))
        if rms < 0.01:
            return "sil"
        zcr = float(np.mean(np.abs(np.diff(np.sign(window))))) / 2.0
        if zcr < 0.15:
            return "M" if rms < 0.05 else "AA"
        if zcr < 0.35:
            return "EH"
        return "IY"

    def process_frame(self, packet: FramePacket, ctx: RenderContext) -> np.ndarray:
        viseme = self._classify_window(packet.audio_window)
        open_w, wide_w, jaw_w = _VISEME_TABLE[viseme]
        frame = packet.rgb.astype(np.float32) / 255.0

        # Mouth region: lower third, horizontal center. Warp is a simple
        # horizontal scale + vertical offset. Placeholder for a real warp.
        h, w = frame.shape[:2]
        y0, y1 = int(h * 0.62), int(h * 0.98)
        x0, x1 = int(w * 0.30), int(w * 0.70)
        mouth = frame[y0:y1, x0:x1]

        if mouth.size:
            scale_x = 1.0 + wide_w * 0.35
            scale_y = 1.0 + open_w * 0.55
            new_w = max(2, int(mouth.shape[1] * scale_x))
            new_h = max(2, int(mouth.shape[0] * scale_y))
            ys = np.linspace(0, mouth.shape[0] - 1, new_h)
            xs = np.linspace(0, mouth.shape[1] - 1, new_w)
            yy, xx = np.meshgrid(ys, xs, indexing="ij")
            y0i = np.clip(yy.astype(int), 0, mouth.shape[0] - 1)
            x0i = np.clip(xx.astype(int), 0, mouth.shape[1] - 1)
            warped = mouth[y0i, x0i]
            # Resample back to original mouth box.
            ys2 = np.linspace(0, warped.shape[0] - 1, mouth.shape[0])
            xs2 = np.linspace(0, warped.shape[1] - 1, mouth.shape[1])
            yy2, xx2 = np.meshgrid(ys2, xs2, indexing="ij")
            y1i = np.clip(yy2.astype(int), 0, warped.shape[0] - 1)
            x1i = np.clip(xx2.astype(int), 0, warped.shape[1] - 1)
            frame[y0:y1, x0:x1] = warped[y1i, x1i]

        ctx.scratch["frame_count"] = int(ctx.scratch.get("frame_count", 0)) + 1
        return np.clip(frame * 255.0, 0, 255).astype(np.uint8)

    def finalize(self, ctx: RenderContext) -> None:
        ctx.scratch["frames_emitted"] = ctx.scratch.get("frame_count", 0)