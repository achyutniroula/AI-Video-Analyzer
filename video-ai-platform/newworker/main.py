"""
NewWorker Main — Video AI Pipeline Worker
Polls SQS, processes videos with the full multimodal pipeline, saves results.
"""

import os, sys, time, traceback, subprocess, tempfile
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from worker.config import settings
from worker.sqs_handler import SQSHandler
from worker.s3_handler import S3Handler
from worker.db_handler import DBHandler
from pipeline.video_pipeline import VideoPipeline
from perception.music_identifier import MusicIdentifier


def extract_video_id(s3_key: str) -> str:
    return os.path.splitext(os.path.basename(s3_key))[0]

def extract_user_id(s3_key: str) -> str:
    parts = s3_key.split('/')
    return parts[1] if len(parts) >= 3 else 'unknown'

def _log(logs: list, level: str, step: str, message: str):
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "level": level,
        "step": step,
        "message": message,
    }
    logs.append(entry)
    print(f"[{level}] [{step}] {message}")

def extract_thumbnail(video_path: str):
    """Extract a JPEG thumbnail at the first frame using ffmpeg. Returns bytes or None."""
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp_path = tmp.name

        for seek in ['0', '1']:
            cmd = [
                'ffmpeg', '-y', '-i', video_path,
                '-ss', seek, '-vframes', '1',
                '-q:v', '3', '-loglevel', 'error',
                tmp_path
            ]
            subprocess.run(cmd, capture_output=True, timeout=30)
            if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                with open(tmp_path, 'rb') as f:
                    return f.read()
        return None
    except Exception as e:
        print(f"Thumbnail extraction error: {e}")
        return None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


class _TeeCapture:
    """
    Intercepts sys.stdout: every write goes to the real stdout AND is
    accumulated in an internal buffer so we can save it as a log file.
    """
    def __init__(self, original):
        self._orig = original
        self._buf = []

    def write(self, text):
        self._orig.write(text)
        self._orig.flush()
        self._buf.append(text)

    def flush(self):
        self._orig.flush()

    def isatty(self):
        return getattr(self._orig, 'isatty', lambda: False)()

    def getvalue(self) -> str:
        return ''.join(self._buf)


def process_message(message, sqs, s3, db, pipeline):
    event = sqs.parse_s3_event(message['Body'])
    if not event:
        # Unparseable message — delete it so it doesn't loop forever
        sqs.delete_message(message['ReceiptHandle'])
        return False

    s3_key   = event['s3_key']
    video_id = extract_video_id(s3_key)
    user_id  = extract_user_id(s3_key)

    # How many times has this message been received (including this attempt)?
    receive_count = int(message.get('Attributes', {}).get('ApproximateReceiveCount', 1))

    # ── Intercept stdout so we can save the full log to S3 ────────────
    _real_stdout = sys.stdout
    _cap = _TeeCapture(_real_stdout)
    sys.stdout = _cap

    # Keep message invisible while processing (prevents duplicate runs)
    heartbeat_stop = sqs.start_heartbeat(message['ReceiptHandle'])
    try:
        result, permanent_failure = _run_video(
            video_id, user_id, s3_key, s3, db, pipeline, receive_count
        )
    finally:
        heartbeat_stop.set()   # stop heartbeat thread
        sys.stdout = _real_stdout
        try:
            raw_bytes = _cap.getvalue().encode('utf-8', errors='replace')
            log_key = f"logs/{video_id}/worker.log"
            s3.upload_bytes(raw_bytes, log_key, 'text/plain; charset=utf-8')
            db.save_raw_log_key(video_id, log_key)
        except Exception as e:
            print(f"Warning: could not save raw log: {e}")

    if permanent_failure:
        print(f"Permanent failure (attempt #{receive_count}) — deleting message to stop retry loop")
        sqs.delete_message(message['ReceiptHandle'])
        return False

    return result


def _run_video(video_id, user_id, s3_key, s3, db, pipeline, receive_count=1):
    """
    Core processing logic. Returns (success: bool, permanent_failure: bool).

    permanent_failure=True means retrying will never help (e.g. file not in S3).
    The caller deletes the SQS message immediately in that case.
    """
    logs = []
    start_time = time.time()

    _log(logs, 'INFO', 'start', f"Worker started for video {video_id} (user: {user_id})")

    print(f"Video ID : {video_id}")
    print(f"User ID  : {user_id}")
    print(f"S3 Key   : {s3_key}")

    os.makedirs(settings.TEMP_DIR, exist_ok=True)
    local_video = os.path.join(settings.TEMP_DIR, f"{video_id}.mp4")

    db.create_video_record(video_id, user_id, s3_key)
    db.update_status(video_id, 'processing')

    # Download
    _log(logs, 'INFO', 'download', f"Downloading video from S3: {s3_key} (attempt #{receive_count})")
    if not s3.download_video(s3_key, local_video):
        _log(logs, 'ERROR', 'download', "Download failed — file not found or inaccessible in S3")
        db.update_status(video_id, 'failed', 'File not found in S3')
        _save_failed_logs(db, video_id, logs)
        # 404 means the file was never uploaded — permanent failure, no point retrying
        return False, True

    file_mb = os.path.getsize(local_video) / 1024 / 1024
    _log(logs, 'INFO', 'download', f"Download complete ({file_mb:.1f} MB)")

    # Thumbnail
    _log(logs, 'INFO', 'thumbnail', "Extracting video thumbnail...")
    try:
        thumb_bytes = extract_thumbnail(local_video)
        if thumb_bytes:
            thumb_key = f"thumbnails/{video_id}.jpg"
            if s3.upload_bytes(thumb_bytes, thumb_key, 'image/jpeg'):
                db.save_thumbnail_key(video_id, thumb_key)
                _log(logs, 'INFO', 'thumbnail', f"Thumbnail saved ({len(thumb_bytes)//1024} KB)")
            else:
                _log(logs, 'WARNING', 'thumbnail', "Thumbnail upload failed — continuing without thumbnail")
        else:
            _log(logs, 'WARNING', 'thumbnail', "Could not extract thumbnail frame")
    except Exception as e:
        _log(logs, 'WARNING', 'thumbnail', f"Thumbnail step error: {e}")

    # ── Music identification (Chromaprint + AcoustID) — whole-video ──────────
    # Run BEFORE the visual pipeline so we can attach results to temporal_assembly.
    # Extracts only the first 30s of audio; does NOT affect visual models.
    music_result = None
    _log(logs, 'INFO', 'audio_music', "Running music fingerprinting (Chromaprint + AcoustID)...")
    audio_tmp = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as af:
            audio_tmp = af.name
        extracted = MusicIdentifier.extract_audio(local_video, audio_tmp, max_secs=30)
        if extracted:
            identifier = MusicIdentifier()
            music_result = identifier.identify(audio_tmp)
            if music_result.get('best_match'):
                m = music_result['best_match']
                _log(logs, 'INFO', 'audio_music',
                     f"✓ Music identified: \"{m['title']}\" by {m['artist']} "
                     f"({m['confidence']*100:.0f}% confidence)")
            elif music_result.get('error'):
                _log(logs, 'INFO', 'audio_music', f"Music ID skipped: {music_result['error']}")
            else:
                _log(logs, 'INFO', 'audio_music', "No music fingerprint match found")
        else:
            _log(logs, 'WARNING', 'audio_music', "Audio extraction failed — music ID skipped")
    except Exception as e:
        _log(logs, 'WARNING', 'audio_music', f"Music identification error: {e}")
    finally:
        if audio_tmp and os.path.exists(audio_tmp):
            os.remove(audio_tmp)

    # Process
    _log(logs, 'INFO', 'pipeline', "Starting multimodal pipeline...")
    try:
        video_result = pipeline.process(local_video, video_id=video_id)
        frame_count = len(getattr(video_result, 'frame_results', [])) or getattr(video_result, 'frame_count', 0)
        _log(logs, 'INFO', 'pipeline', f"Pipeline complete — {frame_count} frames processed")
    except Exception as e:
        _log(logs, 'ERROR', 'pipeline', f"Pipeline failed: {str(e)[:200]}")
        db.update_status(video_id, 'failed', str(e))
        _save_failed_logs(db, video_id, logs)
        return False, False  # transient — SQS can retry
    finally:
        if os.path.exists(local_video):
            os.remove(local_video)

    # Attach music identification result to temporal assembly (before to_dict())
    try:
        if music_result is not None:
            video_result.temporal_assembly.music_identification = music_result
    except Exception:
        pass

    # Audio summary log
    try:
        ta = getattr(video_result, 'temporal_assembly', None)
        audio_summary = getattr(ta, 'audio_summary', None) if ta else None
        if audio_summary:
            transcriptions = audio_summary.get('transcriptions', [])
            events = [e['event'] for e in audio_summary.get('events', [])[:4]]
            has_speech = bool(transcriptions)
            speech_conf = audio_summary.get('avg_speech_confidence', 0.0)
            transcript_preview = ' '.join(t['text'] for t in transcriptions[:2])[:80]
            _log(logs, 'INFO', 'audio',
                 f"Audio: speech={has_speech} (conf={speech_conf:.0%}), "
                 f"events={events}"
                 + (f", transcript='{transcript_preview}'" if transcript_preview else ""))
        else:
            _log(logs, 'INFO', 'audio', "Audio: none (no audio track or extraction failed)")
    except Exception:
        pass

    # Narrative preview
    try:
        narrative_text = video_result.narrative.narrative if hasattr(video_result, 'narrative') else ''
        if narrative_text:
            _log(logs, 'INFO', 'narrative', f"Narrative generated ({len(narrative_text)} chars): {narrative_text[:80]}...")
    except Exception:
        pass

    # Upload results JSON to S3
    _log(logs, 'INFO', 'upload', "Uploading analysis results to S3...")
    results_s3_key = f"results/{video_id}/analysis.json"
    if not s3.upload_json(video_result.to_dict(), results_s3_key):
        _log(logs, 'ERROR', 'upload', "Results upload to S3 failed")
        db.update_status(video_id, 'failed', 'Upload failed')
        _save_failed_logs(db, video_id, logs)
        return False, False  # transient — S3 may recover

    elapsed = time.time() - start_time
    _log(logs, 'INFO', 'complete', f"Processing complete in {elapsed:.0f}s — results at {results_s3_key}")

    # Save summary + logs to DynamoDB
    db.save_narrative_result(video_id, video_result, results_s3_key, processing_logs=logs)

    print(f"\n✓ Processing complete!")
    print(f"  Narrative: {video_result.narrative.narrative[:100]}...")
    return True, False


def _save_failed_logs(db, video_id: str, logs: list):
    """Persist accumulated structured logs even when processing fails (best effort)."""
    try:
        db.table.update_item(
            Key={"video_id": video_id},
            UpdateExpression="SET processing_logs = :logs",
            ExpressionAttributeValues={":logs": logs[-30:]},
        )
    except Exception:
        pass


def main():
    print("=" * 60)
    print("NewWorker — Video AI Pipeline Starting...")
    print("=" * 60)
    print(f"Queue : {settings.SQS_QUEUE_URL}")
    print(f"Bucket: {settings.S3_BUCKET_NAME}")
    print(f"Table : {settings.DYNAMODB_TABLE_NAME}")
    print(f"Device: {settings.DEVICE}")

    sqs = SQSHandler()
    s3  = S3Handler()
    db  = DBHandler()

    pipeline = VideoPipeline(
        device=settings.DEVICE,
        quantize_bits=settings.QUANTIZE_BITS,
        sample_fps=settings.SAMPLE_FPS,
    )

    print("\nWaiting for messages...")

    while True:
        try:
            messages = sqs.receive_messages(max_messages=1, wait_time=20)
            if not messages:
                print(".", end="", flush=True)
                continue

            for message in messages:
                print("\n" + "=" * 60)
                success = process_message(message, sqs, s3, db, pipeline)
                if success:
                    sqs.delete_message(message['ReceiptHandle'])
                else:
                    print("Message processing failed — will retry")

        except KeyboardInterrupt:
            print("\nShutting down...")
            break
        except Exception as e:
            print(f"\nUnexpected error: {e}")
            traceback.print_exc()
            time.sleep(5)


if __name__ == "__main__":
    main()
