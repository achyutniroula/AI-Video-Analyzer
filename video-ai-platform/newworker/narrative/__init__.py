"""
Narrative Layer — Claude API timestamp narrative generation.

Phase 5: Claude generates natural timestamp narrative.
"""

from .narrative_generator import NarrativeGenerator
from .narrative_result import NarrativeResult
from .temporal_assembly import TemporalAssembly

__all__ = [
    "NarrativeGenerator",
    "NarrativeResult",
    "TemporalAssembly",
]
