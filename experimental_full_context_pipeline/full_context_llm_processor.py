"""
Full-Context LLM Processor — Single-Pass Scene Segmentation + Emotion

Accepts the entire script as a string, sends it to the LLM in one call,
and returns structured JSON with scene segmentation and per-scene emotions.

If the script exceeds the token threshold → raises ScriptTooLongError.
NO chunking fallback. This is by design.
"""

import os
import json
import logging
import re

from .config_full_context import (
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_OUTPUT_TOKENS,
    MAX_INPUT_TOKENS,
)

logger = logging.getLogger("experimental.llm_processor")


# =============================================================================
# CUSTOM EXCEPTIONS
# =============================================================================

class ScriptTooLongError(Exception):
    """Raised when the script exceeds the token threshold.
    No chunking is implemented for this experiment."""
    pass


# =============================================================================
# SYSTEM PROMPT — verbatim from spec
# =============================================================================

SYSTEM_PROMPT = """You are a dramaturgical analysis engine and emotional structuring system.

You will receive a complete script.

Your task:

1. Segment the script into chronological scenes.
2. For each scene:
   - Extract:
     - scene_id
     - start_timestamp (if available)
     - end_timestamp (if available)
     - location (if detectable)
   - Assign:
     - primary_emotion (string)
     - energy (float 0.0–1.0)
     - valence (float -1.0 to 1.0)
     - confidence (0.0–1.0)
3. Emotional progression must reflect narrative arc.
4. Avoid sudden emotional flips unless clearly justified by text.
5. Comedy rule:
   - High chaos + positive tone ≠ fear.
   - Distinguish danger from absurdity.
6. Do NOT overuse "neutral".
7. Always output valid JSON.
8. No explanations.
9. No extra fields.

Output format:

{
  "metadata": {
    "dominant_emotion": "...",
    "genre_inferred": "...",
    "emotional_arc_shape": "..."
  },
  "scenes": [
    {
      "scene_id": "...",
      "start_time": "...",
      "end_time": "...",
      "location": "...",
      "emotion": {
        "label": "...",
        "energy": 0.0,
        "valence": 0.0,
        "confidence": 0.0
      }
    }
  ]
}"""


# =============================================================================
# TOKEN ESTIMATION
# =============================================================================

def estimate_tokens(text: str) -> int:
    """
    Rough heuristic token count.
    English text averages ~3.5 characters per token for sub-word tokenisers.
    """
    return int(len(text) / 3.5)


# =============================================================================
# PUBLIC API
# =============================================================================

from utils.openai_client import llm_json, get_active_model

def _validate_response(data) -> dict:
    """Internal validator to safely parse and enforce required keys on the LLM output."""
    if isinstance(data, str):
        try:
            # Strip markdown json blocks if models accidentally append them
            data = data.replace("```json", "").replace("```", "").strip()
            data = json.loads(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM returned invalid JSON: {e} \nRaw data: {data}")
            
    if not isinstance(data, dict):
        raise ValueError(f"Expected dict, got {type(data)}")
        
    if "metadata" not in data or "scenes" not in data:
        raise ValueError("Missing required critical schema keys 'scenes' or 'metadata'")
        
    return data

def process_full_script(script_text: str) -> dict:
    """
    Send the entire script to the LLM in a single call.

    Args:
        script_text: The full script as a plain-text string.

    Returns:
        Validated dict with "metadata" and "scenes" keys.

    Raises:
        ScriptTooLongError: If the script exceeds the token threshold.
        ValueError:         If the LLM response cannot be parsed/validated.
    """
    token_estimate = estimate_tokens(script_text)
    logger.info(f"Script size: {len(script_text)} chars, ~{token_estimate} tokens")

    if token_estimate > MAX_INPUT_TOKENS:
        raise ScriptTooLongError(
            f"Script is ~{token_estimate} tokens, exceeds threshold of "
            f"{MAX_INPUT_TOKENS} tokens ({MAX_INPUT_TOKENS} = "
            f"{int(MAX_INPUT_TOKENS / 0.7)} × 0.70). "
            f"No chunking fallback in this experiment."
        )

    # Use the pipeline's active model, or fallback to the config model
    model_to_use = get_active_model() or LLM_MODEL
    logger.info(f"Sending full script to {model_to_use} (temperature={LLM_TEMPERATURE})")

    # Unified client call
    data = llm_json(
        prompt=script_text,
        system_prompt=SYSTEM_PROMPT,
        temperature=LLM_TEMPERATURE if LLM_TEMPERATURE > 0 else 0.01,
        max_tokens=LLM_MAX_OUTPUT_TOKENS,
        model=model_to_use
    )

    if not data:
        raise ValueError(f"LLM generation failed via unified client for model {model_to_use}")

    data = _validate_response(data)

    logger.info(f"Validated: {len(data['scenes'])} scenes extracted")
    return data
