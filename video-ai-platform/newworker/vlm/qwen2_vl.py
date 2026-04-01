"""
Qwen2-VL-7B-Instruct — Vision-Language Model (Central Reasoning Brain)

Takes the structured UnifiedSceneRepresentation (text prompt) + the
original video frame (image) and produces a coherent natural-language
caption describing the scene.

Model  : Qwen/Qwen2-VL-7B-Instruct
VRAM   : ~8.5 GB (8-bit) | ~4.5 GB (4-bit)
Time   : ~1–2 s per frame on A10 (256 token cap)

Design constraints (from architecture):
  - Always runs AFTER all perception modules have unloaded
  - Must itself unload before any next-frame perception pass
  - Uses bitsandbytes 8-bit quantization by default
  - Batch size = 1
"""

from __future__ import annotations

import gc
import time
from typing import Any, Dict, Optional

import torch
from PIL import Image

from fusion.unified_representation import UnifiedSceneRepresentation
from .vlm_caption import VLMCaption


_MODEL_ID = "Qwen/Qwen2-VL-7B-Instruct"

_SYSTEM_PROMPT = (
    "You are a precise video scene analyst. You are given a frame from a video "
    "alongside structured perception data that describes what sensors detected. "
    "Your task: write a single, fluent paragraph that describes the scene — "
    "what is happening, who or what is present, how the elements are arranged "
    "spatially, and the overall atmosphere. "
    "Synthesize the data into natural language. Do not copy raw labels verbatim. "
    "Be accurate, concrete, and vivid."
)


class Qwen2VLCaptioner:
    """
    Qwen2-VL-7B vision-language captioner.

    Lifecycle mirrors the perception modules (load → caption → unload)
    so it never coexists in VRAM with heavy perception models.

    Example:
        captioner = Qwen2VLCaptioner(quantize_bits=8)
        captioner.load()

        caption = captioner.caption(usr, frame_tensor)
        print(caption.caption)

        captioner.unload()

    Text-only mode (no frame available):
        caption = captioner.caption(usr, frame=None)
    """

    def __init__(
        self,
        model_id: str = _MODEL_ID,
        quantize_bits: int = 8,          # 8 or 4
        max_new_tokens: int = 256,
        temperature: float = 0.7,
        repetition_penalty: float = 1.1,
        device: str = "cuda",
    ):
        self.model_id = model_id
        self.quantize_bits = quantize_bits
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.repetition_penalty = repetition_penalty
        self.device = device

        self._model = None
        self._processor = None

    # ─────────────────────────────────────────────────────────────────
    #  Load / unload
    # ─────────────────────────────────────────────────────────────────

    def load(self):
        """Load Qwen2-VL with bitsandbytes quantization."""
        from transformers import (
            Qwen2VLForConditionalGeneration,
            AutoProcessor,
            BitsAndBytesConfig,
        )
        from perception.utils.quantization import get_8bit_config, get_4bit_config

        print(f"Loading Qwen2-VL-7B ({self.quantize_bits}-bit)...")

        quant_cfg = get_8bit_config() if self.quantize_bits == 8 else get_4bit_config()

        self._model = Qwen2VLForConditionalGeneration.from_pretrained(
            self.model_id,
            quantization_config=quant_cfg,
            device_map="auto",
            # Image token resolution — smaller = faster, less VRAM
            attn_implementation="flash_attention_2" if self._has_flash_attn() else "eager",
        )
        self._model.eval()

        # Use smaller pixel budget to save VRAM on A10
        self._processor = AutoProcessor.from_pretrained(
            self.model_id,
            min_pixels=128 * 28 * 28,   # ~100k pixels minimum
            max_pixels=512 * 28 * 28,   # ~400k pixels maximum
        )

        vram = self._current_vram_gb()
        print(f"✓ Qwen2-VL-7B loaded — VRAM used: {vram:.1f} GB")

    def unload(self):
        """Fully release VRAM (call before next perception pass)."""
        if self._model is not None:
            del self._model
            self._model = None
        if self._processor is not None:
            del self._processor
            self._processor = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()
        print("✓ Qwen2-VL unloaded")

    def is_loaded(self) -> bool:
        return self._model is not None

    # ─────────────────────────────────────────────────────────────────
    #  Caption
    # ─────────────────────────────────────────────────────────────────

    def caption(
        self,
        usr: UnifiedSceneRepresentation,
        frame: Optional[torch.Tensor] = None,
    ) -> VLMCaption:
        """
        Generate a scene caption for one frame.

        Args:
            usr   : UnifiedSceneRepresentation from Phase 2 fusion.
            frame : Raw video frame tensor (H, W, 3) uint8, or PIL Image.
                    If None, runs in text-only mode (no image token).

        Returns:
            VLMCaption with the generated text and diagnostics.
        """
        if not self.is_loaded():
            raise RuntimeError("Call load() before caption()")

        t0 = time.time()
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()

        pil_image = self._to_pil(frame)
        messages = self._build_messages(usr.vlm_prompt, pil_image)
        response, tokens = self._generate(messages)

        gpu_mem = None
        if torch.cuda.is_available():
            gpu_mem = round(torch.cuda.max_memory_allocated() / 1e9, 2)

        caption = VLMCaption(
            frame_id=usr.frame_id,
            timestamp=usr.timestamp,
            caption=response,
            scene_type=usr.scene_type,
            context_tags=usr.context_tags,
            model=self.model_id,
            tokens_generated=tokens,
            processing_time=round(time.time() - t0, 3),
            gpu_memory_used=gpu_mem,
            vlm_prompt_used=usr.vlm_prompt,
            metadata={
                "quantize_bits": self.quantize_bits,
                "max_new_tokens": self.max_new_tokens,
                "image_provided": pil_image is not None,
            },
        )
        return caption

    # ─────────────────────────────────────────────────────────────────
    #  Internals
    # ─────────────────────────────────────────────────────────────────

    def _build_messages(
        self, vlm_prompt: str, pil_image: Optional[Image.Image]
    ) -> list:
        content = []
        if pil_image is not None:
            content.append({"type": "image", "image": pil_image})
        content.append({"type": "text", "text": vlm_prompt})

        return [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": content},
        ]

    def _generate(self, messages: list) -> tuple[str, int]:
        """Run the Qwen2-VL forward pass and return (text, token_count)."""
        from qwen_vl_utils import process_vision_info

        # Build text input from chat template
        text = self._processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        # Extract image/video tensors
        image_inputs, video_inputs = process_vision_info(messages)

        inputs = self._processor(
            text=[text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        ).to(self._model.device)

        with torch.no_grad():
            output_ids = self._model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                temperature=self.temperature,
                do_sample=self.temperature > 0,
                repetition_penalty=self.repetition_penalty,
                pad_token_id=self._processor.tokenizer.eos_token_id,
            )

        # Strip prompt tokens from output
        generated_ids = [
            out[len(inp):]
            for inp, out in zip(inputs.input_ids, output_ids)
        ]
        response = self._processor.batch_decode(
            generated_ids,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )[0].strip()

        tokens = sum(len(ids) for ids in generated_ids)
        return response, tokens

    @staticmethod
    def _to_pil(frame: Optional[Any]) -> Optional[Image.Image]:
        """Convert frame tensor / ndarray / PIL to PIL Image, or return None."""
        if frame is None:
            return None
        if isinstance(frame, Image.Image):
            return frame
        import numpy as np
        arr = frame.cpu().numpy() if isinstance(frame, torch.Tensor) else frame
        if arr.dtype != "uint8":
            arr = (arr * 255).clip(0, 255).astype("uint8")
        return Image.fromarray(arr)

    @staticmethod
    def _has_flash_attn() -> bool:
        try:
            import flash_attn  # noqa: F401
            return True
        except ImportError:
            return False

    @staticmethod
    def _current_vram_gb() -> float:
        if torch.cuda.is_available():
            return torch.cuda.memory_allocated() / 1e9
        return 0.0
