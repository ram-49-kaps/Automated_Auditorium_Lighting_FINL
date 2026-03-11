"""
Three.js Adapter
Bridges the abstract SceneRenderer state to a concrete 3D scene definition.
"""

from typing import Dict, List, Any
import random

class ThreeJSAdapter:
    """
    Adapts renderer state to Three.js compatible JSON.
    Maintains a virtual mapping of groups to 3D positions.
    
    DISCLAIMER: Group positions in Phase 5 are purely illustrative and do not reflect real auditorium geometry.
    """
    
    def __init__(self):
        # Virtual stage layout
        # Maps group_id to (x, y, z)
        self.positions: Dict[str, Dict[str, float]] = {
            "front_wash": {"x": 0, "y": 8, "z": 8},
            "back_light": {"x": 0, "y": 8, "z": -5},
            "side_left": {"x": -8, "y": 4, "z": 0},
            "side_right": {"x": 8, "y": 4, "z": 0},
            "center_spot": {"x": 0, "y": 10, "z": 0},
            "house_lights": {"x": 0, "y": 12, "z": 10},
        }
        # Cache for auto-generated positions of unknown groups
        self._auto_positions: Dict[str, Dict[str, float]] = {}

    def _get_position(self, group_id: str) -> Dict[str, float]:
        """Get or generate a position for a group"""
        if group_id in self.positions:
            return self.positions[group_id]
        
        if group_id in self._auto_positions:
            return self._auto_positions[group_id]
            
        # Generate a deterministic random position above the stage
        # Use semantic hashing based on string
        seed = sum(ord(c) for c in group_id)
        random.seed(seed)
        
        pos = {
            "x": random.uniform(-10, 10),
            "y": random.uniform(5, 12),
            "z": random.uniform(-5, 5)
        }
        self._auto_positions[group_id] = pos
        return pos

    def to_frontend_format(self, renderer_states: List[Dict]) -> Dict[str, Any]:
        """
        Convert renderer states to frontend frame packet.
        
        Args:
            renderer_states: List of dicts from SceneRenderer.get_all_states()
            
        Returns:
            Dict containing 'lights' list for the frontend
        """
        output_lights = []
        
        for state in renderer_states:
            group_id = state["group_id"]
            pos = self._get_position(group_id)
            
            output_lights.append({
                "id": group_id,
                "x": pos["x"],
                "y": pos["y"],
                "z": pos["z"],
                "intensity": state["intensity"],
                "color": state["color"],
                # Focus area could determine rotation/target, but we simplify for now
                "target": state["focus_area"]
            })
            
        return {
            "timestamp": 0, # Could be added if passed
            "lights": output_lights
        }
