"""
Phase 4: LLM Lighting Decision Engine

This module converts scene emotions to lighting INTENT.
Outputs groups + semantic parameters. NO DMX.
"""

from .lighting_decision_engine import (
    # Core engine
    LightingDecisionEngine,
    
    # Output models
    LightingInstruction,
    GroupLightingInstruction,
    LightingParameters,
    TimeWindow,
    Transition,
    
    # Enums
    TransitionType,
    FocusArea,
    
    # Convenience functions
    generate_lighting_instruction,
    batch_generate_instructions,
    
    # Constants
    LIGHTING_GROUPS,
)

__all__ = [
    # Core
    "LightingDecisionEngine",
    
    # Models
    "LightingInstruction",
    "GroupLightingInstruction",
    "LightingParameters",
    "TimeWindow",
    "Transition",
    
    # Enums
    "TransitionType",
    "FocusArea",
    
    # Functions
    "generate_lighting_instruction",
    "batch_generate_instructions",
    
    # Constants
    "LIGHTING_GROUPS",
]
