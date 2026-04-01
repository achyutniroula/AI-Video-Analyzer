"""
Audio Processor — Whisper (speech) + PANNs (audio events)

Transcribes speech and detects non-speech audio events from a raw waveform.
PANNs is optional — if not installed the module falls back to Whisper-only.

Models:
  Whisper base  (~150 MB, ~1.5GB VRAM FP16)
  PANNs CNN14   (~300 MB, ~1.0GB VRAM FP16)  — optional

Combined VRAM: ~2.5GB (FP16)
Time: ~0.5s per audio segment on A10

Input (via `audio_waveform` kwarg):
  numpy array of shape (N,) — mono, 16 kHz PCM float32

Output:
  transcription : str
  audio_events  : list of {event, confidence}  (PANNs) or []
  has_speech    : bool
"""

import time
from typing import Any, Dict, List, Optional

import numpy as np
import torch

from .base import BasePerceptionModule, PerceptionOutput

# PANNs event label subset — keep only meaningful ones (527 total in AudioSet)
_AUDIO_EVENT_LABELS: Dict[int, str] = {
    0:   "speech",
    1:   "male speech",
    2:   "female speech",
    13:  "laughter",
    14:  "applause",
    40:  "music",
    41:  "musical instrument",
    72:  "singing",
    137: "dog",
    138: "cat",
    151: "bird",
    277: "water",
    288: "rain",
    289: "thunder",
    316: "crowd",
    317: "cheering",
    400: "gunshot",
    430: "explosion",
    432: "car",
    440: "siren",
    480: "footsteps",
}

_PANNS_CONFIDENCE_THRESH = 0.15
_WHISPER_SAMPLE_RATE = 16_000


class AudioProcessor(BasePerceptionModule):
    """
    Whisper + PANNs audio processor.

    Does not use a video frame — accepts `audio_waveform` kwarg.
    The `frame` argument is accepted (and ignored) to satisfy the
    BasePerceptionModule interface.

    Example:
        proc = AudioProcessor(device="cuda")
        proc.load_model()
        output = proc(frame, frame_id=5, timestamp=2.0,
                      audio_waveform=waveform_np)
        print(output.data["transcription"])
        print(output.data["audio_events"])
        proc.unload()
    """

    def __init__(
        self,
        whisper_model: str = "base",
        use_panns: bool = True,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.whisper_model_name = whisper_model
        self.use_panns = use_panns
        self._whisper = None
        self._panns = None

    def load_model(self):
        print(f"Loading Whisper ({self.whisper_model_name})...")
        import whisper
        self._whisper = whisper.load_model(
            self.whisper_model_name,
            device=self.device,
        )
        print(f"✓ Whisper loaded on {self.device}")

        if self.use_panns:
            try:
                from panns_inference import AudioTagging
                self._panns = AudioTagging(checkpoint_path=None, device=self.device)
                print(f"✓ PANNs CNN14 loaded on {self.device}")
            except Exception as e:
                print(f"⚠  PANNs not available ({e}) — running Whisper-only")
                self._panns = None

        self.model = self._whisper   # satisfy is_loaded()

    def unload(self):
        if self._whisper is not None:
            del self._whisper
            self._whisper = None
        if self._panns is not None:
            del self._panns
            self._panns = None
        self.model = None
        if self.device == "cuda":
            import gc
            torch.cuda.empty_cache()
            gc.collect()

    # ------------------------------------------------------------------ #
    #  Override __call__ to accept audio_waveform kwarg                   #
    # ------------------------------------------------------------------ #

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
            # No audio segment — return empty result
            data = {
                "transcription": "",
                "audio_events": [],
                "has_speech": False,
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
                "panns_available": self._panns is not None,
            },
            processing_time=time.time() - t0,
            gpu_memory_used=gpu_mem,
        )

    def _process_audio(self, waveform: np.ndarray) -> Dict[str, Any]:
        # Ensure float32 mono
        if waveform.dtype != np.float32:
            waveform = waveform.astype(np.float32)
        if waveform.ndim > 1:
            waveform = waveform.mean(axis=-1)

        # --- Whisper transcription ----------------------------------------
        import whisper
        result = self._whisper.transcribe(waveform, fp16=(self.device == "cuda"))
        transcription = result.get("text", "").strip()
        has_speech = bool(transcription)

        # --- PANNs audio event detection ----------------------------------
        audio_events: List[Dict] = []
        if self._panns is not None:
            try:
                # PANNs expects (batch, samples) numpy float32
                clip = waveform[np.newaxis, :]   # (1, N)
                _, clipwise_output = self._panns.inference(clip)
                # clipwise_output: (1, 527) probabilities
                probs = clipwise_output[0]
                for idx, label in _AUDIO_EVENT_LABELS.items():
                    if idx < len(probs) and probs[idx] >= _PANNS_CONFIDENCE_THRESH:
                        audio_events.append(
                            {
                                "event": label,
                                "confidence": round(float(probs[idx]), 4),
                                "class_id": idx,
                            }
                        )
                audio_events.sort(key=lambda x: x["confidence"], reverse=True)
            except Exception as e:
                audio_events = [{"event": "panns_error", "note": str(e)}]

        return {
            "transcription": transcription,
            "audio_events": audio_events,
            "has_speech": has_speech,
        }

    # ------------------------------------------------------------------ #
    #  Unused abstract methods                                             #
    # ------------------------------------------------------------------ #
    def preprocess(self, frame): return frame
    def inference(self, p): return {}
    def postprocess(self, r): return {}
