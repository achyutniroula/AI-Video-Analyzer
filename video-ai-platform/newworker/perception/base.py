"""
Base Perception Module - Abstract Interface

All perception models inherit from BasePerceptionModule to ensure:
- Consistent input/output format
- GPU memory management
- Performance tracking
- Standardized preprocessing/postprocessing
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import torch
from dataclasses import dataclass, asdict
import time
import json


@dataclass
class PerceptionOutput:
    """
    Standardized output from all perception modules
    
    Attributes:
        module_name: Name of the perception module (e.g., "SigLIPEncoder")
        timestamp: Frame timestamp in seconds
        frame_id: Frame identifier
        data: Structured perception data (JSON-serializable dict)
        metadata: Additional module-specific metadata
        processing_time: Time taken for inference (seconds)
        gpu_memory_used: Peak GPU memory during inference (GB), None if CPU
    """
    module_name: str
    timestamp: float
    frame_id: int
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    processing_time: float
    gpu_memory_used: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    def to_json(self) -> str:
        """Serialize to JSON string"""
        return json.dumps(self.to_dict(), indent=2)


class BasePerceptionModule(ABC):
    """
    Abstract base class for all perception modules
    
    Usage:
        class MyPerceptionModule(BasePerceptionModule):
            def load_model(self):
                self.model = MyModel()
            
            def preprocess(self, frame):
                return preprocess_frame(frame)
            
            def inference(self, preprocessed):
                return self.model(preprocessed)
            
            def postprocess(self, raw_output):
                return {"result": raw_output}
        
        module = MyPerceptionModule(device="cuda")
        module.load_model()
        output = module(frame, frame_id=0, timestamp=0.0)
        module.unload()
    """
    
    def __init__(self, device: str = "cuda", quantize: bool = False):
        """
        Initialize perception module
        
        Args:
            device: "cuda" or "cpu"
            quantize: Whether to use quantized models (8-bit/4-bit)
        """
        self.device = device
        self.quantize = quantize
        self.model = None
        self.name = self.__class__.__name__
        
    @abstractmethod
    def load_model(self):
        """
        Load and initialize the model
        
        This method must:
        1. Load the model from HuggingFace or local path
        2. Move model to self.device
        3. Set model to eval mode
        4. Apply quantization if self.quantize is True
        
        Example:
            self.model = AutoModel.from_pretrained("model_name")
            self.model = self.model.to(self.device)
            self.model.eval()
        """
        pass
    
    @abstractmethod
    def preprocess(self, frame: torch.Tensor) -> Any:
        """
        Preprocess input frame
        
        Args:
            frame: (H, W, 3) RGB tensor, uint8, values [0, 255]
        
        Returns:
            Preprocessed input ready for inference
            (can be tensor, dict, or any format the model expects)
        """
        pass
    
    @abstractmethod
    def inference(self, preprocessed: Any) -> Dict[str, Any]:
        """
        Run model inference
        
        Args:
            preprocessed: Output from preprocess()
        
        Returns:
            Raw model output as dictionary
        """
        pass
    
    @abstractmethod
    def postprocess(self, raw_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert model output to structured format
        
        Args:
            raw_output: Output from inference()
        
        Returns:
            Structured, JSON-serializable dictionary with perception results
        """
        pass
    
    def __call__(self, frame: torch.Tensor, frame_id: int, 
                 timestamp: float, **kwargs) -> PerceptionOutput:
        """
        Run full perception pipeline
        
        Args:
            frame: (H, W, 3) RGB tensor, uint8
            frame_id: Frame identifier
            timestamp: Frame timestamp (seconds)
            **kwargs: Additional module-specific arguments
        
        Returns:
            PerceptionOutput with structured results
        """
        start_time = time.time()
        
        # Track GPU memory before
        if self.device == "cuda":
            torch.cuda.reset_peak_memory_stats()
        
        # Run pipeline
        preprocessed = self.preprocess(frame)
        raw_output = self.inference(preprocessed)
        structured_data = self.postprocess(raw_output)
        
        # Track GPU memory after
        gpu_mem = None
        if self.device == "cuda":
            gpu_mem = torch.cuda.max_memory_allocated() / 1e9  # GB
        
        processing_time = time.time() - start_time
        
        return PerceptionOutput(
            module_name=self.name,
            timestamp=timestamp,
            frame_id=frame_id,
            data=structured_data,
            metadata={
                "device": self.device,
                "quantized": self.quantize,
                **kwargs  # Include any additional args
            },
            processing_time=processing_time,
            gpu_memory_used=gpu_mem
        )
    
    def unload(self):
        """
        Free GPU memory by deleting model and clearing cache
        
        Call this after processing to ensure models are unloaded
        before loading the next model in the pipeline.
        """
        if self.model is not None:
            del self.model
            self.model = None
        
        if self.device == "cuda":
            torch.cuda.empty_cache()
            # Force garbage collection
            import gc
            gc.collect()
    
    def is_loaded(self) -> bool:
        """Check if model is currently loaded"""
        return self.model is not None
    
    def get_memory_usage(self) -> Dict[str, float]:
        """
        Get current GPU memory usage
        
        Returns:
            Dictionary with memory stats (GB)
        """
        if self.device != "cuda":
            return {"device": "cpu"}
        
        return {
            "allocated_gb": torch.cuda.memory_allocated() / 1e9,
            "reserved_gb": torch.cuda.memory_reserved() / 1e9,
            "max_allocated_gb": torch.cuda.max_memory_allocated() / 1e9
        }
