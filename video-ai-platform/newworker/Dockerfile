# ============================================================================
# VLM Video Processing Worker - Production Dockerfile
# ============================================================================
# Target: g5.2xlarge (NVIDIA A10 24GB) or g4dn.xlarge (NVIDIA T4 16GB)
# Base: NVIDIA CUDA 12.1.1 with cuDNN 8 on Ubuntu 22.04
# ============================================================================

FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

# Prevent interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive

# Set working directory
WORKDIR /app

# ============================================================================
# SYSTEM DEPENDENCIES
# ============================================================================

RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    python3-dev \
    ffmpeg \
    build-essential \
    wget \
    curl \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create symbolic link for python
RUN ln -s /usr/bin/python3.10 /usr/bin/python

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# ============================================================================
# PYTHON DEPENDENCIES
# ============================================================================

# Copy requirements first (for Docker layer caching)
COPY requirements.txt .

# Install PyTorch with CUDA 12.1 support
RUN pip install --no-cache-dir \
    torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cu121

# Install all other dependencies
RUN pip install --no-cache-dir -r requirements.txt

# ============================================================================
# APPLICATION CODE
# ============================================================================

# Copy application code
COPY perception/ ./perception/
COPY fusion/ ./fusion/
COPY vlm/ ./vlm/
COPY pipeline/ ./pipeline/
COPY narrative/ ./narrative/
COPY optimization/ ./optimization/
COPY worker/ ./worker/
COPY main.py .

# ============================================================================
# MODEL CACHING (Optional - speeds up first run)
# ============================================================================

# Pre-download SigLIP model (adds ~1GB to image but saves startup time)
RUN python3 -c "from transformers import AutoProcessor, AutoModel; import torch; print('Pre-caching SigLIP...'); AutoProcessor.from_pretrained('google/siglip-base-patch16-224'); AutoModel.from_pretrained('google/siglip-base-patch16-224', torch_dtype=torch.float16); print('✓ SigLIP cached')"

# Uncomment to also cache other models (increases image size)
# Depth model (~500MB)
# RUN python3 -c "from transformers import AutoImageProcessor, AutoModelForDepthEstimation; AutoImageProcessor.from_pretrained('depth-anything/Depth-Anything-V2-Small'); AutoModelForDepthEstimation.from_pretrained('depth-anything/Depth-Anything-V2-Small'); print('✓ Depth cached')"

# Panoptic model (~800MB)
# RUN python3 -c "from transformers import Mask2FormerImageProcessor, Mask2FormerForUniversalSegmentation; Mask2FormerImageProcessor.from_pretrained('facebook/mask2former-swin-large-coco-panoptic'); Mask2FormerForUniversalSegmentation.from_pretrained('facebook/mask2former-swin-large-coco-panoptic'); print('✓ Panoptic cached')"

# ============================================================================
# RUNTIME CONFIGURATION
# ============================================================================

# Create directories
RUN mkdir -p /app/logs /app/temp

# Environment variables (can be overridden at runtime)
ENV PYTHONUNBUFFERED=1
ENV CUDA_VISIBLE_DEVICES=0
ENV TRANSFORMERS_CACHE=/app/.cache/huggingface
ENV HF_HOME=/app/.cache/huggingface

# Expose port (if needed for health checks)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=3 \
    CMD python -c "import torch; assert torch.cuda.is_available()" || exit 1

# ============================================================================
# ENTRYPOINT
# ============================================================================

# Default command
CMD ["python", "main.py"]
