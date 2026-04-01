"""
Phase 5 Test Suite — Claude generates natural timestamp narrative

Tiers:
  CPU / mock tests : always run — test assembly, prompt building, result dataclass
  API tests        : skipped unless ANTHROPIC_API_KEY is set or --api flag passed

Run with:
  python tests/test_narrative.py           # CPU tests only
  python tests/test_narrative.py --api     # include real Claude API call
"""

import sys
import os
import json
import argparse
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from narrative import NarrativeGenerator, NarrativeResult, TemporalAssembly
from narrative.temporal_assembly import SceneSegment, ObjectTrack, ActionSegment


# ─────────────────────────────────────────────────────────────────────────────
#  Shared fixture: build realistic FrameResult list without GPU
# ─────────────────────────────────────────────────────────────────────────────

def _make_frame_results():
    """Return 5 dry-run FrameResults representing a ~2s outdoor cycling scene."""
    import torch
    from pipeline import FramePipeline

    frames = []
    with FramePipeline(dry_run=True) as pipeline:
        for i in range(5):
            # Patch USR with realistic data after dry-run
            result = pipeline.process_frame(
                torch.zeros((360, 640, 3), dtype=torch.uint8),
                frame_id=i,
                timestamp=round(i * 0.5, 1),
            )
            _patch_result(result, i)
            frames.append(result)
    return frames


def _patch_result(result, idx: int):
    """Inject realistic perception data into a dry-run FrameResult."""
    usr = result.usr
    usr.scene_type = "urban"
    usr.context_tags = ["outdoor", "urban"]
    usr.panoptic = {
        "things": [
            {"id": 1, "label": "person",  "bbox": [100, 60, 280, 340], "coverage": 0.18},
            {"id": 2, "label": "bicycle", "bbox": [260, 150, 450, 340], "coverage": 0.11},
        ],
        "stuff": [
            {"label": "road",     "coverage": 0.45},
            {"label": "building", "coverage": 0.22},
            {"label": "sky",      "coverage": 0.10},
        ],
    }
    usr.objects = [
        {"track_id": 1, "label": "person",  "bbox": [100, 60, 280, 340], "depth_zone": "mid",  "score": 0.18},
        {"track_id": 2, "label": "bicycle", "bbox": [260, 150, 450, 340], "depth_zone": "near", "score": 0.11},
    ]
    usr.actions = [
        {"action": "riding a bike", "confidence": 0.72, "class_id": 200},
    ]
    usr.audio = {
        "transcription": "let's go" if idx == 2 else "",
        "audio_events": [{"event": "traffic", "confidence": 0.55}],
        "has_speech": idx == 2,
    }
    usr.spatial_relationships = [
        {"subject": "person", "predicate": "near", "object": "bicycle"},
    ]
    # Patch caption with something realistic
    result.caption.caption = (
        "A cyclist rides along a city road past buildings. "
        "The person is visible in the mid-ground astride a bicycle."
    )
    result.caption.scene_type = "urban"


# ─────────────────────────────────────────────────────────────────────────────
#  Tests — CPU / mock (always run)
# ─────────────────────────────────────────────────────────────────────────────

def test_temporal_assembly_basic():
    """TemporalAssembly builds correct scenes, tracks, and audio from frames."""
    print("\n" + "=" * 70)
    print("TEST 1: TemporalAssembly — scenes, tracks, audio")
    print("=" * 70)

    results = _make_frame_results()
    assembly = TemporalAssembly.from_frame_results(results)

    assert isinstance(assembly, TemporalAssembly)
    assert assembly.frame_count == 5
    assert assembly.video_duration == 2.0

    # All frames have scene_type "urban" → should be one scene segment
    assert len(assembly.scenes) == 1
    assert assembly.scenes[0].scene_type == "urban"
    assert assembly.scenes[0].start_ts == 0.0
    assert assembly.scenes[0].end_ts   == 2.0

    # Two persistent tracks: person (ID:1) and bicycle (ID:2)
    assert len(assembly.object_tracks) == 2
    ids = {t.track_id for t in assembly.object_tracks}
    assert ids == {1, 2}

    # Person track spans all 5 frames
    person_track = next(t for t in assembly.object_tracks if t.track_id == 1)
    assert person_track.frame_count == 5
    assert person_track.first_ts == 0.0
    assert person_track.last_ts  == 2.0

    # Audio: one transcription segment at t=1.0s
    assert len(assembly.audio_summary["transcriptions"]) == 1
    assert assembly.audio_summary["transcriptions"][0]["text"] == "let's go"
    assert len(assembly.audio_summary["events"]) >= 1

    # Action timeline: one segment (riding a bike)
    assert len(assembly.action_timeline) == 1
    assert assembly.action_timeline[0].action == "riding a bike"

    print(f"  Scenes : {len(assembly.scenes)}")
    print(f"  Tracks : {len(assembly.object_tracks)}")
    print(f"  Actions: {[a.action for a in assembly.action_timeline]}")
    print(f"  Audio  : {assembly.audio_summary}")
    print("\n✅ TEST 1 PASSED")
    return True


def test_temporal_assembly_empty():
    """TemporalAssembly handles empty frame list without error."""
    print("\n" + "=" * 70)
    print("TEST 2: TemporalAssembly — empty input")
    print("=" * 70)

    assembly = TemporalAssembly.from_frame_results([])
    assert assembly.frame_count == 0
    assert assembly.video_duration == 0.0
    assert assembly.scenes == []
    assert assembly.object_tracks == []

    print("  Empty assembly created without error")
    print("\n✅ TEST 2 PASSED")
    return True


def test_prompt_summary():
    """to_prompt_summary() produces non-empty text with key fields."""
    print("\n" + "=" * 70)
    print("TEST 3: TemporalAssembly.to_prompt_summary()")
    print("=" * 70)

    results  = _make_frame_results()
    assembly = TemporalAssembly.from_frame_results(results)
    summary  = assembly.to_prompt_summary()

    assert len(summary) > 20
    assert "person" in summary.lower()  or "ID:1" in summary
    assert "riding" in summary.lower()  or "bike" in summary.lower()
    assert "let's go" in summary

    print(f"\n  Summary:\n{'─'*60}")
    print(summary)
    print("─" * 60)
    print("\n✅ TEST 3 PASSED")
    return True


def test_narrative_result_dataclass():
    """NarrativeResult validates, serialises, and represents correctly."""
    print("\n" + "=" * 70)
    print("TEST 4: NarrativeResult dataclass")
    print("=" * 70)

    result = NarrativeResult(
        narrative=(
            "[0.0s–1.0s]: A cyclist rides through a busy city street.\n"
            "[1.0s–2.0s]: The person accelerates past a row of buildings.\n"
            "Throughout: City traffic hums in the background."
        ),
        video_duration=2.0,
        frame_count=5,
        model="claude-sonnet-4-6",
        input_tokens=800,
        output_tokens=120,
        processing_time=1.4,
    )

    warnings = result.validate()
    assert warnings == [], f"Unexpected warnings: {warnings}"

    d = result.to_dict()
    assert "narrative" in d
    assert d["frame_count"] == 5

    json_str = result.to_json()
    parsed = json.loads(json_str)
    assert parsed["model"] == "claude-sonnet-4-6"

    print(f"  repr: {result}")
    print(f"  JSON size: {len(json_str)} chars")
    print("\n✅ TEST 4 PASSED")
    return True


def test_prompt_building():
    """NarrativeGenerator builds a well-formed prompt from frame results."""
    print("\n" + "=" * 70)
    print("TEST 5: NarrativeGenerator prompt building")
    print("=" * 70)

    results  = _make_frame_results()
    assembly = TemporalAssembly.from_frame_results(results)

    # Access private method to inspect prompt without making an API call
    gen    = NarrativeGenerator.__new__(NarrativeGenerator)
    prompt = NarrativeGenerator._build_prompt(results, assembly)

    assert "VIDEO OVERVIEW" in prompt
    assert "FRAME-BY-FRAME ANALYSIS" in prompt
    assert "riding a bike" in prompt.lower()
    assert "let's go" in prompt
    assert "person" in prompt.lower()
    assert "road" in prompt.lower()

    print(f"\n  Prompt length: {len(prompt)} chars")
    print(f"\n  Prompt preview:\n{'─'*60}")
    # Print first 600 chars as preview
    print(prompt[:600])
    print("  ... (truncated)")
    print("─" * 60)
    print("\n✅ TEST 5 PASSED")
    return True


def test_missing_api_key():
    """NarrativeGenerator raises EnvironmentError when API key is missing."""
    print("\n" + "=" * 70)
    print("TEST 6: NarrativeGenerator — missing API key error")
    print("=" * 70)

    # Temporarily remove the key from the environment so the error triggers
    saved = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        gen     = NarrativeGenerator(api_key="")
        results = _make_frame_results()
        gen.generate(results)
        assert False, "Should have raised EnvironmentError"
    except EnvironmentError as e:
        assert "ANTHROPIC_API_KEY" in str(e)
        print(f"  Caught expected error: {e}")
    finally:
        if saved:
            os.environ["ANTHROPIC_API_KEY"] = saved

    print("\n✅ TEST 6 PASSED")
    return True


def test_empty_frame_results_error():
    """NarrativeGenerator raises ValueError for empty frame list."""
    print("\n" + "=" * 70)
    print("TEST 7: NarrativeGenerator — empty frame list error")
    print("=" * 70)

    gen = NarrativeGenerator(api_key="fake-key")
    try:
        gen.generate([])
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  Caught expected error: {e}")

    print("\n✅ TEST 7 PASSED")
    return True


# ─────────────────────────────────────────────────────────────────────────────
#  API test (skipped unless ANTHROPIC_API_KEY is set or --api flag passed)
# ─────────────────────────────────────────────────────────────────────────────

def test_real_narrative(force: bool = False):
    """
    Call the real Claude API and verify the narrative output.

    Requires ANTHROPIC_API_KEY to be set in the environment.
    """
    print("\n" + "=" * 70)
    print("TEST 8: Real Claude API — timestamp narrative generation")
    print("=" * 70)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key and not force:
        print("  ⚠️  ANTHROPIC_API_KEY not set — skipping")
        print("     Set the env var or run with --api to force this test")
        return None

    results  = _make_frame_results()
    assembly = TemporalAssembly.from_frame_results(results)

    gen = NarrativeGenerator(model="claude-sonnet-4-6", max_tokens=512, api_key=api_key)

    t0     = time.time()
    result = gen.generate(results, temporal_assembly=assembly)
    elapsed = time.time() - t0

    assert isinstance(result, NarrativeResult)
    warnings = result.validate()
    assert warnings == [], f"Validation warnings: {warnings}"

    # Narrative should mention time-based segments
    assert any(marker in result.narrative for marker in ["s]:", "s–", "s:"]), \
        "Narrative doesn't contain timestamp markers"

    print(f"\n  Duration : {result.video_duration:.1f}s")
    print(f"  Frames   : {result.frame_count}")
    print(f"  Model    : {result.model}")
    print(f"  Tokens   : {result.input_tokens} in / {result.output_tokens} out")
    print(f"  API time : {elapsed:.2f}s")
    print(f"\n  Narrative:\n{'─'*60}")
    print(result.narrative)
    print("─" * 60)

    print("\n✅ TEST 8 PASSED")
    return True


# ─────────────────────────────────────────────────────────────────────────────
#  Runner
# ─────────────────────────────────────────────────────────────────────────────

def run_all_tests(run_api: bool = False):
    print("\n" + "=" * 70)
    print("PHASE 5: NARRATIVE GENERATION TESTS")
    print("=" * 70)

    tests = [
        ("TemporalAssembly basic",        test_temporal_assembly_basic),
        ("TemporalAssembly empty",         test_temporal_assembly_empty),
        ("Prompt summary",                 test_prompt_summary),
        ("NarrativeResult dataclass",      test_narrative_result_dataclass),
        ("Prompt building",                test_prompt_building),
        ("Missing API key error",          test_missing_api_key),
        ("Empty frame results error",      test_empty_frame_results_error),
        ("Real Claude API (API key)",      lambda: test_real_narrative(force=run_api)),
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
        print("\n🎉 ALL PHASE 5 TESTS PASSED — Narrative layer is working.")
    else:
        print(f"\n⚠️  {len(failures)} test(s) failed.")
    return len(failures) == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", action="store_true",
                        help="Run real Claude API test (requires ANTHROPIC_API_KEY)")
    args = parser.parse_args()
    ok = run_all_tests(run_api=args.api)
    sys.exit(0 if ok else 1)
