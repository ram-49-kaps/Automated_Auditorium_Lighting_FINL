from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# ============================================================================
# PHASE 2A: GLOBAL META-ANCHOR
# ============================================================================
class GlobalMetaAnchor(BaseModel):
    """
    The definitive structural baseline derived prior to processing individual scenes.
    Dictates the ultimate boundaries for the entire lighting session.
    """
    primary_genre: str = Field(default="Drama", description="Dominant narrative framework")
    secondary_genres: List[str] = Field(default_factory=list)
    subgenre: str = Field(default="", description="Specific structural template governing expectations")
    genre_confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    
    narrative_seriousness_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Realism level / Consequence weight")
    overall_thematic_identity: str = Field(default="", description="Primary thesis of the script")
    realism_baseline: str = Field(default="", description="Maximum allowable seriousness score context")
    narrative_universe_logic: str = Field(default="", description="What 'normal' looks like in this world")
    intended_audience_experience: str = Field(default="", description="Global emotional goal of the author")


# ============================================================================
# HIERARCHICAL DOCUMENT TREE
# ============================================================================
class DialogueActionUnit(BaseModel):
    """The atomic level of raw string data."""
    text: str
    is_stage_direction: bool = False
    speaker: Optional[str] = None

class Beat(BaseModel):
    """Sub-scene micro-units containing a single thematic objective or tone shift."""
    beat_id: str
    units: List[DialogueActionUnit] = Field(default_factory=list)
    
    # Deep Emotional Analysis (Phase 2B)
    scene_mood: str = Field(default="neutral", description="Dominant emotional atmosphere")
    subtype: str = Field(default="", description="Specific nuance like betrayal, nostalgia")
    intensity: float = Field(default=0.0, ge=0.0, le=1.0)
    emotion_vector: Dict[str, float] = Field(default_factory=dict, description="Weighted distribution of possible emotions")
    character_emotion: str = Field(default="", description="Emotional state of the main character")
    audience_tone: str = Field(default="sincere", description="How the audience is meant to perceive the scene")
    emotional_signals: str = Field(default="", description="Cues that led to the emotional interpretation")
    emotional_transition: str = Field(default="", description="How this scene's emotion relates to the previous scene")
    
    # Backward compatibility mappings (mostly derived from scene_mood and audience_tone)
    surface_emotion: str = Field(default="neutral", description="Mapped from scene_mood")
    emotion_confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Mapped from intensity")
    narrative_tone: str = Field(default="sincere", description="Mapped from audience_tone")
    tone_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    
    irony_index: float = Field(default=0.0, ge=0.0, le=1.0, description="Divergence between stated meaning and contextual reality")
    
    scene_energy_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Chronological tempo / pacing")
    comedy_intensity_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Pacing and saturation of comedy independent of irony")
    
    character_interaction: Dict[str, Any] = Field(default_factory=dict, description="Dominance shifts, speaker turn density")

class Scene(BaseModel):
    """Bounded spatial/temporal units where location and lighting remain relatively static."""
    scene_id: str
    header: str = ""
    beats: List[Beat] = Field(default_factory=list)
    
    # Phase 3 Narrative Arc state
    narrative_arc_phase: str = Field(default="Setup", description="Setup, Inciting Incident, Rising Action, Climax, Falling Action, Resolution")
    temporal_stability_delta_allowed: float = Field(default=0.0, description="Maximum allowed lighting drift from previous scene")

class Act(BaseModel):
    """Major structural division governing long-term arc trajectories."""
    act_name: str
    scenes: List[Scene] = Field(default_factory=list)

class Script(BaseModel):
    """The global container holding the Meta-Anchor spanning the entire text."""
    title: str = "Untitled Script"
    meta_anchor: GlobalMetaAnchor = Field(default_factory=GlobalMetaAnchor)
    acts: List[Act] = Field(default_factory=list)

# ============================================================================
# RUNTIME CONTEXT STATE
# ============================================================================
class ContextState(BaseModel):
    """Rolling state passed between scenes for Context-Aware Smoothing."""
    previous_surface_emotion_vector: Dict[str, float] = Field(default_factory=dict)
    previous_scene_energy: float = 0.0
    accumulated_tension_score: float = 0.0
    cumulative_confidence: float = 1.0  # Used for Safety Fallback Mechanism
