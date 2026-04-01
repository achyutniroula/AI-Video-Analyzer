"""
Scene Graph Generator (CPU, Heuristic)

Builds a scene graph from panoptic "things" by computing spatial
relationships between every pair of detected objects.

Runs on CPU only — no model loading needed.

Relationships detected:
  - Positional : above, below, left_of, right_of
  - Proximity  : near  (IoU > threshold)
  - Size       : larger_than, smaller_than  (area ratio > 2×)
  - Containment: contains, inside

Output: nodes[] + edges[]
VRAM: 0 MB
Time: ~0.01s per frame
"""

import time
from typing import Any, Dict, List, Optional

import torch

from .base import BasePerceptionModule, PerceptionOutput


class SceneGraphGenerator(BasePerceptionModule):
    """
    CPU heuristic scene graph builder.

    Accepts panoptic things[] via the `panoptic_things` kwarg in __call__.
    The frame tensor is accepted but not used — it exists to satisfy the
    BasePerceptionModule interface.

    Example:
        gen = SceneGraphGenerator()
        gen.load_model()
        output = gen(frame, frame_id=0, timestamp=0.0, panoptic_things=things)
        nodes = output.data["nodes"]
        edges = output.data["edges"]
        gen.unload()
    """

    # Minimum center-distance (pixels) to assign a directional relation.
    # Avoids labelling nearly-overlapping objects as "above/below".
    _MIN_DIRECTIONAL_PX = 20

    def __init__(self, proximity_iou_threshold: float = 0.15, **kwargs):
        kwargs["device"] = "cpu"   # Always CPU
        super().__init__(**kwargs)
        self.proximity_iou_threshold = proximity_iou_threshold

    # ------------------------------------------------------------------ #
    #  BasePerceptionModule abstract methods (not used directly)           #
    # ------------------------------------------------------------------ #

    def load_model(self):
        self.model = True   # sentinel so is_loaded() returns True
        print("✓ Scene Graph Generator initialized (CPU heuristic, no model)")

    def preprocess(self, frame: Any) -> Any:
        return frame

    def inference(self, preprocessed: Any) -> Dict[str, Any]:
        return {}

    def postprocess(self, raw_output: Dict[str, Any]) -> Dict[str, Any]:
        return {}

    # ------------------------------------------------------------------ #
    #  Override __call__ to consume panoptic_things kwarg                  #
    # ------------------------------------------------------------------ #

    def __call__(
        self,
        frame: Any,
        frame_id: int,
        timestamp: float,
        panoptic_things: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> PerceptionOutput:
        start_time = time.time()

        things = panoptic_things or []
        nodes = self._build_nodes(things)
        edges = self._build_edges(things)

        return PerceptionOutput(
            module_name=self.name,
            timestamp=timestamp,
            frame_id=frame_id,
            data={
                "nodes": nodes,
                "edges": edges,
                "num_nodes": len(nodes),
                "num_edges": len(edges),
            },
            metadata={"device": "cpu", "quantized": False},
            processing_time=time.time() - start_time,
            gpu_memory_used=None,
        )

    def unload(self):
        self.model = None

    # ------------------------------------------------------------------ #
    #  Graph construction helpers                                          #
    # ------------------------------------------------------------------ #

    def _build_nodes(self, things: List[Dict]) -> List[Dict]:
        nodes = []
        for t in things:
            bbox = t.get("bbox", [0, 0, 0, 0])
            cx = (bbox[0] + bbox[2]) / 2.0
            cy = (bbox[1] + bbox[3]) / 2.0
            area = max(0, (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]))
            nodes.append(
                {
                    "id": t["id"],
                    "label": t["label"],
                    "bbox": bbox,
                    "center": [round(cx, 1), round(cy, 1)],
                    "area": round(area, 1),
                    "coverage": t.get("coverage", 0.0),
                }
            )
        return nodes

    def _build_edges(self, things: List[Dict]) -> List[Dict]:
        edges = []
        n = len(things)
        for i in range(n):
            for j in range(i + 1, n):
                a, b = things[i], things[j]
                for rel in self._get_relations(a, b):
                    edges.append(
                        {
                            "subject_id": a["id"],
                            "subject_label": a["label"],
                            "predicate": rel,
                            "object_id": b["id"],
                            "object_label": b["label"],
                        }
                    )
        return edges

    def _get_relations(self, a: Dict, b: Dict) -> List[str]:
        relations: List[str] = []
        ba = a.get("bbox", [0, 0, 0, 0])
        bb = b.get("bbox", [0, 0, 0, 0])

        cx_a = (ba[0] + ba[2]) / 2.0
        cy_a = (ba[1] + ba[3]) / 2.0
        cx_b = (bb[0] + bb[2]) / 2.0
        cy_b = (bb[1] + bb[3]) / 2.0

        dy = cy_b - cy_a
        dx = cx_b - cx_a

        # Positional: prefer the dominant axis
        if abs(dy) >= self._MIN_DIRECTIONAL_PX:
            relations.append("above" if dy > 0 else "below")
        if abs(dx) >= self._MIN_DIRECTIONAL_PX:
            relations.append("left_of" if dx > 0 else "right_of")

        # Proximity
        if self._iou(ba, bb) >= self.proximity_iou_threshold:
            relations.append("near")

        # Size
        area_a = max(1, (ba[2] - ba[0]) * (ba[3] - ba[1]))
        area_b = max(1, (bb[2] - bb[0]) * (bb[3] - bb[1]))
        if area_a >= area_b * 2:
            relations.append("larger_than")
        elif area_b >= area_a * 2:
            relations.append("smaller_than")

        # Containment
        if self._contains(ba, bb):
            relations.append("contains")
        elif self._contains(bb, ba):
            relations.append("inside")

        return relations

    @staticmethod
    def _iou(ba: List[int], bb: List[int]) -> float:
        x1 = max(ba[0], bb[0])
        y1 = max(ba[1], bb[1])
        x2 = min(ba[2], bb[2])
        y2 = min(ba[3], bb[3])
        if x2 <= x1 or y2 <= y1:
            return 0.0
        inter = (x2 - x1) * (y2 - y1)
        area_a = max(0, (ba[2] - ba[0])) * max(0, (ba[3] - ba[1]))
        area_b = max(0, (bb[2] - bb[0])) * max(0, (bb[3] - bb[1]))
        union = area_a + area_b - inter
        return inter / (union + 1e-8)

    @staticmethod
    def _contains(outer: List[int], inner: List[int]) -> bool:
        return (
            outer[0] <= inner[0]
            and outer[1] <= inner[1]
            and outer[2] >= inner[2]
            and outer[3] >= inner[3]
        )
