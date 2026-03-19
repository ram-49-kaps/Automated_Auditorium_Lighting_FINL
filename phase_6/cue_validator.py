"""
Validation for generated lighting cues
"""

from typing import Dict, List, Tuple
from pipeline.rag_retriever import get_retriever

class CueValidator:
    """
    Validates lighting cues against fixture capabilities and DMX constraints
    """
    
    def __init__(self):
        """Initialize validator"""
        self.retriever = get_retriever()
        self.errors = []
        self.warnings = []
    
    def validate_cue(self, cue_data: Dict) -> Tuple[bool, List[str], List[str]]:
        """
        Validate a complete cue
        
        Args:
            cue_data: Cue dictionary from generator
            
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []
        
        # Validate structure
        if not self._validate_structure(cue_data):
            return False, self.errors, self.warnings
        
        # Validate each fixture cue
        for cue in cue_data.get("cues", []):
            self._validate_fixture_cue(cue)
        
        is_valid = len(self.errors) == 0
        return is_valid, self.errors, self.warnings
    
    def _validate_structure(self, cue_data: Dict) -> bool:
        """Validate cue data structure"""
        required_fields = ["scene_id", "cues"]
        
        for field in required_fields:
            if field not in cue_data:
                self.errors.append(f"Missing required field: {field}")
                return False
        
        if not isinstance(cue_data["cues"], list):
            self.errors.append("'cues' must be a list")
            return False
        
        return True
    
    def _validate_fixture_cue(self, cue: Dict):
        """Validate a single fixture cue"""
        # Check fixture exists
        fixture_id = cue.get("fixture_id")
        if not fixture_id:
            self.errors.append("Fixture cue missing 'fixture_id'")
            return
        
        fixture = self.retriever.get_fixture_by_id(fixture_id)
        if not fixture:
            self.errors.append(f"Unknown fixture: {fixture_id}")
            return
        
        # Validate DMX channels
        dmx_channels = cue.get("dmx_channels", {})
        if not dmx_channels:
            self.warnings.append(f"No DMX channels specified for {fixture_id}")
            return
        
        for channel_str, value in dmx_channels.items():
            try:
                channel = int(channel_str)
                
                # Check channel range
                if channel < 1 or channel > 512:
                    self.errors.append(f"DMX channel {channel} out of range (1-512)")
                
                # Check value range
                if value < 0 or value > 255:
                    self.errors.append(f"DMX value {value} out of range (0-255) for channel {channel}")
                
                # Check if channel is in fixture's range
                if channel < fixture["dmx_start_channel"] or channel > fixture["dmx_end_channel"]:
                    self.errors.append(
                        f"Channel {channel} not in {fixture_id} range "
                        f"({fixture['dmx_start_channel']}-{fixture['dmx_end_channel']})"
                    )
            
            except ValueError:
                self.errors.append(f"Invalid channel number: {channel_str}")
        
        # Validate transition
        transition_type = cue.get("transition_type", "smooth")
        valid_transitions = ["smooth", "snap", "fade", "flash", "flicker", "pulse"]
        if transition_type not in valid_transitions:
            self.warnings.append(f"Unknown transition type: {transition_type}")
        
        transition_duration = cue.get("transition_duration", 0)
        if transition_duration < 0:
            self.errors.append(f"Negative transition duration: {transition_duration}")

def validate_cues(cue_data: Dict) -> Tuple[bool, List[str], List[str]]:
    """
    Convenience function to validate cues
    
    Args:
        cue_data: Cue dictionary
        
    Returns:
        Tuple of (is_valid, errors, warnings)
    """
    validator = CueValidator()
    return validator.validate_cue(cue_data)