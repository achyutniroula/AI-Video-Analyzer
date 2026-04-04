"""
Narrative Generation Routes - FIXED TO FETCH FROM S3
Endpoints for generating AI-powered video narratives
"""

from fastapi import APIRouter, HTTPException
from typing import Dict
import boto3
import json
from decimal import Decimal
from datetime import datetime
import os
import anthropic

from app.utils.narrative_service import generate_phase4_narrative

router = APIRouter()

# Initialize AWS clients
dynamodb = boto3.resource(
    'dynamodb',
    region_name=os.getenv('AWS_REGION', 'us-east-2')
)
table = dynamodb.Table('video-detections')

s3_client = boto3.client(
    's3',
    region_name=os.getenv('AWS_REGION', 'us-east-2')
)
S3_BUCKET = os.getenv('S3_BUCKET_NAME', 'video-ai-uploads')


def _generate_summary(narrative_text: str) -> str:
    """Use Claude to generate a 1-2 sentence summary of a narrative."""
    try:
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=120,
            messages=[{
                "role": "user",
                "content": (
                    "Write a 1-2 sentence executive summary of this video analysis narrative. "
                    "Be concise and specific about what is in the video:\n\n" + narrative_text[:2000]
                )
            }],
        )
        return response.content[0].text.strip()
    except Exception as e:
        print(f"Summary generation failed: {e}")
        return ""


def decimal_to_float(obj):
    """Convert Decimal to float for JSON serialization"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(item) for item in obj]
    return obj


@router.post("/videos/{video_id}/narrative")
async def generate_narrative(video_id: str):
    """
    Generate AI narrative for a video
    
    Args:
        video_id: UUID of the video
    
    Returns:
        Generated narrative with key moments and summary
    """
    
    try:
        # Get video metadata from DynamoDB
        response = table.get_item(Key={'video_id': video_id})
        
        if 'Item' not in response:
            raise HTTPException(status_code=404, detail=f"Video {video_id} not found")
        
        video_data = response['Item']
        video_data = decimal_to_float(video_data)
        
        # New worker pre-generates the narrative and stores it as a plain string
        # in DynamoDB. Return it directly without regenerating.
        existing_narrative = video_data.get('narrative')
        if isinstance(existing_narrative, str) and existing_narrative:
            print(f"✓ Returning pre-generated narrative for {video_id} (new worker)")
            narrative_text = existing_narrative
            # Use stored summary (new worker saves it) or generate on the fly
            summary_text = video_data.get('narrative_summary') or ''
            if not summary_text:
                summary_text = _generate_summary(narrative_text)
            return {
                "video_id": video_id,
                "narrative": narrative_text,
                "key_moments": [],
                "summary": summary_text,
                "confidence": "high",
                "metadata": {
                    "detection_count": video_data.get('frame_count', 0),
                    "has_audio": bool(video_data.get('audio_analysis')),
                    "duration": float(video_data.get('duration', 0) or 0),
                },
                "generated_at": int(datetime.now().timestamp()),
            }

        # Old worker path: generate narrative from detections
        metadata = video_data.get('metadata', {})
        summary = video_data.get('summary', {})

        s3_key = video_data.get('results_s3_key') or f"results/{video_id}/detections.json"

        try:
            print(f"📥 Fetching detections from S3: {s3_key}")
            s3_response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
            detections_data = json.loads(s3_response['Body'].read())
            detections = detections_data.get('detections', [])
            print(f"✓ Loaded {len(detections)} detections from S3")
        except Exception as e:
            print(f"✗ Error fetching detections from S3: {e}")
            detections = video_data.get('detections', [])
            print(f"  Fallback: Got {len(detections)} detections from DynamoDB")

        if not detections:
            raise HTTPException(
                status_code=400,
                detail="No detections found for this video. Video may not have been processed yet."
            )

        audio_analysis = video_data.get('audio_analysis', None)

        print(f"🤖 Generating narrative for video {video_id}...")
        print(f"  📊 Detections: {len(detections)}")
        print(f"  🎤 Audio: {'Yes' if audio_analysis else 'No'}")

        complete_video_data = {
            'video_id': video_id,
            'metadata': metadata,
            'detections': detections,
            'summary': summary,
            'scenes': video_data.get('scenes', []),
            'lighting_analysis': video_data.get('lighting_analysis', {}),
            'scene_composition': video_data.get('scene_composition', {}),
            'audio_analysis': audio_analysis
        }

        narrative_text = generate_phase4_narrative(complete_video_data)

        narrative_result = {
            'narrative': narrative_text,
            'key_moments': [],
            'summary': narrative_text[:500] + '...' if len(narrative_text) > 500 else narrative_text,
            'confidence': 'high'
        }

        try:
            table.update_item(
                Key={'video_id': video_id},
                UpdateExpression='SET narrative = :narrative, narrative_generated_at = :timestamp',
                ExpressionAttributeValues={
                    ':narrative': narrative_result,
                    ':timestamp': int(datetime.now().timestamp())
                }
            )
            print(f"✓ Narrative saved to DynamoDB")
        except Exception as e:
            print(f"⚠️  Could not save narrative to DynamoDB: {e}")

        return {
            "video_id": video_id,
            "narrative": narrative_result['narrative'],
            "key_moments": narrative_result.get('key_moments', []),
            "summary": narrative_result.get('summary', ''),
            "confidence": narrative_result.get('confidence', 'medium'),
            "metadata": {
                "detection_count": len(detections),
                "has_audio": bool(audio_analysis),
                "duration": metadata.get('duration', 0)
            },
            "generated_at": int(datetime.now().timestamp())
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error generating narrative: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/videos/{video_id}/narrative")
async def get_narrative(video_id: str):
    """
    Get existing narrative for a video
    
    Args:
        video_id: UUID of the video
    
    Returns:
        Previously generated narrative or 404 if not found
    """
    
    try:
        # Get video data from DynamoDB
        response = table.get_item(Key={'video_id': video_id})
        
        if 'Item' not in response:
            raise HTTPException(status_code=404, detail=f"Video {video_id} not found")
        
        video_data = response['Item']
        video_data = decimal_to_float(video_data)
        
        # Check if narrative exists
        if 'narrative' not in video_data:
            raise HTTPException(
                status_code=404,
                detail="No narrative generated yet"
            )

        narrative = video_data['narrative']

        # New worker stores narrative as a plain string;
        # old worker stored it as a dict.
        if isinstance(narrative, str):
            narrative_text = narrative
            key_moments = []
            # Use stored summary if available, otherwise generate one
            summary_text = video_data.get('narrative_summary') or ''
            if not summary_text:
                summary_text = _generate_summary(narrative_text)
            confidence = 'high'
            generated_at = video_data.get('processed_at')
        else:
            narrative_text = narrative.get('narrative', '')
            key_moments = narrative.get('key_moments', [])
            summary_text = narrative.get('summary', '')
            confidence = narrative.get('confidence', 'medium')
            generated_at = video_data.get('narrative_generated_at')

        return {
            "video_id": video_id,
            "narrative": narrative_text,
            "key_moments": key_moments,
            "summary": summary_text,
            "confidence": confidence,
            "generated_at": generated_at,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching narrative: {e}")
        raise HTTPException(status_code=500, detail=str(e))