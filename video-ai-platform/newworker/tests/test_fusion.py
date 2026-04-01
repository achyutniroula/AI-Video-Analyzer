"""
Phase 2 Test Suite — Fusion produces valid UnifiedSceneRepresentation

Tests the fusion engine in isolation using *mock* PerceptionOutput objects
so the test runs on any machine without downloading large models.

Run with:  python tests/test_fusion.py
"""

import sys
import os
import json
import torch
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from perception.base import PerceptionOutput
from fusion import MultiModalFusionEngine, UnifiedSceneRepresentation


# ─────────────────────────────────────────────────────────────────────────────
#  Mock PerceptionOutput factories
# ─────────────────────────────────────────────────────────────────────────────

def _make_siglip_output(frame_id=0, timestamp=0.0) -> PerceptionOutput:
    return PerceptionOutput(
        module_name="SigLIPEncoder",
        frame_id=frame_id,
        timestamp=timestamp,
        data={
            "vision_embedding": list(np.random.randn(768).astype(float)),
            "embedding_dim": 768,
            "model": "google/siglip-base-patch16-224",
            "norm": 1.0,
        },
        metadata={"device": "cpu", "quantized": False},
        processing_time=0.1,
        gpu_memory_used=None,
    )


def _make_depth_output(frame_id=0, timestamp=0.0) -> PerceptionOutput:
    return PerceptionOutput(
        module_name="DepthEstimator",
        frame_id=frame_id,
        timestamp=timestamp,
        data={
            "depth_stats": {
                "mean": 0.52, "std": 0.18, "min": 0.01, "max": 0.99,
                "near_p10": 0.15, "far_p90": 0.85,
            },
            "depth_distribution": {"near_pct": 0.30, "mid_pct": 0.45, "far_pct": 0.25},
            "dominant_zone": "mid",
            "model": "depth-anything/Depth-Anything-V2-Small-hf",
        },
        metadata={"device": "cpu", "quantized": False},
        processing_time=0.15,
        gpu_memory_used=None,
    )


def _make_panoptic_output(frame_id=0, timestamp=0.0) -> PerceptionOutput:
    return PerceptionOutput(
        module_name="PanopticSegmenter",
        frame_id=frame_id,
        timestamp=timestamp,
        data={
            "things": [
                {"id": 1, "label": "person",    "label_id": 0, "bbox": [50, 80, 200, 340], "coverage": 0.12, "pixel_count": 27648},
                {"id": 2, "label": "backpack",  "label_id": 1, "bbox": [60, 200, 150, 340], "coverage": 0.04, "pixel_count": 9216},
            ],
            "stuff": [
                {"label": "tree-merged",  "label_id": 100, "coverage": 0.62, "pixel_count": 143360},
                {"label": "grass-merged", "label_id": 101, "coverage": 0.18, "pixel_count": 41472},
                {"label": "sky-other-merged", "label_id": 102, "coverage": 0.04, "pixel_count": 9216},
            ],
            "num_things": 2,
            "num_stuff": 3,
            "image_size": [360, 640],
        },
        metadata={"device": "cpu", "quantized": False},
        processing_time=0.3,
        gpu_memory_used=None,
    )


def _make_scene_graph_output(frame_id=0, timestamp=0.0) -> PerceptionOutput:
    return PerceptionOutput(
        module_name="SceneGraphGenerator",
        frame_id=frame_id,
        timestamp=timestamp,
        data={
            "nodes": [
                {"id": 1, "label": "person",   "bbox": [50, 80, 200, 340], "center": [125, 210], "area": 38400, "coverage": 0.12},
                {"id": 2, "label": "backpack", "bbox": [60, 200, 150, 340], "center": [105, 270], "area": 12600, "coverage": 0.04},
            ],
            "edges": [
                {"subject_id": 1, "subject_label": "person",
                 "predicate": "larger_than",
                 "object_id": 2, "object_label": "backpack"},
                {"subject_id": 1, "subject_label": "person",
                 "predicate": "near",
                 "object_id": 2, "object_label": "backpack"},
            ],
            "num_nodes": 2,
            "num_edges": 2,
        },
        metadata={"device": "cpu", "quantized": False},
        processing_time=0.01,
        gpu_memory_used=None,
    )


def _make_tracker_output(frame_id=0, timestamp=0.0) -> PerceptionOutput:
    return PerceptionOutput(
        module_name="ByteTracker",
        frame_id=frame_id,
        timestamp=timestamp,
        data={
            "tracks": [
                {"track_id": 1, "label": "person",   "bbox": [50, 80, 200, 340], "score": 0.12, "age": 3, "hits": 3},
                {"track_id": 2, "label": "backpack", "bbox": [60, 200, 150, 340], "score": 0.04, "age": 3, "hits": 3},
            ],
            "num_tracks": 2,
        },
        metadata={"device": "cpu", "quantized": False},
        processing_time=0.01,
        gpu_memory_used=None,
    )


def _make_action_output(frame_id=0, timestamp=0.0) -> PerceptionOutput:
    return PerceptionOutput(
        module_name="ActionRecognizer",
        frame_id=frame_id,
        timestamp=timestamp,
        data={
            "actions": [
                {"action": "hiking", "confidence": 0.72, "class_id": 10},
                {"action": "walking", "confidence": 0.15, "class_id": 20},
            ],
            "top_action": {"action": "hiking", "confidence": 0.72, "class_id": 10},
        },
        metadata={"device": "cpu", "quantized": False, "clip_length": 32},
        processing_time=0.2,
        gpu_memory_used=None,
    )


def _make_audio_output(frame_id=0, timestamp=0.0) -> PerceptionOutput:
    return PerceptionOutput(
        module_name="AudioProcessor",
        frame_id=frame_id,
        timestamp=timestamp,
        data={
            "transcription": "let's keep moving",
            "audio_events": [
                {"event": "speech", "confidence": 0.91, "class_id": 0},
                {"event": "footsteps", "confidence": 0.34, "class_id": 480},
            ],
            "has_speech": True,
        },
        metadata={"device": "cpu", "quantized": False},
        processing_time=0.5,
        gpu_memory_used=None,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_full_fusion():
    """Fuse all seven perception outputs and validate the result."""
    print("\n" + "=" * 70)
    print("TEST 1: Full fusion — all seven modules")
    print("=" * 70)

    engine = MultiModalFusionEngine()
    usr = engine.fuse(
        frame_id  = 0,
        timestamp = 0.0,
        siglip      = _make_siglip_output(),
        depth       = _make_depth_output(),
        panoptic    = _make_panoptic_output(),
        scene_graph = _make_scene_graph_output(),
        tracker     = _make_tracker_output(),
        actions     = _make_action_output(),
        audio       = _make_audio_output(),
    )

    # Type check
    assert isinstance(usr, UnifiedSceneRepresentation), "Wrong return type"

    # vision embedding
    assert len(usr.vision_embedding) == 768, "vision_embedding must be 768-dim"

    # panoptic
    assert len(usr.panoptic["things"]) == 2
    assert len(usr.panoptic["stuff"])  == 3

    # objects (enriched tracks)
    assert len(usr.objects) == 2
    assert "depth_zone" in usr.objects[0]
    assert "track_id"   in usr.objects[0]

    # scene graph
    assert len(usr.scene_graph["edges"]) == 2

    # spatial relationships (flattened edges)
    assert len(usr.spatial_relationships) == 2
    assert "subject" in usr.spatial_relationships[0]
    assert "predicate" in usr.spatial_relationships[0]

    # actions
    assert len(usr.actions) >= 1
    assert usr.actions[0]["action"] == "hiking"

    # audio
    assert usr.audio["transcription"] == "let's keep moving"
    assert usr.audio["has_speech"] is True

    # scene inference (tree/grass → nature/outdoor)
    assert usr.scene_type == "nature", f"Expected 'nature', got {usr.scene_type!r}"
    assert "outdoor" in usr.context_tags

    # VLM prompt
    assert len(usr.vlm_prompt) > 50, "vlm_prompt is too short"
    assert "nature" in usr.vlm_prompt.lower() or "tree" in usr.vlm_prompt.lower()

    # validation
    warnings = usr.validate()
    assert len(warnings) == 0, f"Validation warnings: {warnings}"

    print(f"\n  repr: {usr}")
    print(f"\n  VLM Prompt:\n{'─'*60}")
    print(usr.vlm_prompt)
    print("─" * 60)
    print("\n✅ TEST 1 PASSED")
    return True


def test_partial_fusion():
    """Fuse with only SigLIP + panoptic — all other modules absent."""
    print("\n" + "=" * 70)
    print("TEST 2: Partial fusion — SigLIP + panoptic only")
    print("=" * 70)

    engine = MultiModalFusionEngine()
    usr = engine.fuse(
        frame_id  = 1,
        timestamp = 0.5,
        siglip   = _make_siglip_output(1, 0.5),
        panoptic = _make_panoptic_output(1, 0.5),
    )

    assert isinstance(usr, UnifiedSceneRepresentation)
    assert len(usr.vision_embedding) == 768
    assert usr.objects == []                        # no tracker → no objects
    assert usr.actions == []                        # no action module
    assert usr.audio["transcription"] == ""
    assert usr.scene_type == "nature"               # still inferred from panoptic

    print(f"  scene_type: {usr.scene_type}")
    print(f"  context_tags: {usr.context_tags}")
    print("\n✅ TEST 2 PASSED")
    return True


def test_empty_fusion():
    """Fuse with NO modules — all defaults, no crash."""
    print("\n" + "=" * 70)
    print("TEST 3: Empty fusion — no perception modules provided")
    print("=" * 70)

    engine = MultiModalFusionEngine()
    usr = engine.fuse(frame_id=2, timestamp=1.0)

    assert isinstance(usr, UnifiedSceneRepresentation)
    assert len(usr.vision_embedding) == 768        # filled with zeros
    assert usr.panoptic["things"] == []
    assert usr.objects == []
    assert usr.actions == []
    assert usr.scene_type == "scene"               # default

    print(f"  scene_type: {usr.scene_type!r}  (default)")
    print("\n✅ TEST 3 PASSED")
    return True


def test_serialisation():
    """Verify UnifiedSceneRepresentation is fully JSON-serialisable."""
    print("\n" + "=" * 70)
    print("TEST 4: JSON serialisation")
    print("=" * 70)

    engine = MultiModalFusionEngine()
    usr = engine.fuse(
        frame_id=3, timestamp=1.5,
        siglip   = _make_siglip_output(3, 1.5),
        panoptic = _make_panoptic_output(3, 1.5),
        tracker  = _make_tracker_output(3, 1.5),
        audio    = _make_audio_output(3, 1.5),
    )

    json_str = usr.to_json(include_embedding=True)
    parsed = json.loads(json_str)

    assert "frame_id"          in parsed
    assert "vlm_prompt"        in parsed
    assert "vision_embedding"  in parsed
    assert len(parsed["vision_embedding"]) == 768

    # No-embedding variant
    json_slim = usr.to_json(include_embedding=False)
    parsed_slim = json.loads(json_slim)
    assert "vision_embedding" not in parsed_slim

    print(f"  Full JSON size:   {len(json_str):,} chars")
    print(f"  Slim JSON size:   {len(json_slim):,} chars")
    print("\n✅ TEST 4 PASSED")
    return True


def test_scene_graph_generator_cpu():
    """Test SceneGraphGenerator directly (CPU, no model)."""
    print("\n" + "=" * 70)
    print("TEST 5: SceneGraphGenerator (CPU heuristic)")
    print("=" * 70)

    from perception import SceneGraphGenerator

    gen = SceneGraphGenerator()
    gen.load_model()

    things = [
        {"id": 1, "label": "person",  "bbox": [50, 100, 200, 350], "coverage": 0.15},
        {"id": 2, "label": "bicycle", "bbox": [210, 150, 400, 350], "coverage": 0.10},
    ]

    frame = torch.zeros((360, 640, 3), dtype=torch.uint8)
    output = gen(frame, frame_id=0, timestamp=0.0, panoptic_things=things)

    assert output.module_name == "SceneGraphGenerator"
    assert output.data["num_nodes"] == 2
    assert output.data["num_edges"] >= 1

    gen.unload()
    assert not gen.is_loaded()

    print(f"  nodes: {output.data['num_nodes']}")
    print(f"  edges: {output.data['num_edges']}")
    print(f"  edges: {output.data['edges']}")
    print("\n✅ TEST 5 PASSED")
    return True


def test_bytetracker_cpu():
    """Test ByteTracker across two frames to verify ID persistence."""
    print("\n" + "=" * 70)
    print("TEST 6: ByteTracker — track ID persistence across frames")
    print("=" * 70)

    from perception import ByteTracker

    tracker = ByteTracker()
    tracker.load_model()
    tracker.reset()

    frame = torch.zeros((360, 640, 3), dtype=torch.uint8)

    things_f0 = [
        {"id": 1, "label": "person", "bbox": [50, 80, 200, 340], "coverage": 0.12},
    ]
    things_f1 = [
        {"id": 99, "label": "person", "bbox": [55, 82, 205, 342], "coverage": 0.12},
    ]

    out0 = tracker(frame, frame_id=0, timestamp=0.0, panoptic_things=things_f0)
    out1 = tracker(frame, frame_id=1, timestamp=0.04, panoptic_things=things_f1)

    assert out0.data["num_tracks"] == 1
    assert out1.data["num_tracks"] == 1

    # Same track ID should be assigned (person moved only 5px → high IoU)
    id0 = out0.data["tracks"][0]["track_id"]
    id1 = out1.data["tracks"][0]["track_id"]
    assert id0 == id1, f"Track ID changed: {id0} → {id1}"

    tracker.unload()
    print(f"  Frame 0 track_id: {id0}")
    print(f"  Frame 1 track_id: {id1}  (same ✓)")
    print("\n✅ TEST 6 PASSED")
    return True


# ─────────────────────────────────────────────────────────────────────────────
#  Runner
# ─────────────────────────────────────────────────────────────────────────────

def run_all_tests():
    print("\n" + "=" * 70)
    print("PHASE 2: FUSION LAYER TESTS")
    print("=" * 70)

    tests = [
        ("Full fusion",              test_full_fusion),
        ("Partial fusion",           test_partial_fusion),
        ("Empty fusion",             test_empty_fusion),
        ("JSON serialisation",       test_serialisation),
        ("SceneGraphGenerator CPU",  test_scene_graph_generator_cpu),
        ("ByteTracker CPU",          test_bytetracker_cpu),
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
        print(f"{'✅ PASS' if ok else '❌ FAIL'}: {name}")

    all_passed = all(ok for _, ok in results)
    if all_passed:
        print("\n🎉 ALL PHASE 2 TESTS PASSED — Fusion layer is working.")
    else:
        print("\n⚠️  Some tests failed.")
    return all_passed


if __name__ == "__main__":
    ok = run_all_tests()
    sys.exit(0 if ok else 1)
