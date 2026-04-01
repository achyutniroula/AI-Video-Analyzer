"""
MultiModalFusionEngine

Takes the raw PerceptionOutput objects from every perception module and
combines them into a single UnifiedSceneRepresentation per frame.

Responsibilities:
  1. Temporal alignment  — all outputs indexed by (frame_id, timestamp)
  2. Spatial alignment   — link tracked objects to depth zones and stuff labels
  3. Semantic enrichment — infer context_tags and scene_type
  4. VLM prompt building — format everything into a structured text prompt
                           ready for Qwen2-VL

CPU-only — no GPU operations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from perception.base import PerceptionOutput
from .unified_representation import UnifiedSceneRepresentation


# ─────────────────────────────────────────────────────────────────────────────
#  Scene type inference rules
#  Keys are substrings that can appear in panoptic "stuff" labels.
#  Evaluated in order; first match wins.
# ─────────────────────────────────────────────────────────────────────────────

_SCENE_RULES: List[tuple] = [
    # (stuff label substrings, scene_type, context_tags)
    (["tree", "grass", "dirt", "sand", "rock", "mountain"],    "nature",   ["outdoor", "nature"]),
    (["sea", "ocean", "river", "water", "lake", "waterfall"],  "water",    ["outdoor", "water"]),
    (["snow", "ice"],                                           "winter",   ["outdoor", "winter"]),
    (["sky"],                                                   "outdoor",  ["outdoor"]),
    (["road", "sidewalk", "pavement", "building", "wall"],     "urban",    ["outdoor", "urban"]),
    (["floor", "ceiling", "wall-brick", "wall-wood",
      "carpet", "rug", "furniture"],                           "indoor",   ["indoor"]),
    (["food", "dining table", "plate", "cup"],                 "kitchen",  ["indoor", "food"]),
    (["bed", "pillow", "blanket"],                             "bedroom",  ["indoor", "bedroom"]),
]

_DEFAULT_SCENE = "scene"
_DEFAULT_TAGS  = []


# ─────────────────────────────────────────────────────────────────────────────
#  Engine
# ─────────────────────────────────────────────────────────────────────────────

class MultiModalFusionEngine:
    """
    Combines per-module PerceptionOutputs into a UnifiedSceneRepresentation.

    Usage (single frame):
        engine = MultiModalFusionEngine()
        usr = engine.fuse(
            frame_id  = 5,
            timestamp = 2.0,
            siglip    = siglip_output,
            depth     = depth_output,
            panoptic  = panoptic_output,
            scene_graph = sg_output,
            tracker   = tracker_output,
            actions   = action_output,
            audio     = audio_output,
        )
        print(usr)

    All arguments except frame_id and timestamp are optional — the engine
    fills in sensible empty defaults so the pipeline can be tested
    incrementally as more modules become available.
    """

    def fuse(
        self,
        frame_id: int,
        timestamp: float,
        siglip:      Optional[PerceptionOutput] = None,
        depth:       Optional[PerceptionOutput] = None,
        panoptic:    Optional[PerceptionOutput] = None,
        scene_graph: Optional[PerceptionOutput] = None,
        tracker:     Optional[PerceptionOutput] = None,
        actions:     Optional[PerceptionOutput] = None,
        audio:       Optional[PerceptionOutput] = None,
    ) -> UnifiedSceneRepresentation:
        """
        Fuse all available perception outputs for one frame.

        Returns a validated UnifiedSceneRepresentation.
        """

        # ── 1. Extract per-module data ────────────────────────────────
        vision_embedding = self._get(siglip,      "vision_embedding", [0.0] * 768)
        depth_stats      = self._get_depth(depth)
        panoptic_data    = self._get_panoptic(panoptic)
        sg_data          = self._get_sg(scene_graph)
        tracker_data     = self._get_tracker(tracker)
        actions_data     = self._get_actions(actions)
        audio_data       = self._get_audio(audio)

        # ── 2. Spatial alignment: enrich tracked objects with depth ───
        objects = self._enrich_objects(tracker_data, depth_stats, panoptic_data)

        # ── 3. Flatten scene graph edges → spatial_relationships ──────
        spatial_rels = self._flatten_edges(sg_data.get("edges", []))

        # ── 4. Semantic enrichment ────────────────────────────────────
        stuff_labels = [s["label"] for s in panoptic_data.get("stuff", [])]
        thing_labels = [t["label"] for t in panoptic_data.get("things", [])]
        scene_type, context_tags = self._infer_scene(stuff_labels, thing_labels)

        # ── 5. Build VLM prompt ───────────────────────────────────────
        vlm_prompt = self._build_vlm_prompt(
            timestamp=timestamp,
            panoptic_data=panoptic_data,
            objects=objects,
            actions_data=actions_data,
            audio_data=audio_data,
            spatial_rels=spatial_rels,
            scene_type=scene_type,
            context_tags=context_tags,
            depth_stats=depth_stats,
        )

        # ── 6. Collect processing metadata ────────────────────────────
        metadata = self._collect_metadata(
            siglip, depth, panoptic, scene_graph, tracker, actions, audio
        )

        usr = UnifiedSceneRepresentation(
            frame_id=frame_id,
            timestamp=timestamp,
            vision_embedding=vision_embedding,
            depth_stats=depth_stats,
            panoptic=panoptic_data,
            objects=objects,
            scene_graph=sg_data,
            actions=actions_data,
            audio=audio_data,
            spatial_relationships=spatial_rels,
            context_tags=context_tags,
            scene_type=scene_type,
            vlm_prompt=vlm_prompt,
            processing_metadata=metadata,
        )

        return usr

    # ─────────────────────────────────────────────────────────────────
    #  Per-module extractors
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _get(output: Optional[PerceptionOutput], key: str, default: Any) -> Any:
        if output is None:
            return default
        return output.data.get(key, default)

    @staticmethod
    def _get_depth(output: Optional[PerceptionOutput]) -> Dict[str, Any]:
        if output is None:
            return {
                "depth_stats": {},
                "depth_distribution": {"near_pct": 0, "mid_pct": 0, "far_pct": 0},
                "dominant_zone": "unknown",
            }
        return output.data

    @staticmethod
    def _get_panoptic(output: Optional[PerceptionOutput]) -> Dict[str, Any]:
        if output is None:
            return {"things": [], "stuff": [], "num_things": 0, "num_stuff": 0}
        return output.data

    @staticmethod
    def _get_sg(output: Optional[PerceptionOutput]) -> Dict[str, Any]:
        if output is None:
            return {"nodes": [], "edges": [], "num_nodes": 0, "num_edges": 0}
        return output.data

    @staticmethod
    def _get_tracker(output: Optional[PerceptionOutput]) -> Dict[str, Any]:
        if output is None:
            return {"tracks": [], "num_tracks": 0}
        return output.data

    @staticmethod
    def _get_actions(output: Optional[PerceptionOutput]) -> List[Dict[str, Any]]:
        if output is None:
            return []
        return output.data.get("actions", [])

    @staticmethod
    def _get_audio(output: Optional[PerceptionOutput]) -> Dict[str, Any]:
        if output is None:
            return {"transcription": "", "audio_events": [], "has_speech": False}
        return output.data

    # ─────────────────────────────────────────────────────────────────
    #  Spatial alignment: enrich track objects with depth zone
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _enrich_objects(
        tracker_data: Dict,
        depth_stats: Dict,
        panoptic_data: Dict,
    ) -> List[Dict[str, Any]]:
        """
        Return one dict per tracked object, augmented with a depth_zone
        annotation based on bbox vertical position heuristic.
        """
        tracks = tracker_data.get("tracks", [])
        dominant_zone = depth_stats.get("dominant_zone", "unknown")
        image_h = panoptic_data.get("image_size", [360, 640])[0]

        objects = []
        for t in tracks:
            bbox = t.get("bbox", [0, 0, 0, 0])
            cy = (bbox[1] + bbox[3]) / 2.0
            # Objects lower in frame tend to be closer in natural scenes
            rel_y = cy / max(image_h, 1)
            if rel_y > 0.66:
                zone = "near"
            elif rel_y > 0.33:
                zone = "mid"
            else:
                zone = "far"

            objects.append(
                {
                    "track_id": t["track_id"],
                    "label": t["label"],
                    "bbox": bbox,
                    "depth_zone": zone,
                    "score": t.get("score", 0.0),
                }
            )
        return objects

    # ─────────────────────────────────────────────────────────────────
    #  Flatten scene-graph edges into spatial_relationships
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _flatten_edges(edges: List[Dict]) -> List[Dict[str, Any]]:
        return [
            {
                "subject": e.get("subject_label", "?"),
                "predicate": e.get("predicate", "?"),
                "object": e.get("object_label", "?"),
            }
            for e in edges
        ]

    # ─────────────────────────────────────────────────────────────────
    #  Scene type + context tag inference
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _infer_scene(
        stuff_labels: List[str],
        thing_labels: List[str],
    ) -> tuple:
        combined = " ".join(stuff_labels + thing_labels).lower()

        for keywords, scene_type, base_tags in _SCENE_RULES:
            if any(kw in combined for kw in keywords):
                tags = list(base_tags)
                # Additional crowd tag
                people_count = sum(1 for l in thing_labels if "person" in l.lower())
                if people_count >= 3:
                    tags.append("crowd")
                elif people_count == 1:
                    tags.append("person_present")
                return scene_type, tags

        # No rule matched
        tags = []
        if any("person" in l.lower() for l in thing_labels):
            tags.append("person_present")
        return _DEFAULT_SCENE, tags

    # ─────────────────────────────────────────────────────────────────
    #  VLM prompt builder
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _build_vlm_prompt(
        timestamp: float,
        panoptic_data: Dict,
        objects: List[Dict],
        actions_data: List[Dict],
        audio_data: Dict,
        spatial_rels: List[Dict],
        scene_type: str,
        context_tags: List[str],
        depth_stats: Dict,
    ) -> str:
        lines: List[str] = []

        lines.append(f"[Frame at {timestamp:.2f}s]")
        lines.append(f"Scene Type: {scene_type}")

        if context_tags:
            lines.append(f"Context: {', '.join(context_tags)}")

        # Objects / tracks
        if objects:
            obj_strs = [
                f"{o['label']} (ID:{o['track_id']}, depth:{o['depth_zone']})"
                for o in objects
            ]
            lines.append(f"Objects: {'; '.join(obj_strs)}")
        elif panoptic_data.get("things"):
            thing_strs = [
                f"{t['label']} ({t['coverage']*100:.0f}%)"
                for t in panoptic_data["things"][:5]
            ]
            lines.append(f"Things: {', '.join(thing_strs)}")

        # Environment (stuff labels, top-5 by coverage)
        stuff = panoptic_data.get("stuff", [])
        if stuff:
            env_strs = [
                f"{s['label']} ({s['coverage']*100:.0f}%)"
                for s in stuff[:5]
            ]
            lines.append(f"Environment: {', '.join(env_strs)}")

        # Depth
        dist = depth_stats.get("depth_distribution", {})
        if dist:
            lines.append(
                f"Depth: near={dist.get('near_pct',0)*100:.0f}%  "
                f"mid={dist.get('mid_pct',0)*100:.0f}%  "
                f"far={dist.get('far_pct',0)*100:.0f}%"
            )

        # Actions
        if actions_data:
            act_strs = [
                f"{a['action']} ({a['confidence']*100:.0f}%)"
                for a in actions_data[:3]
            ]
            lines.append(f"Actions: {', '.join(act_strs)}")

        # Spatial relationships (top-5)
        if spatial_rels:
            rel_strs = [
                f"{r['subject']} {r['predicate']} {r['object']}"
                for r in spatial_rels[:5]
            ]
            lines.append(f"Relationships: {'; '.join(rel_strs)}")

        # Audio
        transcription = audio_data.get("transcription", "")
        audio_events  = audio_data.get("audio_events", [])
        if transcription:
            lines.append(f'Speech: "{transcription}"')
        if audio_events:
            ev_strs = [
                f"{e['event']} ({e.get('confidence',0)*100:.0f}%)"
                for e in audio_events[:3]
            ]
            lines.append(f"Audio: {', '.join(ev_strs)}")

        lines.append(
            "\nDescribe this scene in detail, noting what is happening, "
            "who or what is present, their spatial arrangement, and the "
            "overall atmosphere."
        )

        return "\n".join(lines)

    # ─────────────────────────────────────────────────────────────────
    #  Metadata collector
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _collect_metadata(*outputs: Optional[PerceptionOutput]) -> Dict[str, Any]:
        meta: Dict[str, Any] = {}
        for o in outputs:
            if o is not None:
                meta[o.module_name] = {
                    "processing_time_s": round(o.processing_time, 4),
                    "gpu_memory_gb": o.gpu_memory_used,
                }
        return meta
