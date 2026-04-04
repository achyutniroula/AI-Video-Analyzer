"""
NarrativeResult — the final output of the narrative generation layer.

Holds the complete timestamp-based narrative text plus diagnostics.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class NarrativeResult:
    # ── content ───────────────────────────────────────────────────────
    narrative: str              # Full timestamp narrative from Claude
    video_duration: float       # seconds
    frame_count: int

    # ── diagnostics ───────────────────────────────────────────────────
    model: str
    input_tokens: int
    output_tokens: int
    processing_time: float      # seconds

    # ── optional summary ──────────────────────────────────────────────
    summary: str = ""           # 1-2 sentence executive summary

    # ── metadata ──────────────────────────────────────────────────────
    metadata: Dict[str, Any] = field(default_factory=dict)

    # ─────────────────────────────────────────────────────────────────
    #  Validation
    # ─────────────────────────────────────────────────────────────────

    def validate(self) -> List[str]:
        warnings = []
        if not self.narrative or len(self.narrative) < 50:
            warnings.append(f"narrative too short ({len(self.narrative)} chars)")
        if self.output_tokens == 0:
            warnings.append("output_tokens is 0")
        return warnings

    # ─────────────────────────────────────────────────────────────────
    #  Serialisation
    # ─────────────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def __repr__(self) -> str:
        preview = self.narrative[:100].replace("\n", " ")
        return (
            f"NarrativeResult("
            f"duration={self.video_duration:.1f}s, "
            f"frames={self.frame_count}, "
            f"tokens={self.output_tokens}, "
            f'narrative="{preview}...")'
        )
