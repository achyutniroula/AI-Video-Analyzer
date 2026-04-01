"""
FrameResult — complete output for one processed video frame.

Bundles together:
  - UnifiedSceneRepresentation  (Phase 2 fusion output)
  - VLMCaption                  (Phase 3 Qwen2-VL output)
  - Per-step timing breakdown   (Phase 4 profiling)
  - Peak VRAM usage
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional

from fusion.unified_representation import UnifiedSceneRepresentation
from vlm.vlm_caption import VLMCaption


@dataclass
class FrameResult:
    frame_id: int
    timestamp: float                      # seconds from video start

    usr: UnifiedSceneRepresentation
    caption: VLMCaption

    step_times: Dict[str, float]          # e.g. {"siglip": 0.11, "panoptic": 0.31, ...}
    total_time: float                     # sum of step_times
    peak_vram_gb: Optional[float] = None  # GPU high-water mark for this frame

    # ─────────────────────────────────────────────────────────────────
    #  Target check
    # ─────────────────────────────────────────────────────────────────

    def passes_target(self, target_s: float = 5.0) -> bool:
        """Return True if total_time <= target_s."""
        return self.total_time <= target_s

    # ─────────────────────────────────────────────────────────────────
    #  Serialisation (embedding stripped by default — too large)
    # ─────────────────────────────────────────────────────────────────

    def to_dict(self, include_embedding: bool = False) -> Dict[str, Any]:
        return {
            "frame_id": self.frame_id,
            "timestamp": self.timestamp,
            "scene_type": self.usr.scene_type,
            "context_tags": self.usr.context_tags,
            "caption": self.caption.caption,
            "tokens_generated": self.caption.tokens_generated,
            "step_times": self.step_times,
            "total_time": round(self.total_time, 3),
            "peak_vram_gb": self.peak_vram_gb,
            "passes_5s_target": self.passes_target(5.0),
            "usr": (
                self.usr.to_dict() if include_embedding
                else self.usr.to_dict_no_embedding()
            ),
        }

    def to_json(self, indent: int = 2, include_embedding: bool = False) -> str:
        return json.dumps(self.to_dict(include_embedding=include_embedding), indent=indent)

    # ─────────────────────────────────────────────────────────────────
    #  Pretty display
    # ─────────────────────────────────────────────────────────────────

    def format_timings(self, target_s: float = 5.0) -> str:
        """One-line timing string for quick inspection."""
        steps = "  ".join(f"{k}={v:.2f}s" for k, v in self.step_times.items())
        status = "✓" if self.passes_target(target_s) else "✗"
        return (
            f"[Frame {self.frame_id} @ {self.timestamp:.2f}s]  "
            f"total={self.total_time:.2f}s {status}  |  {steps}"
        )

    def __repr__(self) -> str:
        return (
            f"FrameResult(frame={self.frame_id}, t={self.timestamp:.2f}s, "
            f"total={self.total_time:.2f}s, "
            f"scene={self.usr.scene_type!r}, "
            f'caption="{self.caption.caption[:60]}...")'
        )
