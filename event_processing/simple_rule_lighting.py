"""
Simple Rule-Based Lighting Generator

Maps event segments to lighting instructions using config-driven profiles.
All output conforms to contracts/lighting_instruction_schema.json.

No ML, no LLM — pure dictionary lookup + schema validation.
"""

import copy
import json
import logging
from pathlib import Path
from typing import List, Dict

from event_processing.config import SEGMENT_LIGHTING_MAP, SegmentTypes

logger = logging.getLogger("event_processing.rule_lighting")

# Schema path for validation
_SCHEMA_PATH = Path(__file__).parent.parent / "contracts" / "lighting_instruction_schema.json"


def generate_rule_based_lighting(
    segments: List[Dict],
    total_duration: float = 3600.0,
) -> List[Dict]:
    """
    Generate lighting instructions from event segments using rule-based mapping.

    For each segment, looks up its type in SEGMENT_LIGHTING_MAP from config
    and produces a lighting instruction dict conforming to
    contracts/lighting_instruction_schema.json.

    Args:
        segments: Parsed event segments from event_segment_parser.
        total_duration: Total event duration in seconds (default 1 hour).
                        Distributed proportionally across segments.

    Returns:
        List of lighting instruction dicts, one per segment.
    """
    if not segments:
        logger.warning("No segments provided — returning empty lighting list")
        return []

    # Distribute duration proportionally across segments
    # For now, equal distribution — can be refined later
    segment_count = len(segments)
    segment_duration = total_duration / segment_count

    lighting_instructions = []
    current_time = 0.0

    for segment in segments:
        seg_type = segment.get("segment_type", SegmentTypes.INTRODUCTION)
        seg_id = segment.get("segment_id", "seg_000")

        # Look up lighting profile from config
        profile = SEGMENT_LIGHTING_MAP.get(seg_type)
        if profile is None:
            # Unknown segment type — fall back to INTRODUCTION profile
            logger.warning(
                f"No lighting profile for segment type '{seg_type}' — "
                f"using INTRODUCTION fallback"
            )
            profile = SEGMENT_LIGHTING_MAP[SegmentTypes.INTRODUCTION]

        # Build lighting instruction conforming to schema
        start_time = round(current_time, 2)
        end_time = round(current_time + segment_duration, 2)

        instruction = {
            "scene_id": seg_id,
            "emotion": "neutral",  # Always neutral for college events
            "time_window": {
                "start_time": start_time,
                "end_time": end_time,
            },
            "groups": copy.deepcopy(profile["groups"]),
            "metadata": {
                "generation_method": "rule_based_event",
                "segment_type": seg_type,
            },
        }

        lighting_instructions.append(instruction)
        current_time = end_time

    # Validate against schema
    _validate_lighting(lighting_instructions)

    logger.info(
        f"Generated {len(lighting_instructions)} lighting instructions "
        f"(total duration: {total_duration:.0f}s)"
    )

    return lighting_instructions


def _validate_lighting(instructions: List[Dict]) -> None:
    """
    Validate lighting instructions against lighting_instruction_schema.json.
    Logs warnings on failure but does not raise — rule-based output is trusted.
    """
    try:
        import jsonschema
    except ImportError:
        logger.debug("jsonschema not installed — skipping validation")
        return

    if not _SCHEMA_PATH.exists():
        logger.debug(f"Schema not found at {_SCHEMA_PATH} — skipping validation")
        return

    with open(_SCHEMA_PATH) as f:
        schema = json.load(f)

    for instruction in instructions:
        try:
            jsonschema.validate(instance=instruction, schema=schema)
        except jsonschema.ValidationError as e:
            logger.warning(
                f"Lighting instruction {instruction.get('scene_id')} "
                f"failed schema validation: {e.message}"
            )
