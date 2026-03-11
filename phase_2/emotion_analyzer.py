import os
import json
import logging
from typing import Dict, Any, Optional

from utils.openai_client import openai_json

# Hugging Face imports
try:
    from huggingface_hub import InferenceClient
    from transformers import pipeline
    import torch
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False

logger = logging.getLogger("phase_2")

# Constants
LLM_MODEL = "meta-llama/Meta-Llama-3.1-8B-Instruct"
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
    Primary Engine: Llama 3.1 8B (via HF API)
    Fallback Engine: DistilRoBERTa (local pipeline)
    """
    
    def __init__(self):
        self.llm_client = None
        self.classifier = None
        
        if not HF_AVAILABLE:
            logger.error("Hugging Face libraries not installed. Phase 2 cannot operate.")
            return

        # Initialize LLM Client (Primary)
        from dotenv import load_dotenv
        load_dotenv()
        hf_token = os.getenv("HF_API_TOKEN")
        
        if hf_token:
            try:
                self.llm_client = InferenceClient(
                    model=LLM_MODEL,
                    token=hf_token,
                    timeout=15.0  # Prevent unbounded hangs
                )
                logger.info(f"✅ Initialized HF Inference API logic for: {LLM_MODEL}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize LLM client: {e}")
        else:
            logger.warning("⚠️ No HF_TOKEN found in environment. LLM path disabled.")

        # Initialize local classifier (Fallback)
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
        
        # Rule 3: Primary Engine (HF API)
        if self.llm_client:
            emotion_result = self._run_llm(text, context=context)
            
        # Rule 4: Tier 2 Fallback — OpenAI gpt-4o-mini
        if not emotion_result:
            logger.info(f"[{scene_id}] Falling back to OpenAI gpt-4o-mini")
            emotion_result = self._run_openai_fallback(text, context=context)

        # Rule 5: Tier 3 Fallback — DistilRoBERTa classifier
        if not emotion_result and self.classifier:
            logger.info(f"[{scene_id}] Falling back to local DistilRoBERTa classifier")
            emotion_result = self._run_classifier(text)

        # Tier 4: Safe default
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
        """Run Llama 3.1 8B via Inference API and validate strict JSON."""
        try:
            # Build system prompt with optional context
            system_content = SYSTEM_PROMPT
            if context:
                system_content = (
                    SYSTEM_PROMPT
                    + "\n\nCONTEXT FROM SURROUNDING SCENES (use this to improve accuracy):\n"
                    + context
                )

            messages = [
                {"role": "system", "content": system_content},
                {"role": "user", "content": text}
            ]
            
            response = self.llm_client.chat_completion(
                messages,
                temperature=0.0,
                max_tokens=256,
                top_p=1.0,
            )
            
            content = response.choices[0].message.content.strip()
            
            # Extract JSON block if surrounded by markdown
            if content.startswith("```json"):
                content = content[7:]
                if content.endswith("```"):
                    content = content[:-3]
            elif content.startswith("```"):
                content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                    
            content = content.strip()
            json_dict = json.loads(content)
            
            if self._validate_output(json_dict):
                return json_dict
            else:
                logger.warning("LLM JSON failed strict validation.")
                return None
                
        except json.JSONDecodeError:
            logger.warning("LLM produced invalid JSON.")
            return None
        except Exception as e:
            logger.warning(f"LLM API request failed: {e}")
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

    def _run_openai_fallback(self, text: str, context: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Run OpenAI gpt-4o-mini as emotion classifier (Tier 2 fallback)."""
        try:
            prompt = f"Analyze the emotional content of this scene text:\n\n{text[:2000]}"
            if context:
                prompt += f"\n\nCONTEXT FROM SURROUNDING SCENES:\n{context}"
            prompt += (
                '\n\nReturn ONLY valid JSON in this exact format:\n'
                '{"primary": "...", "primary_confidence": 0.0-1.0, '
                '"secondary": "...", "secondary_confidence": 0.0-1.0, '
                '"accent": "...", "accent_confidence": 0.0-1.0}'
            )

            result = openai_json(
                prompt=prompt,
                system_prompt=SYSTEM_PROMPT,
                expected_keys=["primary", "primary_confidence"],
            )

            if result and self._validate_output(result):
                return result
            else:
                logger.warning("OpenAI emotion output failed validation")
                return None

        except Exception as e:
            logger.warning(f"OpenAI emotion analysis failed: {e}")
            return None

    def _validate_output(self, d: Dict[str, Any]) -> bool:
        """Strict structural validation of LLM JSON output."""
        required_keys = {
            "primary", "primary_confidence", 
            "secondary", "secondary_confidence", 
            "accent", "accent_confidence"
        }
        
        # Must have exactly these keys (or superset, but we only trust if these exist)
        if not required_keys.issubset(d.keys()):
            return False
            
        # Validate types and bounds
        try:
            for conf_key in ["primary_confidence", "secondary_confidence", "accent_confidence"]:
                val = float(d[conf_key])
                if not (0.0 <= val <= 1.0):
                    return False
                    
            for label_key in ["primary", "secondary", "accent"]:
                if d[label_key] is not None and not isinstance(d[label_key], str):
                    return False
        except (ValueError, TypeError):
            return False
            
        return True

# =============================================================================
# SINGLETON INTERFACE
# =============================================================================

_analyzer_instance = None

def get_analyzer():
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = EmotionAnalyzer()
    return _analyzer_instance

def analyze_emotion(scene: Dict[str, Any], context: Optional[str] = None) -> Dict[str, Any]:
    """
    Main entrypoint for Phase 2 Pipeline.
    Returns: {"scene_id": "...", "emotion": {...}} or {"scene_id": "...", "emotion": None}
    """
    analyzer = get_analyzer()
    return analyzer.analyze(scene, context=context)