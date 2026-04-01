"""
UnifiedSceneRepresentation — the canonical output of the Fusion Layer.

Every frame processed by the perception pipeline produces one
UnifiedSceneRepresentation that is then handed to the VLM (Qwen2-VL)
and finally to Claude for narrative generation.

Schema mirrors the architecture diagram in infra/:
  vision_embedding    : 768-dim SigLIP vector
  depth_stats         : DepthAnything V2 statistics
  panoptic            : Mask2Former things + stuff
  objects             : tracked objects (ByteTrack IDs)
  scene_graph         : nodes + edges
  actions             : SlowFast top-5 actions
  audio               : Whisper transcription + PANNs events
  spatial_relationships : flattened scene-graph edge list
  context_tags        : inferred semantic tags (outdoor, nature, …)
  scene_type          : coarse scene category (forest, urban, indoor, …)
  vlm_prompt          : pre-formatted text prompt for Qwen2-VL
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class UnifiedSceneRepresentation:
    # ── identity ──────────────────────────────────────────────────────
    frame_id: int
    timestamp: float                  # seconds from video start

    # ── perception outputs ────────────────────────────────────────────
    vision_embedding: List[float]     # (768,) from SigLIP
    depth_stats: Dict[str, Any]       # from DepthAnything V2
    panoptic: Dict[str, Any]          # {"things": [...], "stuff": [...]}
    objects: List[Dict[str, Any]]     # tracked things with track_id
    scene_graph: Dict[str, Any]       # {"nodes": [...], "edges": [...]}
    actions: List[Dict[str, Any]]     # [{"action": str, "confidence": float}]
    audio: Dict[str, Any]             # {"transcription": str, "audio_events": [...]}

    # ── fusion-derived ────────────────────────────────────────────────
    spatial_relationships: List[Dict[str, Any]]   # flattened edge list
    context_tags: List[str]                        # e.g. ["outdoor", "nature"]
    scene_type: str                                # e.g. "forest"

    # ── VLM interface ─────────────────────────────────────────────────
    vlm_prompt: str                   # structured text prompt for Qwen2-VL

    # ── diagnostics ───────────────────────────────────────────────────
    processing_metadata: Dict[str, Any] = field(default_factory=dict)

    # ─────────────────────────────────────────────────────────────────
    #  Serialisation helpers
    # ─────────────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """Return a fully JSON-serialisable dictionary (vision_embedding omitted)."""
        d = asdict(self)
        # Vision embedding is large — keep it but callers can strip it if needed
        return d

    def to_dict_no_embedding(self) -> Dict[str, Any]:
        """Like to_dict but drops vision_embedding (saves bandwidth for logging)."""
        d = self.to_dict()
        d.pop("vision_embedding", None)
        return d

    def to_json(self, indent: int = 2, include_embedding: bool = False) -> str:
        d = self.to_dict() if include_embedding else self.to_dict_no_embedding()
        return json.dumps(d, indent=indent)

    # ─────────────────────────────────────────────────────────────────
    #  Validation
    # ─────────────────────────────────────────────────────────────────

    def validate(self) -> List[str]:
        """
        Check that required fields are populated.

        Returns a list of warning strings (empty = all good).
        """
        warnings = []
        if len(self.vision_embedding) != 768:
            warnings.append(
                f"vision_embedding has {len(self.vision_embedding)} dims, expected 768"
            )
        if not self.panoptic.get("things") and not self.panoptic.get("stuff"):
            warnings.append("panoptic is empty (no things or stuff detected)")
        if not self.scene_type:
            warnings.append("scene_type is empty")
        if not self.vlm_prompt:
            warnings.append("vlm_prompt is empty")
        return warnings

    def __repr__(self) -> str:
        n_things = len(self.panoptic.get("things", []))
        n_stuff  = len(self.panoptic.get("stuff",  []))
        n_tracks = len(self.objects)
        top_action = (
            self.actions[0]["action"] if self.actions else "none"
        )
        return (
            f"UnifiedSceneRepresentation("
            f"frame={self.frame_id}, t={self.timestamp:.2f}s, "
            f"scene={self.scene_type!r}, "
            f"things={n_things}, stuff={n_stuff}, tracks={n_tracks}, "
            f"top_action={top_action!r}, "
            f"tags={self.context_tags})"
        )
