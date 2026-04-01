"""
Sequential GPU Manager

Ensures only ONE heavy model is loaded on GPU at a time,
preventing OOM errors on the A10 24GB GPU.

Critical for g5.2xlarge where we have:
- 24GB VRAM total
- Models ranging from 1.5GB (DepthAnything) to 9GB (Qwen2-VL)
- Must run sequentially, never in parallel
"""

import torch
from typing import Callable, Optional, Any
from contextlib import contextmanager
import gc


class SequentialGPUManager:
    """
    Manages sequential GPU model execution with automatic cleanup
    
    Usage:
        manager = SequentialGPUManager(device="cuda")
        
        # Method 1: Context manager (recommended)
        with manager.load_model(lambda: model.load()) as loaded_model:
            output = loaded_model(input)
        # Model automatically unloaded here
        
        # Method 2: Manual control
        manager.ensure_empty()
        model.load()
        output = model(input)
        manager.cleanup()
    """
    
    def __init__(self, device: str = "cuda", verbose: bool = True):
        """
        Initialize GPU manager
        
        Args:
            device: "cuda" or "cpu"
            verbose: Print memory stats
        """
        self.device = device
        self.verbose = verbose
        self.current_model = None
        self._total_vram_gb = None
        
        if self.device == "cuda":
            self._total_vram_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
            if self.verbose:
                print(f"🎮 GPU Manager initialized: {self._total_vram_gb:.1f}GB total VRAM")
    
    @contextmanager
    def load_model(self, model_loader: Callable[[], Any]):
        """
        Context manager for sequential model loading
        
        Guarantees:
        1. Previous model is unloaded before new model loads
        2. Cache is cleared between models
        3. New model is unloaded when context exits
        4. Memory is freed even if exception occurs
        
        Args:
            model_loader: Function that loads and returns the model
                         Example: lambda: model.load_model()
        
        Yields:
            Loaded model
        
        Example:
            with gpu_manager.load_model(lambda: siglip.load_model()):
                output = siglip(frame)
            # SigLIP automatically unloaded here
            
            with gpu_manager.load_model(lambda: depth.load_model()):
                output = depth(frame)
            # Depth automatically unloaded here
        """
        try:
            # Step 1: Ensure GPU is empty
            self.ensure_empty()
            
            if self.verbose and self.device == "cuda":
                before_mem = torch.cuda.memory_allocated() / 1e9
                print(f"  📦 Loading model... (VRAM before: {before_mem:.2f}GB)")
            
            # Step 2: Load new model
            self.current_model = model_loader()
            
            if self.verbose and self.device == "cuda":
                after_mem = torch.cuda.memory_allocated() / 1e9
                print(f"  ✓ Model loaded (VRAM now: {after_mem:.2f}GB, +{after_mem - before_mem:.2f}GB)")
            
            # Step 3: Yield model for use
            yield self.current_model
            
        finally:
            # Step 4: Always cleanup, even if error occurred
            self.cleanup()
    
    def ensure_empty(self):
        """
        Ensure GPU is empty before loading next model
        
        This is called automatically by load_model() but can also
        be called manually if needed.
        """
        if self.current_model is not None:
            if self.verbose:
                print(f"  🧹 Unloading previous model...")
            del self.current_model
            self.current_model = None
        
        if self.device == "cuda":
            torch.cuda.empty_cache()
            gc.collect()
    
    def cleanup(self):
        """
        Cleanup current model and free memory
        
        Call this manually if not using context manager.
        """
        if self.current_model is not None:
            del self.current_model
            self.current_model = None
        
        if self.device == "cuda":
            torch.cuda.empty_cache()
            gc.collect()
            
            if self.verbose:
                mem_after = torch.cuda.memory_allocated() / 1e9
                print(f"  ✓ Cleanup complete (VRAM: {mem_after:.2f}GB)")
    
    def get_memory_stats(self) -> dict:
        """
        Get current GPU memory statistics
        
        Returns:
            Dictionary with memory usage in GB
        """
        if self.device != "cuda":
            return {"device": "cpu"}
        
        allocated = torch.cuda.memory_allocated() / 1e9
        reserved = torch.cuda.memory_reserved() / 1e9
        max_allocated = torch.cuda.max_memory_allocated() / 1e9
        free = self._total_vram_gb - allocated
        
        return {
            "allocated_gb": allocated,
            "reserved_gb": reserved,
            "max_allocated_gb": max_allocated,
            "free_gb": free,
            "total_gb": self._total_vram_gb,
            "utilization_percent": (allocated / self._total_vram_gb) * 100
        }
    
    def print_memory_stats(self):
        """Print formatted memory statistics"""
        stats = self.get_memory_stats()
        
        if stats.get("device") == "cpu":
            print("💻 Running on CPU")
            return
        
        print(f"\n📊 GPU Memory Stats:")
        print(f"   Allocated: {stats['allocated_gb']:.2f}GB / {stats['total_gb']:.1f}GB ({stats['utilization_percent']:.1f}%)")
        print(f"   Reserved:  {stats['reserved_gb']:.2f}GB")
        print(f"   Peak:      {stats['max_allocated_gb']:.2f}GB")
        print(f"   Free:      {stats['free_gb']:.2f}GB")
    
    def reset_peak_stats(self):
        """Reset peak memory statistics"""
        if self.device == "cuda":
            torch.cuda.reset_peak_memory_stats()
    
    def check_oom_risk(self, required_gb: float) -> bool:
        """
        Check if loading a model of given size risks OOM
        
        Args:
            required_gb: Expected VRAM requirement in GB
        
        Returns:
            True if safe, False if OOM risk
        """
        if self.device != "cuda":
            return True
        
        stats = self.get_memory_stats()
        available = stats['free_gb']
        
        # Leave 2GB safety margin
        safety_margin = 2.0
        safe = (available - safety_margin) >= required_gb
        
        if not safe and self.verbose:
            print(f"⚠️  OOM RISK: Need {required_gb:.1f}GB, only {available:.1f}GB free")
        
        return safe
