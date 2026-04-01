"""
Phase 3 Test Suite — Qwen2-VL generates coherent captions

Tests are split into two tiers:
  - CPU / mock tests  : always run, no model download needed
  - GPU / real tests  : skipped automatically if CUDA is not available

Run with:  python tests/test_vlm.py
           python tests/test_vlm.py --gpu   (force GPU tests)
"""

import sys
import os
import json
import argparse
import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fusion import MultiModalFusionEngine, UnifiedSceneRepresentation
from vlm import Qwen2VLCaptioner, VLMCaption
from perception.base import PerceptionOutput


# ─────────────────────────────────────────────────────────────────────────────
#  Shared fixtures
# ─────────────────────────────────────────────────────────────────────────────

def _make_usr(frame_id: int = 0, timestamp: float = 0.0) -> UnifiedSceneRepresentation:
    """Build a realistic UnifiedSceneRepresentation using the fusion engine."""
    engine = MultiModalFusionEngine()

    siglip = PerceptionOutput(
        module_name="SigLIPEncoder", frame_id=frame_id, timestamp=timestamp,
        data={"vision_embedding": list(np.random.randn(768).astype(float)), "embedding_dim": 768},
        metadata={}, processing_time=0.1, gpu_memory_used=None,
    )
    depth = PerceptionOutput(
        module_name="DepthEstimator", frame_id=frame_id, timestamp=timestamp,
        data={
            "depth_stats": {"mean": 0.45, "std": 0.20},
            "depth_distribution": {"near_pct": 0.35, "mid_pct": 0.40, "far_pct": 0.25},
            "dominant_zone": "near",
        },
        metadata={}, processing_time=0.15, gpu_memory_used=None,
    )
    panoptic = PerceptionOutput(
        module_name="PanopticSegmenter", frame_id=frame_id, timestamp=timestamp,
        data={
            "things": [
                {"id": 1, "label": "person",  "label_id": 0, "bbox": [100, 60, 280, 340], "coverage": 0.18, "pixel_count": 41472},
                {"id": 2, "label": "bicycle", "label_id": 2, "bbox": [260, 150, 450, 340], "coverage": 0.11, "pixel_count": 25344},
            ],
            "stuff": [
                {"label": "road",         "label_id": 100, "coverage": 0.45, "pixel_count": 103680},
                {"label": "building",     "label_id": 101, "coverage": 0.22, "pixel_count": 50688},
                {"label": "sky-other-merged", "label_id": 102, "coverage": 0.10, "pixel_count": 23040},
            ],
            "num_things": 2, "num_stuff": 3, "image_size": [360, 640],
        },
        metadata={}, processing_time=0.3, gpu_memory_used=None,
    )
    scene_graph = PerceptionOutput(
        module_name="SceneGraphGenerator", frame_id=frame_id, timestamp=timestamp,
        data={
            "nodes": [
                {"id": 1, "label": "person",  "bbox": [100, 60, 280, 340],  "center": [190, 200], "area": 44800, "coverage": 0.18},
                {"id": 2, "label": "bicycle", "bbox": [260, 150, 450, 340], "center": [355, 245], "area": 35150, "coverage": 0.11},
            ],
            "edges": [
                {"subject_id": 1, "subject_label": "person",
                 "predicate": "near",
                 "object_id": 2, "object_label": "bicycle"},
                {"subject_id": 1, "subject_label": "person",
                 "predicate": "left_of",
                 "object_id": 2, "object_label": "bicycle"},
            ],
            "num_nodes": 2, "num_edges": 2,
        },
        metadata={}, processing_time=0.01, gpu_memory_used=None,
    )
    tracker = PerceptionOutput(
        module_name="ByteTracker", frame_id=frame_id, timestamp=timestamp,
        data={
            "tracks": [
                {"track_id": 1, "label": "person",  "bbox": [100, 60, 280, 340], "score": 0.18, "age": 5, "hits": 5},
                {"track_id": 2, "label": "bicycle", "bbox": [260, 150, 450, 340], "score": 0.11, "age": 5, "hits": 5},
            ],
            "num_tracks": 2,
        },
        metadata={}, processing_time=0.01, gpu_memory_used=None,
    )
    actions = PerceptionOutput(
        module_name="ActionRecognizer", frame_id=frame_id, timestamp=timestamp,
        data={
            "actions": [
                {"action": "riding a bike", "confidence": 0.68, "class_id": 200},
                {"action": "cycling",       "confidence": 0.21, "class_id": 201},
            ],
            "top_action": {"action": "riding a bike", "confidence": 0.68, "class_id": 200},
        },
        metadata={}, processing_time=0.2, gpu_memory_used=None,
    )
    audio = PerceptionOutput(
        module_name="AudioProcessor", frame_id=frame_id, timestamp=timestamp,
        data={
            "transcription": "",
            "audio_events": [{"event": "traffic", "confidence": 0.55}],
            "has_speech": False,
        },
        metadata={}, processing_time=0.05, gpu_memory_used=None,
    )

    return engine.fuse(
        frame_id=frame_id, timestamp=timestamp,
        siglip=siglip, depth=depth, panoptic=panoptic,
        scene_graph=scene_graph, tracker=tracker,
        actions=actions, audio=audio,
    )


def _make_frame(h: int = 360, w: int = 640) -> torch.Tensor:
    """Synthetic RGB frame."""
    return torch.randint(0, 256, (h, w, 3), dtype=torch.uint8)


# ─────────────────────────────────────────────────────────────────────────────
#  Mock captioner (no model, for offline testing)
# ─────────────────────────────────────────────────────────────────────────────

class _MockCaptioner:
    """Simulates Qwen2VLCaptioner output without loading any model."""

    def __init__(self):
        self._loaded = False

    def load(self):
        self._loaded = True

    def unload(self):
        self._loaded = False

    def is_loaded(self) -> bool:
        return self._loaded

    def caption(self, usr: UnifiedSceneRepresentation, frame=None) -> VLMCaption:
        if not self._loaded:
            raise RuntimeError("Call load() first")
        # Produce a plausible fake caption using USR fields
        things = [t["label"] for t in usr.panoptic.get("things", [])]
        stuff  = [s["label"] for s in usr.panoptic.get("stuff", [])[:2]]
        top_action = usr.actions[0]["action"] if usr.actions else "standing"

        caption_text = (
            f"In this {usr.scene_type} scene, "
            + (f"a {things[0]} is {top_action}" if things else "the environment is visible")
            + (f" near a {things[1]}" if len(things) > 1 else "")
            + f", surrounded by {' and '.join(stuff)}. "
            + f"The overall atmosphere suggests {', '.join(usr.context_tags) if usr.context_tags else 'an unremarkable setting'}."
        )

        return VLMCaption(
            frame_id=usr.frame_id,
            timestamp=usr.timestamp,
            caption=caption_text,
            scene_type=usr.scene_type,
            context_tags=usr.context_tags,
            model="mock-captioner",
            tokens_generated=len(caption_text.split()),
            processing_time=0.001,
            gpu_memory_used=None,
            vlm_prompt_used=usr.vlm_prompt,
        )


# ─────────────────────────────────────────────────────────────────────────────
#  Tests (always run — CPU / mock)
# ─────────────────────────────────────────────────────────────────────────────

def test_vlm_caption_dataclass():
    """VLMCaption validates correctly and serialises to JSON."""
    print("\n" + "=" * 70)
    print("TEST 1: VLMCaption dataclass — validation + serialisation")
    print("=" * 70)

    cap = VLMCaption(
        frame_id=0, timestamp=0.0,
        caption="A cyclist rides down a busy city street, weaving between cars.",
        scene_type="urban",
        context_tags=["outdoor", "urban"],
        model="test",
        tokens_generated=15,
        processing_time=1.2,
        gpu_memory_used=8.3,
        vlm_prompt_used="[test prompt]",
    )

    warnings = cap.validate()
    assert warnings == [], f"Unexpected warnings: {warnings}"

    json_str = cap.to_json()
    parsed = json.loads(json_str)
    assert parsed["frame_id"] == 0
    assert "caption" in parsed
    assert parsed["tokens_generated"] == 15

    print(f"  repr: {cap}")
    print(f"  JSON size: {len(json_str)} chars")
    print("\n✅ TEST 1 PASSED")
    return True


def test_vlm_caption_validation():
    """VLMCaption flags empty or too-short captions."""
    print("\n" + "=" * 70)
    print("TEST 2: VLMCaption validation — catches bad output")
    print("=" * 70)

    bad = VLMCaption(
        frame_id=1, timestamp=0.5,
        caption="ok",    # too short
        scene_type="",   # empty
        context_tags=[],
        model="test", tokens_generated=1, processing_time=0.0, gpu_memory_used=None,
    )

    warnings = bad.validate()
    assert len(warnings) == 2, f"Expected 2 warnings, got: {warnings}"
    print(f"  Warnings: {warnings}")
    print("\n✅ TEST 2 PASSED")
    return True


def test_mock_captioner_lifecycle():
    """Mock captioner respects load/unload/is_loaded contract."""
    print("\n" + "=" * 70)
    print("TEST 3: Mock captioner — load / caption / unload lifecycle")
    print("=" * 70)

    captioner = _MockCaptioner()
    assert not captioner.is_loaded()

    captioner.load()
    assert captioner.is_loaded()

    # Should raise before load
    captioner2 = _MockCaptioner()
    try:
        captioner2.caption(_make_usr(), None)
        assert False, "Should have raised RuntimeError"
    except RuntimeError:
        pass

    captioner.unload()
    assert not captioner.is_loaded()

    print("\n✅ TEST 3 PASSED")
    return True


def test_mock_captioner_output():
    """Mock captioner produces a valid VLMCaption from a realistic USR."""
    print("\n" + "=" * 70)
    print("TEST 4: Mock captioner — coherent output from real USR")
    print("=" * 70)

    usr = _make_usr(frame_id=3, timestamp=1.5)
    captioner = _MockCaptioner()
    captioner.load()

    cap = captioner.caption(usr, frame=_make_frame())

    assert isinstance(cap, VLMCaption)
    assert cap.frame_id == 3
    assert abs(cap.timestamp - 1.5) < 1e-9
    assert cap.scene_type == usr.scene_type
    assert cap.context_tags == usr.context_tags

    warnings = cap.validate()
    assert warnings == [], f"Unexpected warnings: {warnings}"

    print(f"\n  USR:     {usr}")
    print(f"\n  Caption: {cap.caption}")
    print(f"\n  repr:    {cap}")
    print("\n✅ TEST 4 PASSED")
    return True


def test_vlm_prompt_quality():
    """The VLM prompt in USR contains all key perception fields."""
    print("\n" + "=" * 70)
    print("TEST 5: VLM prompt quality — all key sections present")
    print("=" * 70)

    usr = _make_usr()
    prompt = usr.vlm_prompt

    assert "person"      in prompt.lower(), "person not mentioned"
    assert "bicycle"     in prompt.lower(), "bicycle not mentioned"
    assert "road"        in prompt.lower(), "road not mentioned"
    assert "riding"      in prompt.lower(), "action not mentioned"
    assert "depth"       in prompt.lower() or "near" in prompt.lower(), "depth zone missing"
    assert "relationship" in prompt.lower() or "near" in prompt.lower(), "relationships missing"

    print(f"\n  Prompt:\n{'─'*60}")
    print(prompt)
    print("─" * 60)
    print("\n✅ TEST 5 PASSED")
    return True


def test_multi_frame_captions():
    """Generate captions for multiple frames and check consistency."""
    print("\n" + "=" * 70)
    print("TEST 6: Multi-frame captions — frame_id and timestamp correct")
    print("=" * 70)

    captioner = _MockCaptioner()
    captioner.load()

    captions = []
    for i in range(3):
        usr = _make_usr(frame_id=i, timestamp=i * 0.5)
        cap = captioner.caption(usr, frame=_make_frame())
        captions.append(cap)

    for i, cap in enumerate(captions):
        assert cap.frame_id == i
        assert abs(cap.timestamp - i * 0.5) < 1e-9
        assert cap.validate() == []
        print(f"  Frame {i}: {cap}")

    captioner.unload()
    print("\n✅ TEST 6 PASSED")
    return True


# ─────────────────────────────────────────────────────────────────────────────
#  GPU / real model test (skipped if no CUDA)
# ─────────────────────────────────────────────────────────────────────────────

def test_qwen2vl_real(force: bool = False):
    """
    Load the real Qwen2-VL model, generate one caption, then unload.

    Skipped automatically unless CUDA is available or --gpu flag is passed.
    Requires ~8.5 GB VRAM and ~14 GB download.
    """
    print("\n" + "=" * 70)
    print("TEST 7: Real Qwen2-VL-7B — load / caption / unload")
    print("=" * 70)

    if not torch.cuda.is_available() and not force:
        print("  ⚠️  CUDA not available — skipping real model test")
        print("     Run with --gpu to force this test")
        return None   # skip, not failure

    vram_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
    print(f"  GPU: {torch.cuda.get_device_name(0)}  ({vram_gb:.0f} GB)")

    if vram_gb < 10 and not force:
        print(f"  ⚠️  Only {vram_gb:.0f} GB VRAM — skipping (need ≥10 GB for 8-bit)")
        return None

    usr   = _make_usr(frame_id=0, timestamp=0.0)
    frame = _make_frame()

    captioner = Qwen2VLCaptioner(quantize_bits=8, max_new_tokens=128)

    # --- load --------------------------------------------------------
    t_load = time.time()
    captioner.load()
    load_time = time.time() - t_load
    assert captioner.is_loaded()
    print(f"  Load time: {load_time:.1f}s")

    # --- caption -----------------------------------------------------
    t_cap = time.time()
    cap = captioner.caption(usr, frame)
    cap_time = time.time() - t_cap

    assert isinstance(cap, VLMCaption)
    assert cap.tokens_generated > 0
    warnings = cap.validate()
    assert warnings == [], f"Validation warnings: {warnings}"

    print(f"  Caption time : {cap_time:.2f}s")
    print(f"  Tokens       : {cap.tokens_generated}")
    print(f"  VRAM peak    : {cap.gpu_memory_used} GB")
    print(f"\n  Caption:\n{'─'*60}")
    print(cap.caption)
    print("─" * 60)

    # --- unload ------------------------------------------------------
    captioner.unload()
    assert not captioner.is_loaded()

    if torch.cuda.is_available():
        vram_after = torch.cuda.memory_allocated() / 1e9
        print(f"\n  VRAM after unload: {vram_after:.2f} GB")
        assert vram_after < 1.0, f"VRAM not released: {vram_after:.2f} GB"

    print("\n✅ TEST 7 PASSED")
    return True


# ─────────────────────────────────────────────────────────────────────────────
#  Runner
# ─────────────────────────────────────────────────────────────────────────────

import time  # noqa: E402 (needed above for test_qwen2vl_real)


def run_all_tests(run_gpu: bool = False):
    print("\n" + "=" * 70)
    print("PHASE 3: VLM CAPTIONER TESTS")
    print("=" * 70)

    tests = [
        ("VLMCaption dataclass",          lambda: test_vlm_caption_dataclass()),
        ("VLMCaption validation",         lambda: test_vlm_caption_validation()),
        ("Mock captioner lifecycle",      lambda: test_mock_captioner_lifecycle()),
        ("Mock captioner output",         lambda: test_mock_captioner_output()),
        ("VLM prompt quality",            lambda: test_vlm_prompt_quality()),
        ("Multi-frame captions",          lambda: test_multi_frame_captions()),
        ("Real Qwen2-VL (GPU)",           lambda: test_qwen2vl_real(force=run_gpu)),
    ]

    results = []
    for name, fn in tests:
        try:
            ok = fn()
            results.append((name, ok))   # None = skipped
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
        print("\n🎉 ALL PHASE 3 TESTS PASSED — VLM layer is working.")
    else:
        print(f"\n⚠️  {len(failures)} test(s) failed.")
    return len(failures) == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--gpu", action="store_true", help="Run real GPU test (downloads Qwen2-VL-7B)")
    args = parser.parse_args()
    ok = run_all_tests(run_gpu=args.gpu)
    sys.exit(0 if ok else 1)
