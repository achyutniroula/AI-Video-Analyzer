from fastapi import APIRouter, HTTPException, Depends
from app.models.video import UploadRequest, UploadResponse, UploadConfirmation
from app.utils.s3 import generate_presigned_upload_url, verify_file_exists
from app.utils.cognito import get_current_user
from app.config import settings
import os, json, boto3
from datetime import datetime

router = APIRouter(prefix="/upload", tags=["upload"])

@router.post("/get-presigned-url", response_model=UploadResponse)
async def get_presigned_url(
    request: UploadRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate a pre-signed URL for video upload
    """
    if not request.content_type.startswith('video/'):
        raise HTTPException(status_code=400, detail="Only video files are allowed")
    try:
        result = generate_presigned_upload_url(
            filename=request.filename,
            content_type=request.content_type,
            user_id=current_user['user_id']
        )
        return UploadResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/confirm")
async def confirm_upload(
    confirmation: UploadConfirmation,
    current_user: dict = Depends(get_current_user)
):
    """
    Confirm upload and trigger processing: save to DynamoDB + enqueue SQS message.
    """
    if not verify_file_exists(confirmation.file_key):
        raise HTTPException(status_code=404, detail="File not found in S3")

    # Derive video_id from the S3 key so it matches what the worker extracts
    video_id = os.path.splitext(os.path.basename(confirmation.file_key))[0]
    user_id  = current_user['user_id']
    now      = datetime.utcnow().isoformat()

    # Save initial record to DynamoDB
    dynamodb = boto3.resource(
        'dynamodb',
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )
    table = dynamodb.Table(settings.DYNAMODB_TABLE_NAME)
    table.put_item(Item={
        'video_id':   video_id,
        'user_id':    user_id,
        's3_key':     confirmation.file_key,
        'status':     'pending',
        'created_at': now,
        'updated_at': now,
    })

    # Send SQS message in the S3-event format the worker expects
    sqs = boto3.client(
        'sqs',
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )
    message_body = json.dumps({
        "Records": [{
            "eventName": "ObjectCreated:Put",
            "s3": {
                "bucket": {"name": settings.S3_BUCKET_NAME},
                "object": {"key": confirmation.file_key, "size": 0},
            },
        }],
        "disabled_modules": confirmation.disabled_modules,
    })
    sqs.send_message(QueueUrl=settings.SQS_QUEUE_URL, MessageBody=message_body)

    return {
        "message": "Upload confirmed successfully",
        "video_id": video_id,
        "status": "pending",
    }
 
@router.get("/status/{video_id}")
async def get_video_status(
    video_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get processing status of a video
    """
    # TODO: Fetch from database
    return {
        "video_id": video_id,
        "status": "processing",
        "message": "Video is being processed"
    }