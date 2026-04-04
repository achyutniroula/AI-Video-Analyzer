"""
Audio Processor — Three-part audio intelligence pipeline

  Part 1 · Speech  : faster-whisper large-v3 (CTranslate2 backend)
                     High-accuracy transcription with per-segment confidence.
                     Uses float16 on CUDA (~6 GB VRAM) or int8 (~2.5 GB).
                     Set whisper_compute_type="int8" if VRAM is tight.

  Part 2 · Sounds  : LAION CLAP (laion/clap-htsat-unfused)
                     Uses HTS-AT as audio encoder for zero-shot event
                     classification across 28 curated sound categories.
                     (~1.5 GB VRAM in float16)

  Part 3 · Fusion  : Per-segment dominant-type decision combining speech
                     confidence and detected sound events.

Music identification (Chromaprint + AcoustID) is handled by
perception/music_identifier.py which operates on the full audio file.
This module handles only per-frame audio segments.

Input  (via audio_waveform kwarg): numpy (N,) float32, mono, 16 kHz
Output per frame:
  transcription       : str
  speech_confidence   : float 0-1   (1 - no_speech_prob from Whisper)
  has_speech          : bool
  audio_events        : [{"event": str, "confidence": float}, ...]  top-5
  dominant_type       : "speech" | "music" | "environment" | "silent"
"""

from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch

from .base import BasePerceptionModule, PerceptionOutput

# ── HTS-AT / CLAP sound categories ──────────────────────────────────────────
# These become text prompts for zero-shot classification.
# Ordered from most to least common in real-world video content.
_HTSAT_CATEGORIES: List[str] = [
    "speech",
    "music",
    "singing voice",
    "laughter",
    "applause",
    "crowd noise",
    "dog barking",
    "cat meowing",
    "bird chirping",
    "rain",
    "wind",
    "thunder",
    "water flowing or splashing",
    "fire crackling",
    "traffic noise",
    "car engine running",
    "siren",
    "footsteps",
    "door closing",
    "keyboard typing",
    "gunshot",
    "explosion",
    "television audio",
    "telephone ringing",
    "rustling leaves",
    "construction noise",
    "crowd cheering",
    "baby crying",
]

# Minimum cosine similarity score to include a category in the output
_HTSAT_THRESHOLD = 0.20

# Categories that are treated as "music" signal for dominant_type fusion
_MUSIC_LABELS = {"music", "singing voice"}

# CLAP model — uses HTS-AT as audio encoder, RoBERTa as text encoder
_CLAP_MODEL_ID = "laion/clap-htsat-unfused"

_WHISPER_SAMPLE_RATE = 16_000
_CLAP_SAMPLE_RATE = 48_000


class AudioProcessor(BasePerceptionModule):
    """
    Three-part per-frame audio processor (Whisper large-v3 + HTS-AT via CLAP).

    The two models are loaded once at startup and kept in memory for
    the full video run. Call unload() when done to free VRAM.

    Args:
        whisper_model      : Whisper model size (default "large-v3")
        whisper_compute_type: "float16" (default) or "int8" (saves ~3 GB VRAM)
        use_htsat          : Whether to run CLAP/HTS-AT for event classification
    """

    def __init__(
        self,
        whisper_model: str = "large-v3",
        whisper_compute_type: str = "float16",
        use_htsat: bool = True,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.whisper_model_name = whisper_model
        self.whisper_compute_type = whisper_compute_type
        self.use_htsat = use_htsat

        self._whisper = None
        self._clap_model = None
        self._clap_processor = None
        self._text_embeddings: Optional[torch.Tensor] = None  # precomputed

    # ── Model lifecycle ───────────────────────────────────────────────────────

    def load_model(self):
        self._load_whisper()
        if self.use_htsat:
            self._load_htsat()
        self.model = self._whisper  # satisfies BasePerceptionModule.is_loaded()

    def _load_whisper(self):
        print(f"Loading faster-whisper {self.whisper_model_name} "
              f"({self.whisper_compute_type})...")
        try:
            from faster_whisper import WhisperModel
            device = "cuda" if self.device == "cuda" else "cpu"
            self._whisper = WhisperModel(
                self.whisper_model_name,
                device=device,
                compute_type=self.whisper_compute_type,
            )
            print(f"✓ faster-whisper {self.whisper_model_name} loaded on {device}")
        except ImportError:
            print("⚠  faster-whisper not installed — falling back to openai-whisper")
            import whisper
            self._whisper = whisper.load_model(
                self.whisper_model_name, device=self.device
            )
            self._whisper_fallback = True
            print(f"✓ openai-whisper {self.whisper_model_name} loaded (fallback)")

    def _load_htsat(self):
        print("Loading CLAP / HTS-AT audio encoder...")
        try:
            from transformers import ClapModel, ClapProcessor as _ClapProc
            self._clap_processor = _ClapProc.from_pretrained(_CLAP_MODEL_ID)
            self._clap_model = ClapModel.from_pretrained(
                _CLAP_MODEL_ID,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            ).to(self.device).eval()

            # Precompute text embeddings for all categories (do this once)
            self._text_embeddings = self._compute_text_embeddings()
            print(f"✓ CLAP / HTS-AT loaded on {self.device} "
                  f"({len(_HTSAT_CATEGORIES)} sound categories)")
        except Exception as e:
            print(f"⚠  CLAP / HTS-AT not available ({e}) — sound classification disabled")
            self._clap_model = None
            self._clap_processor = None

    def _compute_text_embeddings(self) -> Optional[torch.Tensor]:
        """Precompute and normalise text embeddings for all sound categories."""
        if self._clap_model is None or self._clap_processor is None:
            return None
        try:
            text_inputs = self._clap_processor(
                text=_HTSAT_CATEGORIES,
                return_tensors="pt",
                padding=True,
            )
            text_inputs = {k: v.to(self.device) for k, v in text_inputs.items()}
            with torch.no_grad():
                embeds = self._clap_model.get_text_features(**text_inputs)
            # L2-normalise for cosine similarity
            return torch.nn.functional.normalize(embeds, p=2, dim=-1)
        except Exception as e:
            print(f"⚠  Text embedding precomputation failed: {e}")
            return None

    def unload(self):
        if self._whisper is not None:
            del self._whisper
            self._whisper = None
        if self._clap_model is not None:
            del self._clap_model
            self._clap_model = None
        if self._clap_processor is not None:
            del self._clap_processor
            self._clap_processor = None
        self._text_embeddings = None
        self.model = None
        if self.device == "cuda":
            import gc
            torch.cuda.empty_cache()
            gc.collect()

    # ── Public call interface ─────────────────────────────────────────────────

    def __call__(
        self,
        frame: Any,
        frame_id: int,
        timestamp: float,
        audio_waveform: Optional[np.ndarray] = None,
        **kwargs,
    ) -> PerceptionOutput:
        t0 = time.time()
        if self.device == "cuda":
            torch.cuda.reset_peak_memory_stats()

        if audio_waveform is None:
            data = {
                "transcription": "",
                "speech_confidence": 0.0,
                "has_speech": False,
                "audio_events": [],
                "dominant_type": "silent",
                "note": "no audio segment provided",
            }
        else:
            data = self._process_audio(audio_waveform)

        gpu_mem = None
        if self.device == "cuda":
            gpu_mem = torch.cuda.max_memory_allocated() / 1e9

        return PerceptionOutput(
            module_name=self.name,
            timestamp=timestamp,
            frame_id=frame_id,
            data=data,
            metadata={
                "device": self.device,
                "quantized": self.quantize,
                "whisper_model": self.whisper_model_name,
                "whisper_compute_type": self.whisper_compute_type,
                "htsat_available": self._clap_model is not None,
            },
            processing_time=time.time() - t0,
            gpu_memory_used=gpu_mem,
        )

    # ── Core processing ───────────────────────────────────────────────────────

    def _process_audio(self, waveform: np.ndarray) -> Dict[str, Any]:
        # Ensure float32 mono 16kHz
        if waveform.dtype != np.float32:
            waveform = waveform.astype(np.float32)
        if waveform.ndim > 1:
            waveform = waveform.mean(axis=-1)

        transcription, speech_confidence = self._run_whisper(waveform)
        has_speech = bool(transcription)

        audio_events = self._run_htsat(waveform)

        dominant_type = self._fuse_per_frame(
            transcription, speech_confidence, audio_events
        )

        return {
            "transcription": transcription,
            "speech_confidence": round(speech_confidence, 4),
            "has_speech": has_speech,
            "audio_events": audio_events,
            "dominant_type": dominant_type,
        }

    # ── Whisper ───────────────────────────────────────────────────────────────

    def _run_whisper(self, waveform: np.ndarray) -> Tuple[str, float]:
        """Return (transcription_text, speech_confidence)."""
        try:
            if not getattr(self, '_whisper_fallback', False):
                # faster-whisper: transcribe() returns (generator, TranscriptionInfo)
                segments_gen, info = self._whisper.transcribe(
                    waveform,
                    beam_size=5,
                    language=None,      # auto-detect
                    vad_filter=True,    # skip silent regions
                    vad_parameters=dict(min_silence_duration_ms=500),
                )
                # Consume the generator — segments are lazy in faster-whisper
                texts = [seg.text.strip() for seg in segments_gen if seg.text.strip()]
                transcription = " ".join(texts)
                # info.language_probability: confidence that detected language is correct
                # Use it as a proxy for speech presence confidence
                speech_conf = round(float(info.language_probability), 4) if transcription else 0.0
                return transcription, speech_conf
            else:
                # openai-whisper fallback
                result = self._whisper.transcribe(
                    waveform, fp16=(self.device == "cuda")
                )
                text = result.get("text", "").strip()
                segs = result.get("segments", [])
                if segs:
                    avg_lp = sum(s.get("avg_logprob", -1.0) for s in segs) / len(segs)
                    conf = float(min(1.0, max(0.0, 1.0 + avg_lp)))
                else:
                    conf = 0.85 if text else 0.0
                return text, conf
        except Exception as e:
            print(f"⚠  Whisper error: {e}")
            return "", 0.0

    # ── HTS-AT via CLAP ───────────────────────────────────────────────────────

    def _run_htsat(self, waveform_16k: np.ndarray) -> List[Dict]:
        """Return top audio events as [{"event": str, "confidence": float}]."""
        if self._clap_model is None or self._text_embeddings is None:
            return []
        try:
            # CLAP requires 48kHz — resample manually (processor does NOT auto-resample)
            import torchaudio
            wav_tensor = torch.from_numpy(waveform_16k).unsqueeze(0)  # (1, N)
            waveform_48k = torchaudio.functional.resample(
                wav_tensor, _WHISPER_SAMPLE_RATE, _CLAP_SAMPLE_RATE
            ).squeeze(0).numpy()

            audio_inputs = self._clap_processor(
                audios=waveform_48k,
                sampling_rate=_CLAP_SAMPLE_RATE,
                return_tensors="pt",
            )
            model_dtype = next(self._clap_model.parameters()).dtype
            audio_inputs = {
                k: v.to(self.device, dtype=model_dtype) if v.is_floating_point() else v.to(self.device)
                for k, v in audio_inputs.items()
            }

            with torch.no_grad():
                audio_embeds = self._clap_model.get_audio_features(**audio_inputs)
            audio_embeds = torch.nn.functional.normalize(
                audio_embeds, p=2, dim=-1
            )

            # Cosine similarity with precomputed text embeddings
            # audio_embeds: (1, D), text_embeddings: (C, D)
            sims = (audio_embeds @ self._text_embeddings.T).squeeze(0)  # (C,)
            sims = sims.float().cpu().tolist()

            events = [
                {"event": cat, "confidence": round(score, 4)}
                for cat, score in zip(_HTSAT_CATEGORIES, sims)
                if score >= _HTSAT_THRESHOLD
            ]
            events.sort(key=lambda x: x["confidence"], reverse=True)
            return events[:5]  # top-5
        except Exception as e:
            print(f"⚠  HTS-AT error: {e}")
            return []

    # ── Per-frame fusion ──────────────────────────────────────────────────────

    @staticmethod
    def _fuse_per_frame(
        transcription: str,
        speech_confidence: float,
        audio_events: List[Dict],
    ) -> str:
        """
        Determine the single dominant audio type for this segment.

        Priority: speech > music > environment > silent
        Music can win over low-confidence speech if confidence gap is large.
        """
        has_speech = bool(transcription) and speech_confidence > 0.3

        music_score = max(
            (e["confidence"] for e in audio_events
             if e["event"] in _MUSIC_LABELS),
            default=0.0,
        )
        has_music = music_score > 0.45

        env_events = [
            e for e in audio_events
            if e["event"] not in _MUSIC_LABELS
            and e["event"] != "speech"
        ]
        env_score = env_events[0]["confidence"] if env_events else 0.0
        has_env = env_score > 0.35

        if has_speech and speech_confidence >= music_score + 0.15:
            return "speech"
        if has_music and music_score >= speech_confidence - 0.1:
            return "music"
        if has_speech:
            return "speech"
        if has_env:
            return "environment"
        return "silent"

    # ── Satisfy abstract methods ──────────────────────────────────────────────

    def preprocess(self, frame): return frame
    def inference(self, p): return {}
    def postprocess(self, r): return {}
