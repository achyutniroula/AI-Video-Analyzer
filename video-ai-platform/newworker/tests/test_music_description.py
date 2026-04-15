"""
test_music_description.py — Music description diagnostic via CLAP

Tests the new _describe_music() method added to AudioProcessor.
Extracts audio from a video, runs it through CLAP zero-shot classification,
and shows genre/mood descriptions alongside the existing HTS-AT event output
so you can compare both side by side.

Usage:
    python tests/test_music_description.py --video path/to/video.mp4
    python tests/test_music_description.py --video path/to/video.mp4 --device cpu
    python tests/test_music_description.py --video path/to/video.mp4 --duration 30

Requirements:
    pip install transformers torch torchaudio numpy
    CLAP model auto-downloads on first run (~1 GB): laion/clap-htsat-unfused
"""

import argparse
import os
import subprocess
import sys
import tempfile
import time

import numpy as np

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

DIVIDER = "─" * 60


def _print_step(n: int, title: str):
    print(f"\n{DIVIDER}")
    print(f"  STEP {n}: {title}")
    print(DIVIDER)


def _pass(msg: str):  print(f"  ✓  {msg}")
def _fail(msg: str):  print(f"  ✗  {msg}")
def _info(msg: str):  print(f"     {msg}")


# ── Step 1: Extract audio from video ─────────────────────────────────────────

def extract_audio(video_path: str, duration: int) -> str | None:
    _print_step(1, f"Audio extraction (first {duration}s)")
    _info(f"Input: {video_path}")

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    out_path = tmp.name
    tmp.close()

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-t", str(duration),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",   # 16kHz — what Whisper and our waveform loader expects
        "-ac", "1",
        "-loglevel", "error",
        out_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0 or not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
            _fail(f"ffmpeg failed: {result.stderr.strip()}")
            return None
        size_kb = os.path.getsize(out_path) / 1024
        _pass(f"Extracted {size_kb:.0f} KB WAV at 16kHz mono")
        return out_path
    except Exception as e:
        _fail(f"Extraction error: {e}")
        return None


# ── Step 2: Load waveform ─────────────────────────────────────────────────────

def load_waveform(audio_path: str) -> np.ndarray | None:
    _print_step(2, "Loading waveform")
    try:
        import torchaudio
        waveform, sr = torchaudio.load(audio_path)
        waveform = waveform.mean(dim=0).numpy().astype(np.float32)
        _pass(f"Waveform loaded — {len(waveform)/sr:.1f}s @ {sr}Hz, {len(waveform)} samples")
        return waveform
    except Exception as e:
        _fail(f"Failed to load waveform: {e}")
        return None


# ── Step 3: Load CLAP model ───────────────────────────────────────────────────

def load_clap(device: str):
    _print_step(3, "Loading CLAP model (laion/clap-htsat-unfused)")
    _info("This may take a minute on first run — model is ~1 GB")
    try:
        import torch
        from transformers import ClapModel, ClapProcessor
        t0 = time.time()
        processor = ClapProcessor.from_pretrained("laion/clap-htsat-unfused")
        model = ClapModel.from_pretrained(
            "laion/clap-htsat-unfused",
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        ).to(device).eval()
        _pass(f"CLAP loaded on {device} in {time.time()-t0:.1f}s")
        return model, processor
    except Exception as e:
        _fail(f"Failed to load CLAP: {e}")
        return None, None


# ── Step 4: Run HTS-AT event detection ───────────────────────────────────────

def run_htsat(waveform: np.ndarray, model, processor, device: str) -> list:
    _print_step(4, "HTS-AT — general audio event detection (existing pipeline)")

    from perception.audio_processor import _HTSAT_CATEGORIES, _HTSAT_THRESHOLD
    import torch, torchaudio

    try:
        wav_tensor = torch.from_numpy(waveform).unsqueeze(0)
        waveform_48k = torchaudio.functional.resample(wav_tensor, 16000, 48000).squeeze(0).numpy()

        text_inputs = processor(text=_HTSAT_CATEGORIES, return_tensors="pt", padding=True)
        text_inputs = {k: v.to(device) for k, v in text_inputs.items()}

        audio_inputs = processor(audios=waveform_48k, sampling_rate=48000, return_tensors="pt")
        model_dtype = next(model.parameters()).dtype
        audio_inputs = {
            k: v.to(device, dtype=model_dtype) if v.is_floating_point() else v.to(device)
            for k, v in audio_inputs.items()
        }

        with torch.no_grad():
            text_embeds = torch.nn.functional.normalize(model.get_text_features(**text_inputs), p=2, dim=-1)
            audio_embeds = torch.nn.functional.normalize(model.get_audio_features(**audio_inputs), p=2, dim=-1)

        sims = (audio_embeds @ text_embeds.T).squeeze(0).float().cpu().tolist()

        events = [
            {"event": cat, "confidence": round(score, 4)}
            for cat, score in zip(_HTSAT_CATEGORIES, sims)
            if score >= _HTSAT_THRESHOLD
        ]
        events.sort(key=lambda x: x["confidence"], reverse=True)

        if events:
            _pass(f"{len(events)} events detected above threshold ({_HTSAT_THRESHOLD})")
            for e in events[:6]:
                bar = "█" * int(e["confidence"] * 20)
                print(f"     {e['confidence']*100:5.1f}%  {bar:<20}  {e['event']}")
        else:
            _info("No events detected above threshold")

        return events

    except Exception as e:
        _fail(f"HTS-AT error: {e}")
        return []


# ── Step 5: Run music description ─────────────────────────────────────────────

def run_music_description(waveform: np.ndarray, model, processor, device: str, events: list) -> list:
    _print_step(5, "Music description — genre/mood classification (new)")

    from perception.audio_processor import _MUSIC_DESCRIPTION_LABELS, _MUSIC_DESC_THRESHOLD, _MUSIC_LABELS
    import torch, torchaudio

    music_detected = any(e["event"] in _MUSIC_LABELS for e in events)
    if not music_detected:
        _info("Music not detected by HTS-AT — running description anyway for diagnostic purposes")

    try:
        wav_tensor = torch.from_numpy(waveform).unsqueeze(0)
        waveform_48k = torchaudio.functional.resample(wav_tensor, 16000, 48000).squeeze(0).numpy()

        text_inputs = processor(text=_MUSIC_DESCRIPTION_LABELS, return_tensors="pt", padding=True)
        text_inputs = {k: v.to(device) for k, v in text_inputs.items()}

        audio_inputs = processor(audios=waveform_48k, sampling_rate=48000, return_tensors="pt")
        model_dtype = next(model.parameters()).dtype
        audio_inputs = {
            k: v.to(device, dtype=model_dtype) if v.is_floating_point() else v.to(device)
            for k, v in audio_inputs.items()
        }

        with torch.no_grad():
            text_embeds = torch.nn.functional.normalize(model.get_text_features(**text_inputs), p=2, dim=-1)
            audio_embeds = torch.nn.functional.normalize(model.get_audio_features(**audio_inputs), p=2, dim=-1)

        sims = (audio_embeds @ text_embeds.T).squeeze(0).float().cpu().tolist()

        # Show ALL scores so you can tune the threshold
        all_scores = sorted(
            [{"description": label, "confidence": round(score, 4)}
             for label, score in zip(_MUSIC_DESCRIPTION_LABELS, sims)],
            key=lambda x: x["confidence"], reverse=True
        )

        print(f"\n  All scores (threshold is {_MUSIC_DESC_THRESHOLD}):\n")
        for item in all_scores:
            marker = "  ★" if item["confidence"] >= _MUSIC_DESC_THRESHOLD else "   "
            bar = "█" * int(item["confidence"] * 20)
            print(f"{marker}  {item['confidence']*100:5.1f}%  {bar:<20}  {item['description']}")

        top = [i for i in all_scores if i["confidence"] >= _MUSIC_DESC_THRESHOLD]
        print()
        if top:
            _pass(f"Top description: \"{top[0]['description']}\" ({top[0]['confidence']*100:.1f}%)")
        else:
            _info("No descriptions above threshold — music may be mixed too quietly")

        return top[:3]

    except Exception as e:
        _fail(f"Music description error: {e}")
        return []


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Music description diagnostic")
    parser.add_argument("--video", required=True, metavar="PATH", help="Path to video file")
    parser.add_argument("--device", default="cuda", choices=["cuda", "cpu"], help="Device (default: cuda)")
    parser.add_argument("--duration", type=int, default=30, help="Seconds of audio to analyze (default: 30)")
    args = parser.parse_args()

    if not os.path.exists(args.video):
        print(f"\n  ✗  Video not found: {args.video}\n")
        sys.exit(1)

    # Fall back to CPU if CUDA not available
    import torch
    if args.device == "cuda" and not torch.cuda.is_available():
        print("  ⚠  CUDA not available — falling back to CPU")
        args.device = "cpu"

    print("\n" + "=" * 60)
    print("  Music Description — Diagnostic Test")
    print("=" * 60)
    _info(f"Video  : {args.video}")
    _info(f"Device : {args.device}")
    _info(f"Window : {args.duration}s")

    tmp_audio = None
    try:
        # Step 1
        tmp_audio = extract_audio(args.video, args.duration)
        if not tmp_audio:
            sys.exit(1)

        # Step 2
        waveform = load_waveform(tmp_audio)
        if waveform is None:
            sys.exit(1)

        # Step 3
        model, processor = load_clap(args.device)
        if model is None:
            sys.exit(1)

        # Step 4
        events = run_htsat(waveform, model, processor, args.device)

        # Step 5
        descriptions = run_music_description(waveform, model, processor, args.device, events)

        # Summary
        print(f"\n{DIVIDER}")
        print("  Summary")
        print(DIVIDER)
        music_events = [e for e in events if e["event"] in ("music", "singing voice")]
        if music_events:
            _info(f"HTS-AT music signal  : {music_events[0]['confidence']*100:.1f}%")
        else:
            _info("HTS-AT music signal  : not detected")
        if descriptions:
            _info(f"Music description    : {descriptions[0]['description']} ({descriptions[0]['confidence']*100:.1f}%)")
            if len(descriptions) > 1:
                _info(f"Also matches         : {', '.join(d['description'] for d in descriptions[1:])}")
        else:
            _info("Music description    : no match above threshold")

    finally:
        if tmp_audio and os.path.exists(tmp_audio):
            os.remove(tmp_audio)

    print(f"\n{DIVIDER}")
    print("  Test complete")
    print(DIVIDER + "\n")


if __name__ == "__main__":
    main()
