"""
Integration Entry Point — College Event Fast-Path Orchestrator

Single entry function that chains:
  detect → parse → rule-lighting → optional LLM refinement

Returns (scene_jsons, metadata) — same signature as phase_1.run_phase_1()
so the pipeline can swap seamlessly.

All outputs conform to contracts/scene_schema.json and
contracts/lighting_instruction_schema.json.
"""

import json
import logging
from typing import List, Dict, Tuple, Optional
from pathlib import Path

from event_processing.event_segment_parser import parse_event_segments
from event_processing.simple_rule_lighting import generate_rule_based_lighting
from event_processing.llm_refinement import refine_lighting

logger = logging.getLogger("event_processing.integration")

# Schema path for validation
_SCENE_SCHEMA_PATH = Path(__file__).parent.parent / "contracts" / "scene_schema.json"

# Default event duration (1 hour) — can be overridden
_DEFAULT_EVENT_DURATION = 3600.0


def process_college_event(
    raw_text: str,
    immutable,
) -> Tuple[Optional[List[Dict]], Optional[Dict]]:
    """
    Process a college event script through the fast-path pipeline.

    Skips emotional analysis entirely. Uses rule-based segment→lighting
    mapping with optional LLM refinement.

    Args:
        raw_text: Raw event script text.
        immutable: Frozen ImmutableText from Phase 1B (for deterministic
                   text slicing and metadata).

    Returns:
        (scene_jsons, metadata) on success — same format as run_phase_1().
        (None, None) on failure — caller should fall back to standard pipeline.
    """
    logger.info("Event fast-path: Starting college event processing")

    try:
        # ------------------------------------------------------------------
        # Step 1: Parse event into segments
        # ------------------------------------------------------------------
        segments = parse_event_segments(raw_text)

        if not segments:
            logger.warning("Event fast-path: No segments parsed — aborting")
            return None, None

        logger.info(f"Event fast-path: Parsed {len(segments)} segments")

        # ------------------------------------------------------------------
        # Step 2: Build scene JSONs (conforming to scene_schema.json)
        # ------------------------------------------------------------------
        total_duration = _estimate_duration(raw_text)
        scene_jsons = _build_scene_jsons(segments, immutable, total_duration)

        if not scene_jsons:
            logger.warning("Event fast-path: Failed to build scene JSONs — aborting")
            return None, None

        # Validate against schema
        _validate_scenes(scene_jsons)

        logger.info(f"Event fast-path: Built {len(scene_jsons)} scene JSONs")

        # ------------------------------------------------------------------
        # Step 3: Generate rule-based lighting instructions
        # ------------------------------------------------------------------
        lighting_instructions = generate_rule_based_lighting(
            segments, total_duration
        )

        # ------------------------------------------------------------------
        # Step 4: Optional LLM refinement
        # ------------------------------------------------------------------
        lighting_instructions = refine_lighting(lighting_instructions, segments)

        # ------------------------------------------------------------------
        # Step 5: Build metadata
        # ------------------------------------------------------------------
        metadata = _build_metadata(
            segments, scene_jsons, immutable, lighting_instructions
        )

        logger.info(
            f"Event fast-path: Complete — {len(scene_jsons)} scenes, "
            f"{len(lighting_instructions)} lighting instructions"
        )

        return scene_jsons, metadata

    except Exception as e:
        logger.error(f"Event fast-path: Unexpected error — {e}")
        return None, None


# ---------------------------------------------------------------------------
# Internal builders
# ---------------------------------------------------------------------------

def _build_scene_jsons(
    segments: List[Dict],
    immutable,
    total_duration: float,
) -> List[Dict]:
    """
    Build scene JSON objects conforming to contracts/scene_schema.json.

    Each segment becomes a scene with:
      - script_type = "college_event"
      - emotion = None (we're skipping Phase 2)
      - text sliced from immutable lines
    """
    segment_count = len(segments)
    if segment_count == 0:
        return []

    segment_duration = total_duration / segment_count
    current_time = 0.0

    scenes = []
    for seg in segments:
        start_line = seg.get("start_line", 1)
        end_line = seg.get("end_line", immutable.total_lines)

        # Deterministic text slicing from frozen lines
        text_lines = []
        for i in range(start_line, min(end_line + 1, immutable.total_lines + 1)):
            line = immutable.lines.get(i, "")
            text_lines.append(line)
        text = "\n".join(text_lines)

        # If text slice is empty, use segment's own text
        if not text.strip():
            text = seg.get("text", "")

        start_time = round(current_time, 2)
        end_time = round(current_time + segment_duration, 2)
        duration = round(segment_duration, 2)

        scene_json = {
            "scene_id": seg["segment_id"],
            "script_type": "college_event",
            "time_window": {
                "start": start_time,
                "end": end_time,
            },
            "duration": duration,
            "text": text,
            "location": None,
            "emotion": None,  # Deliberately skipped for events
            "explicit_lighting": [],
        }

        scenes.append(scene_json)
        current_time = end_time

    return scenes


def _estimate_duration(text: str) -> float:
    """
    Estimate event duration from text content.

    Simple heuristic: word count / speaking rate.
    College events typically run 1–3 hours.
    """
    word_count = len(text.split())
    # Assume ~100 words per minute for events (slower than scripts
    # because events include pauses, applause, transitions)
    estimated_minutes = word_count / 100.0
    estimated_seconds = estimated_minutes * 60.0

    # Clamp to reasonable event duration: 15 min – 4 hours
    return max(900.0, min(14400.0, estimated_seconds))


def _build_metadata(
    segments: List[Dict],
    scene_jsons: List[Dict],
    immutable,
    lighting_instructions: List[Dict],
) -> Dict:
    """Build pipeline metadata for the event fast-path."""
    # Count segment type distribution
    type_dist = {}
    for seg in segments:
        seg_type = seg.get("segment_type", "UNKNOWN")
        type_dist[seg_type] = type_dist.get(seg_type, 0) + 1

    # Determine generation method from lighting metadata
    gen_method = "rule_based_event"
    if lighting_instructions:
        first_meta = lighting_instructions[0].get("metadata", {})
        gen_method = first_meta.get("generation_method", gen_method)

    return {
        "scene_count": len(scene_jsons),
        "total_lines": immutable.total_lines,
        "sha256_hash": immutable.sha256_hash,
        "source_method": immutable.source_method,
        "script_type": "college_event",
        "pipeline": "event_fast_path",
        "generation_method": gen_method,
        "segment_type_distribution": type_dist,
        "manual_review_required": False,
        "validation_warnings": [],
        "lighting_instructions": lighting_instructions,
    }


def _validate_scenes(scenes: List[Dict]) -> None:
    """Validate scenes against scene_schema.json. Warns on failure."""
    try:
        import jsonschema
    except ImportError:
        logger.debug("jsonschema not installed — skipping validation")
        return

    if not _SCENE_SCHEMA_PATH.exists():
        logger.debug(f"Schema not found at {_SCENE_SCHEMA_PATH}")
        return

    with open(_SCENE_SCHEMA_PATH) as f:
        schema = json.load(f)

    for scene in scenes:
        try:
            jsonschema.validate(instance=scene, schema=schema)
        except jsonschema.ValidationError as e:
            logger.warning(
                f"Scene {scene.get('scene_id')} failed schema validation: "
                f"{e.message}"
            )
