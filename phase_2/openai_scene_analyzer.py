"""
Phase B — Hybrid Contextual Scene Analysis (OpenAI)

A dual-tier LLM approach optimized for `gpt-4o-mini`:
  1. Global Snapshot: Reads full script once to extract an overarching summary (cheap).
  2. Sequential Sliding Window: Analyzes scenes one-by-one by injecting the
     global summary + the previous scene's outcome. This eliminates hallucination/memory
     loss while minimizing repetitive token loads.
"""

import logging
import time
from typing import List, Dict, Any, Optional
from utils.openai_client import openai_json

logger = logging.getLogger("phase_2.openai_scene_analyzer")


def analyze_all_scenes(
    full_script: str,
    scenes: List[Dict],
) -> List[Dict[str, Any]]:
    """
    V3 Architecture Override:
    Intersects the flat Dict pipeline, converts to V3 Hierarchical models,
    executes Phase 2A (Global Anchor), Phase 2B (Multi-Head), and Phase 3 (Narrative Arc),
    then repackages the results for `main.py` compatibility containing `v3_metrics`.
    """
    if not scenes:
        return []

    logger.info(f"Phase B (V3): Analyzing {len(scenes)} scenes with Multi-Head Hierarchy.")
    
    # 1. Pipeline Imports
    from phase_2.global_anchor_extractor import extract_global_anchor
    from phase_2.multi_head_analyzer import analyze_beat_multi_head
    from phase_3.narrative_arc_detector import detect_narrative_arc_phases
    from models.narrative_state import Script, Act, Scene as V3Scene, Beat, ContextState, DialogueActionUnit
    
    # 2. Map-Reduce Global Anchor (Phase 2A)
    global_anchor = extract_global_anchor(full_script)
    
    # 3. Translate flat dicts -> V3 Objects
    v3_scenes = []
    for s_dict in scenes:
        text_content = s_dict.get("content", "")
        # For compatibility, we map an entire scene into a single initial Beat constraint
        beats = [Beat(beat_id="b1", units=[DialogueActionUnit(text=text_content)])]
        v3_scenes.append(V3Scene(scene_id=s_dict.get("scene_id", "unknown"), beats=beats))
        
    script_obj = Script(title="Active Production", meta_anchor=global_anchor, acts=[Act(act_name="Act 1", scenes=v3_scenes)])
    
    # 4. Multi-Head Processing with Rolling State (Phase 2B)
    context_state = ContextState()
    for scene in script_obj.acts[0].scenes:
        for i, beat in enumerate(scene.beats):
            raw_text = beat.units[0].text
            analyzed_beat = analyze_beat_multi_head(raw_text, global_anchor, context_state)
            scene.beats[i] = analyzed_beat
            
    # 5. Narrative Arc Phase Global Momentum (Phase 3)
    script_obj = detect_narrative_arc_phases(script_obj)
    
    # 6. Repackage to flat Dict for `main.py` Phase 4 and Graph RAG constraints
    results = []
    for scene in script_obj.acts[0].scenes:
        primary_beat = scene.beats[0] if scene.beats else None
        if not primary_beat:
             continue
             
        res = {
            "primary_emotion": primary_beat.surface_emotion,
            "confidence": primary_beat.emotion_confidence,
            "secondary_emotions": [{"emotion": k, "score": v} for k, v in primary_beat.emotion_vector.items() if k != primary_beat.surface_emotion][:3],
            "sentiment_score": primary_beat.emotion_confidence,
            "theatrical_context": {
                "predicted_theme": primary_beat.narrative_tone,
                "confidence": primary_beat.tone_confidence,
            },
            "primary": primary_beat.surface_emotion,
            "primary_confidence": primary_beat.emotion_confidence,
            "narrative_role": scene.narrative_arc_phase.lower().replace(" ", "_"),
            "mood_shift": "none",
            "scene_id": scene.scene_id,
            "deep_emotional_analysis": {
                "scene_mood": primary_beat.scene_mood,
                "subtype": primary_beat.subtype,
                "intensity": primary_beat.intensity,
                "emotion_vector": primary_beat.emotion_vector,
                "character_emotion": primary_beat.character_emotion,
                "audience_tone": primary_beat.audience_tone,
                "emotional_signals": primary_beat.emotional_signals,
                "emotional_transition": primary_beat.emotional_transition
            },
            "v3_metrics": {  
                "irony_index": primary_beat.irony_index,
                "narrative_seriousness_score": global_anchor.narrative_seriousness_score,
                "emotion_confidence": primary_beat.emotion_confidence,
                "temporal_stability_delta": scene.temporal_stability_delta_allowed,
                "comedy_intensity": primary_beat.comedy_intensity_score,
                "scene_energy": primary_beat.scene_energy_score
            }
        }
        results.append(res)
        
    return results


def _extract_global_context(full_script: str) -> Optional[str]:
    prompt = (
        f"SCRIPT:\n{'='*40}\n"
        f"{full_script}\n"
        f"{'='*40}\n\n"
        "Provide a concise, 2-paragraph narrative summary of the overarching plot and main character arcs."
    )
    sys = "You are a professional dramaturg. Output valid JSON containing a single key: 'global_summary'."
    res = openai_json(prompt, sys, expected_keys=["global_summary"], temperature=0.1)
    if res:
        return res.get("global_summary")
    return None


def _analyze_single_scene(
    scene: Dict,
    global_context: str,
    previous_scene_summary: str,
    scene_index: int,
    total_scenes: int
) -> Dict[str, Any]:
    scene_text = scene.get("content", "")
    if not scene_text.strip():
        return _neutral_default(scene)
        
    prompt = (
        f"GLOBAL NARRATIVE CONTEXT:\n{global_context}\n\n"
        f"PREVIOUS SCENE CONTEXT:\n{previous_scene_summary}\n\n"
        f"CURRENT SCENE ({scene_index}/{total_scenes}):\n{'='*40}\n"
        f"{scene_text}\n{'='*40}\n\n"
        "Analyze this scene's emotion considering the global arc and what just happened.\n"
        "Return strict JSON with these keys exactly:\n"
        "- primary_emotion (string: lowercased, e.g. joy, sadness, fear, anger, surprise, neutral, tension, mystery)\n"
        "- primary_confidence (float: 0.0 to 1.0)\n"
        "- secondary_emotion (string or null)\n"
        "- secondary_confidence (float: 0.0 to 1.0)\n"
        "- accent_emotion (string or null)\n"
        "- accent_confidence (float: 0.0 to 1.0)\n"
        "- narrative_role (string: 'introduction', 'rising_action', 'climax', 'falling_action', 'resolution', 'transition', or 'comic_relief')\n"
        "- mood_shift (string: 'none', 'gradual', 'sudden')\n"
        "- scene_summary (string: a concise 1-sentence summary of what happened and the ending mood to pass to the next scene)"
    )
    
    sys = "You are an expert script emotion analyst. You MUST output ONLY valid JSON."
    res = openai_json(
        prompt, 
        system_prompt=sys, 
        expected_keys=["primary_emotion", "primary_confidence", "scene_summary"],
        temperature=0.2
    )

    if not res:
        return _neutral_default(scene)
    return res


def _format_emotion_result(llm_result: Dict, scene: Dict) -> Dict[str, Any]:
    """Convert raw payload to backward-compat emotion format."""
    primary = llm_result.get("primary_emotion", "neutral")
    try:
        primary_conf = float(llm_result.get("primary_confidence", 0.5))
    except (ValueError, TypeError):
        primary_conf = 0.5
        
    secondary = llm_result.get("secondary_emotion")
    try:
        secondary_conf = float(llm_result.get("secondary_confidence", 0.0))
    except (ValueError, TypeError):
         secondary_conf = 0.0
         
    accent = llm_result.get("accent_emotion")
    try:
        accent_conf = float(llm_result.get("accent_confidence", 0.0))
    except (ValueError, TypeError):
         accent_conf = 0.0
         
    secondary_emotions = []
    if secondary and secondary_conf > 0:
        secondary_emotions.append({"emotion": secondary, "score": secondary_conf})
    if accent and accent_conf > 0:
        secondary_emotions.append({"emotion": accent, "score": accent_conf})

    return {
        "primary_emotion": primary,
        "confidence": primary_conf,
        "secondary_emotions": secondary_emotions,
        "sentiment_score": primary_conf,
        "theatrical_context": {
            "predicted_theme": primary,
            "confidence": primary_conf,
        },
        "primary": primary,
        "primary_confidence": primary_conf,
        "secondary": secondary,
        "secondary_confidence": secondary_conf,
        "accent": accent,
        "accent_confidence": accent_conf,
        "narrative_role": llm_result.get("narrative_role", "unknown"),
        "mood_shift": llm_result.get("mood_shift", "none"),
        "scene_id": scene.get("scene_id"),
    }


def _neutral_default(scene: Dict) -> Dict[str, Any]:
    return {
        "primary_emotion": "neutral",
        "confidence": 0.5,
        "secondary_emotions": [],
        "sentiment_score": 0.0,
        "theatrical_context": {"predicted_theme": "neutral", "confidence": 0.5},
        "primary": "neutral",
        "primary_confidence": 0.5,
        "secondary": None,
        "secondary_confidence": 0.0,
        "accent": None,
        "accent_confidence": 0.0,
        "narrative_role": "unknown",
        "mood_shift": "none",
        "scene_id": scene.get("scene_id"),
        "scene_summary": "Neutral/Unknown."
    }
