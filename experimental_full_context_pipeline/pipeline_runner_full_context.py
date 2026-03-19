"""
Pipeline Runner — Full-Context Experimental Pipeline

Orchestrates the entire flow:
  1. Load script
  2. Process full script via LLM (single pass)
  3. Smooth emotion vectors
  4. Generate deterministic lighting
  5. Combine and save output JSON
"""

import os
import json
import logging
from datetime import datetime

from .config_full_context import OUTPUT_DIR, ENABLE_DRIFT_METRICS
from .full_context_llm_processor import process_full_script
from .emotion_vector_model import (
    smooth_emotion_sequence,
    recalculate_dominant_emotion,
    calculate_emotional_drift_score,
)
from .deterministic_lighting_engine import (
    generate_all_lighting,
    calculate_lighting_continuity_score,
)

logger = logging.getLogger("experimental.pipeline_runner")


def run_pipeline(script_path: str) -> dict:
    """
    Run the full-context experimental pipeline end-to-end.

    Args:
        script_path: Path to the input script file (.txt).

    Returns:
        Final result dict with metadata, scenes, lighting, and validation.
    """
    # -------------------------------------------------------------------------
    # Step 1: Load script
    # -------------------------------------------------------------------------
    if not os.path.isfile(script_path):
        raise FileNotFoundError(f"Script file not found: {script_path}")

    with open(script_path, "r", encoding="utf-8") as f:
        script_text = f.read()

    script_name = os.path.splitext(os.path.basename(script_path))[0]
    logger.info(f"Loaded script: {script_name} ({len(script_text)} chars)")

    # -------------------------------------------------------------------------
    # Step 2: Full-script LLM processing
    # -------------------------------------------------------------------------
    logger.info("Step 2: Sending full script to LLM...")
    llm_result = process_full_script(script_text)
    scenes = llm_result["scenes"]
    metadata = llm_result["metadata"]
    logger.info(f"LLM returned {len(scenes)} scenes")

    # -------------------------------------------------------------------------
    # Step 3: Smooth emotion vectors
    # -------------------------------------------------------------------------
    logger.info("Step 3: Smoothing emotion vectors...")
    scenes = smooth_emotion_sequence(scenes)

    # Recalculate dominant emotion post-smoothing
    dominant = recalculate_dominant_emotion(scenes, exclude_neutral=True)
    metadata["dominant_emotion"] = dominant
    logger.info(f"Dominant emotion (post-smoothing): {dominant}")

    # -------------------------------------------------------------------------
    # Step 4: Generate deterministic lighting
    # -------------------------------------------------------------------------
    logger.info("Step 4: Generating deterministic lighting...")
    lighting_states = generate_all_lighting(scenes)
    continuity_score = calculate_lighting_continuity_score(lighting_states)
    logger.info(f"Lighting continuity score: {continuity_score}")

    # -------------------------------------------------------------------------
    # Step 5: Validation metrics
    # -------------------------------------------------------------------------
    validation = {}
    if ENABLE_DRIFT_METRICS:
        drift = calculate_emotional_drift_score(scenes)
        validation["emotional_drift"] = drift
        validation["lighting_continuity_score"] = continuity_score
        logger.info(
            f"Drift: {drift['drift_percentage']}% "
            f"({drift['flip_count']} flips / {drift['total_transitions']} transitions)"
        )

    # -------------------------------------------------------------------------
    # Step 6: Combine and save output
    # -------------------------------------------------------------------------
    result = {
        "pipeline": "experimental_full_context",
        "script_name": script_name,
        "timestamp": datetime.now().isoformat(),
        "metadata": metadata,
        "scenes": scenes,
        "lighting": lighting_states,
        "validation": validation,
    }

    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_filename = f"{script_name}_full_context.json"
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    logger.info(f"Output saved: {output_path}")
    return result
