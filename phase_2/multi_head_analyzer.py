import re
import math
import logging
from typing import List, Dict, Any, Tuple

from models.narrative_state import Scene, Beat, GlobalMetaAnchor, ContextState
from utils.openai_client import openai_json

logger = logging.getLogger("phase_2.multi_head")

# ============================================================================
# ML WRAPPERS (Zero-Shot / Embedding logic placeholders)
# ============================================================================
def get_zero_shot_classification(text: str, candidate_labels: List[str]) -> Dict[str, float]:
    """ Deprecated in favor of perform_deep_emotional_analysis """
    pass

def get_cosine_distance(text1: str, text2: str) -> float:
    """
    Measures semantic divergence between Dialogue and Stage Action.
    Local models use `sentence-transformers/all-MiniLM-L6-v2`.
    Placeholder math to prevent blocking. 1.0 = Max Divergence (irony), 0.0 = Identical.
    """
    return 0.5 # Stubs cosine divergence

# ============================================================================
# LAYER 4 & 7: IRONY & COMEDY INDEX
# ============================================================================
def calculate_irony_and_comedy(beat_text: str, global_anchor: GlobalMetaAnchor) -> Tuple[float, float]:
    """
    Layer 4: Divergence Modeling
    Layer 7: Comedy Intensity Scoring
    """
    # 1. Parse Dialogue vs Action blocks
    dialogue_blocks = re.findall(r'^[A-Z\s]+:\s*(.+)$', beat_text, re.MULTILINE)
    action_blocks = re.findall(r'^\s*\((.*)\)\s*$', beat_text, re.MULTILINE) + \
                    re.findall(r'^\s*\[(.*)\]\s*$', beat_text, re.MULTILINE)
                    
    dialogue_text = " ".join(dialogue_blocks) if dialogue_blocks else beat_text
    action_text = " ".join(action_blocks) if action_blocks else ""
    
    # Base Irony uses Cosine distance if both exist
    base_irony = get_cosine_distance(dialogue_text, action_text) if (dialogue_text and action_text) else 0.0
    
    # Override logic: Call LLM explicitly for the Irony and Comedy scales
    prompt = f"""
    Analyze this scene segment.
    Assess Irony (0.0 to 1.0) and Comedy Intensity (0.0 to 1.0).
    Context Anchor Genre is: {global_anchor.primary_genre}
    Text: {beat_text}
    """
    result = openai_json(
        prompt, 
        system_prompt="Return JSON with 'irony_index' and 'comedy_intensity' floats.", 
        expected_keys=["irony_index", "comedy_intensity"]
    )
    
    if result:
        irony = max(base_irony, float(result.get("irony_index", 0.0)))
        comedy = float(result.get("comedy_intensity", 0.0))
        return irony, comedy
    
    return base_irony, 0.0

# ============================================================================
# LAYER 6 & 8: ENERGY & INTERACTION
# ============================================================================
def calculate_scene_energy(beat_text: str) -> float:
    """
    A pure mechanical kinetic algorithm for parsing speed/velocity of light transitions.
    """
    lines = beat_text.splitlines()
    word_count = len(beat_text.split())
    
    if word_count == 0:
        return 0.0
        
    speaker_changes = len(re.findall(r'^[A-Z\s]+$', beat_text, re.MULTILINE))
    dialogue_velocity = speaker_changes / word_count if word_count else 0
    
    interrupt_density = beat_text.count("-") + beat_text.count("...")
    exclamation_density = beat_text.count("!") / word_count if word_count else 0
    
    # Scale algorithm bounds
    energy = (dialogue_velocity * 10) + (interrupt_density * 2) + (exclamation_density * 5)
    return min(1.0, max(0.0, energy / 10.0))

def model_character_interaction(beat_text: str) -> Dict[str, Any]:
    """ Models relational dynamics. Return raw metrics dict. """
    speakers = re.findall(r'^([A-Z\s]+)$', beat_text, re.MULTILINE)
    unique_speakers = set([s.strip() for s in speakers if len(s.strip()) > 2])
    
    return {
        "speaker_turn_density": len(speakers),
        "unique_speakers": len(unique_speakers),
        "chaos_state": "Isolation" if len(unique_speakers) <= 1 else ("Conflict" if len(unique_speakers) == 2 else "Ensemble Chaos")
    }

# ============================================================================
# MAIN MULTI-HEAD PIPELINE
# ============================================================================
def perform_deep_emotional_analysis(beat_content: str, anchor: GlobalMetaAnchor, context: ContextState) -> Dict[str, Any]:
    """ Performs deep emotional analysis combining genre, realism, and previous state. """
    prev_emotions = context.previous_surface_emotion_vector
    prev_str = ", ".join([f"{k}:{v}" for k, v in prev_emotions.items()]) if prev_emotions else "None"

    prompt = f"""
GLOBAL NARRATIVE CONTEXT:
- Primary Genre: {anchor.primary_genre}
- Seriousness/Realism: {anchor.narrative_seriousness_score} (0=slapstick, 1=absolute realism)
- Thematic Universe: {anchor.narrative_universe_logic}

PREVIOUS SCENE EMOTIONS: 
{prev_str}

CURRENT SCENE TEXT:
{'='*40}
{beat_content}
{'='*40}

For this scene, perform a deep emotional analysis. Extract the following structured emotional information:

1. Scene Mood (Primary Emotion)
   Determine the dominant emotional atmosphere of the scene.

2. Emotion Subtype
   If possible, refine the emotion into more specific categories such as: betrayal, nostalgia, loneliness, regret, tension, moral conflict, romantic warmth, emotional emptiness, psychological pressure, etc.

3. Emotion Intensity
   Estimate the strength of the emotion on a scale from 0.0 to 1.0.

4. Character Emotion
   Identify the emotional state of the main character(s) within the scene.

5. Audience Tone
   Describe how the audience is meant to perceive the scene emotionally.

6. Emotional Signals
   Explain what cues led to your emotional interpretation (dialogue wording, pauses, stage directions, environmental descriptions, character behavior).

7. Emotion Vector
   Provide a weighted distribution of possible emotions.

8. Emotional Transition
   Describe how this scene's emotion relates to the previous scene.

IMPORTANT RULES:
- Do not rely only on dialogue words; pay attention to stage directions and tone.
- In comedic/satirical genres, angry dialogue might be superficial comedy rather than true tension or sadness. Do not be literal if the meta-anchor specifies comedy!
- Avoid oversimplifying complex emotional situations. Provide emotional vectors.

Return ONLY pure valid JSON in the following format:
{{
  "scene_mood": "<string>",
  "subtype": "<string>",
  "intensity": <float 0.0-1.0>,
  "character_emotion": "<string>",
  "audience_tone": "<string>",
  "emotional_signals": "<string>",
  "emotion_vector": {{"emotion1": <float>, "emotion2": <float>}},
  "emotional_transition": "<string>"
}}
"""
    sys_prompt = (
        "You are an expert AI system specialized in narrative understanding, screenplay analysis, "
        "and emotional interpretation in storytelling. Output MUST be strictly valid JSON matching the schema."
    )
    
    expected_keys = ["scene_mood", "subtype", "intensity", "character_emotion", "audience_tone", "emotional_signals", "emotion_vector", "emotional_transition"]
    result = openai_json(prompt, sys_prompt, expected_keys=expected_keys)
    
    if not result:
        return {
            "scene_mood": "neutral", "subtype": "none", "intensity": 0.5,
            "character_emotion": "neutral", "audience_tone": "sincere",
            "emotional_signals": "Fallback triggered.",
            "emotion_vector": {"neutral": 1.0},
            "emotional_transition": "unknown"
        }
    return result

def analyze_beat_multi_head(beat_content: str, anchor: GlobalMetaAnchor, context: ContextState) -> Beat:
    """ Evaluates the beat simultaneously across all independent axes. """
    
    # Deep Emotional Analysis
    deep_emotions = perform_deep_emotional_analysis(beat_content, anchor, context)
    
    # 4/7: Irony & Comedy Intensive Index
    irony_index, comedy_intensity = calculate_irony_and_comedy(beat_content, anchor)
    
    # 6/8: Kinetic Metrics
    energy = calculate_scene_energy(beat_content)
    interaction = model_character_interaction(beat_content)
    
    # Update Context Tracker
    context.previous_scene_energy = energy
    context.previous_surface_emotion_vector = deep_emotions.get("emotion_vector", {})
    
    return Beat(
        beat_id="beat_gen", # ID applied later
        scene_mood=deep_emotions.get("scene_mood", "neutral").lower(),
        subtype=deep_emotions.get("subtype", ""),
        intensity=deep_emotions.get("intensity", 0.0),
        emotion_vector=deep_emotions.get("emotion_vector", {}),
        character_emotion=deep_emotions.get("character_emotion", ""),
        audience_tone=deep_emotions.get("audience_tone", "sincere"),
        emotional_signals=deep_emotions.get("emotional_signals", ""),
        emotional_transition=deep_emotions.get("emotional_transition", ""),
        
        # Backwards compat mappings
        surface_emotion=deep_emotions.get("scene_mood", "neutral").lower(),
        emotion_confidence=deep_emotions.get("intensity", 0.0),
        narrative_tone=deep_emotions.get("audience_tone", "sincere"),
        tone_confidence=deep_emotions.get("intensity", 0.0), # Approximate
        
        irony_index=irony_index,
        scene_energy_score=energy,
        comedy_intensity_score=comedy_intensity,
        character_interaction=interaction
    )
