"""
Test script — upgraded three-part audio intelligence pipeline

Runs all three components on a local audio or video file and prints
the full fused audio summary.

Usage:
    python tests/test_audio_pipeline.py path/to/video.mp4
    python tests/test_audio_pipeline.py path/to/audio.wav
    python tests/test_audio_pipeline.py  # uses a generated test tone

Requirements (on EC2 / Ubuntu):
    pip install faster-whisper pyacoustid
    sudo apt-get install libchromaprint-tools ffmpeg

    # ACOUSTID_API_KEY must be set in .env for music identification
"""

import os
import sys
import json
import time
import tempfile
import subprocess

import numpy as np

# Allow running from the newworker/ root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────

def extract_audio_wav(source_path: str, output_wav: str, max_secs: int = 30) -> bool:
    """Extract mono 16kHz WAV from a video or audio file using ffmpeg."""
    cmd = [
        "ffmpeg", "-y",
        "-i", source_path,
        "-t", str(max_secs),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        "-loglevel", "error",
        output_wav,
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=60)
    return result.returncode == 0 and os.path.getsize(output_wav) > 0


def load_wav_as_float32(wav_path: str) -> np.ndarray:
    """Load a 16kHz mono WAV file as float32 numpy array."""
    import wave
    with wave.open(wav_path, "rb") as wf:
        raw = wf.readframes(wf.getnframes())
        arr = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    return arr


def generate_test_tone(duration_s: float = 5.0, sr: int = 16000) -> np.ndarray:
    """Generate a 440 Hz test tone as a fallback when no audio file is given."""
    t = np.linspace(0, duration_s, int(sr * duration_s))
    return (0.3 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)


def hr(title: str):
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


# ─────────────────────────────────────────────────────────────────────────────
#  Part 1 — Whisper large-v3
# ─────────────────────────────────────────────────────────────────────────────

def test_whisper(waveform: np.ndarray, device: str = "cpu"):
    hr("PART 1 · Whisper large-v3 — Speech Recognition")
    t0 = time.time()

    from perception.audio_processor import AudioProcessor
    proc = AudioProcessor(
        whisper_model="large-v3",
        whisper_compute_type="float16" if device == "cuda" else "int8",
        use_htsat=False,
        device=device,
    )
    proc.load_model()

    # Dummy frame (not used by AudioProcessor)
    dummy_frame = np.zeros((1, 1, 3), dtype=np.uint8)
    output = proc(dummy_frame, frame_id=0, timestamp=0.0, audio_waveform=waveform)
    proc.unload()

    d = output.data
    print(f"  Has speech       : {d['has_speech']}")
    print(f"  Transcription    : {d['transcription']!r}")
    print(f"  Speech confidence: {d['speech_confidence']:.1%}")
    print(f"  Processing time  : {output.processing_time:.2f}s")

    return d


# ─────────────────────────────────────────────────────────────────────────────
#  Part 2 — Chromaprint + AcoustID
# ─────────────────────────────────────────────────────────────────────────────

def test_music_identification(source_path: str):
    hr("PART 2 · Chromaprint + AcoustID — Music Identification")
    t0 = time.time()

    from perception.music_identifier import MusicIdentifier

    identifier = MusicIdentifier()

    # For music identification we need a 44.1kHz WAV
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
        audio_44k = tf.name
    try:
        ok = MusicIdentifier.extract_audio(source_path, audio_44k, max_secs=30)
        if not ok:
            print("  ✗ Could not extract audio for fingerprinting")
            return {"has_music": False, "error": "extraction failed"}

        result = identifier.identify(audio_44k)
    finally:
        if os.path.exists(audio_44k):
            os.remove(audio_44k)

    elapsed = time.time() - t0
    print(f"  Fingerprint duration : {result.get('fingerprint_duration', 0):.1f}s")
    print(f"  Has music match      : {result['has_music']}")
    if result.get("best_match"):
        m = result["best_match"]
        print(f"  Best match           : \"{m['title']}\" by {m['artist']}")
        print(f"  Match confidence     : {m['confidence']:.1%}")
    if result.get("all_results"):
        print(f"  All candidates       :")
        for r in result["all_results"]:
            print(f"    {r['confidence']:.0%}  {r['title']} — {r['artist']}")
    if result.get("error"):
        print(f"  ⚠  Note: {result['error']}")
    print(f"  Processing time      : {elapsed:.2f}s")

    return result


# ─────────────────────────────────────────────────────────────────────────────
#  Part 3 — HTS-AT (via CLAP)
# ─────────────────────────────────────────────────────────────────────────────

def test_htsat(waveform: np.ndarray, device: str = "cpu"):
    hr("PART 3 · HTS-AT (LAION CLAP) — Environmental Sound Detection")
    t0 = time.time()

    from perception.audio_processor import AudioProcessor
    proc = AudioProcessor(
        whisper_model="large-v3",
        whisper_compute_type="float16" if device == "cuda" else "int8",
        use_htsat=True,
        device=device,
    )
    proc.load_model()

    dummy_frame = np.zeros((1, 1, 3), dtype=np.uint8)
    output = proc(dummy_frame, frame_id=0, timestamp=0.0, audio_waveform=waveform)
    proc.unload()

    d = output.data
    events = d.get("audio_events", [])
    if events:
        print(f"  Top detected events:")
        for ev in events:
            bar = "█" * int(ev["confidence"] * 20)
            print(f"    {ev['event']:<30} {bar:<20} {ev['confidence']:.1%}")
    else:
        print("  No events above threshold.")
    print(f"  Dominant type (this segment): {d['dominant_type']}")
    print(f"  Processing time             : {output.processing_time:.2f}s")

    return d


# ─────────────────────────────────────────────────────────────────────────────
#  Part 4 — Unified fusion
# ─────────────────────────────────────────────────────────────────────────────

def test_fusion(whisper_data: dict, htsat_data: dict, music_data: dict):
    hr("PART 4 · Unified Audio Fusion")

    from pipeline.video_result import _fuse_audio_global

    # Simulate what temporal_assembly would aggregate from multiple frames
    has_speech = whisper_data.get("has_speech", False)
    speech_confidence = whisper_data.get("speech_confidence", 0.0)
    has_music = music_data.get("has_music", False)
    htsat_events = htsat_data.get("audio_events", [])

    # Simulate per-frame dominant votes (single frame here)
    dominant_votes = {htsat_data.get("dominant_type", "silent"): 1}

    dominant_type, fusion_notes = _fuse_audio_global(
        has_speech=has_speech,
        speech_confidence=speech_confidence,
        has_music=has_music,
        htsat_events=htsat_events,
        dominant_votes=dominant_votes,
    )

    music_match = music_data.get("best_match")

    result = {
        "has_speech":        has_speech,
        "transcription":     whisper_data.get("transcription"),
        "speech_confidence": speech_confidence,
        "has_music":         has_music,
        "music_match":       music_match,
        "audio_events":      htsat_events,
        "dominant_type":     dominant_type,
        "fusion_notes":      fusion_notes,
    }

    print(json.dumps(result, indent=2))
    return result


# ─────────────────────────────────────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Test the three-part audio pipeline")
    parser.add_argument("source", nargs="?", default=None,
                        help="Path to video or audio file (optional)")
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda"],
                        help="Device for neural models (default: cpu)")
    args = parser.parse_args()

    print("=" * 60)
    print("  Audio Intelligence Pipeline — Test")
    print("  Whisper large-v3  |  HTS-AT  |  Chromaprint + AcoustID")
    print("=" * 60)

    source_path = args.source
    device = args.device

    # Prepare waveform (16kHz mono float32)
    waveform = None
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
        tmp_wav = tf.name

    try:
        if source_path:
            print(f"\n  Source: {source_path}")
            ok = extract_audio_wav(source_path, tmp_wav)
            if ok:
                waveform = load_wav_as_float32(tmp_wav)
                print(f"  Audio loaded: {len(waveform)/16000:.1f}s at 16kHz")
            else:
                print("  ⚠  ffmpeg extraction failed — using test tone")
        else:
            print("\n  No source provided — using 5s 440 Hz test tone")
            source_path = tmp_wav  # for music ID, use the tone WAV

        if waveform is None:
            waveform = generate_test_tone(5.0)
            import wave, struct
            with wave.open(tmp_wav, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                raw = struct.pack(f"<{len(waveform)}h",
                                  *(int(s * 32767) for s in waveform))
                wf.writeframes(raw)

        # Run all three parts
        whisper_data = test_whisper(waveform, device=device)
        music_data   = test_music_identification(source_path or tmp_wav)
        htsat_data   = test_htsat(waveform, device=device)
        fusion_result = test_fusion(whisper_data, htsat_data, music_data)

        hr("SUMMARY")
        print(f"  Dominant type : {fusion_result['dominant_type'].upper()}")
        if fusion_result.get("transcription"):
            print(f"  Speech        : {fusion_result['transcription']!r}")
        if fusion_result.get("music_match"):
            m = fusion_result["music_match"]
            print(f"  Music         : \"{m['title']}\" by {m['artist']}")
        if fusion_result.get("audio_events"):
            top = fusion_result["audio_events"][0]
            print(f"  Top sound     : {top['event']} ({top['confidence']:.1%})")
        if fusion_result.get("fusion_notes"):
            print(f"  Fusion notes  : {fusion_result['fusion_notes']}")
        print("\n  ✓ All three parts completed successfully")

    finally:
        if os.path.exists(tmp_wav):
            os.remove(tmp_wav)


if __name__ == "__main__":
    main()
