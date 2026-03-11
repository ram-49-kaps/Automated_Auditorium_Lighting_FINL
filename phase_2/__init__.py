"""
Phase 2: Emotion Analysis Module
Optional semantic signal extraction

Backward-compatible wrapper: accepts both the new scene-dict format
AND the old raw-text-string format used by main.py and pipeline_runner.py.
"""

from .emotion_analyzer import analyze_emotion as _analyze_emotion_core
from typing import Dict, Any, Union, Optional


def analyze_emotion(
    input_data: Union[str, Dict[str, Any]],
    context: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analyze emotion for a scene.
    
    Accepts EITHER:
      - A scene dict: {"scene_id": "...", "text": "..."}  (new format)
      - A raw string: "The thunder crashed..."               (old format)
    
    Optional context from Graph RAG for improved accuracy.
    Returns emotion result compatible with old downstream consumers.
    """
    # Handle old callers that pass raw text string
    if isinstance(input_data, str):
        scene = {
            "scene_id": "compat",
            "text": input_data,
        }
    else:
        scene = input_data
    
    # Call the actual new analyzer with optional context
    result = _analyze_emotion_core(scene, context=context)
    
    # Map new output format to old format for backward compatibility
    emotion = result.get("emotion")
    
    if emotion is None:
        return {
            "primary_emotion": "neutral",
            "confidence": 0.0,
            "primary": "neutral",
            "primary_confidence": 0.0,
            "secondary_emotions": [],
            "sentiment_score": 0.0,
            "theatrical_context": {"predicted_theme": "neutral", "confidence": 0.0},
        }
    
    primary = emotion.get("primary", "neutral")
    primary_conf = emotion.get("primary_confidence", 0.0)
    secondary = emotion.get("secondary")
    secondary_conf = emotion.get("secondary_confidence", 0.0)
    accent = emotion.get("accent")
    accent_conf = emotion.get("accent_confidence", 0.0)
    
    # Build backward-compatible response
    secondary_emotions = []
    if secondary:
        secondary_emotions.append({"emotion": secondary, "score": secondary_conf})
    if accent:
        secondary_emotions.append({"emotion": accent, "score": accent_conf})
    
    return {
        # Old format fields (for pipeline_runner.py / main.py)
        "primary_emotion": primary,
        "confidence": primary_conf,
        "secondary_emotions": secondary_emotions,
        "sentiment_score": primary_conf,
        "theatrical_context": {
            "predicted_theme": primary,
            "confidence": primary_conf,
        },
        # New format fields (preserved for new consumers)
        "primary": primary,
        "primary_confidence": primary_conf,
        "secondary": secondary,
        "secondary_confidence": secondary_conf,
        "accent": accent,
        "accent_confidence": accent_conf,
        # Scene ID
        "scene_id": result.get("scene_id"),
    }


from .openai_scene_analyzer import analyze_all_scenes


__all__ = [
    'analyze_emotion',
    'analyze_all_scenes',
]
