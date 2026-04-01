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

        return {
            "video_id": self.video_id,
            "video_path": self.video_path,
            "duration": self.duration,
            "frame_count": self.frame_count,
            # Narrative
            "narrative": self.narrative.narrative,
            "narrative_model": self.narrative.model,
            "narrative_input_tokens": self.narrative.input_tokens,
            "narrative_output_tokens": self.narrative.output_tokens,
            "narrative_processing_time": self.narrative.processing_time,
            # Scene info
            "scene_types": scene_types,
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
