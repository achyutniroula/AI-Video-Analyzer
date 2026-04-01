"""
Phase 4 Test Suite — Full pipeline processes 1 frame in <5s

Tiers:
  CPU / dry-run tests : always run — test structure, timing, serialisation
  GPU / real tests    : skipped unless CUDA available or --gpu flag passed

Run with:
  python tests/test_pipeline.py           # CPU tests only
  python tests/test_pipeline.py --gpu     # include real model test
"""

import sys
import os
import json
import time
import argparse
import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from optimization import TimingProfiler
from pipeline import FramePipeline, FrameResult


# ─────────────────────────────────────────────────────────────────────────────
#  Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def _frame(h: int = 360, w: int = 640) -> torch.Tensor:
    return torch.randint(0, 256, (h, w, 3), dtype=torch.uint8)


def _audio(duration_s: float = 0.2, sr: int = 16_000) -> np.ndarray:
    return np.random.randn(int(duration_s * sr)).astype(np.float32) * 0.1


# ─────────────────────────────────────────────────────────────────────────────
#  CPU / dry-run tests (always run)
# ─────────────────────────────────────────────────────────────────────────────

def test_profiler():
    """TimingProfiler records steps and computes total correctly."""
    print("\n" + "=" * 70)
    print("TEST 1: TimingProfiler")
    print("=" * 70)

    prof = TimingProfiler()

    with prof.step("alpha"):
        time.sleep(0.05)

    with prof.step("beta"):
        time.sleep(0.03)

    prof.record("gamma", 0.01)

    assert abs(prof.get("alpha") - 0.05) < 0.02
    assert abs(prof.get("beta")  - 0.03) < 0.02
    assert abs(prof.get("gamma") - 0.01) < 0.005

    total = prof.total()
    assert abs(total - 0.09) < 0.03

    assert prof.passes_target(target_s=1.0)
    assert not prof.passes_target(target_s=0.01)

    d = prof.to_dict()
    assert list(d.keys()) == ["alpha", "beta", "gamma"]

    print(prof.summary(frame_id=0, timestamp=0.0, target_s=1.0))
    print("\n✅ TEST 1 PASSED")
    return True


def test_frame_result_dataclass():
    """FrameResult validates, serialises, and checks target correctly."""
    print("\n" + "=" * 70)
    print("TEST 2: FrameResult dataclass")
    print("=" * 70)

    # Build the minimum required objects
    pipeline = FramePipeline(dry_run=True)
    with pipeline:
        result = pipeline.process_frame(_frame(), frame_id=0, timestamp=0.0)

    assert isinstance(result, FrameResult)
    assert result.frame_id == 0
    assert result.timestamp == 0.0
    assert isinstance(result.step_times, dict)
    assert result.total_time >= 0.0
    assert result.caption is not None
    assert result.usr is not None

    # Serialisation
    d = result.to_dict()
    assert "caption" in d
    assert "step_times" in d
    assert "total_time" in d
    assert "passes_5s_target" in d

    json_str = result.to_json()
    parsed = json.loads(json_str)
    assert parsed["frame_id"] == 0

    print(f"\n  {result}")
    print(f"\n  Timing line: {result.format_timings()}")
    print("\n✅ TEST 2 PASSED")
    return True


def test_dry_run_pipeline_single_frame():
    """Dry-run pipeline produces correct FrameResult with all steps timed."""
    print("\n" + "=" * 70)
    print("TEST 3: Dry-run pipeline — single frame, all steps present")
    print("=" * 70)

    pipeline = FramePipeline(dry_run=True)

    with pipeline:
        result = pipeline.process_frame(
            _frame(), frame_id=2, timestamp=1.0
        )

    expected_steps = {"siglip", "depth", "panoptic", "scene_graph",
                      "slowfast", "tracker", "fusion", "vlm"}
    assert expected_steps.issubset(set(result.step_times.keys())), \
        f"Missing steps: {expected_steps - set(result.step_times.keys())}"

    # All steps must have non-negative time
    for name, t in result.step_times.items():
        assert t >= 0.0, f"Step {name!r} has negative time {t}"

    assert result.total_time == sum(result.step_times.values())

    print(f"\n  Steps: {list(result.step_times.keys())}")
    print(f"  Total: {result.total_time:.4f}s")
    print("\n✅ TEST 3 PASSED")
    return True


def test_dry_run_pipeline_with_audio():
    """Dry-run pipeline includes 'audio' step when audio waveform is provided."""
    print("\n" + "=" * 70)
    print("TEST 4: Dry-run pipeline — audio step included")
    print("=" * 70)

    pipeline = FramePipeline(dry_run=True)

    with pipeline:
        result_no_audio = pipeline.process_frame(_frame(), frame_id=0, timestamp=0.0)
        result_audio    = pipeline.process_frame(_frame(), frame_id=1, timestamp=0.5,
                                                 audio=_audio())

    assert "audio" not in result_no_audio.step_times, "audio step should be absent"
    assert "audio" in result_audio.step_times,        "audio step should be present"

    print(f"  Without audio: {sorted(result_no_audio.step_times.keys())}")
    print(f"  With audio:    {sorted(result_audio.step_times.keys())}")
    print("\n✅ TEST 4 PASSED")
    return True


def test_dry_run_multiple_frames():
    """Dry-run: process 5 frames sequentially, verify tracker increments."""
    print("\n" + "=" * 70)
    print("TEST 5: Dry-run pipeline — 5 frames, context manager")
    print("=" * 70)

    results = []
    with FramePipeline(dry_run=True) as pipeline:
        for i in range(5):
            result = pipeline.process_frame(_frame(), frame_id=i, timestamp=i * 0.2)
            results.append(result)

    assert len(results) == 5
    for i, r in enumerate(results):
        assert r.frame_id == i
        assert abs(r.timestamp - i * 0.2) < 1e-9

    total_times = [r.total_time for r in results]
    print(f"  Total times: {[f'{t:.4f}s' for t in total_times]}")
    print("\n✅ TEST 5 PASSED")
    return True


def test_pipeline_error_before_setup():
    """Calling process_frame before setup() raises RuntimeError."""
    print("\n" + "=" * 70)
    print("TEST 6: Error handling — process_frame before setup()")
    print("=" * 70)

    pipeline = FramePipeline(dry_run=True)
    try:
        pipeline.process_frame(_frame(), frame_id=0, timestamp=0.0)
        assert False, "Expected RuntimeError"
    except RuntimeError as e:
        assert "setup" in str(e).lower()
        print(f"  Caught expected error: {e}")

    print("\n✅ TEST 6 PASSED")
    return True


def test_profiler_summary_format():
    """TimingProfiler summary contains all keys and PASS/FAIL label."""
    print("\n" + "=" * 70)
    print("TEST 7: Profiler summary format")
    print("=" * 70)

    prof = TimingProfiler()
    for name, t in [("siglip", 0.11), ("depth", 0.16), ("panoptic", 0.31),
                    ("vlm", 1.86)]:
        prof.record(name, t)

    summary_pass = prof.summary(frame_id=0, timestamp=0.0, target_s=5.0)
    summary_fail = prof.summary(frame_id=0, timestamp=0.0, target_s=1.0)

    assert "PASS" in summary_pass
    assert "FAIL" in summary_fail
    assert "siglip" in summary_pass
    assert "TOTAL" in summary_pass

    print(summary_pass)
    print("\n✅ TEST 7 PASSED")
    return True


# ─────────────────────────────────────────────────────────────────────────────
#  GPU / real model test (skipped without CUDA)
# ─────────────────────────────────────────────────────────────────────────────

def test_real_pipeline_timing(force: bool = False):
    """
    Run the real pipeline end-to-end on a synthetic frame and verify <5s.

    Requirements:
      - CUDA GPU with ≥ 12 GB VRAM
      - All model weights downloaded (may take several minutes on first run)
    """
    print("\n" + "=" * 70)
    print("TEST 8: Real pipeline — <5s end-to-end on GPU")
    print("=" * 70)

    if not torch.cuda.is_available() and not force:
        print("  ⚠️  CUDA not available — skipping")
        print("     Run with --gpu to force this test")
        return None

    vram_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
    print(f"  GPU: {torch.cuda.get_device_name(0)}  ({vram_gb:.0f} GB VRAM)")

    if vram_gb < 12 and not force:
        print(f"  ⚠️  Only {vram_gb:.0f} GB — skipping (need ≥12 GB)")
        return None

    frame = _frame()

    # --- First frame (models cold — excluded from target) ----------------
    print("\n  Pass 1/2 — cold models (may be slow, not counted toward target):")
    with FramePipeline(device="cuda", quantize_bits=8,
                       max_vlm_tokens=128, skip_audio=True) as pipeline:
        result_cold = pipeline.process_frame(frame, frame_id=0, timestamp=0.0)

    print(result_cold.format_timings())

    # --- Second frame (warm — must meet <5s target) ----------------------
    print("\n  Pass 2/2 — warm models (must be <5s):")
    with FramePipeline(device="cuda", quantize_bits=8,
                       max_vlm_tokens=128, skip_audio=True) as pipeline:
        result_warm = pipeline.process_frame(frame, frame_id=1, timestamp=0.04)

    from optimization.profiler import TimingProfiler as _TP
    prof = _TP()
    for k, v in result_warm.step_times.items():
        prof.record(k, v)
    print(prof.summary(frame_id=1, timestamp=0.04, target_s=5.0))

    print(f"\n  Caption: {result_warm.caption.caption[:120]}")
    print(f"  Peak VRAM: {result_warm.peak_vram_gb} GB")

    assert result_warm.passes_target(5.0), (
        f"Pipeline too slow: {result_warm.total_time:.2f}s > 5.0s\n"
        f"Step breakdown: {result_warm.step_times}"
    )
    assert result_warm.caption.validate() == []

    print(f"\n  Total: {result_warm.total_time:.2f}s ✅  (target: 5.0s)")
    print("\n✅ TEST 8 PASSED")
    return True


# ─────────────────────────────────────────────────────────────────────────────
#  Runner
# ─────────────────────────────────────────────────────────────────────────────

def run_all_tests(run_gpu: bool = False):
    print("\n" + "=" * 70)
    print("PHASE 4: FULL PIPELINE TESTS")
    print("=" * 70)

    tests = [
        ("TimingProfiler",                  test_profiler),
        ("FrameResult dataclass",           test_frame_result_dataclass),
        ("Dry-run single frame",            test_dry_run_pipeline_single_frame),
        ("Dry-run with audio",              test_dry_run_pipeline_with_audio),
        ("Dry-run 5 frames",                test_dry_run_multiple_frames),
        ("Error before setup",              test_pipeline_error_before_setup),
        ("Profiler summary format",         test_profiler_summary_format),
        ("Real pipeline <5s (GPU)",         lambda: test_real_pipeline_timing(force=run_gpu)),
    ]

    results = []
    for name, fn in tests:
        try:
            ok = fn()
            results.append((name, ok))
        except Exception as e:
            import traceback
            print(f"\n❌ {name} FAILED: {e}")
            traceback.print_exc()
            results.append((name, False))

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for name, ok in results:
        if ok is None:
            print(f"⏭️  SKIP: {name}")
        else:
            print(f"{'✅ PASS' if ok else '❌ FAIL'}: {name}")

    failures = [n for n, ok in results if ok is False]
    if not failures:
        print("\n🎉 ALL PHASE 4 TESTS PASSED — Pipeline orchestration is working.")
    else:
        print(f"\n⚠️  {len(failures)} test(s) failed.")
    return len(failures) == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--gpu", action="store_true",
                        help="Run real GPU test (requires all model weights)")
    args = parser.parse_args()
    ok = run_all_tests(run_gpu=args.gpu)
    sys.exit(0 if ok else 1)
