"""Audio/video alignment helpers.

The host runs at a fixed fps; audio is resampled to a fixed rate. This
module produces a monotonic mapping from frame index to audio sample
range, and detects drift between the two clocks.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Alignment:
    fps: int
    sample_rate: int

    @property
    def samples_per_frame(self) -> int:
        return int(round(self.sample_rate / self.fps))

    def frame_to_samples(self, frame_index: int) -> tuple[int, int]:
        s = frame_index * self.samples_per_frame
        return s, s + self.samples_per_frame

    def sample_to_frame(self, sample_index: int) -> int:
        return sample_index // max(self.samples_per_frame, 1)

    def drift_samples(self, total_frames: int, total_samples: int) -> int:
        """Positive means audio is longer than video by this many samples."""
        expected = total_frames * self.samples_per_frame
        return total_samples - expected