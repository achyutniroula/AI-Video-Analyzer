"""
Pipeline Layer — end-to-end frame processing orchestrator.

Phase 4: Full pipeline processes 1 frame in <5s
"""

from .frame_pipeline import FramePipeline
from .frame_result import FrameResult

__all__ = [
    "FramePipeline",
    "FrameResult",
]
