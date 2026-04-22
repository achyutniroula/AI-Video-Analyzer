"""
Detection API Routes — list, detail, detections, rename, delete, thumbnail, logs
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from app.models.detection import VideoResponse, VideoDetailResponse, VideoListResponse
from app.utils.cognito import get_current_user
from app.utils.db_handler import DBHandler
import boto3
from botocore.exceptions import ClientError
import json
import os
import subprocess
import tempfile

router = APIRouter(prefix="/videos", tags=["videos"])
db = DBHandler()

S3_BUCKET = os.getenv('S3_BUCKET_NAME', 'video-ai-uploads')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-2')
s3_client = boto3.client('s3', region_name=AWS_REGION)


class RenameRequest(BaseModel):
    display_name: str

class FolderRequest(BaseModel):
    folder_path: Optional[str] = None


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("/", response_model=VideoListResponse)
async def list_user_videos(current_user: dict = Depends(get_current_user)):
    user_id = current_user['user_id']
    videos = db.get_videos_by_user(user_id)
    videos.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return {"videos": videos, "count": len(videos)}


# ── System-level logs (before /{video_id} to avoid route conflict) ─────────

@router.get("/system/logs")
async def get_system_logs(current_user: dict = Depends(get_current_user)):
    """Return processing logs for all videos belonging to this user."""
    videos = db.get_videos_by_user(current_user['user_id'])
    videos.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return {
        "videos": [
            {
                "video_id": v['video_id'],
                "display_name": v.get('display_name') or v['video_id'],
                "status": v.get('status'),
                "created_at": v.get('created_at'),
                "processed_at": v.get('processed_at'),
                "error_message": v.get('error_message'),
                "processing_logs": v.get('processing_logs', []),
                "has_raw_log": bool(v.get('raw_log_s3_key')),
            }
            for v in videos
        ]
    }


# ── Video detail ──────────────────────────────────────────────────────────────

@router.get("/{video_id}", response_model=VideoDetailResponse)
async def get_video_details(video_id: str, current_user: dict = Depends(get_current_user)):
    video = db.get_video_by_id(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if video.get('user_id') != current_user['user_id']:
        raise HTTPException(status_code=403, detail="Access denied")
    return video


# ── Detections (full S3 payload) ──────────────────────────────────────────────

@router.get("/{video_id}/detections")
async def get_video_detections(video_id: str, current_user: dict = Depends(get_current_user)):
    video = db.get_video_by_id(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if video.get('user_id') != current_user['user_id']:
        raise HTTPException(status_code=403, detail="Access denied")

    s3_key = video.get('results_s3_key') or f"results/{video_id}/detections.json"
    detections = []
    audio_analysis = None
    summary = video.get('summary', {})
    metadata = video.get('metadata', {})
    scenes = video.get('scenes', [])
    scene_composition = video.get('scene_composition', {})
    lighting_analysis = video.get('lighting_analysis', {})

    try:
        print(f"Fetching analysis from S3: {s3_key}")
        s3_response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
        s3_data = json.loads(s3_response['Body'].read())

        if 'detections' in s3_data:
            detections = s3_data.get('detections', [])
            audio_analysis = s3_data.get('audio_analysis') or video.get('audio_analysis')
            print(f"✓ Loaded {len(detections)} detections from S3 (old format)")
        else:
            scenes = [{"scene_type": st} for st in s3_data.get('scene_types', [])]
            object_class_counts = s3_data.get('object_class_counts', {})
            summary = {
                "total_detections": sum(object_class_counts.values()) if object_class_counts else 0,
                "unique_tracked_objects": s3_data.get('num_object_tracks', 0),
                "by_class": object_class_counts,
            }
            metadata = {
                "duration": s3_data.get('duration', 0),
                "frames_processed": s3_data.get('frame_count', 0),
                "processing_mode": "multimodal-newworker",
            }
            # Extract audio from new worker format (prefer S3 data over DynamoDB)
            audio_analysis = s3_data.get('audio_analysis') or video.get('audio_analysis')
            print(f"✓ Loaded new-worker analysis from S3 ({s3_data.get('frame_count', 0)} frames)")

    except Exception as e:
        print(f"✗ S3 fetch error: {e}")
        detections = video.get('detections', [])
        audio_analysis = video.get('audio_analysis')

    return {
        "video_id": video_id,
        "status": video.get('status'),
        "total_detections": len(detections),
        "detections": detections,
        "audio_analysis": audio_analysis,
        "summary": summary,
        "metadata": metadata,
        "scenes": scenes,
        "scene_composition": scene_composition,
        "lighting_analysis": lighting_analysis,
        "narrative": video.get('narrative'),
        "scene_types": video.get('scene_types', []),
        "frame_count": video.get('frame_count'),
        "duration": video.get('duration'),
    }


# ── Status (lightweight) ──────────────────────────────────────────────────────

@router.get("/{video_id}/status")
async def get_video_status(video_id: str, current_user: dict = Depends(get_current_user)):
    video = db.get_video_by_id(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if video.get('user_id') != current_user['user_id']:
        raise HTTPException(status_code=403, detail="Access denied")
    return {
        "video_id": video['video_id'],
        "status": video['status'],
        "updated_at": video.get('updated_at'),
        "error_message": video.get('error_message'),
        "total_detections": (
            video.get('summary', {}).get('total_detections') or video.get('frame_count', 0)
        )
    }


# ── Thumbnail presigned URL ───────────────────────────────────────────────────

@router.get("/{video_id}/thumbnail")
async def get_thumbnail(video_id: str, current_user: dict = Depends(get_current_user)):
    video = db.get_video_by_id(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if video.get('user_id') != current_user['user_id']:
        raise HTTPException(status_code=403, detail="Access denied")

    s3_key = video.get('thumbnail_s3_key') or f"thumbnails/{video_id}.jpg"
    try:
        s3_client.head_object(Bucket=S3_BUCKET, Key=s3_key)
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET, 'Key': s3_key},
            ExpiresIn=3600,
        )
        return {"thumbnail_url": url}
    except ClientError:
        raise HTTPException(status_code=404, detail="Thumbnail not available yet")


# ── Generate thumbnail on-demand ─────────────────────────────────────────────

@router.post("/{video_id}/thumbnail/generate")
async def generate_thumbnail(video_id: str, current_user: dict = Depends(get_current_user)):
    """
    Generate a thumbnail for an existing video by streaming it from S3 via a
    presigned URL into ffmpeg (no full download — ffmpeg seeks to 1s and stops).
    Stores the result at thumbnails/{video_id}.jpg and updates DynamoDB.
    """
    video = db.get_video_by_id(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if video.get('user_id') != current_user['user_id']:
        raise HTTPException(status_code=403, detail="Access denied")

    s3_key = video.get('s3_key') or f"uploads/{video.get('user_id')}/{video_id}.mp4"

    # Generate a short-lived presigned URL for the source video
    try:
        video_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET, 'Key': s3_key},
            ExpiresIn=300,
        )
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"Could not access source video: {e}")

    tmp_thumb_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp_thumb_path = tmp.name

        # Try 1s seek first, then 0s (first frame) as fallback
        extracted = False
        for seek in ['1', '0']:
            cmd = [
                'ffmpeg', '-y',
                '-ss', seek,
                '-i', video_url,
                '-vframes', '1',
                '-q:v', '3',
                '-loglevel', 'error',
                tmp_thumb_path,
            ]
            try:
                subprocess.run(cmd, capture_output=True, timeout=60)
            except subprocess.TimeoutExpired:
                continue
            if os.path.exists(tmp_thumb_path) and os.path.getsize(tmp_thumb_path) > 0:
                extracted = True
                break

        if not extracted:
            raise HTTPException(status_code=500, detail="ffmpeg could not extract a frame")

        # Upload thumbnail to S3
        thumb_key = f"thumbnails/{video_id}.jpg"
        with open(tmp_thumb_path, 'rb') as f:
            s3_client.put_object(
                Bucket=S3_BUCKET,
                Key=thumb_key,
                Body=f.read(),
                ContentType='image/jpeg',
            )

        # Persist thumbnail key in DynamoDB
        try:
            db.table.update_item(
                Key={'video_id': video_id},
                UpdateExpression="SET thumbnail_s3_key = :key",
                ExpressionAttributeValues={":key": thumb_key},
            )
        except Exception:
            pass  # non-fatal — thumbnail is in S3 regardless

        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET, 'Key': thumb_key},
            ExpiresIn=3600,
        )
        return {"thumbnail_url": url}

    finally:
        if tmp_thumb_path and os.path.exists(tmp_thumb_path):
            os.remove(tmp_thumb_path)


# ── Per-video processing logs ─────────────────────────────────────────────────

@router.get("/{video_id}/logs")
async def get_video_logs(video_id: str, current_user: dict = Depends(get_current_user)):
    video = db.get_video_by_id(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if video.get('user_id') != current_user['user_id']:
        raise HTTPException(status_code=403, detail="Access denied")
    return {
        "video_id": video_id,
        "display_name": video.get('display_name') or video_id,
        "status": video.get('status'),
        "logs": video.get('processing_logs', []),
    }


# ── Raw worker log (full stdout captured during processing) ───────────────────

@router.get("/{video_id}/raw-log")
async def get_raw_log(video_id: str, current_user: dict = Depends(get_current_user)):
    """Return the full raw stdout log captured during worker processing."""
    video = db.get_video_by_id(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if video.get('user_id') != current_user['user_id']:
        raise HTTPException(status_code=403, detail="Access denied")

    log_key = video.get('raw_log_s3_key')
    if not log_key:
        raise HTTPException(status_code=404, detail="No raw log available for this video")

    try:
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=log_key)
        log_text = response['Body'].read().decode('utf-8', errors='replace')
        return {"log": log_text}
    except ClientError:
        raise HTTPException(status_code=404, detail="Log file not found in S3")


# ── Rename ─────────────────────────────────────────────────────────────────────

@router.patch("/{video_id}/rename")
async def rename_video(video_id: str, body: RenameRequest, current_user: dict = Depends(get_current_user)):
    video = db.get_video_by_id(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if video.get('user_id') != current_user['user_id']:
        raise HTTPException(status_code=403, detail="Access denied")
    if not body.display_name.strip():
        raise HTTPException(status_code=400, detail="Name cannot be empty")
    try:
        db.table.update_item(
            Key={'video_id': video_id},
            UpdateExpression="SET display_name = :name",
            ExpressionAttributeValues={":name": body.display_name.strip()},
        )
        return {"message": "Renamed successfully", "display_name": body.display_name.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rename failed: {str(e)}")


# ── Move to folder ────────────────────────────────────────────────────────────

@router.patch("/{video_id}/folder")
async def move_video_to_folder(video_id: str, body: FolderRequest, current_user: dict = Depends(get_current_user)):
    video = db.get_video_by_id(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if video.get('user_id') != current_user['user_id']:
        raise HTTPException(status_code=403, detail="Access denied")
    try:
        if body.folder_path and body.folder_path.strip():
            db.table.update_item(
                Key={'video_id': video_id},
                UpdateExpression="SET folder_path = :fp",
                ExpressionAttributeValues={":fp": body.folder_path.strip()},
            )
            return {"message": "Moved successfully", "folder_path": body.folder_path.strip()}
        else:
            db.table.update_item(
                Key={'video_id': video_id},
                UpdateExpression="REMOVE folder_path",
            )
            return {"message": "Moved to root", "folder_path": None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Move failed: {str(e)}")


# ── Delete ─────────────────────────────────────────────────────────────────────

@router.delete("/{video_id}")
async def delete_video(video_id: str, current_user: dict = Depends(get_current_user)):
    video = db.get_video_by_id(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if video.get('user_id') != current_user['user_id']:
        raise HTTPException(status_code=403, detail="Access denied")

    user_id = video.get('user_id')

    # Delete S3 objects (video, results, thumbnail) — best effort
    s3_keys_to_delete = [
        f"uploads/{user_id}/{video_id}.mp4",
        f"results/{video_id}/analysis.json",
        f"results/{video_id}/detections.json",
        f"thumbnails/{video_id}.jpg",
    ]
    if video.get('results_s3_key'):
        s3_keys_to_delete.append(video['results_s3_key'])

    for key in set(s3_keys_to_delete):
        try:
            s3_client.delete_object(Bucket=S3_BUCKET, Key=key)
        except Exception:
            pass  # best effort

    # Delete DynamoDB record
    try:
        db.table.delete_item(Key={'video_id': video_id})
        return {"message": "Video deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete video: {str(e)}")
