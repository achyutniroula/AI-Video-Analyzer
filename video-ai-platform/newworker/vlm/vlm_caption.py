"""
VLMCaption — structured output produced by Qwen2-VL for one frame.

Passed downstream to the narrative layer (Phase 5) and stored in
the per-frame result alongside the UnifiedSceneRepresentation.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


@dataclass
class VLMCaption:
    # ── identity ──────────────────────────────────────────────────────
    frame_id: int
    timestamp: float               # seconds from video start

    # ── VLM output ────────────────────────────────────────────────────
    caption: str                   # full natural-language scene description
    scene_type: str                # echoed from UnifiedSceneRepresentation
    context_tags: List[str]        # echoed from UnifiedSceneRepresentation

    # ── diagnostics ───────────────────────────────────────────────────
    model: str
    tokens_generated: int
    processing_time: float         # seconds
    gpu_memory_used: float | None  # GB peak, or None if CPU

    # ── provenance ────────────────────────────────────────────────────
    vlm_prompt_used: str = field(default="", repr=False)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # ─────────────────────────────────────────────────────────────────
    #  Serialisation
    # ─────────────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    # ─────────────────────────────────────────────────────────────────
    #  Validation
    # ─────────────────────────────────────────────────────────────────

    def validate(self) -> List[str]:
        warnings = []
        if not self.caption or len(self.caption) < 20:
            warnings.append(f"caption is too short ({len(self.caption)} chars)")
        if not self.scene_type:
            warnings.append("scene_type is empty")
        return warnings

    def __repr__(self) -> str:
        preview = self.caption[:80].replace("\n", " ")
        return (
            f"VLMCaption(frame={self.frame_id}, t={self.timestamp:.2f}s, "
            f"tokens={self.tokens_generated}, "
            f'caption="{preview}...")'
        )
