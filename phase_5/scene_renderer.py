"""
Scene Renderer
Maintains the current visual state of the auditorium lights.
"""

from typing import Dict, Optional, List
from dataclasses import dataclass, field
from .color_utils import get_hex_from_semantic

@dataclass
class LightState:
    """Current state of a light group"""
    group_id: str
    intensity: float = 0.0  # 0.0 to 1.0
    color_hex: str = "#000000"
    focus_area: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "group_id": self.group_id,
            "intensity": self.intensity,
            "color": self.color_hex,
            "focus_area": self.focus_area
        }

class SceneRenderer:
    """
    Manages the visual state of all light groups.
    Does not handle timing or transitions, just holds the 'now'.
    """
    
    def __init__(self):
        self._states: Dict[str, LightState] = {}
        
    def ensure_group(self, group_id: str):
        """Ensure a group exists in the state"""
        if group_id not in self._states:
            # Default to off
            self._states[group_id] = LightState(group_id=group_id)
            
    def update_group(self, group_id: str, intensity: Optional[float] = None, 
                     color_semantic: Optional[str] = None, 
                     color_hex: Optional[str] = None,
                     focus_area: Optional[str] = None):
        """
        Update the state of a specific group.
        
        Args:
            group_id: The group to update
            intensity: New intensity (0.0-1.0)
            color_semantic: Semantic color name (e.g. "warm_amber")
            color_hex: Direct hex code (overrides semantic if provided)
            focus_area: New focus area
        """
        self.ensure_group(group_id)
        state = self._states[group_id]
        
        if intensity is not None:
            state.intensity = max(0.0, min(1.0, intensity))
            
        if color_hex:
            state.color_hex = color_hex
        elif color_semantic:
            state.color_hex = get_hex_from_semantic(color_semantic)
            
        if focus_area is not None:
            state.focus_area = focus_area
            
    def get_state(self, group_id: str) -> Optional[LightState]:
        return self._states.get(group_id)
        
    def get_all_states(self) -> List[Dict]:
        """
        Get list of all group states for rendering.
        Safe to call even when playback is paused (returns last known state).
        """
        return [state.to_dict() for state in self._states.values()]
        
    def reset(self):
        """Reset all lights to off"""
        for state in self._states.values():
            state.intensity = 0.0
            state.color_hex = "#000000"
