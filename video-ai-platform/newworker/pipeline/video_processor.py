"""
VideoProcessor — extracts frames and audio from an MP4 file.

Frame extraction uses OpenCV (cv2.VideoCapture).
Audio extraction uses a subprocess call to ffmpeg, loading the result
with scipy.io.wavfile for reliability across platforms.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import warnings
from dataclasses import dataclass
from typing import Generator, List, Optional

import cv2
import numpy as np
import torch


@dataclass
class FrameData:
    frame_id: int
    timestamp: float
    frame: torch.Tensor  # (H, W, 3) uint8 RGB


class VideoProcessor:
    """
    Extracts sampled frames and full audio from an MP4 file.

    Args:
        sample_fps:        Target sampling rate in frames per second.
                           e.g. 1.0 = one frame per second.
        audio_sample_rate: Target audio sample rate (Hz). Default 16 kHz.
    """

    MAX_FRAMES = 120  # hard cap for very long videos

    def __init__(self, sample_fps: float = 1.0, audio_sample_rate: int = 16000):
        self.sample_fps = sample_fps
        self.audio_sample_rate = audio_sample_rate

    # ─────────────────────────────────────────────────────────────────
    #  Frame extraction
    # ─────────────────────────────────────────────────────────────────

    def extract_frames(self, video_path: str) -> List[FrameData]:
        """
        Sample frames from the video at self.sample_fps.

        Returns:
            List of FrameData (up to MAX_FRAMES), ordered by timestamp.
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise IOError(f"Cannot open video: {video_path}")

        source_fps = cap.get(cv2.CAP_PROP_FPS)
        if source_fps <= 0:
            source_fps = 25.0  # fallback

        # How many source frames to skip between samples
        step = max(1, int(round(source_fps / self.sample_fps)))

        frames: List[FrameData] = []
        source_frame_idx = 0

        while True:
            ret, bgr = cap.read()
            if not ret:
                break

            if source_frame_idx % step == 0:
                # BGR → RGB
                rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                tensor = torch.from_numpy(rgb)  # (H, W, 3) uint8
                timestamp = source_frame_idx / source_fps
                frames.append(FrameData(
                    frame_id=len(frames),
                    timestamp=round(timestamp, 4),
                    frame=tensor,
                ))
                if len(frames) >= self.MAX_FRAMES:
                    break

            source_frame_idx += 1

        cap.release()
        return frames

    def iter_frames(self, video_path: str) -> Generator[FrameData, None, None]:
        """
        Memory-efficient generator that yields one FrameData at a time.
        Only one frame tensor is live in RAM at any point — use this in the
        main pipeline instead of extract_frames() to avoid OOM on large videos.
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise IOError(f"Cannot open video: {video_path}")

        source_fps = cap.get(cv2.CAP_PROP_FPS)
        if source_fps <= 0:
            source_fps = 25.0

        step = max(1, int(round(source_fps / self.sample_fps)))
        frame_count = 0
        source_frame_idx = 0

        try:
            while True:
                ret, bgr = cap.read()
                if not ret:
                    break
                if source_frame_idx % step == 0:
                    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                    tensor = torch.from_numpy(rgb.copy())
                    timestamp = source_frame_idx / source_fps
                    yield FrameData(
                        frame_id=frame_count,
                        timestamp=round(timestamp, 4),
                        frame=tensor,
                    )
                    frame_count += 1
                    if frame_count >= self.MAX_FRAMES:
                        break
                source_frame_idx += 1
        finally:
            cap.release()

    # ─────────────────────────────────────────────────────────────────
    #  Audio extraction
    # ─────────────────────────────────────────────────────────────────

    def extract_audio(self, video_path: str) -> Optional[np.ndarray]:
        """
        Extract full audio track as a mono float32 numpy array at
        self.audio_sample_rate Hz.

        Uses a subprocess call to ffmpeg (more reliable than ffmpeg-python).
        Returns None if there is no audio track or if ffmpeg fails.
        """
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name

            cmd = [
                "ffmpeg",
                "-y",                          # overwrite
                "-i", video_path,
                "-vn",                         # no video
                "-ac", "1",                    # mono
                "-ar", str(self.audio_sample_rate),
                "-f", "wav",
                "-loglevel", "error",
                tmp_path,
            ]

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=120,
            )

            if result.returncode != 0:
                # No audio stream or ffmpeg error
                return None

            if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) == 0:
                return None

            from scipy.io import wavfile
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                sr, data = wavfile.read(tmp_path)

            # Convert to float32 in [-1.0, 1.0]
            if data.dtype == np.int16:
                audio = data.astype(np.float32) / 32768.0
            elif data.dtype == np.int32:
                audio = data.astype(np.float32) / 2147483648.0
            elif data.dtype == np.uint8:
                audio = (data.astype(np.float32) - 128.0) / 128.0
            else:
                audio = data.astype(np.float32)

            # Ensure 1-D (mono)
            if audio.ndim > 1:
                audio = audio.mean(axis=1)

            return audio

        except Exception:
            return None
        finally:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass

    # ─────────────────────────────────────────────────────────────────
    #  Audio slicing
    # ─────────────────────────────────────────────────────────────────

    def get_audio_segment(
        self,
        audio: np.ndarray,
        timestamp: float,
        duration: float = 1.0,
        sr: int = 16000,
    ) -> np.ndarray:
        """
        Slice audio array to [timestamp, timestamp + duration] seconds.

        Returns a zero-padded array if the slice extends past the end.
        """
        start_sample = int(timestamp * sr)
        end_sample = int((timestamp + duration) * sr)

        total_samples = len(audio)
        if start_sample >= total_samples:
            return np.zeros(int(duration * sr), dtype=np.float32)

        segment = audio[start_sample:end_sample]

        # Zero-pad if segment is shorter than requested duration
        expected_len = int(duration * sr)
        if len(segment) < expected_len:
            segment = np.pad(segment, (0, expected_len - len(segment)))

        return segment.astype(np.float32)

    # ─────────────────────────────────────────────────────────────────
    #  Video info
    # ─────────────────────────────────────────────────────────────────

    def get_video_info(self, video_path: str) -> dict:
        """
        Return basic video metadata.

        Returns:
            {duration, fps, width, height, frame_count}
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise IOError(f"Cannot open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = frame_count / fps if fps > 0 else 0.0

        cap.release()

        return {
            "duration": round(duration, 3),
            "fps": round(fps, 3),
            "width": width,
            "height": height,
            "frame_count": frame_count,
        }
