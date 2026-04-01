"""
Mask2Former Panoptic Segmentation

Labels every pixel in the frame as either a "thing" (countable object like
person, car) or "stuff" (amorphous region like sky, grass, floor).

Model: facebook/mask2former-swin-large-coco-panoptic
Output:
  things: list of {id, label, bbox, coverage, pixel_count}
  stuff:  list of {label, coverage, pixel_count}
VRAM: ~5.5GB (FP16)
Time: ~0.3s per frame on A10
"""

from transformers import AutoImageProcessor, Mask2FormerForUniversalSegmentation
import torch
import numpy as np
from PIL import Image
from typing import Dict, Any, List

from .base import BasePerceptionModule


class PanopticSegmenter(BasePerceptionModule):
    """
    Mask2Former panoptic segmenter.

    things[] are objects with individual instance IDs and bounding boxes.
    stuff[] are background regions with coverage percentages only.

    Both lists are sorted by coverage (largest first) so downstream
    modules always see the most dominant elements at index 0.

    Example:
        segmenter = PanopticSegmenter(device="cuda")
        segmenter.load_model()
        output = segmenter(frame, frame_id=0, timestamp=0.0)
        things = output.data["things"]   # [{id, label, bbox, coverage}, ...]
        stuff  = output.data["stuff"]    # [{label, coverage}, ...]
        segmenter.unload()
    """

    def __init__(
        self,
        model_name: str = "facebook/mask2former-swin-large-coco-panoptic",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.model_name = model_name
        self.processor = None

    def load_model(self):
        print(f"Loading Mask2Former: {self.model_name}")
        self.processor = AutoImageProcessor.from_pretrained(self.model_name)
        self.model = Mask2FormerForUniversalSegmentation.from_pretrained(
            self.model_name,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
        ).to(self.device)
        self.model.eval()
        print(f"✓ Mask2Former loaded on {self.device}")

    def preprocess(self, frame: torch.Tensor) -> Dict[str, Any]:
        frame_np = frame.cpu().numpy() if isinstance(frame, torch.Tensor) else frame
        pil_image = Image.fromarray(frame_np)
        inputs = self.processor(images=pil_image, return_tensors="pt")
        model_dtype = next(self.model.parameters()).dtype
        return {
            "inputs": {
                k: v.to(self.device, dtype=model_dtype) if v.is_floating_point() else v.to(self.device)
                for k, v in inputs.items()
            },
            "pil_image": pil_image,
        }

    def inference(self, preprocessed: Dict[str, Any]) -> Dict[str, Any]:
        with torch.no_grad():
            outputs = self.model(**preprocessed["inputs"])
        return {"outputs": outputs, "pil_image": preprocessed["pil_image"]}

    def postprocess(self, raw_output: Dict[str, Any]) -> Dict[str, Any]:
        outputs = raw_output["outputs"]
        pil_image = raw_output["pil_image"]

        # Post-process into panoptic segmentation map
        result = self.processor.post_process_panoptic_segmentation(
            outputs, target_sizes=[pil_image.size[::-1]]
        )[0]

        panoptic_map = result["segmentation"].cpu().numpy()  # (H, W) — segment IDs
        segments_info = result["segments_info"]

        h, w = panoptic_map.shape
        total_pixels = h * w

        things: List[Dict[str, Any]] = []
        stuff: List[Dict[str, Any]] = []

        for seg in segments_info:
            seg_id = seg["id"]
            label_id = seg["label_id"]
            is_thing = seg.get("isthing", False)
            label = self.model.config.id2label.get(label_id, f"class_{label_id}")

            mask = panoptic_map == seg_id
            pixel_count = int(mask.sum())
            coverage = round(pixel_count / total_pixels, 4)

            if is_thing:
                rows = np.where(mask.any(axis=1))[0]
                cols = np.where(mask.any(axis=0))[0]
                bbox = (
                    [int(cols.min()), int(rows.min()), int(cols.max()), int(rows.max())]
                    if len(rows) > 0 and len(cols) > 0
                    else [0, 0, 0, 0]
                )
                things.append(
                    {
                        "id": int(seg_id),
                        "label": label,
                        "label_id": int(label_id),
                        "bbox": bbox,      # [x1, y1, x2, y2]
                        "coverage": coverage,
                        "pixel_count": pixel_count,
                    }
                )
            else:
                stuff.append(
                    {
                        "label": label,
                        "label_id": int(label_id),
                        "coverage": coverage,
                        "pixel_count": pixel_count,
                    }
                )

        # Sort by coverage descending
        things.sort(key=lambda x: x["coverage"], reverse=True)
        stuff.sort(key=lambda x: x["coverage"], reverse=True)

        return {
            "things": things,
            "stuff": stuff,
            "num_things": len(things),
            "num_stuff": len(stuff),
            "image_size": [h, w],
        }

    def unload(self):
        if self.processor is not None:
            del self.processor
            self.processor = None
        super().unload()
