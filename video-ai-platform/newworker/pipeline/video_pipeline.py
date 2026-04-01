"""
VideoPipeline — full end-to-end video processing pipeline.

MP4 → sampled frames + audio → per-frame analysis (FramePipeline)
    → TemporalAssembly → NarrativeGenerator → VideoResult

Target: process a 33 s video in < 5 minutes on a g5.2xlarge (A10 GPU).

Usage:
    pipeline = VideoPipeline(device="cuda", quantize_bits=8, sample_fps=1.0)
    result = pipeline.process("path/to/video.mp4", video_id="abc123")
    print(result.summary())

Dry-run (no GPU / no model weights required):
    pipeline = VideoPipeline(dry_run=True)
    result = pipeline.process("path/to/video.mp4")
"""

from __future__ import annotations

import os
import time
import traceback
import warnings
from collections import deque
from typing import Deque, List, Optional

import torch

from narrative.narrative_generator import NarrativeGenerator
from narrative.temporal_assembly import TemporalAssembly
from pipeline.frame_pipeline import FramePipeline
from pipeline.frame_result import FrameResult
from pipeline.video_processor import FrameData, VideoProcessor
from pipeline.video_result import VideoResult


# Dry-run stub for NarrativeGenerator so no Claude API key is needed
class _DryRunNarrativeGenerator:
    def generate(self, frame_results, temporal_assembly=None):
        from narrative.narrative_result import NarrativeResult

        assembly = temporal_assembly or TemporalAssembly.from_frame_results(frame_results)
        stub = (
            f"[dry-run narrative] Processed {len(frame_results)} frames "
            f"spanning {assembly.video_duration:.1f}s. "
            "No real narrative generated in dry-run mode."
        )
        return NarrativeResult(
            narrative=stub,
            video_duration=assembly.video_duration,
            frame_count=assembly.frame_count,
            model="dry-run",
            input_tokens=0,
            output_tokens=len(stub.split()),
            processing_time=0.001,
            metadata={"dry_run": True},
        )


class VideoPipeline:
    """
    Full video processing pipeline: MP4 → frames → per-frame analysis → narrative.

    Processing steps:
    1. VideoProcessor extracts sampled frames + full audio
    2. FramePipeline processes each frame (with rolling clip buffer for SlowFast)
    3. TemporalAssembly aggregates all FrameResults
    4. NarrativeGenerator calls Claude API for final narrative

    Target: 33 s video in < 5 minutes on g5.2xlarge
    """

    # Rolling window size for the SlowFast clip buffer
    CLIP_BUFFER_SIZE = 32

    def __init__(
        self,
        device: str = "cuda",
        quantize_bits: int = 8,
        sample_fps: float = 1.0,
        skip_audio: bool = False,
        dry_run: bool = False,
    ):
        self.device = device
        self.quantize_bits = quantize_bits
        self.sample_fps = sample_fps
        self.skip_audio = skip_audio
        self.dry_run = dry_run

        self.video_processor = VideoProcessor(sample_fps=sample_fps)

        self.frame_pipeline = FramePipeline(
            device=device,
            quantize_bits=quantize_bits,
            skip_audio=skip_audio,
            dry_run=dry_run,
        )

        if dry_run:
            self.narrative_gen = _DryRunNarrativeGenerator()
        else:
            self.narrative_gen = NarrativeGenerator()

    # ─────────────────────────────────────────────────────────────────
    #  Main entry point
    # ─────────────────────────────────────────────────────────────────

    def process(self, video_path: str, video_id: Optional[str] = None) -> VideoResult:
        """
        Process a full video file end-to-end.

        Args:
            video_path: Absolute or relative path to the MP4 file.
            video_id:   Optional identifier; defaults to the filename stem.

        Returns:
            VideoResult containing narrative, frame results, and diagnostics.
        """
        if video_id is None:
            video_id = os.path.splitext(os.path.basename(video_path))[0]

        t_start = time.time()

        # ── 1. Video info ─────────────────────────────────────────────
        info = self.video_processor.get_video_info(video_path)
        duration = info["duration"]
        print(f"Video   : {video_path}")
        print(f"ID      : {video_id}")
        print(f"Duration: {duration:.1f}s  |  {info['fps']:.2f} fps  |  "
              f"{info['width']}x{info['height']}")

        # ── 2. Frame extraction ───────────────────────────────────────
        print("Extracting frames...")
        frames: List[FrameData] = self.video_processor.extract_frames(video_path)
        n_frames = len(frames)
        print(f"Extracted {n_frames} frames (sample_fps={self.sample_fps})")

        # ── 3. Audio extraction ───────────────────────────────────────
        audio = None
        if not self.skip_audio:
            print("Extracting audio...")
            audio = self.video_processor.extract_audio(video_path)
            if audio is not None:
                print(f"Audio   : {len(audio) / self.video_processor.audio_sample_rate:.1f}s "
                      f"@ {self.video_processor.audio_sample_rate} Hz")
            else:
                print("Audio   : none (no audio track or extraction failed)")

        # ── 4. Per-frame analysis ─────────────────────────────────────
        frame_results: List[FrameResult] = []

        # Rolling clip buffer for SlowFast (ActionRecognizer)
        clip_buffer: Deque[torch.Tensor] = deque(maxlen=self.CLIP_BUFFER_SIZE)

        with self.frame_pipeline:
            for i, fd in enumerate(frames):
                print(f"Processing frame {i + 1}/{n_frames} (t={fd.timestamp:.1f}s)...",
                      flush=True)

                # Update clip buffer
                clip_buffer.append(fd.frame)
                clip = list(clip_buffer)  # list of (H, W, 3) tensors

                # Slice 1 s audio segment at this frame's timestamp
                audio_segment = None
                if audio is not None and not self.skip_audio:
                    audio_segment = self.video_processor.get_audio_segment(
                        audio,
                        timestamp=fd.timestamp,
                        duration=1.0,
                        sr=self.video_processor.audio_sample_rate,
                    )

                try:
                    result = self.frame_pipeline.process_frame(
                        frame=fd.frame,
                        frame_id=fd.frame_id,
                        timestamp=fd.timestamp,
                        audio=audio_segment,
                        clip=clip,
                    )
                    frame_results.append(result)
                except Exception as exc:
                    warnings.warn(
                        f"Frame {fd.frame_id} (t={fd.timestamp:.1f}s) failed: {exc}",
                        RuntimeWarning,
                        stacklevel=2,
                    )
                    traceback.print_exc()
                    continue  # skip this frame, keep going

        if not frame_results:
            raise RuntimeError("All frames failed to process; cannot produce VideoResult.")

        # ── 5. Temporal assembly ──────────────────────────────────────
        print("Building temporal assembly...")
        temporal_assembly = TemporalAssembly.from_frame_results(frame_results)

        # ── 6. Narrative generation ───────────────────────────────────
        print("Generating narrative...")
        narrative = self.narrative_gen.generate(frame_results, temporal_assembly)

        # ── 7. Diagnostics ────────────────────────────────────────────
        total_time = time.time() - t_start

        # Peak VRAM = max across all frames
        vram_values = [fr.peak_vram_gb for fr in frame_results if fr.peak_vram_gb is not None]
        peak_vram = max(vram_values) if vram_values else None

        result = VideoResult(
            video_path=video_path,
            video_id=video_id,
            duration=duration,
            frame_count=len(frame_results),
            frame_results=frame_results,
            temporal_assembly=temporal_assembly,
            narrative=narrative,
            total_processing_time=round(total_time, 3),
            peak_vram_gb=peak_vram,
        )

        print(result.summary())
        return result
