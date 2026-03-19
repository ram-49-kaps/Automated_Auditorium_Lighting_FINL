"""
Phase 1: Script → Scene Structure Processing

Architecture:
  Phase 1A — Text Acquisition (Direct or OCR)
  Phase 1B — Immutable Structuring
  Chunk Preprocessing
  Phase 1C — LLM Structural Intelligence
    Call 1: Scene Segmentation (with robust multi-tier fallback)
    Call 2: Hybrid Timestamp Assignment (with 10s minimum duration)
  Phase 1D — Deterministic Validation & Fallback
  Phase 1E — Scene JSON Construction

Single entry point: run_phase_1(script_path) → (scenes, metadata)
"""

import logging
from typing import List, Dict, Tuple

logger = logging.getLogger("phase_1")


def run_phase_1(script_path: str, model: str = None) -> Tuple[List[Dict], Dict]:
    """
    Execute the full Phase 1 pipeline.

    Args:
        script_path: Path to the input script file.

    Returns:
        (scenes, metadata) tuple where:
          - scenes: List of schema-valid scene dicts
          - metadata: Dict with pipeline metadata (scene_count, hash, etc.)

    Raises:
        AcquisitionHardStop: If text cannot be acquired safely.
        ValidationHardFail: If validation fails after all retries.
        jsonschema.ValidationError: If output doesn't match scene_schema.json.
    """
    # ------------------------------------------------------------------
    # Phase 1A — Text Acquisition
    # ------------------------------------------------------------------
    from phase_1.text_acquisition import acquire_text

    acquisition = acquire_text(script_path)
    logger.info(
        f"Phase 1A complete: {len(acquisition.text)} chars, "
        f"method={acquisition.source_method}"
    )

    # ------------------------------------------------------------------
    # Phase 1B — Immutable Structuring
    # ------------------------------------------------------------------
    from phase_1.immutable_structurer import structure_text

    immutable = structure_text(acquisition.text, acquisition.source_method)
    logger.info(
        f"Phase 1B complete: {immutable.total_lines} lines, "
        f"hash={immutable.sha256_hash[:16]}..."
    )

    # ------------------------------------------------------------------
    # College Event Fast-Path Check
    # ------------------------------------------------------------------
    # If the script looks like a college event (annual day, symposium, etc.),
    # skip the standard pipeline (chunking, LLM segmentation, emotion analysis)
    # and use the event processing fast-path instead.
    from event_processing import detect_college_event, process_college_event
    from config import EVENT_DETECTION_CONFIDENCE_MIN

    detection = detect_college_event(immutable.raw_text)
    if detection["is_college_event"] and detection["confidence"] >= EVENT_DETECTION_CONFIDENCE_MIN:
        logger.info(
            f"College event detected (confidence={detection['confidence']:.2f}, "
            f"keywords={len(detection['matched_keywords'])}). "
            f"Routing to event fast-path."
        )
        event_result = process_college_event(immutable.raw_text, immutable)
        if event_result[0] is not None:
            logger.info("Event fast-path succeeded — returning early.")
            return event_result
        logger.warning(
            "Event fast-path returned None — falling back to standard pipeline."
        )
    else:
        logger.debug(
            f"Not a college event (confidence={detection['confidence']:.2f}). "
            f"Continuing standard pipeline."
        )

    # ------------------------------------------------------------------
    # Chunk Preprocessing
    # ------------------------------------------------------------------
    from phase_1.chunk_preprocessor import create_chunks

    chunks = create_chunks(immutable)
    logger.info(f"Chunking complete: {len(chunks)} chunks")

    # ------------------------------------------------------------------
    # Phase 1C Call 1 — Scene Segmentation
    # ------------------------------------------------------------------
    from phase_1.llm_scene_segmenter import segment_scenes_llm, segment_scenes_rulebased

    use_rule_based = (model == "rule_based")

    if use_rule_based:
        # Rule-based mode: skip LLM entirely, use enhanced rule-based segmenter
        logger.info("Phase 1C: RULE-BASED mode — skipping LLM segmentation")
        scenes = segment_scenes_rulebased(immutable)
    else:
        # LLM mode: use HuggingFace model with multi-tier fallback
        scenes = segment_scenes_llm(chunks, immutable)
        # Handle old return format (tuple) for backward compat
        if isinstance(scenes, tuple):
            scenes = scenes[0]

    # ------------------------------------------------------------------
    # Post-segmentation: Deterministic boundary snap to INT./EXT. markers
    # ------------------------------------------------------------------
    scenes = _snap_boundaries_to_markers(scenes, immutable)

    logger.info(f"Phase 1C Call 1 complete: {len(scenes)} scenes")

    # ------------------------------------------------------------------
    # Phase 1C Call 2 — Hybrid Timestamp Assignment
    # ------------------------------------------------------------------
    from phase_1.timestamp_estimator import estimate_raw_duration, interpolate_missing_timestamps

    # Build initial timestamp list
    timestamps = []
    for scene in scenes:
        ts_entry = {
            "scene_id": scene.get("scene_id", ""),
            "start": scene.get("start_time"),
            "end": scene.get("end_time"),
            "duration": None,
            "source": "explicit" if scene.get("start_time") is not None else None,
        }
        timestamps.append(ts_entry)

    # Interpolate missing timestamps using narrative-aware estimation
    timestamps = interpolate_missing_timestamps(timestamps, scenes)

    # Apply timestamps back to scenes + enforce 10-second minimum duration
    for i, scene in enumerate(scenes):
        ts = timestamps[i]
        scene["start_time"] = ts.get("start", 0.0)
        scene["end_time"] = ts.get("end", 0.0)
        duration = ts.get("duration", 0.0)

        # Enforce 10-second minimum scene duration
        if duration is not None and duration < 10.0:
            duration = 10.0
            scene["end_time"] = scene["start_time"] + duration
            logger.debug(
                f"  Scene {scene.get('scene_id')}: clamped to 10s minimum"
            )

        scene["duration"] = round(duration, 1) if duration else 0.0

    # Recalculate cumulative timestamps so scenes are sequential
    # (scene N starts where scene N-1 ends)
    cumulative_time = 0.0
    for scene in scenes:
        scene["start_time"] = round(cumulative_time, 2)
        dur = scene.get("duration", 10.0) or 10.0
        cumulative_time += dur
        scene["end_time"] = round(cumulative_time, 2)

    logger.info("Phase 1C Call 2 complete: hybrid timestamps assigned (10s min enforced)")

    # ------------------------------------------------------------------
    # Phase 1D — Deterministic Validation & Fallback
    # ------------------------------------------------------------------
    from phase_1.validation_layer import validate_and_enforce

    def _retry_callback():
        """Re-run segmentation + timestamps."""
        if use_rule_based:
            new_scenes = segment_scenes_rulebased(immutable)
        else:
            new_chunks = create_chunks(immutable)
            new_scenes = segment_scenes_llm(new_chunks, immutable)
            if isinstance(new_scenes, tuple):
                new_scenes = new_scenes[0]
        return new_scenes

    def _fallback_callback():
        """Rule-based segmentation + timestamps."""
        fb_scenes = segment_scenes_rulebased(immutable)
        return fb_scenes

    scenes, validation_result = validate_and_enforce(
        scenes,
        immutable,
        retry_callback=_retry_callback,
        fallback_callback=_fallback_callback,
    )
    logger.info(
        f"Phase 1D complete: valid={validation_result.valid}, "
        f"warnings={len(validation_result.warnings)}"
    )

    # ------------------------------------------------------------------
    # Phase 1E — Scene JSON Construction
    # ------------------------------------------------------------------
    from phase_1.scene_json_builder import build_scene_json, build_phase1_metadata

    scene_jsons = build_scene_json(scenes, immutable)
    metadata = build_phase1_metadata(scenes, immutable, validation_result)
    logger.info(f"Phase 1E complete: {len(scene_jsons)} scene JSONs built")

    return scene_jsons, metadata


# ---------------------------------------------------------------------------
# Deterministic boundary snapping
# ---------------------------------------------------------------------------
import re

_SCENE_MARKER = re.compile(
    r"^\s*(INT\.|EXT\.|INTERIOR|EXTERIOR)\s*",
    re.IGNORECASE,
)


def _snap_boundaries_to_markers(scenes, immutable):
    """
    Deterministic post-LLM fix: snap scene start_line to nearest INT./EXT. marker.

    How it works:
      1. Find all INT./EXT. marker line numbers in the script
      2. If no markers found → keep LLM boundaries unchanged (e.g. dialogue scripts)
      3. For each marker, create a scene starting at that line
      4. Fill in end_line = next_marker_start - 1
      5. Handle content before first marker (FADE IN, title cards) and after last marker

    This is deterministic and format-agnostic:
      - Screenplay with INT./EXT. → precise marker-aligned scenes
      - Dialogue-only scripts → LLM boundaries preserved
    """
    # Step 1: Find all INT./EXT. markers
    marker_lines = []
    for line_num, content in sorted(immutable.lines.items()):
        if _SCENE_MARKER.match(content.strip()):
            marker_lines.append(line_num)

    # Step 2: If no markers, return LLM scenes unchanged
    if not marker_lines:
        logger.info("Boundary snap: No INT./EXT. markers — keeping LLM boundaries")
        return scenes

    # Step 3: Build canonical scene list from markers
    snapped = []

    # Any content before the first marker becomes scene prologue
    if marker_lines[0] > 1:
        # Check if there's meaningful content before first marker
        has_content = any(
            immutable.lines.get(i, "").strip()
            for i in range(1, marker_lines[0])
        )
        if has_content:
            snapped.append({
                "scene_id": "prologue",
                "start_line": 1,
                "end_line": marker_lines[0] - 1,
            })

    # Each marker starts a new scene
    for i, ml in enumerate(marker_lines):
        if i + 1 < len(marker_lines):
            end_line = marker_lines[i + 1] - 1
        else:
            end_line = immutable.total_lines

        snapped.append({
            "scene_id": f"scene_{len(snapped) + 1:03d}",
            "start_line": ml,
            "end_line": end_line,
        })

    # Reassign scene_ids sequentially
    for i, s in enumerate(snapped):
        s["scene_id"] = f"scene_{i + 1:03d}"

    logger.info(
        f"Boundary snap: {len(scenes)} LLM scenes → "
        f"{len(snapped)} marker-aligned scenes "
        f"({len(marker_lines)} INT./EXT. markers found)"
    )
    return snapped


# Backward compatibility — expose the main entry point
__all__ = ["run_phase_1"]

# Backward-compat stubs for friend's pipeline path
def detect_format(text):
    """Stub: detect script format."""
    return "screenplay" if any(m in text.upper() for m in ["INT.", "EXT."]) else "theatrical"

def clean_text(text):
    """Stub: passthrough — cleaning is done in immutable structuring."""
    return text

def segment_scenes(text):
    """Stub: rule-based segmentation for backward compat."""
    from phase_1.llm_scene_segmenter import segment_scenes_rulebased
    from phase_1.immutable_structurer import structure_text
    immutable = structure_text(text, "direct")
    return segment_scenes_rulebased(immutable)
