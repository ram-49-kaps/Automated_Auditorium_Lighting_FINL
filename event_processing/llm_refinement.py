"""
Lightweight LLM Refinement for Event Lighting

Optional step that uses a small LLM (Qwen2.5-1.5B-Instruct via HF Inference API)
to refine rule-based lighting instructions. Same pattern as
phase_1/llm_scene_segmenter.py — lazy client singleton, chat_completion API.

The LLM is strictly constrained to:
  - Adjust intensity values within 0.0–1.0
  - Suggest color tuning from the allowed palette
  - Smooth transition durations (0–10s)
  - Formal vs informal tone modulation

The LLM must NOT:
  - Perform emotional inference
  - Reclassify event type
  - Modify structure (add/remove groups)
  - Redefine schema
"""

import json
import os
import logging
from typing import List, Dict, Optional

from config import (
    EVENT_LLM_REFINEMENT_ENABLED,
    EVENT_LLM_MODEL,
    EVENT_LLM_TEMPERATURE,
    EVENT_LLM_MAX_TOKENS,
)
from event_processing.config import ALLOWED_COLORS

logger = logging.getLogger("event_processing.llm_refinement")

from utils.openai_client import llm_chat, get_active_model


# ---------------------------------------------------------------------------
# System prompt — tightly constrained
# ---------------------------------------------------------------------------
REFINEMENT_SYSTEM_PROMPT = f"""You are a lighting refinement engine for college auditorium events.

You receive a JSON array of lighting instructions and segment context.
Your job is to make SMALL adjustments to improve lighting quality.

YOU MAY ONLY:
1. Adjust "intensity" values (must stay within 0.0–1.0)
2. Change "color" values (ONLY from this allowed list: {', '.join(ALLOWED_COLORS)})
3. Adjust "duration_seconds" in transitions (must stay within 0.0–10.0)
4. These adjustments should reflect the event tone (formal → warmer, informal → cooler)

YOU MUST NOT:
- Add or remove any fields
- Add or remove any groups
- Change group_id values
- Change scene_id values
- Change time_window values
- Perform emotional analysis
- Reclassify event types
- Output anything except the refined JSON array

INPUT: A JSON array of lighting instructions + segment context.
OUTPUT: The same JSON array with refined values. Nothing else. No markdown, no explanation."""


def refine_lighting(
    lighting_instructions: List[Dict],
    segments: List[Dict],
) -> List[Dict]:
    """
    Optionally refine rule-based lighting using the unified LLM client.

    If refinement is disabled or LLM fails,
    returns the original instructions unchanged.

    Args:
        lighting_instructions: Rule-based lighting instructions.
        segments: Parsed event segments (for context).

    Returns:
        Refined (or original) lighting instructions.
    """
    if not EVENT_LLM_REFINEMENT_ENABLED:
        logger.info("LLM refinement disabled by config — using rule-based output")
        return lighting_instructions

    try:
        refined = _call_llm(lighting_instructions, segments)
        if refined is not None:
            logger.info(
                f"LLM refinement successful — {len(refined)} instructions refined"
            )
            return refined
        else:
            logger.warning("LLM refinement failed — using original rule-based output")
            return lighting_instructions

    except Exception as e:
        logger.error(f"LLM refinement error: {e} — using original rule-based output")
        return lighting_instructions


def _call_llm(
    instructions: List[Dict],
    segments: List[Dict],
) -> Optional[List[Dict]]:
    """
    Make a single LLM call to refine lighting instructions using the active model.

    Sends: lighting instructions + segment contexts
    Expects: refined JSON array with same structure
    """
    # Build context: pair each instruction with its segment text
    context_pairs = []
    for instr, seg in zip(instructions, segments):
        context_pairs.append({
            "segment_type": seg.get("segment_type", "UNKNOWN"),
            "segment_text_preview": seg.get("text", "")[:200],  # First 200 chars
            "lighting": instr,
        })

    user_prompt = (
        "Refine these lighting instructions for a college event. "
        "Output ONLY the refined JSON array of lighting instructions.\n\n"
        f"CONTEXT AND INSTRUCTIONS:\n{json.dumps(context_pairs, indent=2)}"
    )

    model_to_use = get_active_model() or EVENT_LLM_MODEL

    response_text = llm_chat(
        prompt=user_prompt,
        system_prompt=REFINEMENT_SYSTEM_PROMPT,
        temperature=EVENT_LLM_TEMPERATURE if EVENT_LLM_TEMPERATURE > 0 else 0.01,
        max_tokens=EVENT_LLM_MAX_TOKENS,
        model=model_to_use
    )

    if not response_text:
        return None

    return _parse_and_validate(response_text, instructions)


def _parse_and_validate(
    response_text: str,
    original: List[Dict],
) -> Optional[List[Dict]]:
    """
    Parse LLM JSON response and validate structure matches original.
    Returns None if parsing fails or structure is invalid.
    """
    import re

    # Try direct parse
    refined = _try_parse_json(response_text)

    # Try extracting from markdown code block
    if refined is None:
        code_block = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", response_text, re.DOTALL)
        if code_block:
            refined = _try_parse_json(code_block.group(1))

    # Try finding array pattern
    if refined is None:
        array_match = re.search(r"\[.*\]", response_text, re.DOTALL)
        if array_match:
            refined = _try_parse_json(array_match.group(0))

    if refined is None:
        logger.warning("Could not parse JSON from LLM refinement response")
        return None

    # Structural validation: must be same length as original
    if not isinstance(refined, list) or len(refined) != len(original):
        logger.warning(
            f"LLM returned {len(refined) if isinstance(refined, list) else 'non-list'} "
            f"items, expected {len(original)}"
        )
        return None

    # Validate each instruction preserves required structure
    for i, (ref, orig) in enumerate(zip(refined, original)):
        if not isinstance(ref, dict):
            return None
        # scene_id must match
        if ref.get("scene_id") != orig.get("scene_id"):
            logger.warning(f"scene_id mismatch at index {i} — rejecting LLM output")
            return None
        # Must have groups array
        if "groups" not in ref or not isinstance(ref["groups"], list):
            return None
        # Group count must match
        if len(ref["groups"]) != len(orig["groups"]):
            return None

    # Extract just the lighting fields we trust from LLM output,
    # preserving original structure for everything else
    merged = []
    for ref, orig in zip(refined, original):
        merged_instr = orig.copy()
        merged_instr["groups"] = []

        for ref_group, orig_group in zip(ref["groups"], orig["groups"]):
            merged_group = orig_group.copy()
            merged_group["parameters"] = orig_group["parameters"].copy()

            # Only trust: intensity, color, transition duration
            ref_params = ref_group.get("parameters", {})

            # Intensity
            if "intensity" in ref_params:
                try:
                    val = float(ref_params["intensity"])
                    if 0.0 <= val <= 1.0:
                        merged_group["parameters"]["intensity"] = round(val, 2)
                except (ValueError, TypeError):
                    pass

            # Color
            if "color" in ref_params:
                if ref_params["color"] in ALLOWED_COLORS:
                    merged_group["parameters"]["color"] = ref_params["color"]

            # Transition duration
            ref_transition = ref_group.get("transition", {})
            if ref_transition and "duration_seconds" in ref_transition:
                try:
                    dur = float(ref_transition["duration_seconds"])
                    if 0.0 <= dur <= 10.0:
                        if merged_group.get("transition"):
                            merged_group["transition"] = merged_group["transition"].copy()
                            merged_group["transition"]["duration_seconds"] = round(dur, 1)
                except (ValueError, TypeError):
                    pass

            merged_instr["groups"].append(merged_group)

        # Update metadata to reflect LLM refinement
        if "metadata" in merged_instr and merged_instr["metadata"]:
            merged_instr["metadata"] = merged_instr["metadata"].copy()
            merged_instr["metadata"]["generation_method"] = "rule_based_event+llm_refined"
        else:
            merged_instr["metadata"] = {"generation_method": "rule_based_event+llm_refined"}

        merged.append(merged_instr)

    return merged


def _try_parse_json(text: str) -> Optional[list]:
    """Attempt to parse text as JSON. Returns list or None."""
    try:
        data = json.loads(text.strip())
        if isinstance(data, list):
            return data
    except (json.JSONDecodeError, TypeError):
        pass
    return None
