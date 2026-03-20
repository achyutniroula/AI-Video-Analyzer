#!/usr/bin/env python3
"""
AUDIO SYSTEM TEST SCRIPT
=========================
Tests all 4 audio components:
✅ Whisper (speech transcription)
✅ Wav2Vec2 (sound classification)
✅ Enhanced Audio Events
✅ Fusion Timeline

Usage:
    python test_audio.py
"""

import sys

print("="*70)
print("🧪 AUDIO SYSTEM COMPONENT TEST")
print("="*70)

# Test 1: Import Check
print("\n1️⃣  Testing Imports...")
print("-"*70)

components = {
    'whisper': False,
    'wav2vec2': False,
    'librosa': False,
    'audio_processor': False
}

try:
    import whisper
    components['whisper'] = True
    print("   ✅ Whisper: INSTALLED")
except ImportError as e:
    print(f"   ❌ Whisper: NOT INSTALLED ({e})")

try:
    from transformers import Wav2Vec2Processor, Wav2Vec2ForCTC
    components['wav2vec2'] = True
    print("   ✅ Wav2Vec2: INSTALLED")
except ImportError as e:
    print(f"   ❌ Wav2Vec2: NOT INSTALLED ({e})")

try:
    import librosa
    components['librosa'] = True
    print("   ✅ Librosa: INSTALLED")
except ImportError as e:
    print(f"   ❌ Librosa: NOT INSTALLED ({e})")

try:
    from audio_processor import AudioProcessor
    components['audio_processor'] = True
    print("   ✅ AudioProcessor: LOADS SUCCESSFULLY")
except ImportError as e:
    print(f"   ❌ AudioProcessor: FAILED TO LOAD ({e})")

# Test 2: Model Loading
if components['audio_processor']:
    print("\n2️⃣  Testing Audio Processor Initialization...")
    print("-"*70)
    try:
        processor = AudioProcessor()
        print("   ✅ AudioProcessor initialized successfully!")
    except Exception as e:
        print(f"   ❌ Initialization failed: {e}")
        components['audio_processor'] = False

# Test 3: Check Capabilities
if components['audio_processor']:
    print("\n3️⃣  Checking Component Capabilities...")
    print("-"*70)
    
    try:
        has_whisper = hasattr(processor, 'whisper_model') and processor.whisper_available
        has_wav2vec2 = hasattr(processor, 'wav2vec2_model') and processor.wav2vec2_available
        has_events = hasattr(processor, 'audio_event_categories')
        has_fusion = hasattr(processor, 'fuse_audio_visual')
        
        print(f"   {'✅' if has_whisper else '❌'} Whisper (Speech Transcription)")
        print(f"   {'✅' if has_wav2vec2 else '❌'} Wav2Vec2 (Sound Classification)")
        print(f"   {'✅' if has_events else '❌'} Enhanced Audio Events")
        print(f"   {'✅' if has_fusion else '❌'} Audio-Visual Fusion")
        
    except Exception as e:
        print(f"   ❌ Capability check failed: {e}")

# Test 4: FFmpeg Check
print("\n4️⃣  Checking FFmpeg (Required for audio extraction)...")
print("-"*70)

import subprocess
try:
    result = subprocess.run(
        ['ffmpeg', '-version'],
        capture_output=True,
        timeout=5
    )
    if result.returncode == 0:
        version_line = result.stdout.decode().split('\n')[0]
        print(f"   ✅ FFmpeg: INSTALLED ({version_line})")
    else:
        print("   ❌ FFmpeg: FOUND BUT NOT WORKING")
except FileNotFoundError:
    print("   ❌ FFmpeg: NOT INSTALLED (install with: apt-get install ffmpeg)")
except Exception as e:
    print(f"   ❌ FFmpeg check failed: {e}")

# Final Summary
print("\n" + "="*70)
print("📊 COMPONENT SUMMARY")
print("="*70)

total = len(components)
passed = sum(1 for v in components.values() if v)

for name, status in components.items():
    icon = "✅" if status else "❌"
    print(f"   {icon} {name.upper().replace('_', ' ')}")

print("-"*70)
print(f"   Score: {passed}/{total} components working")

if passed == total:
    print("\n   🎉 ALL COMPONENTS READY!")
    print("   Your audio system is fully operational!")
else:
    print("\n   ⚠️  SOME COMPONENTS MISSING")
    print("   Check requirements.txt and rebuild Docker image")

print("="*70)

# Exit code
sys.exit(0 if passed == total else 1)