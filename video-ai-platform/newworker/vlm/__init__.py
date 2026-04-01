"""
VLM Layer — Qwen2-VL-7B unified reasoning brain.

Phase 3: Qwen2-VL generates coherent captions from UnifiedSceneRepresentation.
"""

from .qwen2_vl import Qwen2VLCaptioner
from .vlm_caption import VLMCaption

__all__ = [
    "Qwen2VLCaptioner",
    "VLMCaption",
]
