"""
SPATIAL RELATIONSHIPS ANALYZER
Understands spatial relationships: "person sitting ON log", "water on BOTH SIDES", etc.
"""

import numpy as np
from typing import List, Dict, Tuple

class SpatialRelationshipAnalyzer:
    """
    Analyzes spatial relationships between objects and environment
    """
    
    def __init__(self):
        self.relationship_types = [
            'on', 'in', 'next_to', 'above', 'below', 'between',
            'surrounded_by', 'facing', 'near', 'inside'
        ]
    
    def analyze_relationships(self, detections: List[Dict], 
                             panoptic_segments: List[Dict]) -> List[Dict]:
        """
        Analyze spatial relationships in a frame
        
        Args:
            detections: Object detections (person, backpack, etc.)
            panoptic_segments: Background segments (water, grass, log, etc.)
            
        Returns:
            List of relationships: [
                {
                    'subject': 'person',
                    'subject_id': 0,
                    'relationship': 'sitting_on',
                    'object': 'log',
                    'confidence': 0.85,
                    'details': {...}
                }
            ]
        """
        relationships = []
        
        # For each foreground object (person, backpack)
        for det in detections:
            if det.get('class_name') == 'person':
                # Check what the person is ON (sitting/standing on)
                on_what = self._find_surface_below(det, panoptic_segments)
                if on_what:
                    relationships.append({
                        'subject': 'person',
                        'subject_id': det.get('track_id', 0),
                        'relationship': 'on',
                        'object': on_what['name'],
                        'confidence': on_what['confidence'],
                        'details': on_what
                    })
                
                # Check what surrounds the person
                surrounding = self._find_surrounding_elements(det, panoptic_segments)
                if surrounding:
                    relationships.append({
                        'subject': 'person',
                        'subject_id': det.get('track_id', 0),
                        'relationship': 'surrounded_by',
                        'object': surrounding['elements'],
                        'confidence': surrounding['confidence'],
                        'details': surrounding
                    })
        
        # Check for water on both sides (of a path/bridge)
        both_sides = self._check_both_sides_water(panoptic_segments)
        if both_sides:
            relationships.append({
                'subject': 'scene',
                'relationship': 'water_on_both_sides',
                'object': 'path',
                'confidence': both_sides['confidence'],
                'details': both_sides
            })
        
        return relationships
    
    def _find_surface_below(self, detection: Dict, 
                           background: List[Dict]) -> Dict:
        """
        Find what surface the object is on (below it)
        
        For person: check if on grass, log, bench, sand, etc.
        """
        bbox = detection.get('bbox', {})
        if not bbox:
            return None
        
        # Get bottom center of person
        x_center = (bbox['x1'] + bbox['x2']) / 2
        y_bottom = bbox['y2']
        
        # Find background elements near the bottom of the person
        candidates = []
        
        for bg in background:
            if not bg.get('is_background'):
                continue
            
            bg_name = bg.get('class_name', '').lower()
            
            # Check if this background element could be a surface
            # (ground-level things: grass, sand, floor, pavement, wood, etc.)
            if not self._is_surface(bg_name):
                continue
            
            # Simple spatial check: is this background element in the lower part of frame?
            # (More sophisticated: check actual segmentation mask overlap)
            if bg.get('area', 0) > 1000:  # Significant coverage
                candidates.append({
                    'name': bg_name,
                    'coverage': bg.get('coverage_percent', 0),
                    'confidence': 0.7
                })
        
        if candidates:
            # Return highest coverage surface
            candidates.sort(key=lambda x: x['coverage'], reverse=True)
            return candidates[0]
        
        return None
    
    def _is_surface(self, class_name: str) -> bool:
        """Check if class name represents a surface/ground"""
        surfaces = [
            'grass', 'sand', 'floor', 'pavement', 'road', 'ground',
            'wood', 'platform', 'carpet', 'rug', 'mat', 'rock',
            'dirt', 'gravel', 'stone', 'concrete', 'snow', 'ice'
        ]
        return any(surf in class_name for surf in surfaces)
    
    def _find_surrounding_elements(self, detection: Dict,
                                   background: List[Dict]) -> Dict:
        """
        Find what surrounds the object (trees, water, buildings, etc.)
        """
        # Get all significant background elements
        elements = {}
        
        for bg in background:
            if not bg.get('is_background'):
                continue
            
            coverage = bg.get('coverage_percent', 0)
            if coverage > 5:  # At least 5% of frame
                name = bg.get('class_name', '').lower()
                elements[name] = coverage
        
        if not elements:
            return None
        
        # Sort by coverage
        sorted_elements = sorted(elements.items(), key=lambda x: x[1], reverse=True)
        
        return {
            'elements': [elem[0] for elem in sorted_elements[:3]],  # Top 3
            'coverages': {elem[0]: elem[1] for elem in sorted_elements[:3]},
            'confidence': 0.8
        }
    
    def _check_both_sides_water(self, background: List[Dict]) -> Dict:
        """
        Detect if there's water on both sides (land bridge scenario)
        
        This is tricky - need to check segmentation mask positions
        For now, use heuristic: if water coverage is moderate (20-40%)
        and distributed (not all in one area)
        """
        water_segments = [
            bg for bg in background
            if 'water' in bg.get('class_name', '').lower() or 
               'sea' in bg.get('class_name', '').lower() or
               'river' in bg.get('class_name', '').lower()
        ]
        
        if not water_segments:
            return None
        
        total_water_coverage = sum(seg.get('coverage_percent', 0) for seg in water_segments)
        
        # Moderate water coverage suggests water on sides (not fully surrounded, not absent)
        if 15 < total_water_coverage < 50:
            return {
                'confidence': 0.6,
                'water_coverage': total_water_coverage,
                'pattern': 'sides'
            }
        
        return None
    
    def create_spatial_description(self, relationships: List[Dict]) -> str:
        """
        Create natural language description of spatial relationships
        
        Example: "Person sitting on log surrounded by trees and water"
        """
        if not relationships:
            return ""
        
        descriptions = []
        
        for rel in relationships:
            subject = rel.get('subject', 'object')
            relationship = rel.get('relationship', '')
            obj = rel.get('object', '')
            
            if relationship == 'on':
                descriptions.append(f"{subject} on {obj}")
            elif relationship == 'surrounded_by':
                elements = obj if isinstance(obj, list) else [obj]
                elements_str = ', '.join(elements[:2])
                descriptions.append(f"surrounded by {elements_str}")
            elif relationship == 'water_on_both_sides':
                descriptions.append("water on both sides")
        
        return "; ".join(descriptions)
    
    def group_by_scene(self, relationships: List[Dict]) -> Dict:
        """
        Group relationships by scene type
        
        Returns:
            {
                'forest': ['person surrounded by trees'],
                'water': ['water on both sides'],
                'urban': ['person on pavement']
            }
        """
        grouped = {
            'forest': [],
            'water': [],
            'urban': [],
            'indoor': [],
            'other': []
        }
        
        for rel in relationships:
            obj = rel.get('object', '')
            
            # Categorize by environment
            if isinstance(obj, list):
                obj_str = ' '.join(obj)
            else:
                obj_str = str(obj)
            
            obj_lower = obj_str.lower()
            
            if any(term in obj_lower for term in ['tree', 'grass', 'wood', 'forest']):
                grouped['forest'].append(rel)
            elif any(term in obj_lower for term in ['water', 'sea', 'river', 'lake']):
                grouped['water'].append(rel)
            elif any(term in obj_lower for term in ['building', 'pavement', 'road', 'street']):
                grouped['urban'].append(rel)
            elif any(term in obj_lower for term in ['floor', 'ceiling', 'wall', 'room']):
                grouped['indoor'].append(rel)
            else:
                grouped['other'].append(rel)
        
        # Remove empty categories
        return {k: v for k, v in grouped.items() if v}
