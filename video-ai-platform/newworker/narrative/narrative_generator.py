"""
NarrativeGenerator — calls Claude API to produce a timestamp narrative.

Takes a list of FrameResults + a TemporalAssembly and generates a
flowing, human-like narrative with timestamps — the final output of
the entire newworker pipeline.

Model   : claude-sonnet-4-6  (default; can override to opus-4-6)
Tokens  : up to 1024 output tokens
API key : ANTHROPIC_API_KEY environment variable

The prompt is structured in three parts:
  1. Video overview  (duration, scene type, context)
  2. Frame analyses  (one block per frame: VLM caption + objects + actions + audio)
  3. Temporal summary (persistent tracks, action timeline, audio events)
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from dotenv import load_dotenv
load_dotenv()

if TYPE_CHECKING:
    from pipeline.frame_result import FrameResult

from .narrative_result import NarrativeResult
from .temporal_assembly import TemporalAssembly


_DEFAULT_MODEL = "claude-sonnet-4-6"
_MAX_TOKENS    = 1024

_SYSTEM_PROMPT = """\
You are an expert video analyst generating timestamp-based narratives.
You will receive structured analysis data from a computer vision pipeline \
that processed a video frame-by-frame.

Your task: write a flowing, human-like narrative that describes what happens \
in the video, organized by time. Use this format for each segment:

  [Xs–Ys]: Description of what happens during this time range.

Rules:
- Group related frames into natural time segments (don't write one line per frame).
- Use concrete, vivid language — describe what is actually happening, not just what was detected.
- Mention specific objects, actions, spatial relationships, and atmosphere.
- If audio events or speech are present, weave them into the narrative naturally.
- End with a brief "Throughout:" sentence describing any constant elements.
- Be concise but informative. Target 200–400 words.
"""


class NarrativeGenerator:
    """
    Calls the Claude API to generate a timestamp narrative for a video.

    Usage:
        gen = NarrativeGenerator()                  # uses ANTHROPIC_API_KEY
        result = gen.generate(frame_results)
        print(result.narrative)

    With explicit API key:
        gen = NarrativeGenerator(api_key="sk-ant-...")
        result = gen.generate(frame_results)
    """

    def __init__(
        self,
        model: str = _DEFAULT_MODEL,
        max_tokens: int = _MAX_TOKENS,
        api_key: Optional[str] = None,
    ):
        self.model = model
        self.max_tokens = max_tokens
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")

    # ─────────────────────────────────────────────────────────────────
    #  Main entry point
    # ─────────────────────────────────────────────────────────────────

    def generate(
        self,
        frame_results: List["FrameResult"],
        temporal_assembly: Optional[TemporalAssembly] = None,
    ) -> NarrativeResult:
        """
        Generate a timestamp narrative from frame results.

        Args:
            frame_results      : Ordered list of FrameResult objects.
            temporal_assembly  : Pre-built assembly; built automatically if None.

        Returns:
            NarrativeResult with narrative text and token diagnostics.
        """
        if not frame_results:
            raise ValueError("frame_results must not be empty")

        if not self._api_key:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY is not set. "
                "Export it or pass api_key= to NarrativeGenerator."
            )

        assembly = temporal_assembly or TemporalAssembly.from_frame_results(frame_results)
        prompt   = self._build_prompt(frame_results, assembly)

        t0 = time.time()
        narrative_text, in_tok, out_tok = self._call_claude(prompt)
        elapsed = time.time() - t0

        return NarrativeResult(
            narrative=narrative_text,
            video_duration=assembly.video_duration,
            frame_count=assembly.frame_count,
            model=self.model,
            input_tokens=in_tok,
            output_tokens=out_tok,
            processing_time=round(elapsed, 3),
            metadata={
                "max_tokens": self.max_tokens,
                "num_scenes": len(assembly.scenes),
                "num_tracks": len(assembly.object_tracks),
            },
        )

    # ─────────────────────────────────────────────────────────────────
    #  Prompt construction
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _build_prompt(
        results: List["FrameResult"],
        assembly: TemporalAssembly,
    ) -> str:
        results = sorted(results, key=lambda r: r.timestamp)
        duration = assembly.video_duration

        # ── Video overview ────────────────────────────────────────────
        scene_types = list(dict.fromkeys(s.scene_type for s in assembly.scenes))
        lines = [
            f"VIDEO OVERVIEW",
            f"  Duration : {duration:.1f}s",
            f"  Frames   : {len(results)} key frames analyzed",
            f"  Scenes   : {', '.join(scene_types) if scene_types else 'unknown'}",
            "",
        ]

        # ── Per-frame analysis ────────────────────────────────────────
        lines.append("FRAME-BY-FRAME ANALYSIS")
        for r in results:
            usr = r.usr
            caption = r.caption.caption

            # Objects (track_id + label)
            objs = usr.objects
            if objs:
                obj_str = "; ".join(
                    f"{o['label']} (ID:{o['track_id']}, {o['depth_zone']})"
                    for o in objs[:4]
                )
            else:
                thing_str = ", ".join(
                    t["label"] for t in usr.panoptic.get("things", [])[:4]
                )
                obj_str = thing_str or "none detected"

            # Environment (top-3 stuff labels)
            stuff = usr.panoptic.get("stuff", [])
            env_str = ", ".join(
                f"{s['label']} ({s['coverage']*100:.0f}%)"
                for s in stuff[:3]
            ) if stuff else "n/a"

            # Actions (top-2)
            acts = usr.actions[:2]
            act_str = ", ".join(
                f"{a['action']} ({a['confidence']*100:.0f}%)"
                for a in acts
            ) if acts else "n/a"

            # Audio
            audio = usr.audio
            speech = f'"{audio["transcription"]}"' if audio.get("transcription") else ""
            ev_str = ", ".join(
                e["event"] for e in audio.get("audio_events", [])[:2]
            )
            audio_str = " | ".join(filter(None, [speech, ev_str])) or "none"

            lines += [
                f"\n[{r.timestamp:.1f}s — Frame {r.frame_id}]",
                f"  VLM Caption : {caption}",
                f"  Objects     : {obj_str}",
                f"  Environment : {env_str}",
                f"  Actions     : {act_str}",
                f"  Audio       : {audio_str}",
            ]

        # ── Temporal summary ──────────────────────────────────────────
        temporal_text = assembly.to_prompt_summary()
        if temporal_text != "(no temporal data)":
            lines += ["", temporal_text]

        lines += [
            "",
            "─" * 60,
            "Now write the timestamp narrative for this video.",
        ]

        return "\n".join(lines)

    # ─────────────────────────────────────────────────────────────────
    #  Claude API call
    # ─────────────────────────────────────────────────────────────────

    def _call_claude(self, prompt: str):
        """Call Claude API and return (narrative_text, input_tokens, output_tokens)."""
        import anthropic

        client = anthropic.Anthropic(api_key=self._api_key)
        response = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        narrative = response.content[0].text.strip()
        in_tok    = response.usage.input_tokens
        out_tok   = response.usage.output_tokens
        return narrative, in_tok, out_tok
