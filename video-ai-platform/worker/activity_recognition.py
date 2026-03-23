"""
ACTIVITY RECOGNITION FROM POSE KEYPOINTS
Classifies human actions: sitting, standing, walking, looking, embracing, etc.
"""

import numpy as np
from typing import Dict, List, Tuple

class ActivityRecognizer:
    """
    Recognizes human activities from YOLOv11 pose keypoints
    
    YOLOv11-Pose provides 17 keypoints:
    0: nose, 1-2: eyes, 3-4: ears, 5-6: shoulders,
    7-8: elbows, 9-10: wrists, 11-12: hips,
    13-14: knees, 15-16: ankles
    """
    
    def __init__(self):
        self.keypoint_names = [
            'nose', 'left_eye', 'right_eye', 'left_ear', 'right_ear',
            'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
            'left_wrist', 'right_wrist', 'left_hip', 'right_hip',
            'left_knee', 'right_knee', 'left_ankle', 'right_ankle'
        ]
    
    def recognize_activity(self, keypoints: np.ndarray, confidence: np.ndarray) -> Dict:
        """
        Recognize activity from pose keypoints
        
        Args:
            keypoints: (17, 2) array of (x, y) coordinates
            confidence: (17,) array of keypoint confidences
            
        Returns:
            {
                'activity': 'sitting' | 'standing' | 'walking' | 'looking_up' | 'embracing' | 'balancing',
                'confidence': float,
                'details': dict with additional info
            }
        """
        # Filter low-confidence keypoints
        valid_kpts = confidence > 0.5
        if not valid_kpts.any():
            return {'activity': 'unknown', 'confidence': 0.0, 'details': {}}
        
        # Extract key body parts
        nose = keypoints[0] if valid_kpts[0] else None
        left_shoulder = keypoints[5] if valid_kpts[5] else None
        right_shoulder = keypoints[6] if valid_kpts[6] else None
        left_hip = keypoints[11] if valid_kpts[11] else None
        right_hip = keypoints[12] if valid_kpts[12] else None
        left_knee = keypoints[13] if valid_kpts[13] else None
        right_knee = keypoints[14] if valid_kpts[14] else None
        left_ankle = keypoints[15] if valid_kpts[15] else None
        right_ankle = keypoints[16] if valid_kpts[16] else None
        left_wrist = keypoints[9] if valid_kpts[9] else None
        right_wrist = keypoints[10] if valid_kpts[10] else None
        
        # Calculate body metrics
        results = []
        
        # Check for SITTING
        sitting_score = self._check_sitting(
            left_hip, right_hip, left_knee, right_knee, left_ankle, right_ankle
        )
        if sitting_score > 0.6:
            results.append(('sitting', sitting_score, {}))
        
        # Check for STANDING
        standing_score = self._check_standing(
            left_shoulder, right_shoulder, left_hip, right_hip, left_knee, right_knee
        )
        if standing_score > 0.6:
            results.append(('standing', standing_score, {}))
        
        # Check for LOOKING UP/DOWN
        looking = self._check_looking_direction(nose, left_shoulder, right_shoulder)
        if looking['score'] > 0.5:
            results.append((looking['activity'], looking['score'], {'direction': looking['direction']}))
        
        # Check for ARMS STRETCHED (balancing)
        balancing_score = self._check_balancing(
            left_shoulder, right_shoulder, left_wrist, right_wrist
        )
        if balancing_score > 0.6:
            results.append(('balancing', balancing_score, {'arms_stretched': True}))
        
        # Check for EMBRACING (close to another person - needs multiple pose data)
        # This is checked separately in recognize_multi_person_activity
        
        # Return highest confidence activity
        if results:
            results.sort(key=lambda x: x[1], reverse=True)
            activity, conf, details = results[0]
            return {
                'activity': activity,
                'confidence': float(conf),
                'details': details
            }
        
        return {'activity': 'standing', 'confidence': 0.5, 'details': {}}
    
    def _check_sitting(self, left_hip, right_hip, left_knee, right_knee, 
                       left_ankle, right_ankle) -> float:
        """Check if person is sitting"""
        if left_hip is None or right_hip is None or left_knee is None or right_knee is None:
            return 0.0
        
        # Sitting: knees are ABOVE ankles (smaller y value)
        # and hips are close to knee level
        score = 0.0
        
        # Average positions
        hip_y = (left_hip[1] + right_hip[1]) / 2
        knee_y = (left_knee[1] + right_knee[1]) / 2
        
        # In sitting position, hips and knees should be at similar height
        hip_knee_diff = abs(hip_y - knee_y)
        
        if hip_knee_diff < 50:  # pixels - close together
            score += 0.5
        
        # Check if knees are bent (angle check)
        if left_ankle is not None and right_ankle is not None:
            ankle_y = (left_ankle[1] + right_ankle[1]) / 2
            
            # In sitting, ankles should be below or at knee level
            if ankle_y >= knee_y - 20:
                score += 0.5
        
        return min(score, 1.0)
    
    def _check_standing(self, left_shoulder, right_shoulder, left_hip, right_hip,
                        left_knee, right_knee) -> float:
        """Check if person is standing upright"""
        if left_shoulder is None or right_shoulder is None:
            return 0.0
        if left_hip is None or right_hip is None:
            return 0.0
        
        score = 0.0
        
        # Standing: vertical alignment
        shoulder_y = (left_shoulder[1] + right_shoulder[1]) / 2
        hip_y = (left_hip[1] + right_hip[1]) / 2
        
        # Shoulders should be above hips
        if shoulder_y < hip_y - 30:
            score += 0.5
        
        # Check vertical alignment (shoulders and hips roughly aligned horizontally)
        shoulder_x = (left_shoulder[0] + right_shoulder[0]) / 2
        hip_x = (left_hip[0] + right_hip[0]) / 2
        
        horizontal_diff = abs(shoulder_x - hip_x)
        if horizontal_diff < 30:  # Good vertical posture
            score += 0.5
        
        return min(score, 1.0)
    
    def _check_looking_direction(self, nose, left_shoulder, right_shoulder) -> Dict:
        """Check if person is looking up, down, or straight"""
        if nose is None or left_shoulder is None or right_shoulder is None:
            return {'activity': 'looking_straight', 'score': 0.0, 'direction': 'straight'}
        
        shoulder_y = (left_shoulder[1] + right_shoulder[1]) / 2
        nose_y = nose[1]
        
        # Looking up: nose significantly above shoulders
        if nose_y < shoulder_y - 40:
            return {
                'activity': 'looking_up',
                'score': 0.8,
                'direction': 'up'
            }
        
        # Looking down: nose close to or below shoulders
        elif nose_y > shoulder_y + 20:
            return {
                'activity': 'looking_down',
                'score': 0.7,
                'direction': 'down'
            }
        
        return {'activity': 'looking_straight', 'score': 0.6, 'direction': 'straight'}
    
    def _check_balancing(self, left_shoulder, right_shoulder, 
                         left_wrist, right_wrist) -> float:
        """Check if person has arms stretched out (balancing)"""
        if left_shoulder is None or right_shoulder is None:
            return 0.0
        if left_wrist is None or right_wrist is None:
            return 0.0
        
        # Calculate shoulder width
        shoulder_width = abs(left_shoulder[0] - right_shoulder[0])
        
        # Calculate arm span
        arm_span = abs(left_wrist[0] - right_wrist[0])
        
        # If arm span is significantly wider than shoulders, arms are stretched
        if arm_span > shoulder_width * 1.5:
            # Check if arms are roughly horizontal (similar y-coordinates)
            wrist_y_diff = abs(left_wrist[1] - right_wrist[1])
            shoulder_y = (left_shoulder[1] + right_shoulder[1]) / 2
            wrist_y = (left_wrist[1] + right_wrist[1]) / 2
            
            # Arms at shoulder height
            if abs(wrist_y - shoulder_y) < 50 and wrist_y_diff < 50:
                return 0.8
        
        return 0.0
    
    def recognize_multi_person_activity(self, poses: List[Dict]) -> List[Dict]:
        """
        Recognize activities involving multiple people
        
        Args:
            poses: List of pose data with keypoints
            
        Returns:
            List of interactions detected (embracing, walking_together, etc.)
        """
        if len(poses) < 2:
            return []
        
        interactions = []
        
        # Check each pair of people
        for i in range(len(poses)):
            for j in range(i + 1, len(poses)):
                pose1 = poses[i]
                pose2 = poses[j]
                
                # Check for EMBRACING
                embrace = self._check_embracing(pose1, pose2)
                if embrace['score'] > 0.6:
                    interactions.append({
                        'activity': 'embracing',
                        'confidence': embrace['score'],
                        'people_indices': [i, j],
                        'details': embrace
                    })
                
                # Check for WALKING TOGETHER
                walking = self._check_walking_together(pose1, pose2)
                if walking['score'] > 0.6:
                    interactions.append({
                        'activity': 'walking_together',
                        'confidence': walking['score'],
                        'people_indices': [i, j],
                        'details': walking
                    })
        
        return interactions
    
    def _check_embracing(self, pose1: Dict, pose2: Dict) -> Dict:
        """Check if two people are embracing"""
        kp1 = pose1.get('keypoints')
        kp2 = pose2.get('keypoints')
        
        if kp1 is None or kp2 is None:
            return {'score': 0.0}
        
        # Get center points (average of hips and shoulders)
        center1 = self._get_body_center(kp1)
        center2 = self._get_body_center(kp2)
        
        if center1 is None or center2 is None:
            return {'score': 0.0}
        
        # Calculate distance between people
        distance = np.sqrt((center1[0] - center2[0])**2 + (center1[1] - center2[1])**2)
        
        # Embracing: very close distance (< 50 pixels typically)
        if distance < 50:
            return {
                'score': 0.9,
                'distance': float(distance),
                'type': 'close_embrace'
            }
        elif distance < 100:
            return {
                'score': 0.6,
                'distance': float(distance),
                'type': 'proximity'
            }
        
        return {'score': 0.0}
    
    def _check_walking_together(self, pose1: Dict, pose2: Dict) -> Dict:
        """Check if two people are walking side by side"""
        kp1 = pose1.get('keypoints')
        kp2 = pose2.get('keypoints')
        
        if kp1 is None or kp2 is None:
            return {'score': 0.0}
        
        center1 = self._get_body_center(kp1)
        center2 = self._get_body_center(kp2)
        
        if center1 is None or center2 is None:
            return {'score': 0.0}
        
        # Walking together: similar y-coordinate (side by side), reasonable x distance
        y_diff = abs(center1[1] - center2[1])
        x_diff = abs(center1[0] - center2[0])
        
        # Side by side: small y difference, moderate x distance
        if y_diff < 50 and 50 < x_diff < 200:
            return {
                'score': 0.7,
                'arrangement': 'side_by_side',
                'distance': float(x_diff)
            }
        
        return {'score': 0.0}
    
    def _get_body_center(self, keypoints: np.ndarray) -> np.ndarray:
        """Get center point of body (average of shoulders and hips)"""
        # Use shoulders (5, 6) and hips (11, 12)
        valid_points = []
        
        for idx in [5, 6, 11, 12]:
            if idx < len(keypoints):
                valid_points.append(keypoints[idx])
        
        if len(valid_points) < 2:
            return None
        
        return np.mean(valid_points, axis=0)
