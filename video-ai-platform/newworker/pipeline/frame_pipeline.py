"""
FramePipeline — end-to-end orchestrator for a single video frame.

Execution order (all sequential, per architecture constraints):
  1. SigLIP          load → infer → unload     (GPU ~2GB)
  2. DepthAnything   load → infer → unload     (GPU ~1.5GB)
  3. Mask2Former     load → infer → unload     (GPU ~5.5GB)
  4. SceneGraph      infer                     (CPU, kept alive)
  5. SlowFast        load → infer → unload     (GPU ~3.5GB)
  6. ByteTracker     infer                     (CPU, kept alive)
  7. AudioProcessor  load → infer → unload     (GPU ~2.5GB, optional)
  8. FusionEngine    fuse                      (CPU)
  9. Qwen2-VL        caption                   (GPU ~8.5GB, pre-loaded)

Qwen2-VL stays loaded across frames (call setup() once before processing).
All perception models load/unload each frame so they never coexist with VLM.
Peak VRAM per frame: max(5.5GB perception, 8.5GB VLM) = 8.5GB — well within A10 24GB.

dry_run mode:
  Skips all model loading and GPU calls.  Returns placeholder outputs.
  Used by the test suite on machines without CUDA / without model weights.
"""

from __future__ import annotations

import gc
import time
from typing import Any, Dict, Optional

import numpy as np
import torch

from fusion import MultiModalFusionEngine
from optimization.profiler import TimingProfiler
from perception.base import PerceptionOutput
from .frame_result import FrameResult


# ─────────────────────────────────────────────────────────────────────────────
#  Dry-run placeholder helpers
# ─────────────────────────────────────────────────────────────────────────────

def _dummy_perception(name: str, frame_id: int, timestamp: float) -> PerceptionOutput:
    """Return an empty-but-valid PerceptionOutput for dry-run mode."""
    return PerceptionOutput(
        module_name=name,
        frame_id=frame_id,
        timestamp=timestamp,
        data={},
        metadata={"dry_run": True},
        processing_time=0.001,
        gpu_memory_used=None,
    )


def _dummy_vlm_caption(usr, frame_id: int, timestamp: float):
    """Return a placeholder VLMCaption for dry-run mode."""
    from vlm.vlm_caption import VLMCaption

    things = [t["label"] for t in usr.panoptic.get("things", [])]
    stub = f"[dry-run] Frame {frame_id}: {', '.join(things) or 'scene'} detected."
    return VLMCaption(
        frame_id=frame_id,
        timestamp=timestamp,
        caption=stub,
        scene_type=usr.scene_type,
        context_tags=usr.context_tags,
        model="dry-run",
        tokens_generated=len(stub.split()),
        processing_time=0.001,
        gpu_memory_used=None,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Pipeline
# ─────────────────────────────────────────────────────────────────────────────

class FramePipeline:
    """
    Single-frame processing pipeline.

    Typical usage:
        pipeline = FramePipeline(device="cuda", quantize_bits=8)

        with pipeline:           # calls setup() / teardown() automatically
            result = pipeline.process_frame(frame, frame_id=0, timestamp=0.0)

        print(result.caption.caption)
        print(result.format_timings())

    For testing without GPU:
        pipeline = FramePipeline(dry_run=True)
        with pipeline:
            result = pipeline.process_frame(frame, frame_id=0, timestamp=0.0)
    """

    def __init__(
        self,
        device: str = "cuda",
        quantize_bits: int = 8,
        max_vlm_tokens: int = 256,
        skip_audio: bool = False,
        dry_run: bool = False,
        # Inject a pre-built captioner (e.g. for tests)
        captioner=None,
    ):
        self.device = device
        self.quantize_bits = quantize_bits
        self.max_vlm_tokens = max_vlm_tokens
        self.skip_audio = skip_audio
        self.dry_run = dry_run

        self._fusion = MultiModalFusionEngine()
        self._captioner = captioner       # injected or created in setup()
        self._tracker = None
        self._scene_graph = None
        self._ready = False

    # ─────────────────────────────────────────────────────────────────
    #  Setup / teardown
    # ─────────────────────────────────────────────────────────────────

    def setup(self):
        """
        Pre-load Qwen2-VL + CPU modules.  Call once before processing frames.

        Qwen2-VL stays loaded across all frames processed by this pipeline
        instance, so its load cost is amortised.
        """
        if self._ready:
            return

        # GPU optimisation: allow cuDNN to benchmark and pick fastest kernels
        if torch.cuda.is_available() and not self.dry_run:
            torch.backends.cudnn.benchmark = True

        # CPU modules — instantiate and init once
        if not self.dry_run:
            from perception import SceneGraphGenerator, ByteTracker
            self._scene_graph = SceneGraphGenerator()
            self._scene_graph.load_model()
            self._tracker = ByteTracker()
            self._tracker.load_model()
        else:
            self._tracker = None
            self._scene_graph = None

        # VLM — load once, keep resident
        if not self.dry_run and self._captioner is None:
            from vlm import Qwen2VLCaptioner
            self._captioner = Qwen2VLCaptioner(
                quantize_bits=self.quantize_bits,
                max_new_tokens=self.max_vlm_tokens,
                device=self.device,
            )
            self._captioner.load()

        self._ready = True

    def teardown(self):
        """Unload all models and release GPU memory."""
        if self._captioner is not None and not self.dry_run:
            self._captioner.unload()
            self._captioner = None
        if self._tracker is not None:
            self._tracker.unload()
            self._tracker = None
        if self._scene_graph is not None:
            self._scene_graph.unload()
            self._scene_graph = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            gc.collect()
        self._ready = False

    def __enter__(self):
        self.setup()
        return self

    def __exit__(self, *args):
        self.teardown()

    # ─────────────────────────────────────────────────────────────────
    #  Main entry point
    # ─────────────────────────────────────────────────────────────────

    def process_frame(
        self,
        frame: torch.Tensor,
        frame_id: int,
        timestamp: float,
        audio: Optional[np.ndarray] = None,
        clip: Optional[Any] = None,
    ) -> FrameResult:
        """
        Run the full pipeline for one frame.

        Args:
            frame     : (H, W, 3) uint8 RGB tensor.
            frame_id  : Frame index in the video.
            timestamp : Time in seconds from video start.
            audio     : (N,) float32 mono 16kHz waveform for this frame's
                        audio segment.  Pass None to skip AudioProcessor.
            clip      : List of frames (or (T,H,W,3) tensor) for SlowFast.
                        If None, the single frame is tiled.

        Returns:
            FrameResult with usr, caption, timing breakdown.
        """
        if not self._ready:
            raise RuntimeError("Call setup() (or use 'with pipeline:') before process_frame()")

        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()

        profiler = TimingProfiler()

        # ── 1. SigLIP ────────────────────────────────────────────────
        with profiler.step("siglip"):
            siglip_out = self._run_gpu_module("SigLIPEncoder", frame, frame_id, timestamp)

        # ── 2. DepthAnything ─────────────────────────────────────────
        with profiler.step("depth"):
            depth_out = self._run_gpu_module("DepthEstimator", frame, frame_id, timestamp)

        # ── 3. Mask2Former ───────────────────────────────────────────
        with profiler.step("panoptic"):
            panoptic_out = self._run_gpu_module("PanopticSegmenter", frame, frame_id, timestamp)

        things = panoptic_out.data.get("things", []) if panoptic_out else []

        # ── 4. Scene Graph (CPU) ─────────────────────────────────────
        with profiler.step("scene_graph"):
            if self.dry_run:
                sg_out = _dummy_perception("SceneGraphGenerator", frame_id, timestamp)
            else:
                sg_out = self._scene_graph(
                    frame, frame_id, timestamp, panoptic_things=things
                )

        # ── 5. SlowFast ──────────────────────────────────────────────
        with profiler.step("slowfast"):
            action_out = self._run_gpu_module(
                "ActionRecognizer", frame, frame_id, timestamp, clip=clip
            )

        # ── 6. ByteTracker (CPU) ─────────────────────────────────────
        with profiler.step("tracker"):
            if self.dry_run:
                tracker_out = _dummy_perception("ByteTracker", frame_id, timestamp)
            else:
                tracker_out = self._tracker(
                    frame, frame_id, timestamp, panoptic_things=things
                )

        # ── 7. Audio (optional) ──────────────────────────────────────
        audio_out = None
        if audio is not None and not self.skip_audio:
            with profiler.step("audio"):
                audio_out = self._run_gpu_module(
                    "AudioProcessor", frame, frame_id, timestamp,
                    audio_waveform=audio
                )

        # ── 8. Fusion ────────────────────────────────────────────────
        with profiler.step("fusion"):
            usr = self._fusion.fuse(
                frame_id=frame_id,
                timestamp=timestamp,
                siglip=siglip_out,
                depth=depth_out,
                panoptic=panoptic_out,
                scene_graph=sg_out,
                tracker=tracker_out,
                actions=action_out,
                audio=audio_out,
            )

        # ── 9. Qwen2-VL caption ──────────────────────────────────────
        with profiler.step("vlm"):
            if self.dry_run:
                caption = _dummy_vlm_caption(usr, frame_id, timestamp)
            else:
                caption = self._captioner.caption(usr, frame)

        # ── Collect diagnostics ──────────────────────────────────────
        peak_vram = None
        if torch.cuda.is_available() and not self.dry_run:
            peak_vram = round(torch.cuda.max_memory_allocated() / 1e9, 2)

        step_times = profiler.to_dict()
        total_time = sum(step_times.values())
        return FrameResult(
            frame_id=frame_id,
            timestamp=timestamp,
            usr=usr,
            caption=caption,
            step_times=step_times,
            total_time=total_time,
            peak_vram_gb=peak_vram,
        )

    # ─────────────────────────────────────────────────────────────────
    #  Internal helpers
    # ─────────────────────────────────────────────────────────────────

    def _run_gpu_module(
        self,
        class_name: str,
        frame: torch.Tensor,
        frame_id: int,
        timestamp: float,
        **kwargs,
    ) -> PerceptionOutput:
        """
        Instantiate a perception module by class name, run it, then unload.

        Always uses try/finally so unload() is called even on exception.
        In dry_run mode returns a placeholder output without touching the GPU.
        """
        if self.dry_run:
            return _dummy_perception(class_name, frame_id, timestamp)

        import perception as _perc
        cls = getattr(_perc, class_name)
        module = cls(device=self.device)
        try:
            module.load_model()
            return module(frame, frame_id, timestamp, **kwargs)
        finally:
            module.unload()
