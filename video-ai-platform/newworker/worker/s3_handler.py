"""
S3 Handler — download and upload files from/to S3.

Mirrors the old worker's S3Handler interface, extended with upload_json().
"""

import json
import os

import boto3
from botocore.exceptions import ClientError

from worker.config import settings


class S3Handler:
    def __init__(self):
        self.s3_client = boto3.client(
            "s3",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        self.bucket_name = settings.S3_BUCKET_NAME

    # ─────────────────────────────────────────────────────────────────
    #  Download
    # ─────────────────────────────────────────────────────────────────

    def download_video(self, s3_key: str, local_path: str) -> bool:
        """Download video from S3 to a local file."""
        try:
            print(f"Downloading {s3_key} from S3...")
            self.s3_client.download_file(self.bucket_name, s3_key, local_path)
            print(f"Downloaded to {local_path}")
            return True
        except ClientError as e:
            print(f"Failed to download: {e}")
            return False

    # ─────────────────────────────────────────────────────────────────
    #  Upload
    # ─────────────────────────────────────────────────────────────────

    def upload_results(self, local_path: str, s3_key: str) -> bool:
        """Upload a local file (e.g. JSON results) to S3."""
        try:
            print(f"Uploading results to S3: {s3_key}")
            self.s3_client.upload_file(
                local_path,
                self.bucket_name,
                s3_key,
                ExtraArgs={"ContentType": "application/json"},
            )
            print("Results uploaded")
            return True
        except ClientError as e:
            print(f"Failed to upload: {e}")
            return False

    def upload_json(self, data: dict, s3_key: str) -> bool:
        """Serialise a dict to JSON and upload it directly to S3 (no temp file)."""
        try:
            print(f"Uploading JSON to S3: {s3_key}")
            body = json.dumps(data, indent=2).encode("utf-8")
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=body,
                ContentType="application/json",
            )
            print("JSON uploaded")
            return True
        except ClientError as e:
            print(f"Failed to upload JSON: {e}")
            return False

    def upload_bytes(self, data: bytes, s3_key: str, content_type: str = 'application/octet-stream') -> bool:
        """Upload raw bytes to S3 (used for thumbnails, etc.)."""
        try:
            print(f"Uploading bytes to S3: {s3_key} ({len(data)} bytes)")
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=data,
                ContentType=content_type,
            )
            print("Bytes uploaded")
            return True
        except ClientError as e:
            print(f"Failed to upload bytes: {e}")
            return False

    # ─────────────────────────────────────────────────────────────────
    #  Existence check
    # ─────────────────────────────────────────────────────────────────

    def file_exists(self, s3_key: str) -> bool:
        """Return True if the object exists in the configured bucket."""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError:
            return False
