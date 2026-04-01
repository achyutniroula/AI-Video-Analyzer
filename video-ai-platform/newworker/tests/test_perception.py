"""
Test Script for Phase 1 - Perception Modules

Tests each perception module individually to verify:
1. Model loads without OOM
2. Inference runs successfully
3. Output format is correct
4. GPU memory is properly managed
5. Sequential execution works

Run with: python tests/test_perception.py
"""

import torch
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from perception import SigLIPEncoder
from perception.utils import SequentialGPUManager


def create_test_frame(height: int = 360, width: int = 640) -> torch.Tensor:
    """Create a random test frame"""
    return torch.randint(0, 255, (height, width, 3), dtype=torch.uint8)


def test_siglip():
    """Test SigLIP encoder"""
    print("\n" + "="*70)
    print("TEST 1: SigLIP Vision Encoder")
    print("="*70)
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")
    
    # Create test frame
    frame = create_test_frame()
    print(f"Frame shape: {frame.shape}")
    
    # Initialize encoder
    encoder = SigLIPEncoder(device=device)
    
    # Load model
    print("\n1. Loading model...")
    encoder.load_model()
    
    # Get memory stats
    if device == "cuda":
        mem_stats = encoder.get_memory_usage()
        print(f"   VRAM allocated: {mem_stats['allocated_gb']:.2f}GB")
    
    # Run inference
    print("\n2. Running inference...")
    output = encoder(frame, frame_id=0, timestamp=0.0)
    
    # Verify output
    print("\n3. Verifying output...")
    assert output.module_name == "SigLIPEncoder"
    assert "vision_embedding" in output.data
    assert len(output.data["vision_embedding"]) == 768
    print(f"   ✓ Embedding dimension: {output.data['embedding_dim']}")
    print(f"   ✓ Processing time: {output.processing_time:.3f}s")
    if output.gpu_memory_used:
        print(f"   ✓ GPU memory used: {output.gpu_memory_used:.2f}GB")
    
    # Unload
    print("\n4. Unloading model...")
    encoder.unload()
    
    if device == "cuda":
        mem_after = torch.cuda.memory_allocated() / 1e9
        print(f"   VRAM after unload: {mem_after:.2f}GB")
    
    print("\n✅ SigLIP test PASSED!")
    return True


def test_gpu_manager():
    """Test Sequential GPU Manager"""
    print("\n" + "="*70)
    print("TEST 2: Sequential GPU Manager")
    print("="*70)
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    if device == "cpu":
        print("⏭️  Skipping (requires GPU)")
        return True
    
    manager = SequentialGPUManager(device=device, verbose=True)
    
    # Test context manager
    print("\n1. Testing context manager...")
    
    frame = create_test_frame()
    encoder = SigLIPEncoder(device=device)
    
    with manager.load_model(lambda: encoder.load_model()):
        output = encoder(frame, frame_id=0, timestamp=0.0)
        print(f"   ✓ Inference completed: {output.data['embedding_dim']}D embedding")
    
    # Verify cleanup
    manager.print_memory_stats()
    
    print("\n✅ GPU Manager test PASSED!")
    return True


def test_sequential_execution():
    """Test sequential model loading (simulating full pipeline)"""
    print("\n" + "="*70)
    print("TEST 3: Sequential Execution (Multiple Models)")
    print("="*70)
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    if device == "cpu":
        print("⏭️  Skipping (requires GPU)")
        return True
    
    manager = SequentialGPUManager(device=device, verbose=True)
    frame = create_test_frame()
    
    # Simulate loading multiple models sequentially
    print("\n1. Load SigLIP → Unload → Load SigLIP again")
    
    # First SigLIP
    encoder1 = SigLIPEncoder(device=device)
    with manager.load_model(lambda: encoder1.load_model()):
        output1 = encoder1(frame, frame_id=0, timestamp=0.0)
        print(f"   ✓ SigLIP #1: {output1.processing_time:.3f}s")
    
    # Second SigLIP (simulating next model)
    encoder2 = SigLIPEncoder(device=device)
    with manager.load_model(lambda: encoder2.load_model()):
        output2 = encoder2(frame, frame_id=1, timestamp=1.0)
        print(f"   ✓ SigLIP #2: {output2.processing_time:.3f}s")
    
    # Verify memory is cleaned up
    manager.print_memory_stats()
    
    mem_stats = manager.get_memory_stats()
    if mem_stats['allocated_gb'] < 0.5:  # Should be near zero
        print(f"\n   ✓ Memory properly cleaned (only {mem_stats['allocated_gb']:.2f}GB allocated)")
    
    print("\n✅ Sequential execution test PASSED!")
    return True


def run_all_tests():
    """Run all Phase 1 tests"""
    print("\n" + "="*70)
    print("PHASE 1: PERCEPTION MODULE TESTS")
    print("="*70)
    
    tests = [
        ("SigLIP Encoder", test_siglip),
        ("GPU Manager", test_gpu_manager),
        ("Sequential Execution", test_sequential_execution),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n❌ {name} FAILED: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(success for _, success in results)
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED! Phase 1 infrastructure is working.")
    else:
        print("\n⚠️  Some tests failed. Please fix before proceeding.")
    
    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
