"""
DynamoDB Handler - Store and retrieve video metadata
"""

import boto3
from botocore.exceptions import ClientError
from config import settings
from datetime import datetime
from typing import Optional, Dict, Any

class DBHandler:
    def __init__(self):
        self.dynamodb = boto3.resource(
            'dynamodb',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        self.table = self.dynamodb.Table(settings.DYNAMODB_TABLE_NAME)
    
    def create_video_record(self, video_id: str, user_id: str, s3_key: str) -> bool:
        """
        Create initial video record in database
        """
        try:
            self.table.put_item(
                Item={
                    'video_id': video_id,
                    'user_id': user_id,
                    's3_key': s3_key,
                    'status': 'processing',
                    'created_at': datetime.utcnow().isoformat(),
                    'updated_at': datetime.utcnow().isoformat()
                },
                ConditionExpression='attribute_not_exists(video_id)'  # Idempotency
            )
            print(f"✓ Created database record for {video_id}")
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                print(f"Record already exists for {video_id} (idempotency check)")
                return True  # Already processed
            print(f"✗ Failed to create record: {e}")
            return False
    
    def update_status(self, video_id: str, status: str, error: str = None) -> bool:
        """
        Update processing status
        """
        try:
            update_expr = "SET #status = :status, updated_at = :updated_at"
            expr_values = {
                ':status': status,
                ':updated_at': datetime.utcnow().isoformat()
            }
            
            if error:
                update_expr += ", error_message = :error"
                expr_values[':error'] = error
            
            self.table.update_item(
                Key={'video_id': video_id},
                UpdateExpression=update_expr,
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues=expr_values
            )
            print(f"✓ Updated status to '{status}' for {video_id}")
            return True
            
        except ClientError as e:
            print(f"✗ Failed to update status: {e}")
            return False
    
    def save_detections(self, video_id: str, detections: list, metadata: dict) -> bool:
        """
        Save detection SUMMARY to DynamoDB (full detections already in S3)
        This avoids the 400KB DynamoDB item size limit
        """
        try:
            # Calculate summary statistics
            total_dets = len(detections)
            
            # Count by class
            by_class = {}
            by_model = {}
            by_type = {}
            tracked_ids = set()
            
            for det in detections:
                # Count by class
                class_name = det.get('class_name', 'unknown')
                by_class[class_name] = by_class.get(class_name, 0) + 1
                
                # Count by model source
                model_source = det.get('model_source', 'unknown')
                by_model[model_source] = by_model.get(model_source, 0) + 1
                
                # Count by model type
                model_type = det.get('model_type', 'unknown')
                by_type[model_type] = by_type.get(model_type, 0) + 1
                
                # Track unique objects
                track_id = det.get('track_id')
                if track_id:
                    tracked_ids.add(track_id)
            
            # Build comprehensive summary
            summary = {
                'total_detections': total_dets,
                'unique_tracked_objects': len(tracked_ids),
                'by_class': by_class,
                'by_model': by_model,
                'by_type': by_type
            }
            
            # Extract additional metadata if available
            scenes = metadata.get('scenes', [])
            lighting = metadata.get('lighting_analysis', {})
            scene_comp = metadata.get('scene_composition', {})
            
            # Update DynamoDB with SUMMARY only (not full detections array)
            update_expr = """
                SET summary = :summary,
                    metadata = :metadata,
                    #status = :status,
                    updated_at = :updated_at,
                    processed_at = :processed_at
            """
            
            expr_values = {
                ':summary': summary,
                ':metadata': metadata,
                ':status': 'completed',
                ':updated_at': datetime.utcnow().isoformat(),
                ':processed_at': datetime.utcnow().isoformat()
            }
            
            # Add optional fields if available
            if scenes:
                update_expr += ", scenes = :scenes"
                expr_values[':scenes'] = scenes
            
            if lighting:
                update_expr += ", lighting_analysis = :lighting"
                expr_values[':lighting'] = lighting
            
            if scene_comp:
                update_expr += ", scene_composition = :scene_comp"
                expr_values[':scene_comp'] = scene_comp
            
            self.table.update_item(
                Key={'video_id': video_id},
                UpdateExpression=update_expr,
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues=expr_values
            )
            
            print(f"✓ Saved summary to DynamoDB ({total_dets} detections)")
            print(f"  Unique tracked objects: {len(tracked_ids)}")
            print(f"  Full detections available in S3: results/{video_id}/detections.json")
            return True
            
        except ClientError as e:
            print(f"✗ Failed to save summary: {e}")
            return False
    
    def get_video(self, video_id: str) -> Optional[Dict[Any, Any]]:
        """
        Get video record from database
        """
        try:
            response = self.table.get_item(Key={'video_id': video_id})
            return response.get('Item')
            
        except ClientError as e:
            print(f"✗ Failed to get video: {e}")
            return None