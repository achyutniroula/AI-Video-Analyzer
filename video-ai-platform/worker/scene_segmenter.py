"""
TEMPORAL SCENE SEGMENTATION
Breaks video into distinct scenes based on visual/audio changes
"""

import numpy as np
from typing import List, Dict, Tuple

class TemporalSceneSegmenter:
    """
    Detects scene boundaries and creates timestamp-based segments
    """
    
    def __init__(self, threshold=0.3):
        self.threshold = threshold
    
    def segment_video(self, detections: List[Dict], duration: float) -> List[Dict]:
        """
        Break video into temporal scenes
        
        Returns list of scenes with:
        - start_time, end_time
        - dominant_objects
        - dominant_activity
        - environment (from panoptic)
        """
        # Group detections by timestamp
        frames = {}
        for det in detections:
            ts = det.get('timestamp', 0)
            if ts not in frames:
                frames[ts] = []
            frames[ts].append(det)
        
        # Sort timestamps
        timestamps = sorted(frames.keys())
        
        # Detect scene boundaries
        boundaries = [0.0]  # Start of video
        
        for i in range(1, len(timestamps)):
            prev_ts = timestamps[i-1]
            curr_ts = timestamps[i]
            
            # Check if scene changed
            if self._is_scene_boundary(frames[prev_ts], frames[curr_ts]):
                boundaries.append(curr_ts)
        
        boundaries.append(duration)  # End of video
        
        # Create scenes
        scenes = []
        for i in range(len(boundaries) - 1):
            start = boundaries[i]
            end = boundaries[i + 1]
            
            # Get all detections in this scene
            scene_dets = []
            for ts in timestamps:
                if start <= ts < end:
                    scene_dets.extend(frames[ts])
            
            scene = self._analyze_scene(scene_dets, start, end)
            scenes.append(scene)
        
        return scenes
    
    def _is_scene_boundary(self, prev_frame: List[Dict], curr_frame: List[Dict]) -> bool:
        """
        Detect if there's a scene change between frames
        
        Indicators:
        - Major change in objects present
        - Change in environment (indoor/outdoor)
        - Change in lighting
        - Change in number of people
        """
        # Object similarity
        prev_objects = set([d.get('class_name') for d in prev_frame])
        curr_objects = set([d.get('class_name') for d in curr_frame])
        
        if not prev_objects or not curr_objects:
            return False
        
        # Jaccard similarity
        intersection = len(prev_objects & curr_objects)
        union = len(prev_objects | curr_objects)
        similarity = intersection / union if union > 0 else 0
        
        # Scene changed if similarity < threshold
        return similarity < self.threshold
    
    def _analyze_scene(self, detections: List[Dict], start: float, end: float) -> Dict:
        """
        Analyze a temporal scene
        
        Returns:
        - What objects are present
        - What's happening (activity)
        - Where (environment from panoptic)
        """
        # Count objects
        object_counts = {}
        people_count = 0
        background_elements = []
        
        for det in detections:
            cls = det.get('class_name', 'unknown')
            object_counts[cls] = object_counts.get(cls, 0) + 1
            
            if cls == 'person':
                people_count += 1
            
            # Collect background elements (from panoptic)
            if det.get('is_background'):
                background_elements.append(cls)
        
        # Get dominant objects (top 3)
        dominant_objects = sorted(
            object_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:3]
        
        # Get dominant background (environment)
        background_counts = {}
        for elem in background_elements:
            background_counts[elem] = background_counts.get(elem, 0) + 1
        
        dominant_background = sorted(
            background_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3] if background_counts else []
        
        return {
            'start_time': round(start, 1),
            'end_time': round(end, 1),
            'duration': round(end - start, 1),
            'dominant_objects': [
                {'name': obj, 'count': count} 
                for obj, count in dominant_objects
            ],
            'environment': [
                {'name': bg, 'frequency': count}
                for bg, count in dominant_background
            ],
            'people_count': people_count,
            'total_detections': len(detections)
        }
    
    def create_narrative_segments(self, scenes: List[Dict], audio_analysis: Dict) -> str:
        """
        Create narrative with timestamps
        
        Format:
        0-4s: 2 people sitting on log by pond
        4-7s: Girl on bench in forest
        etc.
        """
        segments = []
        
        for scene in scenes:
            start = scene['start_time']
            end = scene['end_time']
            
            # Build scene description
            desc_parts = []
            
            # People
            if scene['people_count'] > 0:
                if scene['people_count'] == 1:
                    desc_parts.append("person")
                else:
                    desc_parts.append(f"{scene['people_count']} people")
            
            # Environment
            if scene['environment']:
                env = scene['environment'][0]['name']  # Top environment
                desc_parts.append(f"in {env}")
            
            # Objects
            for obj_info in scene['dominant_objects'][:2]:  # Top 2 objects
                if obj_info['name'] != 'person':
                    desc_parts.append(f"with {obj_info['name']}")
            
            description = " ".join(desc_parts) if desc_parts else "scene"
            
            segments.append(f"{start}-{end}s: {description}")
        
        # Add audio if available
        if audio_analysis and audio_analysis.get('transcript'):
            transcript = audio_analysis['transcript'].get('text', '')
            if transcript:
                segments.append(f"\nAudio: {transcript}")
        
        return "\n".join(segments)
