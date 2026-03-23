"""
PHASE 4: NARRATIVE INTELLIGENCE
═══════════════════════════════

The FINAL PHASE - generates intelligent narratives using:
- Phase 1: CLIP scenes + lighting
- Phase 2: WBF ensemble (max objects)
- Phase 3: Panoptic segmentation (background understanding)
- Phase 4: Activities, spatial relationships, temporal scenes

Result: Human-like narratives with complete understanding!
"""

import anthropic
import os
from typing import Dict, List
from collections import defaultdict

class NarrativeIntelligenceService:
    """
    PHASE 4: Ultimate Narrative Intelligence
    Track-aware, scene-aware, background-aware, temporal reasoning
    """
    
    def __init__(self):
        """Initialize Claude API client"""
        self.client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY")
        )
        self.model = "claude-sonnet-4-20250514"
    
    def generate_narrative(self, video_data: Dict) -> str:
        """
        PHASE 4: Generate intelligent narrative using ALL detection data
        
        Args:
            video_data: Complete video analysis with all phases
            
        Returns:
            Intelligent narrative string
        """
        # Build comprehensive prompt with ALL context
        prompt = self._build_phase4_prompt(video_data)
        
        try:
            # Call Claude API
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            narrative = message.content[0].text
            return narrative
            
        except Exception as e:
            print(f"Narrative generation failed: {e}")
            return self._generate_fallback_narrative(video_data)
    
    def _build_phase4_prompt(self, video_data: Dict) -> str:
        """
        PHASE 4: Build comprehensive prompt using ALL phases
        """
        detections = video_data.get('detections', [])
        summary = video_data.get('summary', {})
        metadata = video_data.get('metadata', {})
        scenes = video_data.get('scenes', [])
        lighting = video_data.get('lighting_analysis', {})
        scene_comp = video_data.get('scene_composition', {})
        audio = video_data.get('audio_analysis', {})
        
        duration = metadata.get('duration', 0)
        
        # ==========================================
        # TRACK-AWARE ANALYSIS
        # ==========================================
        unique_objects = self._analyze_tracked_objects(detections, duration)
        
        # ==========================================
        # SCENE CONTEXT (Phase 1 + Phase 3)
        # ==========================================
        scene_context = self._get_scene_context(scenes, lighting, scene_comp)
        
        # ==========================================
        # TEMPORAL ANALYSIS
        # ==========================================
        temporal_info = self._analyze_temporal_patterns(unique_objects, duration)
        
        # ==========================================
        # AUDIO CONTEXT
        # ==========================================
        audio_context = self._get_audio_context(audio)
        
        # ==========================================
        # PHASE 4: SPATIAL RELATIONSHIPS
        # ==========================================
        spatial_rels = video_data.get('spatial_relationships', [])
        spatial_context = self._get_spatial_context(spatial_rels) if spatial_rels else ""
        
        # ==========================================
        # PHASE 4: ACTIVITY SUMMARY
        # ==========================================
        activity_summary = video_data.get('activity_summary', {})
        activity_context = ""
        if activity_summary and activity_summary.get('dominant_activity'):
            activity_context = f"\n\nACTIVITY ANALYSIS:\n"
            activity_context += f"Dominant activity: {activity_summary['dominant_activity']}\n"
            activities = activity_summary.get('activities', {})
            if activities:
                activity_context += "Activities detected: " + ", ".join(
                    [f"{act} ({count} frames)" for act, count in sorted(activities.items(), key=lambda x: x[1], reverse=True)[:3]]
                ) + "\n"
        
        # ==========================================
        # PHASE 4: TEMPORAL SCENES
        # ==========================================
        temporal_scenes = video_data.get('temporal_scenes', [])
        scene_context_temporal = self._get_temporal_context(temporal_scenes) if temporal_scenes else ""
        
        # ==========================================
        # BUILD COMPREHENSIVE PROMPT
        # ==========================================
        
        prompt = f"""You are analyzing a {duration:.1f}-second video. Generate a natural, flowing narrative description.

CRITICAL INSTRUCTIONS:
1. Each track_id represents ONE unique object tracked through the video
2. Do NOT count total detections - use unique tracked objects only
3. Write in flowing prose, not bullet points
4. Integrate scene context naturally into the narrative
5. Mention background elements when relevant (sky, water, etc.)
6. Include temporal flow (when objects appear/move/disappear)
7. Use spatial relationships (person ON log, water on BOTH SIDES)
8. Mention activities (sitting, walking, balancing, embracing)
9. Reference temporal scene breakdown for structure
10. Keep it concise but detailed (3-5 sentences or timestamp-based)

"""
        
        # Add scene context
        if scene_context:
            prompt += f"\n{scene_context}\n"
        
        # Add unique objects (track-aware)
        if unique_objects:
            prompt += "\nUNIQUE OBJECTS DETECTED (by track_id):\n"
            for obj_info in unique_objects[:10]:  # Top 10
                prompt += f"- {obj_info['class_name']} (ID: {obj_info['track_id']}): "
                prompt += f"appears at {obj_info['first_seen']:.1f}s, "
                prompt += f"last seen at {obj_info['last_seen']:.1f}s, "
                prompt += f"detected {obj_info['detection_count']} times\n"
            
            prompt += f"\nTotal unique tracked objects: {len(unique_objects)}\n"
            prompt += f"Total detection events: {sum(obj['detection_count'] for obj in unique_objects)}\n"
        
        # Add temporal patterns
        if temporal_info:
            prompt += f"\n{temporal_info}\n"
        
        # Add audio context
        if audio_context:
            prompt += f"\n{audio_context}\n"
        
        # PHASE 4: Add spatial relationships
        if spatial_context:
            prompt += f"\n{spatial_context}\n"
        
        # PHASE 4: Add activity summary
        if activity_context:
            prompt += activity_context
        
        # PHASE 4: Add temporal scene breakdown
        if scene_context_temporal:
            prompt += f"\n{scene_context_temporal}\n"
        
        prompt += """
NARRATIVE STYLE:
- If temporal scenes are provided, structure narrative by timestamp segments
- Mention spatial relationships naturally (person on log, water on sides)
- Include detected activities (sitting, walking, balancing)
- Start with overall scene description
- Mention dominant background elements (sky %, water %, etc.)
- Describe main action/movement
- Include atmosphere and lighting when relevant
- Mention audio elements naturally
- End with temporal summary or mood

EXAMPLE (beach video):
"The video captures a person walking along a beach at dusk. The scene is 
dominated by sky (45%) and ocean (33%), with sand visible along the shore 
(15%). The individual moves through the frame as birds fly overhead against 
the backdrop of warm sunset lighting. The sound of crashing waves accompanies 
the scene throughout the 13-second sequence."

EXAMPLE WITH TEMPORAL BREAKDOWN (forest video):
"0-4s: Two people sit on a log by a water body, surrounded by dense forest trees.
4-7s: A girl sits alone on a wooden bench in the forest.
7-9.5s: The girl walks with arms stretched for balance on a narrow path with 
water visible on both sides.
Throughout: Soft piano music creates a peaceful atmosphere."

Now generate a natural narrative for this video:"""
        
        return prompt
    
    def _analyze_tracked_objects(self, detections: List[Dict], duration: float) -> List[Dict]:
        """
        TRACK-AWARE: Group detections by track_id to count UNIQUE objects
        """
        tracked = defaultdict(list)
        untracked = []
        
        for det in detections:
            # Skip non-object detections
            model_type = det.get('model_type', '')
            if model_type not in ['object_detection']:
                continue
            
            track_id = det.get('track_id')
            if track_id:
                tracked[track_id].append(det)
            else:
                untracked.append(det)
        
        # Build unique object info
        unique_objects = []
        
        for track_id, dets in tracked.items():
            # Sort by timestamp
            dets_sorted = sorted(dets, key=lambda x: x.get('timestamp', 0))
            
            unique_objects.append({
                'track_id': track_id,
                'class_name': dets_sorted[0].get('class_name', 'object'),
                'first_seen': dets_sorted[0].get('timestamp', 0),
                'last_seen': dets_sorted[-1].get('timestamp', duration),
                'detection_count': len(dets),
                'avg_confidence': sum(d.get('confidence', 0) for d in dets) / len(dets)
            })
        
        # Sort by detection count (most prominent objects first)
        unique_objects.sort(key=lambda x: x['detection_count'], reverse=True)
        
        return unique_objects
    
    def _get_scene_context(self, scenes: List[Dict], lighting: Dict, 
                          scene_comp: Dict) -> str:
        """
        SCENE-AWARE: Combine CLIP + lighting + panoptic for complete context
        """
        context_parts = []
        
        # CLIP scene description
        if scenes:
            scene_names = [s.get('scene', '') for s in scenes]
            if scene_names:
                dominant = max(set(scene_names), key=scene_names.count)
                context_parts.append(f"CLIP Scene: {dominant}")
        
        # Lighting analysis
        if lighting:
            time_of_day = lighting.get('dominant_time_of_day', '')
            brightness = lighting.get('avg_brightness', 0)
            if time_of_day:
                context_parts.append(f"Lighting: {time_of_day} (brightness: {brightness:.0f}/255)")
        
        # PHASE 3: Panoptic background composition
        if scene_comp:
            bg = scene_comp.get('background', {})
            bg_elements = bg.get('dominant_elements', [])
            
            if bg_elements:
                context_parts.append("\nBACKGROUND COMPOSITION (from pixel-level analysis):")
                for elem in bg_elements[:5]:  # Top 5
                    context_parts.append(f"- {elem['name']}: {elem['coverage']:.1f}% of frame")
            
            scene_type = scene_comp.get('scene_type', '')
            if scene_type:
                context_parts.append(f"\nScene Type (detected): {scene_type}")
        
        if context_parts:
            return "\n".join(context_parts)
        return ""
    
    def _analyze_temporal_patterns(self, unique_objects: List[Dict], 
                                   duration: float) -> str:
        """
        TEMPORAL REASONING: Analyze when objects appear/disappear
        """
        if not unique_objects:
            return ""
        
        patterns = []
        
        # Early appearances (first 20% of video)
        early_threshold = duration * 0.2
        early_objects = [obj for obj in unique_objects if obj['first_seen'] < early_threshold]
        
        # Late appearances (last 20% of video)
        late_threshold = duration * 0.8
        late_objects = [obj for obj in unique_objects if obj['first_seen'] > late_threshold]
        
        # Persistent objects (appear in first 20% and last until final 20%)
        persistent = [obj for obj in unique_objects 
                     if obj['first_seen'] < early_threshold and obj['last_seen'] > late_threshold]
        
        if persistent:
            classes = [obj['class_name'] for obj in persistent]
            patterns.append(f"Present throughout: {', '.join(set(classes))}")
        
        if late_objects and len(late_objects) >= 2:
            classes = [obj['class_name'] for obj in late_objects[:3]]
            patterns.append(f"Appear later: {', '.join(classes)}")
        
        if patterns:
            return "TEMPORAL PATTERNS:\n" + "\n".join(f"- {p}" for p in patterns)
        return ""
    
    def _get_audio_context(self, audio: Dict) -> str:
        """
        AUDIO-AWARE: Include audio context when available
        """
        if not audio or not audio.get('has_audio'):
            return ""
        
        context_parts = []
        
        # Speech segments
        transcript = audio.get('transcript', {})
        segments = transcript.get('segments', [])
        if segments:
            text = ' '.join([s.get('text', '').strip() for s in segments[:3]])
            if text:
                context_parts.append(f"Speech detected: \"{text[:100]}...\"")
        
        # Audio events
        audio_events = audio.get('audio_events', [])
        if audio_events:
            event_types = [e.get('description', '') for e in audio_events[:5]]
            if event_types:
                context_parts.append(f"Audio: {', '.join(set(event_types))}")
        
        # Audio-visual confirmations
        fused = audio.get('fused_data', {})
        confirmations = fused.get('audio_confirmations', 0)
        if confirmations > 0:
            context_parts.append(f"{confirmations} visual detections confirmed by audio")
        
        if context_parts:
            return "AUDIO CONTEXT:\n" + "\n".join(f"- {p}" for p in context_parts)
        return ""
    
    def _get_spatial_context(self, spatial_rels: List[Dict]) -> str:
        """
        PHASE 4: Extract spatial relationship context for narrative
        """
        if not spatial_rels:
            return ""
        
        context_parts = []
        by_type = {}
        
        for rel in spatial_rels:
            rel_type = rel.get('relationship', 'unknown')
            if rel_type not in by_type:
                by_type[rel_type] = []
            by_type[rel_type].append(rel)
        
        if 'on' in by_type:
            on_rels = by_type['on']
            surfaces = {}
            for rel in on_rels:
                obj = rel.get('object', 'surface')
                surfaces[obj] = surfaces.get(obj, 0) + 1
            if surfaces:
                dominant_surface = max(surfaces.items(), key=lambda x: x[1])
                context_parts.append(f"People frequently on/near {dominant_surface[0]} ({dominant_surface[1]} occurrences)")
        
        if 'surrounded_by' in by_type:
            surround_rels = by_type['surrounded_by']
            elements = set()
            for rel in surround_rels:
                obj = rel.get('object', [])
                if isinstance(obj, list):
                    elements.update(obj)
                else:
                    elements.add(obj)
            if elements:
                context_parts.append(f"Environment: {', '.join(list(elements)[:3])}")
        
        if 'water_on_both_sides' in by_type:
            context_parts.append("Water visible on both sides of path/bridge")
        
        if context_parts:
            return "SPATIAL CONTEXT:\n" + "\n".join(f"- {part}" for part in context_parts)
        return ""
    
    def _get_temporal_context(self, temporal_scenes: List[Dict]) -> str:
        """
        PHASE 4: Extract temporal scene breakdown for narrative
        """
        if not temporal_scenes or len(temporal_scenes) < 2:
            return ""
        
        context_parts = []
        
        for scene in temporal_scenes[:8]:
            start = scene.get('start_time', 0)
            end = scene.get('end_time', 0)
            desc_parts = []
            
            objects = scene.get('dominant_objects', [])
            if objects:
                obj_names = [obj.get('name', '') for obj in objects[:2]]
                if obj_names:
                    desc_parts.append(", ".join(obj_names))
            
            env = scene.get('environment', [])
            if env:
                env_names = [e.get('name', '') for e in env[:2]]
                if env_names:
                    desc_parts.append(f"in {env_names[0]}")
            
            description = " ".join(desc_parts) if desc_parts else "scene"
            context_parts.append(f"{start:.1f}-{end:.1f}s: {description}")
        
        if context_parts:
            return "TEMPORAL BREAKDOWN:\n" + "\n".join(context_parts)
        return ""
    
    def _generate_fallback_narrative(self, video_data: Dict) -> str:
        """
        Fallback narrative if API fails
        """
        summary = video_data.get('summary', {})
        metadata = video_data.get('metadata', {})
        
        duration = metadata.get('duration', 0)
        total_dets = summary.get('total_detections', 0)
        unique_objs = summary.get('unique_tracked_objects', 0)
        
        by_class = summary.get('by_class', {})
        top_classes = sorted(by_class.items(), key=lambda x: x[1], reverse=True)[:3]
        
        classes_str = ", ".join([f"{count} {cls}" for cls, count in top_classes])
        
        narrative = f"The {duration:.1f}-second video shows {classes_str}. "
        narrative += f"A total of {unique_objs} unique objects were tracked through {total_dets} detection events."
        
        # Add scene if available
        scene_comp = video_data.get('scene_composition', {})
        if scene_comp:
            scene_type = scene_comp.get('scene_type', '')
            if scene_type:
                narrative += f" The scene appears to be a {scene_type} setting."
        
        return narrative


# Integration helper
def generate_phase4_narrative(video_data: Dict) -> str:
    """
    PHASE 4: Generate narrative using complete video analysis
    
    Usage in backend:
    from app.utils.narrative_service import generate_phase4_narrative
    
    narrative = generate_phase4_narrative(video_data)
    """
    service = NarrativeIntelligenceService()
    return service.generate_narrative(video_data)