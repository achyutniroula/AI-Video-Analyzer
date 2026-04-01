"""
NewWorker Main — Video AI Pipeline Worker
Polls SQS, processes videos with the full multimodal pipeline, saves results.
"""

import os, sys, time, traceback
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from worker.config import settings
from worker.sqs_handler import SQSHandler
from worker.s3_handler import S3Handler
from worker.db_handler import DBHandler
from pipeline.video_pipeline import VideoPipeline


def extract_video_id(s3_key: str) -> str:
    return os.path.splitext(os.path.basename(s3_key))[0]

def extract_user_id(s3_key: str) -> str:
    parts = s3_key.split('/')
    return parts[1] if len(parts) >= 3 else 'unknown'

def process_message(message, sqs, s3, db, pipeline):
    event = sqs.parse_s3_event(message['Body'])
    if not event:
        return False

    s3_key   = event['s3_key']
    video_id = extract_video_id(s3_key)
    user_id  = extract_user_id(s3_key)

    print(f"Video ID : {video_id}")
    print(f"User ID  : {user_id}")
    print(f"S3 Key   : {s3_key}")

    os.makedirs(settings.TEMP_DIR, exist_ok=True)
    local_video = os.path.join(settings.TEMP_DIR, f"{video_id}.mp4")

    db.create_video_record(video_id, user_id, s3_key)
    db.update_status(video_id, 'processing')

    # Download
    if not s3.download_video(s3_key, local_video):
        db.update_status(video_id, 'failed', 'Download failed')
        return False

    # Process
    try:
        video_result = pipeline.process(local_video, video_id=video_id)
    except Exception as e:
        db.update_status(video_id, 'failed', str(e))
        return False
    finally:
        if os.path.exists(local_video):
            os.remove(local_video)

    # Upload results JSON to S3
    results_s3_key = f"results/{video_id}/analysis.json"
    if not s3.upload_json(video_result.to_dict(), results_s3_key):
        db.update_status(video_id, 'failed', 'Upload failed')
        return False

    # Save summary to DynamoDB
    db.save_narrative_result(video_id, video_result, results_s3_key)

    print(f"\n✓ Processing complete!")
    print(f"  Narrative: {video_result.narrative.narrative[:100]}...")
    return True


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
