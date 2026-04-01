"""
Fusion Layer — combines perception outputs into UnifiedSceneRepresentation.

Phase 2: Fusion produces valid UnifiedSceneRepresentation
"""

from .fusion_engine import MultiModalFusionEngine
from .unified_representation import UnifiedSceneRepresentation

__all__ = [
    "MultiModalFusionEngine",
    "UnifiedSceneRepresentation",
]
