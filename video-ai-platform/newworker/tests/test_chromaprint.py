"""
test_chromaprint.py — Manual Chromaprint + AcoustID diagnostic

Tests the full music identification chain step by step so you can
pinpoint exactly where it breaks down:

  Step 1 — fpcalc binary check
  Step 2 — Audio extraction from video (ffmpeg)
  Step 3 — Chromaprint fingerprint generation
  Step 4 — AcoustID lookup (requires ACOUSTID_API_KEY in .env)

Usage:
    # Test with a video file
    python test_chromaprint.py --video path/to/video.mp4

    # Test with an audio file you already have
    python test_chromaprint.py --audio path/to/audio.wav

    # Test with longer audio window (default is 30s)
    python test_chromaprint.py --video path/to/video.mp4 --duration 60

Requirements:
    sudo apt-get install libchromaprint-tools
    pip install pyacoustid
    ACOUSTID_API_KEY set in .env or environment
"""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

# Allow imports from the newworker package
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


DIVIDER = "─" * 60


def _print_step(n: int, title: str):
    print(f"\n{DIVIDER}")
    print(f"  STEP {n}: {title}")
    print(DIVIDER)


def _pass(msg: str):
    print(f"  ✓  {msg}")


def _fail(msg: str):
    print(f"  ✗  {msg}")


def _info(msg: str):
    print(f"     {msg}")


# ── Step 1: fpcalc binary ─────────────────────────────────────────────────────

def check_fpcalc() -> bool:
    _print_step(1, "fpcalc binary")
    try:
        result = subprocess.run(
            ["fpcalc", "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            version = result.stdout.strip() or result.stderr.strip()
            _pass(f"fpcalc found — {version}")
            return True
        else:
            _fail("fpcalc returned non-zero exit code")
            _info("Install with: sudo apt-get install libchromaprint-tools")
            return False
    except FileNotFoundError:
        _fail("fpcalc not found in PATH")
        _info("Install with: sudo apt-get install libchromaprint-tools")
        return False
    except subprocess.TimeoutExpired:
        _fail("fpcalc timed out")
        return False


# ── Step 2: Audio extraction ──────────────────────────────────────────────────

def extract_audio(video_path: str, output_path: str, max_secs: int) -> bool:
    _print_step(2, f"Audio extraction (first {max_secs}s via ffmpeg)")
    _info(f"Input  : {video_path}")
    _info(f"Output : {output_path}")

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-t", str(max_secs),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "44100",
        "-ac", "1",
        "-loglevel", "error",
        output_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            _fail("ffmpeg extraction failed")
            _info(result.stderr.strip())
            return False

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            _fail("Output file is empty or missing")
            return False

        size_kb = os.path.getsize(output_path) / 1024
        _pass(f"Audio extracted successfully ({size_kb:.0f} KB)")
        return True

    except subprocess.TimeoutExpired:
        _fail("ffmpeg timed out after 120s")
        return False
    except Exception as e:
        _fail(f"Unexpected error: {e}")
        return False


# ── Step 3: Chromaprint fingerprint ──────────────────────────────────────────

def generate_fingerprint(audio_path: str, max_secs: int) -> tuple:
    """Returns (duration, fingerprint_str) or (None, None) on failure."""
    _print_step(3, "Chromaprint fingerprint generation")

    try:
        import acoustid
        duration, fingerprint = acoustid.fingerprint_file(
            audio_path,
            maxlength=max_secs,
        )

        if not fingerprint:
            _fail("Fingerprint is empty — audio may be silent or corrupt")
            return None, None

        fp_preview = fingerprint[:40] + "..." if len(fingerprint) > 40 else fingerprint
        _pass(f"Fingerprint generated")
        _info(f"Duration   : {duration:.2f}s")
        _info(f"Fingerprint: {fp_preview}")
        _info(f"Length     : {len(fingerprint)} chars")

        if duration < 5:
            print(f"\n  ⚠  Audio is only {duration:.1f}s — too short for reliable matching (need 5s+)")

        return duration, fingerprint

    except ImportError:
        _fail("pyacoustid not installed — run: pip install pyacoustid")
        return None, None
    except Exception as e:
        _fail(f"Fingerprint generation failed: {e}")
        return None, None


# ── Step 4: AcoustID lookup ───────────────────────────────────────────────────

def lookup_acoustid(audio_path: str, api_key: str) -> list:
    """Returns list of result dicts."""
    _print_step(4, "AcoustID lookup")

    if not api_key:
        _fail("No API key — set ACOUSTID_API_KEY in your .env file")
        _info("Get a free key at: https://acoustid.biz/login")
        return []

    _info(f"API key : {api_key[:6]}{'*' * (len(api_key) - 6)}")
    _info(f"Audio   : {audio_path}")

    try:
        import acoustid

        results = []
        for score, recording_id, title, artist in acoustid.match(api_key, audio_path):
            results.append({
                "confidence":    round(float(score), 4),
                "recording_id":  recording_id or "",
                "title":         title or "Unknown",
                "artist":        artist or "Unknown",
            })

        results.sort(key=lambda x: x["confidence"], reverse=True)

        if not results:
            _fail("No matches returned from AcoustID")
            _info("Possible reasons:")
            _info("  • Song not in AcoustID/MusicBrainz database")
            _info("  • Audio is too noisy or mixed (background sounds corrupt fingerprint)")
            _info("  • Music is too quiet relative to other sounds")
            _info("  • Independent/niche artist with few database submissions")
            return []

        _pass(f"{len(results)} result(s) returned")
        print()
        for i, r in enumerate(results[:5]):
            confidence_pct = f"{r['confidence'] * 100:.1f}%"
            marker = "  ★" if r["confidence"] > 0.40 else "   "
            print(f"{marker} [{i+1}] {confidence_pct} — \"{r['title']}\" by {r['artist']}")
            _info(f"Recording ID: {r['recording_id']}")

        threshold_note = "(threshold for has_music=True is 40%)"
        best = results[0]
        print()
        if best["confidence"] > 0.40:
            _pass(f"Best match above threshold — music identified! {threshold_note}")
        else:
            print(f"  ⚠  Best match confidence {best['confidence']*100:.1f}% is below 40% threshold {threshold_note}")

        return results

    except ImportError:
        _fail("pyacoustid not installed — run: pip install pyacoustid")
        return []
    except Exception as e:
        _fail(f"AcoustID lookup failed: {e}")
        _info(str(e))
        return []


# ── Bonus: run fpcalc directly for raw output ─────────────────────────────────

def run_fpcalc_raw(audio_path: str):
    """Runs fpcalc directly and shows its raw output."""
    print(f"\n{DIVIDER}")
    print("  BONUS: Raw fpcalc output")
    print(DIVIDER)
    try:
        result = subprocess.run(
            ["fpcalc", audio_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                # Truncate the fingerprint line so it doesn't flood the terminal
                if line.startswith("FINGERPRINT=") and len(line) > 60:
                    print(f"  {line[:60]}... (truncated)")
                else:
                    print(f"  {line}")
        else:
            _fail("fpcalc returned error")
            _info(result.stderr.strip())
    except Exception as e:
        _fail(f"fpcalc error: {e}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Chromaprint + AcoustID diagnostic test"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--video", metavar="PATH", help="Path to a video file (MP4, etc.)")
    group.add_argument("--audio", metavar="PATH", help="Path to an audio file (WAV, MP3, etc.)")
    parser.add_argument(
        "--duration", type=int, default=30,
        help="Seconds of audio to fingerprint (default: 30)"
    )
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  Chromaprint + AcoustID — Diagnostic Test")
    print("=" * 60)

    api_key = os.getenv("ACOUSTID_API_KEY", "")

    # ── Step 1: fpcalc ────────────────────────────────────────────────
    if not check_fpcalc():
        print("\n  Cannot proceed without fpcalc. Exiting.\n")
        sys.exit(1)

    # ── Step 2: Audio extraction (only if video provided) ─────────────
    tmp_audio = None
    if args.video:
        if not os.path.exists(args.video):
            print(f"\n  ✗  Video file not found: {args.video}\n")
            sys.exit(1)

        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp_audio = tmp.name
        tmp.close()

        if not extract_audio(args.video, tmp_audio, args.duration):
            print("\n  Cannot proceed — audio extraction failed. Exiting.\n")
            if os.path.exists(tmp_audio):
                os.remove(tmp_audio)
            sys.exit(1)

        audio_path = tmp_audio

    else:
        if not os.path.exists(args.audio):
            print(f"\n  ✗  Audio file not found: {args.audio}\n")
            sys.exit(1)
        audio_path = args.audio
        _print_step(2, "Audio extraction")
        _info("Skipped — audio file provided directly")

    # ── Step 3: Fingerprint ───────────────────────────────────────────
    duration, fingerprint = generate_fingerprint(audio_path, args.duration)

    if fingerprint is None:
        print("\n  Cannot proceed — fingerprinting failed. Exiting.\n")
        if tmp_audio and os.path.exists(tmp_audio):
            os.remove(tmp_audio)
        sys.exit(1)

    # ── Raw fpcalc output ─────────────────────────────────────────────
    run_fpcalc_raw(audio_path)

    # ── Step 4: AcoustID lookup ───────────────────────────────────────
    lookup_acoustid(audio_path, api_key)

    # ── Cleanup ───────────────────────────────────────────────────────
    if tmp_audio and os.path.exists(tmp_audio):
        os.remove(tmp_audio)

    print(f"\n{DIVIDER}")
    print("  Test complete")
    print(DIVIDER + "\n")


if __name__ == "__main__":
    main()
