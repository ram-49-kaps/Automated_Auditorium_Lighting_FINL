"""
DMX Adapter - Converts Phase 4 lighting intent to DMX execution details

This adapter is responsible for:
1. Group → Fixture expansion (based on venue configuration)
2. Semantic color → RGB values
3. Intensity percentage → DMX value (0-255)
4. Focus area → Pan/Tilt values for moving heads

This separation ensures:
- LLM reasons at semantic level
- Hardware details are venue-specific
- Three.js simulation can use same intent with different renderer
"""

import json
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# Import Phase 4 models
from phase_4 import (
    LightingInstruction,
    GroupLightingInstruction,
    LightingParameters,
    FocusArea
)


# =============================================================================
# COLOR MAPPINGS (Semantic → RGB)
# =============================================================================

COLOR_MAP = {
    # Warm colors
    "white": (255, 255, 255),
    "warm_white": (255, 244, 229),
    "warm_amber": (255, 191, 0),
    "amber": (255, 126, 0),
    "orange": (255, 165, 0),
    "yellow": (255, 255, 0),
    
    # Cool colors
    "cool_white": (240, 248, 255),
    "steel_blue": (70, 130, 180),
    "lavender": (230, 230, 250),
    
    # Emotional colors
    "deep_red": (150, 0, 50),
    "dark_red": (139, 0, 0),
    "red": (255, 0, 0),
    "deep_purple": (50, 0, 100),
    "purple": (128, 0, 128),
    "blue": (0, 0, 255),
    "green": (0, 255, 0),
    "cyan": (0, 255, 255),
    "magenta": (255, 0, 255),
    "pink": (255, 192, 203),
    
    # Neutral
    "neutral": (255, 255, 255),
}


# =============================================================================
# FOCUS AREA → PAN/TILT MAPPINGS (for moving heads)
# =============================================================================

FOCUS_TO_POSITION = {
    FocusArea.CENTER_STAGE: {"pan": 128, "tilt": 100},
    FocusArea.STAGE_LEFT: {"pan": 64, "tilt": 100},
    FocusArea.STAGE_RIGHT: {"pan": 192, "tilt": 100},
    FocusArea.UPSTAGE: {"pan": 128, "tilt": 70},
    FocusArea.DOWNSTAGE: {"pan": 128, "tilt": 130},
    FocusArea.FULL_STAGE: {"pan": 128, "tilt": 100},
    FocusArea.AUDIENCE: {"pan": 128, "tilt": 160},
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class FixtureCue:
    """DMX-level cue for a single fixture (Phase 8 compatible)"""
    fixture_id: str
    fixture_type: str
    dmx_start_channel: int
    dmx_channels: Dict[str, int]
    transition_type: str
    transition_duration: float
    description: str


@dataclass
class ExecutableCueSheet:
    """Complete cue sheet ready for DMX output"""
    scene_id: str
    emotion: str
    start_time: float
    end_time: float
    fixture_cues: List[FixtureCue]
    generation_method: str


# =============================================================================
# DMX ADAPTER
# =============================================================================

class DMXAdapter:
    """
    Converts Phase 4 LightingInstruction to executable DMX cues
    
    This is where semantic intent becomes hardware-specific commands.
    """
    
    def __init__(self, fixtures_path: str = "data/auditorium_knowledge/fixtures.json"):
        """
        Initialize adapter with venue fixture configuration
        
        Args:
            fixtures_path: Path to fixtures.json
        """
        self.fixtures = self._load_fixtures(fixtures_path)
        self.group_to_fixtures = self._build_group_mapping()
    
    def _load_fixtures(self, path: str) -> Dict:
        """Load fixture inventory from JSON"""
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
        return {"fixtures": []}
    
    def _build_group_mapping(self) -> Dict[str, List[Dict]]:
        """Build mapping from group_id to fixtures"""
        mapping = {
            "front_wash": [],
            "back_light": [],
            "side_fill": [],
            "specials": [],
            "ambient": [],
        }
        
        # Map fixtures to groups based on type and position
        for fixture in self.fixtures.get("fixtures", []):
            fixture_type = fixture.get("type", "").lower()
            fixture_id = fixture.get("id", "")
            
            # Simple heuristic mapping (would be configured per-venue)
            if "par" in fixture_type.lower() or "PAR" in fixture_id:
                if "front" in fixture.get("notes", "").lower():
                    mapping["front_wash"].append(fixture)
                else:
                    mapping["back_light"].append(fixture)
            elif "moving" in fixture_type.lower():
                mapping["specials"].append(fixture)
            elif "wash" in fixture_type.lower() or "rgb" in fixture_type.lower():
                mapping["ambient"].append(fixture)
            else:
                # Default to front wash
                mapping["front_wash"].append(fixture)
        
        return mapping
    
    def convert(self, instruction: LightingInstruction) -> ExecutableCueSheet:
        """
        Convert Phase 4 LightingInstruction to executable cue sheet
        
        Args:
            instruction: LightingInstruction from Phase 4
            
        Returns:
            ExecutableCueSheet with DMX-level fixture cues
        """
        fixture_cues = []
        
        for group_instruction in instruction.groups:
            group_fixtures = self.group_to_fixtures.get(group_instruction.group_id, [])
            
            for fixture in group_fixtures:
                cue = self._create_fixture_cue(fixture, group_instruction)
                if cue:
                    fixture_cues.append(cue)
        
        return ExecutableCueSheet(
            scene_id=instruction.scene_id,
            emotion=instruction.emotion,
            start_time=instruction.time_window.start_time,
            end_time=instruction.time_window.end_time,
            fixture_cues=fixture_cues,
            generation_method=instruction.metadata.get("generation_method", "unknown") if instruction.metadata else "unknown"
        )
    
    def _create_fixture_cue(
        self, 
        fixture: Dict, 
        group_instruction: GroupLightingInstruction
    ) -> Optional[FixtureCue]:
        """Create DMX cue for a single fixture from group instruction"""
        params = group_instruction.parameters
        capabilities = fixture.get("capabilities", {})
        
        dmx_channels = {}
        
        # Convert color to RGB
        rgb = self._resolve_color(params.color)
        
        if "red" in capabilities:
            dmx_channels[str(capabilities["red"]["channel"])] = rgb[0]
        if "green" in capabilities:
            dmx_channels[str(capabilities["green"]["channel"])] = rgb[1]
        if "blue" in capabilities:
            dmx_channels[str(capabilities["blue"]["channel"])] = rgb[2]
        
        # Convert intensity percentage to DMX
        if "intensity" in capabilities:
            dmx_value = int((params.intensity / 100) * 255)
            dmx_channels[str(capabilities["intensity"]["channel"])] = dmx_value
        
        # Handle moving heads
        if fixture.get("type") == "moving_head" and params.focus_area:
            position = FOCUS_TO_POSITION.get(params.focus_area, {"pan": 128, "tilt": 100})
            if "pan" in capabilities:
                dmx_channels[str(capabilities["pan"]["channel"])] = position["pan"]
            if "tilt" in capabilities:
                dmx_channels[str(capabilities["tilt"]["channel"])] = position["tilt"]
        
        return FixtureCue(
            fixture_id=fixture["id"],
            fixture_type=fixture["type"],
            dmx_start_channel=fixture["dmx_start_channel"],
            dmx_channels=dmx_channels,
            transition_type=group_instruction.transition.type.value,
            transition_duration=group_instruction.transition.duration_seconds,
            description=f"{params.color} @ {params.intensity}%"
        )
    
    def _resolve_color(self, color: str) -> tuple:
        """Resolve color name or hex to RGB tuple"""
        color = color.lower().strip()
        
        # Check color map
        if color in COLOR_MAP:
            return COLOR_MAP[color]
        
        # Try hex color
        if color.startswith("#"):
            try:
                hex_val = color.lstrip("#")
                return tuple(int(hex_val[i:i+2], 16) for i in (0, 2, 4))
            except ValueError:
                pass
        
        # Default to white
        return (255, 255, 255)
    
    def to_dict(self, cue_sheet: ExecutableCueSheet) -> Dict:
        """Convert cue sheet to dictionary for JSON serialization"""
        return {
            "scene_id": cue_sheet.scene_id,
            "emotion": cue_sheet.emotion,
            "start_time": cue_sheet.start_time,
            "end_time": cue_sheet.end_time,
            "generation_method": cue_sheet.generation_method,
            "cues": [
                {
                    "fixture_id": cue.fixture_id,
                    "fixture_type": cue.fixture_type,
                    "dmx_start_channel": cue.dmx_start_channel,
                    "dmx_channels": cue.dmx_channels,
                    "transition_type": cue.transition_type,
                    "transition_duration": cue.transition_duration,
                    "description": cue.description
                }
                for cue in cue_sheet.fixture_cues
            ]
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def convert_instruction_to_cues(instruction: LightingInstruction) -> Dict:
    """
    Convert Phase 4 instruction to Phase 8 compatible cue dictionary
    
    Args:
        instruction: LightingInstruction from Phase 4
        
    Returns:
        Dictionary with fixture-level DMX cues
    """
    adapter = DMXAdapter()
    cue_sheet = adapter.convert(instruction)
    return adapter.to_dict(cue_sheet)


def batch_convert_instructions(instructions: List[LightingInstruction]) -> List[Dict]:
    """Convert multiple instructions to cue dictionaries"""
    adapter = DMXAdapter()
    return [adapter.to_dict(adapter.convert(inst)) for inst in instructions]
