"""
SQS Handler — receive and delete messages from an SQS queue.

Mirrors the old worker's SQSHandler exactly, only the config import changes.
"""

import json
import threading

import boto3
from botocore.exceptions import ClientError

from worker.config import settings

# How long to make the message invisible when first received (seconds).
# Must be >= your longest expected processing time.
_INITIAL_VISIBILITY = 3600  # 1 hour

# How often the heartbeat extends the timeout (seconds).
_HEARTBEAT_INTERVAL = 300   # 5 minutes

# How much extra time to add each heartbeat (seconds).
_HEARTBEAT_EXTENSION = 600  # 10 minutes


class SQSHandler:
    def __init__(self):
        self.sqs_client = boto3.client(
            "sqs",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        self.queue_url = settings.SQS_QUEUE_URL

    def receive_messages(self, max_messages: int = 1, wait_time: int = 20):
        """Receive messages from the SQS queue (long polling)."""
        try:
            response = self.sqs_client.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=max_messages,
                WaitTimeSeconds=wait_time,
                VisibilityTimeout=_INITIAL_VISIBILITY,
                MessageAttributeNames=["All"],
                AttributeNames=["All"],
            )
            return response.get("Messages", [])
        except ClientError as e:
            print(f"Error receiving messages: {e}")
            return []

    def extend_visibility(self, receipt_handle: str, extra_seconds: int = _HEARTBEAT_EXTENSION) -> bool:
        """Extend the visibility timeout for an in-flight message."""
        try:
            self.sqs_client.change_message_visibility(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle,
                VisibilityTimeout=extra_seconds,
            )
            return True
        except ClientError as e:
            print(f"Warning: could not extend visibility timeout: {e}")
            return False

    def start_heartbeat(self, receipt_handle: str) -> threading.Event:
        """
        Start a background thread that periodically extends the visibility
        timeout for a message being processed.

        Returns a stop_event — call stop_event.set() when processing is done.
        """
        stop_event = threading.Event()

        def _heartbeat():
            while not stop_event.wait(timeout=_HEARTBEAT_INTERVAL):
                ok = self.extend_visibility(receipt_handle, _HEARTBEAT_EXTENSION)
                if ok:
                    print(f"[SQS] Visibility extended by {_HEARTBEAT_EXTENSION}s")
                else:
                    print("[SQS] Warning: heartbeat extend failed")

        t = threading.Thread(target=_heartbeat, daemon=True)
        t.start()
        return stop_event

    def delete_message(self, receipt_handle: str) -> bool:
        """Delete a message from the queue after successful processing."""
        try:
            self.sqs_client.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle,
            )
            print("Message deleted from queue")
            return True
        except ClientError as e:
            print(f"Failed to delete message: {e}")
            return False

    def parse_s3_event(self, message_body: str) -> dict:
        """
        Parse an S3 event notification from an SQS message body.

        Returns a dict with keys: bucket, s3_key, size, event_name.
        Returns None if the body cannot be parsed or is not an S3 event.
        """
        try:
            body = json.loads(message_body)

            # S3 events are wrapped in a Records array
            if "Records" in body:
                record = body["Records"][0]
                s3_info = record["s3"]
                raw_disabled = body.get("disabled_modules", [])
                return {
                    "bucket": s3_info["bucket"]["name"],
                    "s3_key": s3_info["object"]["key"],
                    "size": s3_info["object"]["size"],
                    "event_name": record["eventName"],
                    "disabled_modules": frozenset(m.strip().lower() for m in raw_disabled if m.strip()),
                }

            return None

        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error parsing message: {e}")
            return None
