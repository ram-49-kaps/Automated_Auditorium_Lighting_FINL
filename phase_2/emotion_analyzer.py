import os
import json
import logging
from typing import Dict, Any, Optional

from utils.openai_client import llm_json

# Hugging Face imports for local fallback
try:
    from transformers import pipeline
    import torch
    HF_LOCAL_AVAILABLE = True
except ImportError:
    HF_LOCAL_AVAILABLE = False

logger = logging.getLogger("phase_2")

# Constants
CLASSIFIER_MODEL = "j-hartmann/emotion-english-distilroberta-base"

SYSTEM_PROMPT = """You are an expert AI system specialized in narrative understanding, screenplay analysis, and emotional interpretation in storytelling.

Analyze scenes from a theatrical or screenplay script and determine the emotional state accurately.

Extract the following structured emotional information and return ONLY valid JSON:

{
  "scene_mood": "string (Dominant emotional atmosphere)",
  "subtype": "string (Specific nuance: betrayal, nostalgia, loneliness, etc)",
  "intensity": float (0.0-1.0),
  "emotion_vector": {"emotion1": float, "emotion2": float},
  "character_emotion": "string (Emotional state of the main character)",
  "audience_tone": "string (How audience should perceive the scene)",
  "emotional_signals": "string (Cues: dialogue wording, stage directions, etc)",
  "emotional_transition": "string (How this relates to previous scene)",
  "primary": "string (backward compat - matches scene_mood)",
  "primary_confidence": float (backward compat - matches intensity),
  "secondary": "string (backward compat - top emotion in vector)",
  "secondary_confidence": float (backward compat),
  "accent": "string (backward compat)",
  "accent_confidence": float (backward compat)
}

Rules:
- Do not rely only on dialogue words. Pay attention to stage directions.
- In comedic/satirical genres, avoid literal emotion interpretation of jokes.
- Confidence/Intensity values must be realistic floats between 0 and 1.
- Output JSON only. No explanations.
"""

class EmotionAnalyzer:
    """
    Stateless scene-local emotion classifier.
    Primary Engine: Unified LLM Client (routes dynamically)
    Fallback Engine: DistilRoBERTa (local pipeline)
    """
    
    def __init__(self):
        self.classifier = None
        
        # Initialize local classifier (Fallback)
        if HF_LOCAL_AVAILABLE:
            try:
                device = 0 if torch.cuda.is_available() else -1
                self.classifier = pipeline(
                    "text-classification",
                    model=CLASSIFIER_MODEL,
                    top_k=None,
                    device=device
                )
                logger.info(f"✅ Loaded local fallback classifier: {CLASSIFIER_MODEL}")
            except Exception as e:
                logger.error(f"❌ Failed to load local fallback classifier: {e}")
        else:
            logger.warning("Hugging Face transformers not installed. Local fallback disabled.")

    def analyze(self, scene: Dict[str, Any], context: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze emotion for a single scene with full architectural rules.
        Optionally accepts cross-scene context from Graph RAG.
        """
        scene_id = scene.get("scene_id")
        text = scene.get("text", "")
        
        # Rule 1 & 2: Structural Guard (Input Contract)
        if len(text.split()) < 5:
            return {"scene_id": scene_id, "emotion": None}
            
        emotion_result = None
        
        # Rule 3: Primary Engine (Unified LLM Call)
        emotion_result = self._run_llm(text, context=context)
            
        # Rule 4: Tier 2 Fallback — DistilRoBERTa classifier
        if not emotion_result and self.classifier:
            logger.info(f"[{scene_id}] Falling back to local DistilRoBERTa classifier")
            emotion_result = self._run_classifier(text)

        # Tier 3: Safe default
        if not emotion_result:
            logger.warning(f"[{scene_id}] All emotion engines failed — using neutral default")
            emotion_result = {
                "primary": "neutral",
                "primary_confidence": 0.5,
                "secondary": "neutral",
                "secondary_confidence": 0.3,
                "accent": "neutral",
                "accent_confidence": 0.1,
            }
            
        return {"scene_id": scene_id, "emotion": emotion_result}

    def _run_llm(self, text: str, context: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Run emotion analysis via unified llm_json (uses active model)."""
        try:
            prompt = f"Analyze the emotional content of this scene text:\n\n{text[:2000]}"
            if context:
                prompt += f"\n\nCONTEXT FROM SURROUNDING SCENES:\n{context}"

            result = llm_json(
                prompt=prompt,
                system_prompt=SYSTEM_PROMPT,
                expected_keys=["primary", "primary_confidence"],
                temperature=0.1
            )

            if result and self._validate_output(result):
                return result
            else:
                logger.warning("LLM emotion output failed validation or parsing")
                return None

        except Exception as e:
            logger.warning(f"LLM emotion analysis failed: {e}")
            return None

    def _run_classifier(self, text: str) -> Optional[Dict[str, Any]]:
        """Run DistilRoBERTa fallback and map top 3 to primary/secondary/accent."""
        try:
            # Prevent token limit crashes
            if len(text) > 2000:
                text = text[:2000]
                
            results = self.classifier(text)[0]
            # Ensure sorted descending by score
            results = sorted(results, key=lambda x: x['score'], reverse=True)
            
            if len(results) < 3:
                return None
                
            return {
                "primary": results[0]['label'],
                "primary_confidence": float(round(results[0]['score'], 3)),
                "secondary": results[1]['label'],
                "secondary_confidence": float(round(results[1]['score'], 3)),
                "accent": results[2]['label'],
                "accent_confidence": float(round(results[2]['score'], 3))
            }
            
        except Exception as e:
            logger.error(f"Fallback classifier failed: {e}")
            return None

    def _validate_output(self, d: Dict[str, Any]) -> bool:
        """Strict structural validation of LLM JSON output."""
        if not isinstance(d, dict): return False
        
        # Ensure 'primary' exists and is string
        if not isinstance(d.get("primary"), str): return False
            
        try:
            conf = float(d.get("primary_confidence", 0.0))
            if not (0.0 <= conf <= 1.0): return False
        except (ValueError, TypeError):
            return False
            
        return True

# Global singleton instance for backward compatibility
_analyzer_instance = None

def analyze_emotion(scene: Dict[str, Any], context: Optional[str] = None) -> Dict[str, Any]:
    """Module-level endpoint for `main.py` consumption."""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = EmotionAnalyzer()
    
    return _analyzer_instance.analyze(scene, context=context)