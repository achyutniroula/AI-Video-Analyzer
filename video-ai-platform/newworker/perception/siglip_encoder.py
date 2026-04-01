"""
SigLIP Vision Encoder

Extracts dense semantic embeddings from images using Google's SigLIP.
SigLIP is similar to CLIP but uses a sigmoid loss instead of softmax,
making it better for dense retrieval tasks.

Model: google/siglip-base-patch16-224
Output: 768-dimensional embedding per image
VRAM: ~2GB (FP16)
Time: ~0.1s per frame on A10
"""

from transformers import AutoProcessor, AutoModel
import torch
from PIL import Image
import numpy as np
from .base import BasePerceptionModule
from typing import Dict, Any


class SigLIPEncoder(BasePerceptionModule):
    """
    SigLIP vision encoder for semantic image embeddings
    
    Features:
    - 768-dim dense embeddings
    - Pre-trained on image-text pairs
    - Fast inference (~100ms)
    - Low VRAM (2GB)
    
    Example:
        encoder = SigLIPEncoder(device="cuda")
        encoder.load_model()
        
        output = encoder(frame, frame_id=0, timestamp=0.0)
        embedding = output.data["vision_embedding"]  # (768,)
        
        encoder.unload()
    """
    
    def __init__(
        self, 
        model_name: str = "google/siglip-base-patch16-224",
        **kwargs
    ):
        """
        Initialize SigLIP encoder
        
        Args:
            model_name: HuggingFace model name
            **kwargs: Passed to BasePerceptionModule (device, quantize)
        """
        super().__init__(**kwargs)
        self.model_name = model_name
        self.processor = None
        
    def load_model(self):
        """Load SigLIP model and processor"""
        print(f"Loading SigLIP: {self.model_name}")
        
        # Load processor
        self.processor = AutoProcessor.from_pretrained(self.model_name)
        
        # Load model
        self.model = AutoModel.from_pretrained(
            self.model_name,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32
        ).to(self.device)
        
        self.model.eval()
        print(f"✓ SigLIP loaded on {self.device}")
        
        return self.model
    
    def preprocess(self, frame: torch.Tensor) -> Dict[str, torch.Tensor]:
        """
        Preprocess frame for SigLIP
        
        Args:
            frame: (H, W, 3) RGB tensor, uint8, values [0, 255]
        
        Returns:
            Dict with preprocessed pixel_values
        """
        # Convert to PIL Image
        frame_np = frame.cpu().numpy()
        pil_image = Image.fromarray(frame_np)
        
        # Process with SigLIP processor
        inputs = self.processor(images=pil_image, return_tensors="pt")
        
        # Move to device
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        return inputs
    
    def inference(self, preprocessed: Dict[str, torch.Tensor]) -> Dict[str, Any]:
        """
        Extract vision features
        
        Args:
            preprocessed: Output from preprocess()
        
        Returns:
            Dict with vision embeddings (as tensor)
        """
        with torch.no_grad():
            # Option 1: Use the vision model directly (recommended)
            outputs = self.model.vision_model(**preprocessed)
            
            # Extract pooled output (this is the image embedding)
            # outputs.pooler_output is the (batch_size, hidden_size) tensor
            embeddings = outputs.pooler_output
        
        return {"embeddings": embeddings}
    
    def postprocess(self, raw_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Structure embeddings output
        
        Args:
            raw_output: Output from inference() containing embeddings tensor
        
        Returns:
            Structured dict with vision embedding as list
        """
        # Extract embeddings tensor
        embeddings = raw_output["embeddings"]
        
        # Convert to CPU numpy for JSON serialization
        # embeddings shape: (batch_size, embedding_dim) = (1, 768)
        embeddings_np = embeddings.cpu().numpy()
        
        return {
            "vision_embedding": embeddings_np[0].tolist(),  # (768,) -> list
            "embedding_dim": embeddings_np.shape[-1],
            "model": self.model_name,
            "norm": float(np.linalg.norm(embeddings_np[0]))  # L2 norm for debugging
        }
    
    def unload(self):
        """Free GPU memory"""
        if self.processor is not None:
            del self.processor
            self.processor = None
        
        super().unload()


# Convenience function for quick testing
def extract_embedding(
    frame: torch.Tensor,
    device: str = "cuda"
) -> np.ndarray:
    """
    Quick helper to extract SigLIP embedding from a frame
    
    Args:
        frame: (H, W, 3) RGB tensor
        device: "cuda" or "cpu"
    
    Returns:
        (768,) numpy array
    
    Example:
        embedding = extract_embedding(frame)
        print(embedding.shape)  # (768,)
    """
    encoder = SigLIPEncoder(device=device)
    encoder.load_model()
    
    output = encoder(frame, frame_id=0, timestamp=0.0)
    embedding = np.array(output.data["vision_embedding"])
    
    encoder.unload()
    
    return embedding