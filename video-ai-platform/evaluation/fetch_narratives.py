"""
fetch_narratives.py
-------------------
Queries DynamoDB directly (using your AWS credentials) to pull every video
record that belongs to your user and writes the generated narratives to
generated_narratives.json.

Run this after your newworker has processed the videos.

Requirements:
    pip install boto3

Usage:
    python fetch_narratives.py

    Optional flags:
        --user-id  <cognito_sub>   Filter to a specific user (default: all)
        --region   <aws_region>    AWS region (default: us-east-2)
        --table    <table_name>    DynamoDB table (default: video-detections)
        --status   completed       Only include videos with this status
"""

import boto3
import json
import argparse
import os
from datetime import datetime, timezone
from decimal import Decimal


class _DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return int(o) if o == o.to_integral_value() else float(o)
        return super().default(o)

DEFAULT_TABLE  = os.getenv("DYNAMODB_TABLE_NAME", "video-detections")
DEFAULT_REGION = os.getenv("AWS_REGION", "us-east-2")


def fetch_all_videos(table_name: str, region: str, user_id: str | None, status_filter: str | None) -> list[dict]:
    dynamodb = boto3.resource("dynamodb", region_name=region)
    table    = dynamodb.Table(table_name)

    print(f"Scanning DynamoDB table '{table_name}' in region '{region}' ...")

    items = []
    kwargs = {}
    while True:
        response = table.scan(**kwargs)
        items.extend(response.get("Items", []))
        last = response.get("LastEvaluatedKey")
        if not last:
            break
        kwargs["ExclusiveStartKey"] = last

    print(f"  Total records fetched: {len(items)}")

    if user_id:
        items = [v for v in items if v.get("user_id") == user_id]
        print(f"  After user_id filter:  {len(items)}")

    if status_filter:
        items = [v for v in items if v.get("status") == status_filter]
        print(f"  After status filter:   {len(items)}")

    return items


def build_output(items: list[dict]) -> dict:
    videos = []
    for v in items:
        narrative = v.get("narrative") or ""
        if not narrative:
            # Some workers store it nested in narrative_summary
            narrative = v.get("narrative_summary") or ""

        videos.append({
            "video_id":      v.get("video_id", ""),
            "display_name":  v.get("display_name") or v.get("video_id", ""),
            "status":        v.get("status", ""),
            "created_at":    v.get("created_at", ""),
            "processed_at":  v.get("processed_at", ""),
            "narrative":     narrative,
            "narrative_model": v.get("narrative_model", ""),
            "has_narrative": bool(narrative),
        })

    videos.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return {"fetched_at": datetime.now(timezone.utc).isoformat(), "videos": videos}


def main():
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Fetch generated narratives from DynamoDB")
    parser.add_argument("--user-id", default=None,         help="Cognito sub (user_id) to filter by")
    parser.add_argument("--region",  default=DEFAULT_REGION, help="AWS region")
    parser.add_argument("--table",   default=DEFAULT_TABLE,  help="DynamoDB table name")
    parser.add_argument("--status",  default="completed",    help="Only include this status (default: completed)")
    parser.add_argument("--out",     default="generated_narratives.json", help="Output file")
    args = parser.parse_args()

    items = fetch_all_videos(args.table, args.region, args.user_id, args.status)

    if not items:
        print("No videos found. Check your AWS credentials and filters.")
        return

    output = build_output(items)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, cls=_DecimalEncoder)

    print(f"\n✓ Written {len(output['videos'])} records to '{args.out}'")
    print("\nVideo IDs and narrative status:")
    for v in output["videos"]:
        status_icon = "✓" if v["has_narrative"] else "✗"
        print(f"  {status_icon} {v['video_id'][:36]}  |  {v['display_name'][:40]:<40}  |  narrative: {status_icon}")


if __name__ == "__main__":
    main()
