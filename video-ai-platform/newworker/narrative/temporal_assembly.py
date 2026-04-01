"""
TemporalAssembly — aggregates a list of FrameResults into temporal structure.

Detects:
  - Scene segments   : consecutive frames sharing the same scene_type
  - Object tracks    : persistent track_ids with first/last timestamp
  - Action timeline  : dominant action per scene segment
  - Audio summary    : all transcriptions + audio events across frames

This is CPU-only post-processing. It runs after all frames are processed
and before the Claude narrative call.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.frame_result import FrameResult


@dataclass
class SceneSegment:
    start_ts: float
    end_ts: float
    scene_type: str
    context_tags: List[str]
    dominant_stuff: List[str]          # top-3 environment labels
    dominant_action: Optional[str]
    frame_ids: List[int]


@dataclass
class ObjectTrack:
    track_id: int
    label: str
    first_ts: float
    last_ts: float
    frame_count: int
    depth_zones: List[str]             # zones seen across frames


@dataclass
class ActionSegment:
    start_ts: float
    end_ts: float
    action: str
    confidence: float


@dataclass
class TemporalAssembly:
    video_duration: float
    frame_count: int

    scenes: List[SceneSegment]
    object_tracks: List[ObjectTrack]
    action_timeline: List[ActionSegment]
    audio_summary: Dict[str, Any]      # transcriptions + events

    # ─────────────────────────────────────────────────────────────────
    #  Factory
    # ─────────────────────────────────────────────────────────────────

    @classmethod
    def from_frame_results(cls, results: List["FrameResult"]) -> "TemporalAssembly":
        """Build a TemporalAssembly from a list of FrameResults."""
        if not results:
            return cls(
                video_duration=0.0, frame_count=0,
                scenes=[], object_tracks=[], action_timeline=[],
                audio_summary={"transcriptions": [], "events": []},
            )

        results = sorted(results, key=lambda r: r.timestamp)
        duration = results[-1].timestamp

        scenes         = cls._build_scenes(results)
        object_tracks  = cls._build_tracks(results)
        action_timeline = cls._build_action_timeline(scenes, results)
        audio_summary  = cls._build_audio_summary(results)

        return cls(
            video_duration=duration,
            frame_count=len(results),
            scenes=scenes,
            object_tracks=object_tracks,
            action_timeline=action_timeline,
            audio_summary=audio_summary,
        )

    # ─────────────────────────────────────────────────────────────────
    #  Scene segmentation
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _build_scenes(results: List["FrameResult"]) -> List[SceneSegment]:
        """Group consecutive frames with the same scene_type into segments."""
        segments: List[SceneSegment] = []
        current: Optional[SceneSegment] = None

        for r in results:
            usr = r.usr
            scene_type = usr.scene_type
            stuff = [s["label"] for s in usr.panoptic.get("stuff", [])[:3]]
            action = usr.actions[0]["action"] if usr.actions else None
            tags = usr.context_tags

            if current is None or current.scene_type != scene_type:
                if current is not None:
                    current.end_ts = r.timestamp
                    segments.append(current)
                current = SceneSegment(
                    start_ts=r.timestamp,
                    end_ts=r.timestamp,
                    scene_type=scene_type,
                    context_tags=list(tags),
                    dominant_stuff=stuff,
                    dominant_action=action,
                    frame_ids=[r.frame_id],
                )
            else:
                current.end_ts = r.timestamp
                current.frame_ids.append(r.frame_id)
                # Refresh dominant action to latest
                if action:
                    current.dominant_action = action

        if current is not None:
            segments.append(current)

        return segments

    # ─────────────────────────────────────────────────────────────────
    #  Object tracking across frames
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _build_tracks(results: List["FrameResult"]) -> List[ObjectTrack]:
        """Aggregate per-frame tracker outputs into persistent tracks."""
        track_map: Dict[int, Dict] = {}

        for r in results:
            for obj in r.usr.objects:
                tid = obj.get("track_id")
                if tid is None:
                    continue
                if tid not in track_map:
                    track_map[tid] = {
                        "label": obj.get("label", "unknown"),
                        "first_ts": r.timestamp,
                        "last_ts": r.timestamp,
                        "frame_count": 0,
                        "depth_zones": [],
                    }
                entry = track_map[tid]
                entry["last_ts"] = r.timestamp
                entry["frame_count"] += 1
                zone = obj.get("depth_zone")
                if zone and zone not in entry["depth_zones"]:
                    entry["depth_zones"].append(zone)

        tracks = [
            ObjectTrack(
                track_id=tid,
                label=v["label"],
                first_ts=v["first_ts"],
                last_ts=v["last_ts"],
                frame_count=v["frame_count"],
                depth_zones=v["depth_zones"],
            )
            for tid, v in sorted(track_map.items())
        ]
        return tracks

    # ─────────────────────────────────────────────────────────────────
    #  Action timeline
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _build_action_timeline(
        scenes: List[SceneSegment],
        results: List["FrameResult"],
    ) -> List[ActionSegment]:
        """One ActionSegment per scene segment (dominant action)."""
        segments: List[ActionSegment] = []
        for scene in scenes:
            if not scene.dominant_action:
                continue
            # Find average confidence for this action in the scene frames
            confs = []
            for r in results:
                if r.frame_id in scene.frame_ids and r.usr.actions:
                    top = r.usr.actions[0]
                    if top["action"] == scene.dominant_action:
                        confs.append(top["confidence"])
            avg_conf = sum(confs) / len(confs) if confs else 0.5
            segments.append(ActionSegment(
                start_ts=scene.start_ts,
                end_ts=scene.end_ts,
                action=scene.dominant_action,
                confidence=round(avg_conf, 3),
            ))
        return segments

    # ─────────────────────────────────────────────────────────────────
    #  Audio summary
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _build_audio_summary(results: List["FrameResult"]) -> Dict[str, Any]:
        """Collect all transcription segments and unique audio events."""
        transcriptions = []
        event_counts: Dict[str, float] = {}

        for r in results:
            audio = r.usr.audio
            text = audio.get("transcription", "").strip()
            if text:
                transcriptions.append({"ts": r.timestamp, "text": text})
            for ev in audio.get("audio_events", []):
                name = ev.get("event", "")
                conf = ev.get("confidence", 0.0)
                if name:
                    event_counts[name] = max(event_counts.get(name, 0.0), conf)

        top_events = sorted(event_counts.items(), key=lambda x: -x[1])[:5]
        return {
            "transcriptions": transcriptions,
            "events": [{"event": e, "confidence": round(c, 3)} for e, c in top_events],
        }

    # ─────────────────────────────────────────────────────────────────
    #  Prompt-friendly summary string (used by NarrativeGenerator)
    # ─────────────────────────────────────────────────────────────────

    def to_prompt_summary(self) -> str:
        """Return a compact text summary for inclusion in the Claude prompt."""
        lines = []

        if self.object_tracks:
            lines.append("PERSISTENT OBJECTS:")
            for t in self.object_tracks:
                dur = round(t.last_ts - t.first_ts, 1)
                zones = "/".join(t.depth_zones) if t.depth_zones else "unknown depth"
                lines.append(
                    f"  - {t.label} (ID:{t.track_id}) "
                    f"seen {t.frame_count} frames, "
                    f"{t.first_ts:.1f}s–{t.last_ts:.1f}s ({dur}s), "
                    f"depth: {zones}"
                )

        if self.action_timeline:
            lines.append("ACTION TIMELINE:")
            for a in self.action_timeline:
                lines.append(
                    f"  - {a.start_ts:.1f}s–{a.end_ts:.1f}s: "
                    f"{a.action} ({a.confidence*100:.0f}%)"
                )

        audio = self.audio_summary
        if audio.get("transcriptions"):
            lines.append("SPEECH:")
            for seg in audio["transcriptions"]:
                lines.append(f"  - {seg['ts']:.1f}s: \"{seg['text']}\"")

        if audio.get("events"):
            ev_str = ", ".join(
                f"{e['event']} ({e['confidence']*100:.0f}%)"
                for e in audio["events"]
            )
            lines.append(f"AUDIO EVENTS: {ev_str}")

        return "\n".join(lines) if lines else "(no temporal data)"
