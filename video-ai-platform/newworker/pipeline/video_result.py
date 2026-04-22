"""
VideoResult — the complete output of the full video processing pipeline.

Bundles all per-frame results, the temporal assembly, the final narrative,
and top-level timing / diagnostics.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.frame_result import FrameResult
    from narrative.temporal_assembly import TemporalAssembly
    from narrative.narrative_result import NarrativeResult


def _fuse_audio_global(
    has_speech: bool,
    speech_confidence: float,
    has_music: bool,
    htsat_events: list,
    dominant_votes: dict,
) -> tuple:
    """
    Determine the global dominant audio type and generate fusion notes.

    Resolves conflicts such as:
      - Music identified by fingerprint + speech detected → speech over music
      - CLAP detects "singing voice" + Whisper detects speech → singing/speech
      - High-confidence environment sounds + low-confidence speech → environment
      - Music fingerprinted but no speech → music

    Returns: (dominant_type: str, fusion_notes: str | None)
    """
    notes = []

    # Music signal from CLAP (per-frame)
    music_clap_score = max(
        (e["confidence"] for e in htsat_events
         if e["event"] in ("music", "singing voice")),
        default=0.0,
    )
    has_music_clap = music_clap_score > 0.40

    # Environment signal
    env_events = [
        e for e in htsat_events
        if e["event"] not in ("music", "singing voice", "speech")
    ]
    env_score = env_events[0]["confidence"] if env_events else 0.0

    # Resolve conflicts
    if has_music and has_speech:
        notes.append("speech detected over identified music track")
    if has_music_clap and has_speech and not has_music:
        notes.append("possible music or singing in background")
    if has_music_clap and has_music:
        # Fingerprint confirms it
        notes.append(f"music confirmed by fingerprint (CLAP score {music_clap_score:.0%})")
    if env_events and has_speech:
        notes.append(f"speech with {env_events[0]['event']} in background")

    # Vote tally from per-frame decisions
    vote_total = sum(dominant_votes.values()) or 1
    vote_pcts = {k: v / vote_total for k, v in dominant_votes.items()}

    # Final dominant type decision
    if has_speech and speech_confidence > 0.55:
        dominant_type = "speech"
    elif has_music:
        if has_speech:
            dominant_type = "speech"  # speech wins over music
        else:
            dominant_type = "music"
    elif has_music_clap and music_clap_score > 0.60:
        dominant_type = "music"
    elif has_speech:
        dominant_type = "speech"
    elif env_score > 0.40:
        dominant_type = "environment"
    elif vote_pcts.get("silent", 0) > 0.70:
        dominant_type = "silent"
    else:
        # Fall back to per-frame majority vote
        dominant_type = max(vote_pcts, key=vote_pcts.get) if vote_pcts else "silent"

    return dominant_type, " | ".join(notes) if notes else None


@dataclass
class VideoResult:
    # ── Identity ─────────────────────────────────────────────────────
    video_path: str
    video_id: str
    duration: float          # seconds (from VideoProcessor.get_video_info)
    frame_count: int         # number of frames actually analyzed

    # ── Per-frame outputs (kept for downstream use, excluded from to_dict) ──
    frame_results: List["FrameResult"]

    # ── Temporal / narrative ─────────────────────────────────────────
    temporal_assembly: "TemporalAssembly"
    narrative: "NarrativeResult"

    # ── Timing diagnostics ───────────────────────────────────────────
    total_processing_time: float        # wall-clock seconds for full video
    peak_vram_gb: Optional[float] = None

    # ─────────────────────────────────────────────────────────────────
    #  Target check
    # ─────────────────────────────────────────────────────────────────

    def passes_target(self, target_s: float = 300.0) -> bool:
        """Return True if the full video was processed within target_s seconds.

        Default target is 5 minutes (300 s) — the g5.2xlarge SLA.
        """
        return self.total_processing_time <= target_s

    # ─────────────────────────────────────────────────────────────────
    #  Serialisation
    # ─────────────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """
        Serialise to a JSON-safe dict.

        Intentionally omits full frame_results (too large for DynamoDB /
        inline storage).  Full per-frame data is kept in the object.
        """
        from collections import Counter

        # Collect scene types seen across frames
        scene_types: List[str] = []
        seen: set = set()
        for fr in self.frame_results:
            st = fr.usr.scene_type
            if st and st not in seen:
                scene_types.append(st)
                seen.add(st)

        # Average per-frame processing time
        avg_frame_time = (
            sum(fr.total_time for fr in self.frame_results) / len(self.frame_results)
            if self.frame_results else 0.0
        )

        # Object class counts from tracked objects (label → track count)
        label_counter = Counter(
            t.label for t in self.temporal_assembly.object_tracks if t.label
        )
        object_class_counts = dict(label_counter.most_common(15))

        # ── Audio analysis — fused from three-part pipeline ─────────────────
        audio_summary = self.temporal_assembly.audio_summary
        music_result  = self.temporal_assembly.music_identification or {}

        # Speech
        transcription_text = " ".join(
            seg["text"] for seg in audio_summary.get("transcriptions", [])
            if seg.get("text")
        ).strip()
        has_speech = bool(transcription_text)
        speech_confidence = audio_summary.get("avg_speech_confidence", 0.0)

        # Music
        has_music = bool(music_result.get("best_match"))
        music_match = music_result.get("best_match")

        # Environmental sounds (HTS-AT)
        htsat_events = audio_summary.get("events", [])

        # Music genre/mood description (CLAP zero-shot, per-frame aggregate)
        music_descriptions = audio_summary.get("music_descriptions", [])

        # Global dominant type via majority vote + music fingerprint
        dominant_type, fusion_notes = _fuse_audio_global(
            has_speech=has_speech,
            speech_confidence=speech_confidence,
            has_music=has_music,
            htsat_events=htsat_events,
            dominant_votes=audio_summary.get("dominant_votes", {}),
        )

        audio_analysis = {
            # Speech (Whisper large-v3)
            "has_speech": has_speech,
            "transcription": transcription_text or None,
            "speech_confidence": round(speech_confidence, 4),
            # Music (Chromaprint + AcoustID)
            "has_music": has_music,
            "music_match": music_match,
            # Environmental sounds (HTS-AT)
            "audio_events": htsat_events,
            # Music genre/mood (CLAP zero-shot per-frame aggregate)
            "music_descriptions": music_descriptions,
            # Unified fusion
            "dominant_type": dominant_type,
            "fusion_notes": fusion_notes,
        }

        return {
            "video_id": self.video_id,
            "video_path": self.video_path,
            "duration": self.duration,
            "frame_count": self.frame_count,
            # Narrative
            "narrative": self.narrative.narrative,
            "narrative_summary": self.narrative.summary,
            "narrative_model": self.narrative.model,
            "narrative_input_tokens": self.narrative.input_tokens,
            "narrative_output_tokens": self.narrative.output_tokens,
            "narrative_processing_time": self.narrative.processing_time,
            # Scene info
            "scene_types": scene_types,
            # Detections / tracking
            "object_class_counts": object_class_counts,
            # Audio
            "audio_analysis": audio_analysis,
            # Timing
            "total_processing_time": round(self.total_processing_time, 3),
            "avg_frame_processing_time": round(avg_frame_time, 3),
            "passes_5min_target": self.passes_target(300.0),
            "peak_vram_gb": self.peak_vram_gb,
            # Temporal summary counts
            "num_scenes": len(self.temporal_assembly.scenes),
            "num_object_tracks": len(self.temporal_assembly.object_tracks),
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    # ─────────────────────────────────────────────────────────────────
    #  Human-readable summary
    # ─────────────────────────────────────────────────────────────────

    def summary(self) -> str:
        """Print-friendly summary of the video processing result."""
        d = self.to_dict()
        target_str = "PASS" if d["passes_5min_target"] else "FAIL"
        vram_str = (
            f"{self.peak_vram_gb:.2f} GB" if self.peak_vram_gb is not None else "N/A"
        )
        narrative_preview = self.narrative.narrative[:200].replace("\n", " ")

        lines = [
            "=" * 60,
            f"VideoResult — {self.video_id}",
            "=" * 60,
            f"  Duration        : {self.duration:.1f}s",
            f"  Frames analyzed : {self.frame_count}",
            f"  Scene types     : {', '.join(d['scene_types']) or 'unknown'}",
            f"  Object tracks   : {d['num_object_tracks']}",
            "",
            f"  Processing time : {self.total_processing_time:.1f}s  [{target_str}]",
            f"  Avg / frame     : {d['avg_frame_processing_time']:.2f}s",
            f"  Peak VRAM       : {vram_str}",
            "",
            "  Narrative (preview):",
            f"  {narrative_preview}...",
            "=" * 60,
        ]
        return "\n".join(lines)
