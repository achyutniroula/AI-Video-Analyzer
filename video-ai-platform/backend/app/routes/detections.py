"""
Detection API Routes - WITH S3 DETECTIONS + AUDIO ANALYSIS
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from app.models.detection import (
    VideoResponse, 
    VideoDetailResponse, 
    VideoListResponse
)
from app.utils.cognito import get_current_user
from app.utils.db_handler import DBHandler
import boto3
import json
import os

router = APIRouter(prefix="/videos", tags=["videos"])
db = DBHandler()

# AWS Config
S3_BUCKET = os.getenv('S3_BUCKET_NAME', 'video-ai-uploads')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-2')
s3_client = boto3.client('s3', region_name=AWS_REGION)

@router.get("/", response_model=VideoListResponse)
async def list_user_videos(
    current_user: dict = Depends(get_current_user)
):
    """
    List all videos for the authenticated user
    
    Returns:
        - List of videos with basic info
        - Total count
        - Sorted by created_at (newest first)
    """
    user_id = current_user['user_id']
    
    # Get all videos for this user
    videos = db.get_videos_by_user(user_id)
    
    # Sort by created_at (newest first)
    videos.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    return {
        "videos": videos,
        "count": len(videos)
    }

@router.get("/{video_id}", response_model=VideoDetailResponse)
async def get_video_details(
    video_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed information about a specific video including detections
    
    Parameters:
        - video_id: The unique identifier for the video
    
    Returns:
        - Complete video information
        - All detections
        - Detection summary
    
    Raises:
        - 404: Video not found
        - 403: Video belongs to different user
    """
    # Get video from database
    video = db.get_video_by_id(video_id)
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Verify user owns this video
    if video.get('user_id') != current_user['user_id']:
        raise HTTPException(
            status_code=403, 
            detail="You don't have permission to access this video"
        )
    
    return video

@router.get("/{video_id}/detections")
async def get_video_detections(
    video_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get full detections + audio analysis for a video (from S3)
    
    This endpoint fetches the complete detection list AND audio analysis from S3
    while the main video endpoint only returns summary from DynamoDB
    
    Returns:
        - Full detection list from S3
        - Audio analysis from S3
        - Summary and metadata from DynamoDB
    """
    # Get metadata from DynamoDB
    video = db.get_video_by_id(video_id)
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if video.get('user_id') != current_user['user_id']:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # ✅ FIX: Fetch full detections + audio_analysis from S3
    s3_key = f"results/{video_id}/detections.json"
    
    detections = []
    audio_analysis = None
    
    try:
        print(f"Fetching detections from S3: {s3_key}")
        s3_response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
        detections_data = json.loads(s3_response['Body'].read())
        
        # Get detections
        detections = detections_data.get('detections', [])
        print(f"✓ Loaded {len(detections)} detections from S3")
        
        # ✅ NEW: Get audio_analysis from S3
        audio_analysis = detections_data.get('audio_analysis')
        if audio_analysis:
            print(f"✓ Loaded audio analysis from S3:")
            print(f"  - Whisper segments: {len(audio_analysis.get('transcript', {}).get('segments', []))}")
            print(f"  - Wav2Vec2 classifications: {len(audio_analysis.get('wav2vec2_classifications', []))}")
            print(f"  - Audio events: {len(audio_analysis.get('audio_events', []))}")
            print(f"  - Fused moments: {len(audio_analysis.get('fused_data', {}).get('timeline', []))}")
        else:
            print("  No audio_analysis in S3 data")
            # Fallback to DynamoDB
            audio_analysis = video.get('audio_analysis')
            if audio_analysis:
                print("  ✓ Found audio_analysis in DynamoDB (fallback)")
                
    except Exception as e:
        print(f"✗ Error fetching detections from S3: {e}")
        # Fallback: try to get from DynamoDB (old videos)
        detections = video.get('detections', [])
        audio_analysis = video.get('audio_analysis')
        print(f"  Fallback: Got {len(detections)} detections from DynamoDB")
    
    return {
        "video_id": video_id,
        "status": video.get('status'),
        "total_detections": len(detections),
        "detections": detections,
        "audio_analysis": audio_analysis,  # ✅ NOW FROM S3!
        "summary": video.get('summary', {}),
        "metadata": video.get('metadata', {}),
        "scenes": video.get('scenes', []),
        "scene_composition": video.get('scene_composition', {}),
        "lighting_analysis": video.get('lighting_analysis', {}),
    }

@router.get("/{video_id}/status")
async def get_video_status(
    video_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get just the processing status of a video (lightweight endpoint)
    
    Useful for polling while video is processing
    
    Returns:
        - video_id
        - status (processing, completed, failed)
        - updated_at
        - error_message (if failed)
    """
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
        "total_detections": video.get('summary', {}).get('total_detections', 0)
    }

@router.delete("/{video_id}")
async def delete_video(
    video_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a video and its detections (optional feature)
    
    Note: This only deletes the database record, not S3 files
    For production, you'd want to delete S3 files too
    """
    video = db.get_video_by_id(video_id)
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if video.get('user_id') != current_user['user_id']:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Delete from database
    try:
        db.table.delete_item(Key={'video_id': video_id})
        return {"message": "Video deleted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to delete video: {str(e)}"
        )