"""
DynamoDB Handler — store and retrieve video records for the narrative pipeline.

Schema (DynamoDB primary key: video_id):
  video_id        str   PK
  user_id         str
  s3_key          str
  status          str   'pending' | 'processing' | 'completed' | 'failed'
  created_at      str   ISO-8601 UTC
  updated_at      str   ISO-8601 UTC
  error_message   str   (optional)
  narrative       str   full narrative text
  frame_count     int
  duration        float
  scene_types     list
  processing_time float
  results_s3_key  str   S3 key for the full analysis JSON
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError

from worker.config import settings


def _now() -> str:
    return datetime.utcnow().isoformat()


class DBHandler:
    def __init__(self):
        self.dynamodb = boto3.resource(
            "dynamodb",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        self.table = self.dynamodb.Table(settings.DYNAMODB_TABLE_NAME)

    # ─────────────────────────────────────────────────────────────────
    #  Create
    # ─────────────────────────────────────────────────────────────────

    def create_video_record(self, video_id: str, user_id: str, s3_key: str) -> bool:
        """Create (or overwrite) an initial video record — always reprocesses."""
        try:
            self.table.put_item(
                Item={
                    "video_id": video_id,
                    "user_id": user_id,
                    "s3_key": s3_key,
                    "status": "pending",
                    "created_at": _now(),
                    "updated_at": _now(),
                },
            )
            print(f"Created database record for {video_id}")
            return True
        except ClientError as e:
            print(f"Failed to create record: {e}")
            return False

    # ─────────────────────────────────────────────────────────────────
    #  Status update
    # ─────────────────────────────────────────────────────────────────

    def update_status(self, video_id: str, status: str, error: str = None) -> bool:
        """Update the processing status (and optionally record an error message)."""
        try:
            update_expr = "SET #status = :status, updated_at = :updated_at"
            expr_values: Dict[str, Any] = {
                ":status": status,
                ":updated_at": _now(),
            }

            if error:
                update_expr += ", error_message = :error"
                expr_values[":error"] = error

            self.table.update_item(
                Key={"video_id": video_id},
                UpdateExpression=update_expr,
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues=expr_values,
            )
            print(f"Updated status to '{status}' for {video_id}")
            return True
        except ClientError as e:
            print(f"Failed to update status: {e}")
            return False

    # ─────────────────────────────────────────────────────────────────
    #  Thumbnail
    # ─────────────────────────────────────────────────────────────────

    def save_raw_log_key(self, video_id: str, log_s3_key: str) -> bool:
        """Store the S3 key of the raw worker stdout log file."""
        try:
            self.table.update_item(
                Key={"video_id": video_id},
                UpdateExpression="SET raw_log_s3_key = :key",
                ExpressionAttributeValues={":key": log_s3_key},
            )
            return True
        except ClientError as e:
            print(f"Failed to save raw log key: {e}")
            return False

    def save_thumbnail_key(self, video_id: str, thumbnail_s3_key: str) -> bool:
        """Store the S3 key of the generated thumbnail in DynamoDB."""
        try:
            self.table.update_item(
                Key={"video_id": video_id},
                UpdateExpression="SET thumbnail_s3_key = :key, updated_at = :ts",
                ExpressionAttributeValues={
                    ":key": thumbnail_s3_key,
                    ":ts": _now(),
                },
            )
            return True
        except ClientError as e:
            print(f"Failed to save thumbnail key: {e}")
            return False

    # ─────────────────────────────────────────────────────────────────
    #  Save narrative result
    # ─────────────────────────────────────────────────────────────────

    def save_narrative_result(
        self,
        video_id: str,
        video_result: "VideoResult",  # type: ignore[name-defined]
        results_s3_key: str,
        processing_logs: list = None,
    ) -> bool:
        """
        Save a summary of the completed VideoResult to DynamoDB.

        Stores: narrative text, frame_count, duration, scene_types,
        processing_time, and the S3 key for the full analysis JSON.
        Full frame-level data stays in S3 to respect the 400 KB item limit.
        """
        try:
            d = video_result.to_dict()

            update_expr = (
                "SET #status = :status, "
                "updated_at = :updated_at, "
                "processed_at = :processed_at, "
                "narrative = :narrative, "
                "narrative_summary = :narrative_summary, "
                "frame_count = :frame_count, "
                "#duration = :duration, "
                "scene_types = :scene_types, "
                "processing_time = :processing_time, "
                "results_s3_key = :results_s3_key"
            )
            expr_values = {
                ":status": "completed",
                ":updated_at": _now(),
                ":processed_at": _now(),
                ":narrative": d["narrative"],
                ":narrative_summary": d.get("narrative_summary", ""),
                ":frame_count": d["frame_count"],
                ":duration": str(d["duration"]),
                ":scene_types": d["scene_types"],
                ":processing_time": str(d["total_processing_time"]),
                ":results_s3_key": results_s3_key,
            }

            if processing_logs:
                update_expr += ", processing_logs = :logs"
                expr_values[":logs"] = processing_logs[-30:]  # cap at 30 entries

            self.table.update_item(
                Key={"video_id": video_id},
                UpdateExpression=update_expr,
                ExpressionAttributeNames={"#status": "status", "#duration": "duration"},
                ExpressionAttributeValues=expr_values,
            )
            print(f"Saved narrative result for {video_id}")
            return True
        except ClientError as e:
            print(f"Failed to save narrative result: {e}")
            return False

    # ─────────────────────────────────────────────────────────────────
    #  Read
    # ─────────────────────────────────────────────────────────────────

    def get_video(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a video record by ID. Returns None if not found."""
        try:
            response = self.table.get_item(Key={"video_id": video_id})
            return response.get("Item")
        except ClientError as e:
            print(f"Failed to get video: {e}")
            return None
