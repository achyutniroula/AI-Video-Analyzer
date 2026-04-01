"""
Phase 6 Test Suite — VideoProcessor, VideoResult, VideoPipeline, config, SQS parsing.

All tests run without a GPU, real model weights, or real AWS credentials.

Run with:
    python tests/test_video_pipeline.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ─────────────────────────────────────────────────────────────────────────────
#  Stub heavy / absent dependencies before any pipeline imports
#
#  The perception layer unconditionally imports `transformers`, `timm`, etc.
#  at module level.  These are not available in this lean test environment.
#  We register lightweight stub modules so the import chain succeeds without
#  downloading any weights.
# ─────────────────────────────────────────────────────────────────────────────

import types as _types
from unittest.mock import MagicMock as _MM

def _stub(name: str):
    """Register a MagicMock module under `name` if not already present."""
    if name not in sys.modules:
        m = _types.ModuleType(name)
        # Module-level __getattr__ (PEP 562) takes only the attribute name
        m.__getattr__ = lambda k: _MM()
        sys.modules[name] = m

# Third-party model libraries
for _dep in [
    "transformers",
    "timm",
    "einops",
    "anthropic",
    "boto3",
    "botocore",
    "botocore.exceptions",
    "scipy",
    "scipy.io",
    "scipy.io.wavfile",
]:
    _stub(_dep)

# botocore.exceptions.ClientError must be a real exception class
import botocore.exceptions as _bce
if not isinstance(getattr(_bce, "ClientError", None), type):
    _bce.ClientError = type("ClientError", (Exception,), {
        "response": {"Error": {"Code": "Unknown"}}
    })

# boto3.client / boto3.resource must be callable
import boto3 as _b3
_b3.client   = _MM()
_b3.resource = _MM()


# ─────────────────────────────────────────────────────────────────────────────
#  Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_synthetic_video(path: str, num_frames: int = 10, fps: int = 5,
                           width: int = 64, height: int = 48) -> str:
    """
    Write a tiny synthetic MP4 using cv2.VideoWriter.
    Returns the path.
    """
    import cv2

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(path, fourcc, fps, (width, height))

    rng = np.random.default_rng(42)
    for _ in range(num_frames):
        frame_bgr = rng.integers(0, 256, (height, width, 3), dtype=np.uint8)
        writer.write(frame_bgr)

    writer.release()
    return path


def _make_dummy_usr(frame_id: int = 0, timestamp: float = 0.0):
    """Build a minimal UnifiedSceneRepresentation for mock FrameResults."""
    from fusion.unified_representation import UnifiedSceneRepresentation

    return UnifiedSceneRepresentation(
        frame_id=frame_id,
        timestamp=timestamp,
        vision_embedding=[0.0] * 768,
        depth_stats={"mean": 0.5, "std": 0.1},
        panoptic={"things": [{"label": "person", "coverage": 0.3}], "stuff": []},
        objects=[],
        scene_graph={"nodes": [], "edges": []},
        actions=[{"action": "walking", "confidence": 0.9}],
        audio={"transcription": "", "audio_events": []},
        spatial_relationships=[],
        context_tags=["outdoor"],
        scene_type="street",
        vlm_prompt="[dry-run prompt]",
    )


def _make_dummy_frame_result(frame_id: int = 0, timestamp: float = 0.0):
    """Build a minimal FrameResult for mock VideoResults."""
    from pipeline.frame_result import FrameResult
    from vlm.vlm_caption import VLMCaption

    usr = _make_dummy_usr(frame_id, timestamp)
    caption = VLMCaption(
        frame_id=frame_id,
        timestamp=timestamp,
        caption=f"[mock caption frame {frame_id}]",
        scene_type="street",
        context_tags=["outdoor"],
        model="dry-run",
        tokens_generated=5,
        processing_time=0.001,
        gpu_memory_used=None,
    )
    return FrameResult(
        frame_id=frame_id,
        timestamp=timestamp,
        usr=usr,
        caption=caption,
        step_times={"siglip": 0.01, "depth": 0.01, "panoptic": 0.01,
                    "scene_graph": 0.01, "slowfast": 0.01, "tracker": 0.01,
                    "fusion": 0.01, "vlm": 0.02},
        total_time=0.09,
        peak_vram_gb=None,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Test 1 — VideoProcessor: frame extraction from synthetic MP4
# ─────────────────────────────────────────────────────────────────────────────

def test_video_processor_synthetic():
    """
    Create a tiny synthetic MP4 with cv2.VideoWriter, run extract_frames,
    verify frame count and shapes.
    """
    print("\n" + "=" * 70)
    print("TEST 1: VideoProcessor — synthetic MP4 frame extraction")
    print("=" * 70)

    from pipeline.video_processor import VideoProcessor, FrameData

    num_frames = 10
    fps        = 5
    width      = 64
    height     = 48

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        video_path = tmp.name

    try:
        _make_synthetic_video(video_path, num_frames=num_frames, fps=fps,
                               width=width, height=height)

        # sample_fps=5 → step=1 → should get all 10 frames (capped at 120)
        vp = VideoProcessor(sample_fps=5.0)
        frames = vp.extract_frames(video_path)

        assert len(frames) > 0, "extract_frames returned no frames"
        # We wrote 10 frames at 5 fps sampling rate → expect 10 frames
        assert len(frames) == num_frames, (
            f"Expected {num_frames} frames, got {len(frames)}"
        )

        # Check every FrameData
        for i, fd in enumerate(frames):
            assert isinstance(fd, FrameData)
            assert fd.frame_id == i
            assert fd.timestamp >= 0.0
            assert isinstance(fd.frame, torch.Tensor)
            # Shape must be (H, W, 3)
            assert fd.frame.ndim == 3, f"Frame {i} has wrong ndim: {fd.frame.ndim}"
            assert fd.frame.shape[2] == 3, f"Frame {i} last dim != 3"
            assert fd.frame.dtype == torch.uint8, f"Frame {i} dtype != uint8"
            # Values in [0, 255]
            assert fd.frame.min() >= 0 and fd.frame.max() <= 255

        print(f"  Extracted {len(frames)} frames")
        print(f"  Frame shape : {frames[0].frame.shape}")
        print(f"  Timestamps  : {[round(f.timestamp, 3) for f in frames]}")

        # get_video_info
        info = vp.get_video_info(video_path)
        assert "duration" in info
        assert "fps" in info
        assert "width" in info
        assert "height" in info
        assert "frame_count" in info
        assert info["width"] == width
        assert info["height"] == height
        print(f"  Video info  : {info}")

        # Test MAX_FRAMES cap: use a low sample_fps so fewer frames, but verify cap works
        assert VideoProcessor.MAX_FRAMES == 120

        print("\nTEST 1 PASSED")
    finally:
        os.remove(video_path)

    return True


# ─────────────────────────────────────────────────────────────────────────────
#  Test 2 — VideoResult dataclass: to_dict / to_json / passes_target
# ─────────────────────────────────────────────────────────────────────────────

def test_video_result_dataclass():
    """
    Build a VideoResult from mock data, verify to_dict / to_json / passes_target.
    """
    print("\n" + "=" * 70)
    print("TEST 2: VideoResult — dataclass serialisation and target check")
    print("=" * 70)

    from narrative.narrative_result import NarrativeResult
    from narrative.temporal_assembly import TemporalAssembly
    from pipeline.video_result import VideoResult

    # Build 3 mock frame results
    frame_results = [_make_dummy_frame_result(i, float(i)) for i in range(3)]

    assembly = TemporalAssembly.from_frame_results(frame_results)

    narrative = NarrativeResult(
        narrative="[mock narrative] A person walks down a street.",
        video_duration=2.0,
        frame_count=3,
        model="dry-run",
        input_tokens=100,
        output_tokens=20,
        processing_time=0.5,
        metadata={"dry_run": True},
    )

    vr = VideoResult(
        video_path="/tmp/test.mp4",
        video_id="test123",
        duration=2.0,
        frame_count=3,
        frame_results=frame_results,
        temporal_assembly=assembly,
        narrative=narrative,
        total_processing_time=10.0,
        peak_vram_gb=None,
    )

    # passes_target
    assert vr.passes_target(300.0), "Should pass 5-minute target"
    assert not vr.passes_target(5.0), "Should fail 5-second target"

    # to_dict
    d = vr.to_dict()
    assert d["video_id"] == "test123"
    assert d["duration"] == 2.0
    assert d["frame_count"] == 3
    assert "narrative" in d
    assert "scene_types" in d
    assert "total_processing_time" in d
    assert "passes_5min_target" in d
    assert d["passes_5min_target"] is True
    # frame_results must NOT be in to_dict (too large)
    assert "frame_results" not in d
    print(f"  to_dict keys: {sorted(d.keys())}")

    # to_json
    json_str = vr.to_json()
    parsed = json.loads(json_str)
    assert parsed["video_id"] == "test123"
    assert isinstance(parsed["scene_types"], list)
    print(f"  to_json round-trips correctly")

    # summary
    summary_str = vr.summary()
    assert "test123" in summary_str
    assert "2.0" in summary_str  # duration
    print(f"  summary:\n{summary_str}")

    print("\nTEST 2 PASSED")
    return True


# ─────────────────────────────────────────────────────────────────────────────
#  Test 3 — VideoPipeline dry_run on synthetic video
# ─────────────────────────────────────────────────────────────────────────────

def test_video_pipeline_dry_run():
    """
    Run VideoPipeline(dry_run=True) on a synthetic video.
    Verify VideoResult is returned with correct structure.
    """
    print("\n" + "=" * 70)
    print("TEST 3: VideoPipeline — dry_run end-to-end on synthetic MP4")
    print("=" * 70)

    from pipeline.video_pipeline import VideoPipeline
    from pipeline.video_result import VideoResult

    num_frames = 5
    fps = 5  # 5 fps source, sample_fps=5 → all 5 frames extracted

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        video_path = tmp.name

    try:
        _make_synthetic_video(video_path, num_frames=num_frames, fps=fps,
                               width=64, height=48)

        pipeline = VideoPipeline(
            device="cpu",
            quantize_bits=8,
            sample_fps=5.0,
            skip_audio=True,   # skip audio for speed / no ffmpeg dep in test
            dry_run=True,
        )

        result = pipeline.process(video_path, video_id="dryrun_test")

        # Basic type checks
        assert isinstance(result, VideoResult)
        assert result.video_id == "dryrun_test"
        assert result.video_path == video_path
        assert result.frame_count > 0
        assert result.duration >= 0.0
        assert result.total_processing_time > 0.0

        # Narrative must be a non-empty string
        assert isinstance(result.narrative.narrative, str)
        assert len(result.narrative.narrative) > 0
        print(f"  Narrative : {result.narrative.narrative[:120]}")

        # to_dict / to_json must work
        d = result.to_dict()
        assert "narrative" in d
        assert d["video_id"] == "dryrun_test"
        json_str = result.to_json()
        parsed = json.loads(json_str)
        assert parsed["video_id"] == "dryrun_test"

        # TemporalAssembly populated
        assert result.temporal_assembly is not None
        assert result.temporal_assembly.frame_count == result.frame_count

        # passes_target uses wall-clock which should be small in dry-run
        assert result.passes_target(300.0), "Dry-run should easily finish in 5 min"

        print(f"  Frames processed : {result.frame_count}")
        print(f"  Processing time  : {result.total_processing_time:.3f}s")
        print(f"  Scenes detected  : {len(result.temporal_assembly.scenes)}")

        print("\nTEST 3 PASSED")
    finally:
        os.remove(video_path)

    return True


# ─────────────────────────────────────────────────────────────────────────────
#  Test 4 — worker/config.py: Settings loads from environment
# ─────────────────────────────────────────────────────────────────────────────

def test_worker_config():
    """
    Verify Settings loads from environment variables (with defaults).

    Settings uses class-level attributes populated from os.environ at import
    time, so we test the already-imported singleton for type correctness and
    verify that each attribute maps to the right env var by rebuilding a fresh
    Settings class in a controlled environment.
    """
    print("\n" + "=" * 70)
    print("TEST 4: worker/config.py — Settings loads from environment")
    print("=" * 70)

    # ── 1. Type-check the already-imported singleton ──────────────────
    from worker.config import settings as _settings, Settings

    assert isinstance(_settings.AWS_REGION, str) and len(_settings.AWS_REGION) > 0
    assert isinstance(_settings.DYNAMODB_TABLE_NAME, str)
    assert isinstance(_settings.TEMP_DIR, str)
    assert isinstance(_settings.SAMPLE_FPS, float)
    assert isinstance(_settings.QUANTIZE_BITS, int)
    assert isinstance(_settings.DEVICE, str)
    assert isinstance(_settings.S3_BUCKET_NAME, str)
    assert isinstance(_settings.SQS_QUEUE_URL, str)
    assert isinstance(_settings.AWS_ACCESS_KEY_ID, str)
    assert isinstance(_settings.AWS_SECRET_ACCESS_KEY, str)

    print(f"  AWS_REGION         : {_settings.AWS_REGION}")
    print(f"  DYNAMODB_TABLE_NAME: {_settings.DYNAMODB_TABLE_NAME}")
    print(f"  TEMP_DIR           : {_settings.TEMP_DIR}")
    print(f"  SAMPLE_FPS         : {_settings.SAMPLE_FPS}")
    print(f"  DEVICE             : {_settings.DEVICE}")
    print(f"  QUANTIZE_BITS      : {_settings.QUANTIZE_BITS}")

    # ── 2. Verify env-var mapping by patching os.environ and re-evaluating
    #       the class body via importlib in a fresh module namespace ──────
    import importlib.util as _ilu
    import types

    _config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "worker", "config.py",
    )

    # Inject known values into the environment
    _saved = {}
    _overrides = {
        "AWS_REGION": "eu-central-1",
        "DYNAMODB_TABLE_NAME": "my-test-table",
        "SAMPLE_FPS": "3.0",
        "QUANTIZE_BITS": "16",
        "DEVICE": "cpu",
        "TEMP_DIR": "/tmp/newworker_test",
    }
    for k, v in _overrides.items():
        _saved[k] = os.environ.get(k)
        os.environ[k] = v

    try:
        _spec = _ilu.spec_from_file_location("worker.config_fresh", _config_path)
        _fresh_mod = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_fresh_mod)
        s = _fresh_mod.Settings()

        assert s.AWS_REGION == "eu-central-1",          f"Got {s.AWS_REGION!r}"
        assert s.DYNAMODB_TABLE_NAME == "my-test-table", f"Got {s.DYNAMODB_TABLE_NAME!r}"
        assert s.SAMPLE_FPS == 3.0,                     f"Got {s.SAMPLE_FPS!r}"
        assert s.QUANTIZE_BITS == 16,                   f"Got {s.QUANTIZE_BITS!r}"
        assert s.DEVICE == "cpu",                       f"Got {s.DEVICE!r}"
        assert s.TEMP_DIR == "/tmp/newworker_test",     f"Got {s.TEMP_DIR!r}"
        print("  Fresh Settings with patched env: all assertions passed")

        # Default fallback: unset env var → default value
        del os.environ["TEMP_DIR"]
        _spec2 = _ilu.spec_from_file_location("worker.config_fresh2", _config_path)
        _fresh2 = _ilu.module_from_spec(_spec2)
        _spec2.loader.exec_module(_fresh2)
        s2 = _fresh2.Settings()
        assert s2.TEMP_DIR == "./temp", f"Expected './temp', got {s2.TEMP_DIR!r}"
        print("  Default TEMP_DIR = './temp' verified")

    finally:
        # Restore environment
        for k, old_val in _saved.items():
            if old_val is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = old_val

    print("\nTEST 4 PASSED")
    return True


# ─────────────────────────────────────────────────────────────────────────────
#  Test 5 — SQSHandler.parse_s3_event
# ─────────────────────────────────────────────────────────────────────────────

def test_sqs_parse_s3_event():
    """Test SQSHandler.parse_s3_event with a sample S3 event JSON."""
    print("\n" + "=" * 70)
    print("TEST 5: SQSHandler.parse_s3_event")
    print("=" * 70)

    # boto3 and botocore are stubbed at module load time (top of this file),
    # so the normal import path works fine here.
    from worker.sqs_handler import SQSHandler

    # Typical S3-PUT event message body (as sent by AWS)
    sample_event = json.dumps({
        "Records": [
            {
                "eventName": "ObjectCreated:Put",
                "s3": {
                    "bucket": {"name": "my-video-bucket"},
                    "object": {
                        "key": "uploads/user42/video_abc123.mp4",
                        "size": 5242880,
                    },
                },
            }
        ]
    })

    # SQSHandler constructor calls boto3; we need to avoid that.
    # Instantiate without __init__ using object.__new__ and set the attribute manually.
    handler = object.__new__(SQSHandler)
    handler.queue_url = "https://sqs.us-east-2.amazonaws.com/123456789/test-queue"

    event = handler.parse_s3_event(sample_event)

    assert event is not None, "parse_s3_event returned None for valid event"
    assert event["bucket"] == "my-video-bucket"
    assert event["s3_key"] == "uploads/user42/video_abc123.mp4"
    assert event["size"] == 5242880
    assert event["event_name"] == "ObjectCreated:Put"

    print(f"  Parsed event: {event}")

    # Non-S3-event body → should return None
    bad_body = json.dumps({"hello": "world"})
    result = handler.parse_s3_event(bad_body)
    assert result is None, "Expected None for non-S3-event body"
    print("  Non-S3-event body correctly returns None")

    # Malformed JSON → should return None
    result2 = handler.parse_s3_event("not valid json {{{{")
    assert result2 is None, "Expected None for malformed JSON"
    print("  Malformed JSON correctly returns None")

    print("\nTEST 5 PASSED")
    return True


# ─────────────────────────────────────────────────────────────────────────────
#  Runner
# ─────────────────────────────────────────────────────────────────────────────

def run_all_tests():
    print("\n" + "=" * 70)
    print("PHASE 6: VIDEO PIPELINE TESTS")
    print("=" * 70)

    tests = [
        ("VideoProcessor synthetic frames",   test_video_processor_synthetic),
        ("VideoResult dataclass",             test_video_result_dataclass),
        ("VideoPipeline dry_run",             test_video_pipeline_dry_run),
        ("worker/config Settings",            test_worker_config),
        ("SQSHandler parse_s3_event",         test_sqs_parse_s3_event),
    ]

    results = []
    for name, fn in tests:
        try:
            ok = fn()
            results.append((name, ok))
        except Exception as e:
            import traceback
            print(f"\nFAIL: {name}: {e}")
            traceback.print_exc()
            results.append((name, False))

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for name, ok in results:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}")

    failures = [n for n, ok in results if ok is False]
    if not failures:
        print("\nALL PHASE 6 TESTS PASSED")
    else:
        print(f"\n{len(failures)} test(s) failed: {failures}")

    return len(failures) == 0


if __name__ == "__main__":
    ok = run_all_tests()
    sys.exit(0 if ok else 1)
