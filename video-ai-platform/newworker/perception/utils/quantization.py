"""
Model Quantization Helpers

Utilities for loading models with 8-bit or 4-bit quantization
to reduce VRAM usage on the A10 24GB GPU.

Quantization benefits:
- FP16: Full precision (e.g., 7B model = ~14GB VRAM)
- 8-bit: ~50% reduction (e.g., 7B model = ~8GB VRAM)
- 4-bit: ~75% reduction (e.g., 7B model = ~4GB VRAM)

Trade-offs:
- 8-bit: Minimal quality loss, stable
- 4-bit: Slight quality loss, more VRAM savings
"""

import torch
from transformers import BitsAndBytesConfig
from typing import Optional


def get_8bit_config() -> BitsAndBytesConfig:
    """
    Get 8-bit quantization config
    
    Best for: Qwen2-VL, SlowFast (if needed)
    VRAM savings: ~50%
    Quality: Near-identical to FP16
    
    Returns:
        BitsAndBytesConfig for 8-bit quantization
    """
    return BitsAndBytesConfig(
        load_in_8bit=True,
        llm_int8_threshold=6.0,
        llm_int8_has_fp16_weight=False,
        llm_int8_enable_fp32_cpu_offload=False
    )


def get_4bit_config() -> BitsAndBytesConfig:
    """
    Get 4-bit quantization config
    
    Best for: Extreme VRAM constraints
    VRAM savings: ~75%
    Quality: Slight degradation, still usable
    
    Returns:
        BitsAndBytesConfig for 4-bit quantization
    """
    return BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4"  # Normal Float 4-bit
    )


def load_quantized_model(
    model_class,
    model_name: str,
    quantize_bits: int = 8,
    device_map: str = "auto",
    **kwargs
):
    """
    Load model with quantization
    
    Args:
        model_class: Model class from transformers
                    (e.g., AutoModel, Qwen2VLForConditionalGeneration)
        model_name: HuggingFace model name or local path
        quantize_bits: 8 or 4 (or None for FP16)
        device_map: Device mapping strategy
                   - "auto": Automatic distribution
                   - "cuda:0": Specific GPU
        **kwargs: Additional arguments for from_pretrained()
    
    Returns:
        Quantized model
    
    Example:
        from transformers import AutoModel
        
        model = load_quantized_model(
            AutoModel,
            "google/siglip-base-patch16-224",
            quantize_bits=8
        )
    """
    # Select quantization config
    quantization_config = None
    torch_dtype = torch.float16  # Default
    
    if quantize_bits == 8:
        quantization_config = get_8bit_config()
        torch_dtype = None  # bitsandbytes handles dtype
        
    elif quantize_bits == 4:
        quantization_config = get_4bit_config()
        torch_dtype = None  # bitsandbytes handles dtype
    
    # Load model
    model = model_class.from_pretrained(
        model_name,
        quantization_config=quantization_config,
        device_map=device_map,
        torch_dtype=torch_dtype,
        **kwargs
    )
    
    return model


def estimate_vram_usage(
    param_count_billions: float,
    quantize_bits: Optional[int] = None
) -> float:
    """
    Estimate VRAM usage for a model
    
    Args:
        param_count_billions: Number of parameters in billions
                             (e.g., 7.0 for 7B model)
        quantize_bits: 8, 4, or None for FP16
    
    Returns:
        Estimated VRAM in GB
    
    Example:
        >>> estimate_vram_usage(7.0, quantize_bits=8)
        8.5  # ~8.5GB for 7B model in 8-bit
    """
    if quantize_bits == 8:
        # 8-bit: ~1.2 GB per billion parameters
        return param_count_billions * 1.2
    
    elif quantize_bits == 4:
        # 4-bit: ~0.6 GB per billion parameters
        return param_count_billions * 0.6
    
    else:
        # FP16: ~2.0 GB per billion parameters
        return param_count_billions * 2.0


# Pre-computed VRAM estimates for common models
MODEL_VRAM_ESTIMATES = {
    # Vision encoders
    "siglip-base": {"fp16": 2.0, "8bit": 1.2, "4bit": 0.8},
    
    # Depth estimation
    "depth-anything-v2-small": {"fp16": 1.5, "8bit": 1.0, "4bit": 0.6},
    
    # Panoptic segmentation
    "mask2former-swin-large": {"fp16": 5.5, "8bit": 3.2, "4bit": 2.0},
    
    # Action recognition
    "slowfast-r50": {"fp16": 4.0, "8bit": 2.5, "4bit": 1.5},
    
    # Audio
    "whisper-base": {"fp16": 1.5, "8bit": 1.0, "4bit": 0.6},
    "panns": {"fp16": 1.0, "8bit": 0.7, "4bit": 0.4},
    
    # VLM (Phase 3)
    "qwen2-vl-7b": {"fp16": 14.0, "8bit": 8.5, "4bit": 4.5},
}


def get_model_vram_estimate(model_key: str, quantize_bits: Optional[int] = None) -> float:
    """
    Get VRAM estimate for known models
    
    Args:
        model_key: Key from MODEL_VRAM_ESTIMATES
        quantize_bits: 8, 4, or None
    
    Returns:
        Estimated VRAM in GB
    """
    if model_key not in MODEL_VRAM_ESTIMATES:
        raise ValueError(f"Unknown model: {model_key}. Available: {list(MODEL_VRAM_ESTIMATES.keys())}")
    
    estimates = MODEL_VRAM_ESTIMATES[model_key]
    
    if quantize_bits == 8:
        return estimates["8bit"]
    elif quantize_bits == 4:
        return estimates["4bit"]
    else:
        return estimates["fp16"]
