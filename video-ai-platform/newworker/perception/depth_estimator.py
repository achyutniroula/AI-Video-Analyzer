"""
DepthAnything V2 - Monocular Depth Estimator

Produces a dense depth map from a single RGB frame, then summarizes
it into statistics suitable for the fusion layer.

Model: depth-anything/Depth-Anything-V2-Small-hf
Output: depth stats dict (no raw map stored — too large for JSON)
VRAM: ~1.5GB (FP16)
Time: ~0.15s per frame on A10
"""

from transformers import AutoImageProcessor, AutoModelForDepthEstimation
import torch
import numpy as np
from PIL import Image
from typing import Dict, Any

from .base import BasePerceptionModule


class DepthEstimator(BasePerceptionModule):
    """
    DepthAnything V2 monocular depth estimator.

    Outputs statistical summaries of the depth map rather than the full map
    so results remain JSON-serializable and small enough for the fusion layer.

    Example:
        estimator = DepthEstimator(device="cuda")
        estimator.load_model()
        output = estimator(frame, frame_id=0, timestamp=0.0)
        stats = output.data["depth_stats"]   # dict with mean, std, etc.
        estimator.unload()
    """

    def __init__(
        self,
        model_name: str = "depth-anything/Depth-Anything-V2-Small-hf",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.model_name = model_name
        self.processor = None

    def load_model(self):
        """Load DepthAnything V2 processor and model."""
        print(f"Loading DepthAnything V2: {self.model_name}")
        self.processor = AutoImageProcessor.from_pretrained(self.model_name)
        self.model = AutoModelForDepthEstimation.from_pretrained(
            self.model_name,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
        ).to(self.device)
        self.model.eval()
        print(f"✓ DepthAnything V2 loaded on {self.device}")

    def preprocess(self, frame: torch.Tensor) -> Dict[str, torch.Tensor]:
        frame_np = frame.cpu().numpy() if isinstance(frame, torch.Tensor) else frame
        pil_image = Image.fromarray(frame_np)
        inputs = self.processor(images=pil_image, return_tensors="pt")
        return {k: v.to(self.device) for k, v in inputs.items()}

    def inference(self, preprocessed: Dict[str, torch.Tensor]) -> Dict[str, Any]:
        with torch.no_grad():
            outputs = self.model(**preprocessed)
        # predicted_depth: (batch, H, W) — raw inverse-depth logits
        return {"predicted_depth": outputs.predicted_depth}

    def postprocess(self, raw_output: Dict[str, Any]) -> Dict[str, Any]:
        depth = raw_output["predicted_depth"].squeeze().cpu().float().numpy()

        # Normalize to [0, 1]  (0 = closest, 1 = farthest)
        d_min, d_max = float(depth.min()), float(depth.max())
        depth_norm = (depth - d_min) / (d_max - d_min + 1e-8)

        near_mask = depth_norm < 0.33
        mid_mask = (depth_norm >= 0.33) & (depth_norm < 0.66)
        far_mask = depth_norm >= 0.66

        return {
            "depth_stats": {
                "mean": round(float(np.mean(depth_norm)), 4),
                "std": round(float(np.std(depth_norm)), 4),
                "min": round(float(depth_norm.min()), 4),
                "max": round(float(depth_norm.max()), 4),
                "near_p10": round(float(np.percentile(depth_norm, 10)), 4),
                "far_p90": round(float(np.percentile(depth_norm, 90)), 4),
            },
            "depth_distribution": {
                "near_pct": round(float(near_mask.mean()), 4),
                "mid_pct": round(float(mid_mask.mean()), 4),
                "far_pct": round(float(far_mask.mean()), 4),
            },
            # Dominant depth zone (useful for scene description)
            "dominant_zone": (
                "near" if near_mask.mean() > 0.5
                else "far" if far_mask.mean() > 0.5
                else "mid"
            ),
            "model": self.model_name,
        }

    def unload(self):
        if self.processor is not None:
            del self.processor
            self.processor = None
        super().unload()
