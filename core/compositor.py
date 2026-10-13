"""Frame compositor.

Plugins return a full frame. The compositor is responsible for
enforcing output geometry and codec-friendly pixel formats. Kept
separate from the pipeline so plugins and the writer can evolve
independently.
"""

from __future__ import annotations

import numpy as np


def ensure_bgr(frame: np.ndarray) -> np.ndarray:
    if frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError(f"expected HxWx3 frame, got {frame.shape}")
    return frame


def letterbox(frame: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    """Fit `frame` into `size` (w, h) preserving aspect, pad with black."""
    h, w = size[1], size[0]
    fh, fw = frame.shape[:2]
    scale = min(w / fw, h / fh)
    nw, nh = int(fw * scale), int(fh * scale)
    ys = np.linspace(0, fh - 1, nh).astype(int)
    xs = np.linspace(0, fw - 1, nw).astype(int)
    resized = frame[ys][:, xs]
    canvas = np.zeros((h, w, 3), dtype=frame.dtype)
    y0 = (h - nh) // 2
    x0 = (w - nw) // 2
    canvas[y0 : y0 + nh, x0 : x0 + nw] = resized
    return canvas