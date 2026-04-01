"""
Perception Layer - Modular AI Model Interfaces

All perception modules inherit from BasePerceptionModule and follow
a standardized input/output interface for seamless integration.

PHASE 1: SigLIPEncoder + infrastructure
PHASE 2: All remaining perception modules added
"""

from .base import BasePerceptionModule, PerceptionOutput
from .siglip_encoder import SigLIPEncoder
from .depth_estimator import DepthEstimator
from .panoptic_segmenter import PanopticSegmenter
from .scene_graph_generator import SceneGraphGenerator
from .action_recognizer import ActionRecognizer
from .tracker import ByteTracker
from .audio_processor import AudioProcessor

__all__ = [
    "BasePerceptionModule",
    "PerceptionOutput",
    "SigLIPEncoder",
    "DepthEstimator",
    "PanopticSegmenter",
    "SceneGraphGenerator",
    "ActionRecognizer",
    "ByteTracker",
    "AudioProcessor",
]