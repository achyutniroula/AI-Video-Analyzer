"""
Detection API Models - COMPLETE FIXED VERSION
Matches DynamoDB structure exactly
"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class BoundingBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float

class Detection(BaseModel):
    frame: int
    timestamp: float
    class_id: int
    class_name: str
    confidence: float
    bbox: BoundingBox
    track_id: Optional[int] = None
    area: Optional[float] = None
    
    # MODEL ATTRIBUTION FIELDS - Added for model breakdown
    model_source: Optional[str] = None
    model_type: Optional[str] = None
    ensemble_models: Optional[List[str]] = None
    tracking_source: Optional[str] = None
    
    class Config:
        # Allow extra fields from DynamoDB that aren't in schema
        extra = "allow"

class VideoMetadata(BaseModel):
    width: int
    height: int
    fps: float
    total_frames: int
    duration: float
    frames_processed: int
    processing_mode: Optional[str] = None
    ensemble_models: Optional[List[str]] = None
    has_audio: Optional[bool] = None
    wbf_enabled: Optional[bool] = None
    panoptic_enabled: Optional[bool] = None
    
    class Config:
        extra = "allow"

class DetectionSummary(BaseModel):
    """
    ✅ FIXED: Field names match DynamoDB exactly
    
    DynamoDB structure:
    {
      "total_detections": 5485,
      "unique_tracked_objects": 30,
      "by_class": {...},
      "by_model": {...},
      "by_type": {...}
    }
    """
    total_detections: int                          # ✅ Was 'total'
    unique_tracked_objects: int                    # ✅ Was 'unique_classes'
    by_class: Dict[str, int]
    by_model: Optional[Dict[str, int]] = None      # ✅ Added - Phase 2 WBF
    by_type: Optional[Dict[str, int]] = None       # ✅ Added - Multi-model types
    
    # Optional fields for additional analysis
    dominant_objects: Optional[List[Dict[str, Any]]] = None
    processing_quality: Optional[str] = None
    optimization: Optional[str] = None
    model_contributions: Optional[Dict[str, Any]] = None
    has_audio: Optional[bool] = None
    speech_segments: Optional[int] = None
    audio_confirmations: Optional[int] = None
    
    class Config:
        extra = "allow"

class VideoResponse(BaseModel):
    video_id: str
    user_id: str
    s3_key: str
    status: str
    created_at: str
    updated_at: str
    processed_at: Optional[str] = None
    total_detections: Optional[int] = None
    metadata: Optional[VideoMetadata] = None
    error_message: Optional[str] = None
    display_name: Optional[str] = None
    folder_path: Optional[str] = None

class VideoDetailResponse(VideoResponse):
    """
    Complete video details with all analysis results
    """
    detections: Optional[List[Detection]] = None
    summary: Optional[DetectionSummary] = None
    
    # Phase 1 - CLIP Scene Understanding
    scenes: Optional[List[Dict[str, Any]]] = None
    
    # Phase 3 - Panoptic Segmentation
    scene_composition: Optional[Dict[str, Any]] = None
    
    # Additional analysis
    lighting_analysis: Optional[Dict[str, Any]] = None
    motion_analysis: Optional[Dict[str, Any]] = None
    
    # Enhanced Audio Analysis
    audio_analysis: Optional[Dict[str, Any]] = None
    
    class Config:
        extra = "allow"

class VideoListResponse(BaseModel):
    videos: List[VideoResponse]
    count: int