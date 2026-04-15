"""
Music Identifier — Chromaprint fingerprinting + AcoustID lookup

Identifies exact songs in a video's audio track, similar to Shazam /
YouTube Content ID. Runs ONCE per video on the full audio (not per-frame).

Requirements:
  pip install pyacoustid
  sudo apt-get install libchromaprint-tools   # installs fpcalc binary

Environment:
  ACOUSTID_API_KEY  — free key from https://acoustid.biz/login

Usage (from main.py):
    identifier = MusicIdentifier()
    result = identifier.identify(audio_path)
    # result["best_match"] → {"title": ..., "artist": ..., "confidence": ...}
    # result["has_music"]  → bool

The module is OPTIONAL — if fpcalc is not installed or the API key is
missing, identify() returns {"has_music": False, "error": "..."}.
This will not affect the visual pipeline.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from typing import Any, Dict, List, Optional


class MusicIdentifier:
    """
    Chromaprint + AcoustID music fingerprinting.

    Args:
        api_key   : AcoustID API key. Falls back to ACOUSTID_API_KEY env var.
        max_secs  : Maximum seconds of audio to fingerprint (30s is sufficient).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        max_secs: int = 30,
    ):
        self.api_key = api_key or os.getenv("ACOUSTID_API_KEY", "")
        self.max_secs = max_secs

    # ── Public API ────────────────────────────────────────────────────────────

    def identify(self, audio_path: str) -> Dict[str, Any]:
        """
        Run fingerprinting and AcoustID lookup on an audio file.

        Args:
            audio_path : Path to any audio file supported by fpcalc
                         (WAV, MP3, AAC, FLAC, etc.)

        Returns:
            {
              "has_music"         : bool,
              "fingerprint_duration": float,
              "best_match"        : {"title", "artist", "confidence"} | None,
              "all_results"       : [{score, title, artist}, ...],
              "error"             : str | None,
            }
        """
        base: Dict[str, Any] = {
            "has_music": False,
            "fingerprint_duration": 0.0,
            "best_match": None,
            "all_results": [],
            "error": None,
        }

        if not self.api_key:
            base["error"] = (
                "No AcoustID API key — set ACOUSTID_API_KEY in .env. "
                "Get a free key at https://acoustid.biz/login"
            )
            print(f"⚠  Music identification skipped: {base['error']}")
            return base

        if not self._fpcalc_available():
            base["error"] = (
                "fpcalc not found — install with: "
                "sudo apt-get install libchromaprint-tools"
            )
            print(f"⚠  Music identification skipped: {base['error']}")
            return base

        try:
            # Get duration from fingerprint step (to validate audio length)
            duration, _ = self._fingerprint(audio_path)
            base["fingerprint_duration"] = round(duration, 2)

            if duration < 5:
                base["error"] = f"Audio too short ({duration:.1f}s) for fingerprinting"
                return base

            # acoustid.match() takes the FILE PATH directly — it fingerprints internally
            results = self._lookup(audio_path)
            base["all_results"] = results

            if results:
                best = results[0]
                base["has_music"] = best["confidence"] > 0.40
                if base["has_music"]:
                    base["best_match"] = {
                        "title":      best.get("title", "Unknown"),
                        "artist":     best.get("artist", "Unknown"),
                        "confidence": round(best["confidence"], 4),
                    }

            return base

        except Exception as e:
            base["error"] = str(e)
            print(f"⚠  Music identification error: {e}")
            return base

    # ── Fingerprinting ────────────────────────────────────────────────────────

    def _fingerprint(self, audio_path: str):
        """
        Generate Chromaprint fingerprint via fpcalc.
        Returns (duration_seconds, fingerprint_string).
        """
        import acoustid
        duration, fp = acoustid.fingerprint_file(
            audio_path,
            maxlength=self.max_secs,
        )
        if isinstance(fp, bytes):
            fp = fp.decode("utf-8")
        return duration, fp

    # ── AcoustID lookup ───────────────────────────────────────────────────────

    def _lookup(self, audio_path: str) -> List[Dict[str, Any]]:
        """
        Query AcoustID using the audio file path directly.

        acoustid.match(apikey, path) handles fingerprinting + lookup internally.

        Result format per item:
          {"confidence": float, "title": str, "artist": str, "recording_id": str}
        """
        import acoustid

        results: List[Dict[str, Any]] = []
        try:
            for score, recording_id, title, artist in acoustid.match(
                self.api_key,
                audio_path,
            ):
                results.append({
                    "confidence": round(float(score), 4),
                    "recording_id": recording_id or "",
                    "title": title or "Unknown",
                    "artist": artist or "Unknown",
                })
        except acoustid.WebServiceError as e:
            raise RuntimeError(f"AcoustID API error: {e}")

        results.sort(key=lambda x: x["confidence"], reverse=True)
        return results[:5]  # top 5 matches

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _fpcalc_available() -> bool:
        """Check if the fpcalc binary is available in PATH."""
        try:
            result = subprocess.run(
                ["fpcalc", "-version"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    @staticmethod
    def extract_audio(video_path: str, output_path: str, max_secs: int = 30) -> bool:
        """
        Extract audio from a video file using ffmpeg.

        Args:
            video_path  : Source video file.
            output_path : Destination WAV file.
            max_secs    : Maximum seconds to extract (default 30).

        Returns:
            True on success, False on failure.
        """
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-t", str(max_secs),
            "-vn",                    # no video
            "-acodec", "pcm_s16le",  # uncompressed WAV (fpcalc prefers this)
            "-ar", "44100",           # 44.1kHz (Chromaprint standard)
            "-ac", "1",               # mono
            "-loglevel", "error",
            output_path,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=60)
            return result.returncode == 0 and os.path.getsize(output_path) > 0
        except Exception:
            return False
