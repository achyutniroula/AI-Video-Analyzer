"""
PHASE 3: PANOPTIC SEGMENTATION
═══════════════════════════════

Labels EVERY PIXEL in the frame:
- Stuff (background): sky, water, sand, grass, road, wall
- Things (objects): person, car, dog, boat

Uses Mask2Former-Swin-Large-COCO-Panoptic
- 133 classes (80 things + 53 stuff)
- Pixel-level understanding
- Background + foreground combined

Result: Complete scene understanding!
"""

from transformers import Mask2FormerImageProcessor, Mask2FormerForUniversalSegmentation
from PIL import Image
import torch
import numpy as np
from typing import Dict, List

class PanopticSegmentationProcessor:
    """
    PHASE 3: Panoptic Segmentation
    Labels every pixel - background AND foreground
    """
    
    def __init__(self, device='cuda'):
        """
        Initialize Mask2Former for panoptic segmentation
        
        Args:
            device: 'cuda' or 'cpu'
        """
        self.device = device
        
        print("\n🎨 Loading Panoptic Segmentation Model...")
        print("-" * 70)
        
        try:
            # Load Mask2Former
            model_name = "facebook/mask2former-swin-large-coco-panoptic"
            
            self.processor = Mask2FormerImageProcessor.from_pretrained(model_name)
            self.model = Mask2FormerForUniversalSegmentation.from_pretrained(
                model_name
            ).to(device)
            
            print(f"   ✓ Mask2Former loaded ({len(self.model.config.id2label)} classes)")
            print("   ✓ Panoptic segmentation ready")
            
            self.enabled = True
            
        except Exception as e:
            print(f"   ⚠️  Mask2Former failed to load: {e}")
            print("   Install: pip install transformers")
            self.enabled = False
    
    def segment_frame(self, frame_rgb: np.ndarray, timestamp: float, 
                     min_area: int = 500, confidence_threshold: float = 0.5) -> Dict:
        """
        Perform panoptic segmentation on a frame
        
        Args:
            frame_rgb: RGB frame (numpy array)
            timestamp: Video timestamp
            min_area: Minimum pixel area to keep (default 500)
            confidence_threshold: Minimum confidence (default 0.5)
            
        Returns:
            Dict with segments and statistics
        """
        if not self.enabled:
            return {'segments': [], 'coverage': 0.0}
        
        try:
            # Convert to PIL
            pil_image = Image.fromarray(frame_rgb)
            
            # Prepare inputs
            inputs = self.processor(images=pil_image, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Run inference
            with torch.no_grad():
                outputs = self.model(**inputs)
            
            # Post-process for panoptic segmentation
            result = self.processor.post_process_panoptic_segmentation(
                outputs,
                target_sizes=[frame_rgb.shape[:2]]
            )[0]
            
            # Extract segments
            segments = []
            total_pixels = frame_rgb.shape[0] * frame_rgb.shape[1]
            labeled_pixels = 0
            
            for segment_info in result['segments_info']:
                # Get label info
                label_id = segment_info['label_id']
                label_name = self.model.config.id2label[label_id]
                
                # Category: 'thing' (object) or 'stuff' (background)
                is_thing = segment_info['isthing']
                category = 'foreground' if is_thing else 'background'
                
                # Area and confidence
                area = segment_info['area']
                score = segment_info.get('score', 1.0)
                
                # Filter small segments
                if area < min_area or score < confidence_threshold:
                    continue
                
                labeled_pixels += area
                
                # Calculate coverage percentage
                coverage = (area / total_pixels) * 100
                
                segments.append({
                    'timestamp': timestamp,
                    'class_name': label_name,
                    'class_id': label_id,
                    'category': category,  # foreground or background
                    'area': int(area),
                    'coverage_percent': float(coverage),
                    'confidence': float(score),
                    'model_source': 'mask2former',
                    'model_type': 'panoptic_segmentation',
                    'is_background': not is_thing,
                    'bbox': {'x1': 0, 'y1': 0, 'x2': 0, 'y2': 0}  # Placeholder
                })
            
            # Calculate total coverage
            total_coverage = (labeled_pixels / total_pixels) * 100
            
            return {
                'segments': segments,
                'coverage': float(total_coverage),
                'total_segments': len(segments),
                'background_segments': sum(1 for s in segments if s['is_background']),
                'foreground_segments': sum(1 for s in segments if not s['is_background'])
            }
            
        except Exception as e:
            print(f"   ⚠️  Panoptic segmentation failed: {e}")
            return {'segments': [], 'coverage': 0.0}
    
    def get_scene_composition(self, segments: List[Dict]) -> Dict:
        """
        Analyze scene composition from panoptic segments
        
        Args:
            segments: List of segment detections
            
        Returns:
            Scene composition breakdown
        """
        if not segments:
            return {}
        
        # Separate background and foreground
        background = [s for s in segments if s['is_background']]
        foreground = [s for s in segments if not s['is_background']]
        
        # Sort by coverage
        background_sorted = sorted(background, key=lambda x: x['coverage_percent'], reverse=True)
        foreground_sorted = sorted(foreground, key=lambda x: x['coverage_percent'], reverse=True)
        
        # Get dominant elements
        dominant_background = background_sorted[:5] if background_sorted else []
        dominant_foreground = foreground_sorted[:5] if foreground_sorted else []
        
        # Calculate total coverage
        bg_coverage = sum(s['coverage_percent'] for s in background)
        fg_coverage = sum(s['coverage_percent'] for s in foreground)
        
        composition = {
            'background': {
                'total_coverage': float(bg_coverage),
                'segment_count': len(background),
                'dominant_elements': [
                    {
                        'name': s['class_name'],
                        'coverage': s['coverage_percent']
                    }
                    for s in dominant_background
                ]
            },
            'foreground': {
                'total_coverage': float(fg_coverage),
                'segment_count': len(foreground),
                'dominant_elements': [
                    {
                        'name': s['class_name'],
                        'coverage': s['coverage_percent']
                    }
                    for s in dominant_foreground
                ]
            }
        }
        
        # Detect scene type from background
        composition['scene_type'] = self._infer_scene_type(dominant_background)
        
        return composition
    
    def _infer_scene_type(self, background_segments: List[Dict]) -> str:
        """
        Infer scene type from background elements
        """
        if not background_segments:
            return 'unknown'
        
        # Get top 3 background elements
        top_elements = [s['class_name'].lower() for s in background_segments[:3]]
        
        # Scene type rules
        if 'sky-other' in top_elements or 'sea' in top_elements or 'water-other' in top_elements:
            if 'sand' in top_elements or 'beach' in str(top_elements):
                return 'beach'
            elif 'sea' in top_elements or 'water' in str(top_elements):
                return 'waterfront'
            else:
                return 'outdoor'
        
        if 'building-other' in top_elements or 'wall-brick' in top_elements or 'pavement' in top_elements:
            return 'urban'
        
        if 'grass' in top_elements or 'tree' in top_elements or 'plant-other' in top_elements:
            return 'nature'
        
        if 'floor' in top_elements or 'wall-wood' in top_elements or 'ceiling' in top_elements:
            return 'indoor'
        
        if 'road' in top_elements or 'pavement' in top_elements:
            return 'street'
        
        return 'outdoor'
    
    def should_process_frame(self, frame_count: int, process_every_n: int = 6) -> bool:
        """
        Decide if this frame should be processed
        Panoptic segmentation is expensive, so process less frequently
        
        Args:
            frame_count: Current frame number
            process_every_n: Process every Nth frame (default: 6)
        """
        return frame_count % process_every_n == 0


# Integration helper functions
def integrate_panoptic_with_phase2(frame_rgb, timestamp, panoptic_processor):
    """
    PHASE 3 Integration: Add panoptic segmentation to pipeline
    
    Usage in processor.py:
    
    # In __init__:
    from panoptic_segmentation import PanopticSegmentationProcessor
    self.panoptic_processor = PanopticSegmentationProcessor(device=self.device)
    
    # In process_video loop:
    if self.panoptic_processor.should_process_frame(frame_count, process_every_n=6):
        panoptic_result = panoptic_processor.segment_frame(frame_rgb, timestamp)
        all_data['panoptic'].extend(panoptic_result['segments'])
    """
    result = panoptic_processor.segment_frame(frame_rgb, timestamp)
    return result


def create_comprehensive_scene_description(panoptic_segments, clip_scene, lighting_data):
    """
    PHASE 3: Combine panoptic + CLIP + lighting for complete scene understanding
    
    Args:
        panoptic_segments: List of panoptic detections
        clip_scene: CLIP scene description
        lighting_data: Lighting analysis
        
    Returns:
        Comprehensive scene description
    """
    # Get composition from panoptic
    composition = PanopticSegmentationProcessor(device='cpu').get_scene_composition(panoptic_segments)
    
    # Build comprehensive description
    description = {
        'overview': {
            'clip_scene': clip_scene.get('scene', 'unknown') if clip_scene else 'unknown',
            'panoptic_scene_type': composition.get('scene_type', 'unknown'),
            'lighting': lighting_data.get('time_of_day', 'unknown') if lighting_data else 'unknown'
        },
        'background': composition.get('background', {}),
        'foreground': composition.get('foreground', {}),
        'atmosphere': {
            'brightness': lighting_data.get('brightness', 0) if lighting_data else 0,
            'color_temp': lighting_data.get('color_temp', 'unknown') if lighting_data else 'unknown'
        }
    }
    
    return description


# Example usage and expected output
"""
PHASE 3 EXAMPLE - Beach Video:

Input: Beach video frame at dusk

Panoptic Output:
{
  'segments': [
    {
      'class_name': 'sky-other',
      'category': 'background',
      'coverage_percent': 45.2,
      'is_background': True
    },
    {
      'class_name': 'sea',
      'category': 'background',
      'coverage_percent': 32.8,
      'is_background': True
    },
    {
      'class_name': 'sand',
      'category': 'background',
      'coverage_percent': 15.3,
      'is_background': True
    },
    {
      'class_name': 'person',
      'category': 'foreground',
      'coverage_percent': 3.2,
      'is_background': False
    },
    {
      'class_name': 'bird',
      'category': 'foreground',
      'coverage_percent': 0.8,
      'is_background': False
    }
  ],
  'coverage': 97.3,  # 97.3% of pixels labeled!
  'scene_type': 'beach'
}

Composition:
{
  'background': {
    'total_coverage': 93.3,
    'dominant_elements': [
      {'name': 'sky-other', 'coverage': 45.2},
      {'name': 'sea', 'coverage': 32.8},
      {'name': 'sand', 'coverage': 15.3}
    ]
  },
  'foreground': {
    'total_coverage': 4.0,
    'dominant_elements': [
      {'name': 'person', 'coverage': 3.2},
      {'name': 'bird', 'coverage': 0.8}
    ]
  },
  'scene_type': 'beach'
}

Combined with CLIP + Lighting:
{
  'overview': {
    'clip_scene': 'beach at dusk',
    'panoptic_scene_type': 'beach',
    'lighting': 'sunset_dusk'
  },
  'background': {
    'sky': 45.2%,
    'water': 32.8%,
    'sand': 15.3%
  },
  'foreground': {
    'person': 3.2%,
    'bird': 0.8%
  }
}

This gives the narrative EVERYTHING it needs:
"A person walks along a beach at dusk. The scene is dominated by 
sky (45%) and ocean (33%), with sand visible below (15%). Birds 
fly overhead as the sun sets, creating warm lighting."
"""
