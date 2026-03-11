"""
Phase 1: Script → Scene Structure Processing

New architecture (LOCKED):
  Phase 1A — Text Acquisition (Direct or OCR)
  Phase 1B — Immutable Structuring
  Chunk Preprocessing
  Phase 1C — LLM Structural Intelligence
    Call 1: Scene Segmentation
    Call 2: Hybrid Timestamp Assignment
  Phase 1D — Deterministic Validation & Fallback
  Phase 1E — Scene JSON Construction

Single entry point: run_phase_1(script_path) → (scenes, metadata)
"""

import logging
from typing import List, Dict, Tuple

logger = logging.getLogger("phase_1")


def run_phase_1(script_path: str) -> Tuple[List[Dict], Dict]:
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
    # Chunk Preprocessing
    # ------------------------------------------------------------------
    from phase_1.chunk_preprocessor import create_chunks

    chunks = create_chunks(immutable)
    logger.info(f"Chunking complete: {len(chunks)} chunks")

    # ------------------------------------------------------------------
    # Phase 1C Call 1 — LLM Scene Segmentation
    # ------------------------------------------------------------------
    from phase_1.llm_scene_segmenter import segment_scenes_llm, segment_scenes_rulebased

    scenes = segment_scenes_llm(chunks, immutable)

    # ------------------------------------------------------------------
    # Post-LLM: Deterministic boundary snap to INT./EXT. markers
    # ------------------------------------------------------------------
    scenes = _snap_boundaries_to_markers(scenes, immutable)

    logger.info(f"Phase 1C Call 1 complete: {len(scenes)} scenes")

    # ------------------------------------------------------------------
    # Phase 1C Call 2 — Hybrid Timestamp Assignment
    # ------------------------------------------------------------------
    from phase_1.timestamp_engine import assign_timestamps

    scenes = assign_timestamps(scenes, immutable)
    logger.info("Phase 1C Call 2 complete: timestamps assigned")

    # ------------------------------------------------------------------
    # Phase 1D — Deterministic Validation & Fallback
    # ------------------------------------------------------------------
    from phase_1.validation_layer import validate_and_enforce

    def _retry_callback():
        """Re-run LLM segmentation + timestamps."""
        new_chunks = create_chunks(immutable)
        new_scenes = segment_scenes_llm(new_chunks, immutable)
        new_scenes = assign_timestamps(new_scenes, immutable)
        return new_scenes

    def _fallback_callback():
        """Rule-based segmentation + timestamps."""
        fb_scenes = segment_scenes_rulebased(immutable)
        fb_scenes = assign_timestamps(fb_scenes, immutable)
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


# ===========================================================================
# BACKWARD-COMPAT STUBS
# These replicate the OLD Phase 1 API surface expected by main.py,
# backend/pipeline_runner.py, and backend/app.py.
# They do NOT change the Hitesh run_phase_1 pipeline — they are independent
# pass-through functions using simple text processing.
# ===========================================================================

import re as _re
import os as _os
import json as _json
from config import (
    WORDS_PER_MINUTE as _WPM,
    SCENE_MARKERS as _SCENE_MARKERS,
    MAX_WORDS_PER_SCENE as _MAX_WORDS,
    MIN_WORDS_PER_SCENE as _MIN_WORDS,
)


def detect_format(text):
    """Detect script format from raw text (old API)."""
    has_timestamps = bool(_re.search(r'\d{1,2}:\d{2}', text))
    has_screenplay = bool(_re.search(r'(?:INT\.|EXT\.)', text, _re.IGNORECASE))
    has_acts = bool(_re.search(r'ACT\s+[IVX\d]+', text, _re.IGNORECASE))

    if has_screenplay:
        fmt = "screenplay"
    elif has_timestamps:
        fmt = "timestamped_drama"
    elif has_acts:
        fmt = "theatrical"
    else:
        fmt = "unknown"

    return {
        "estimated_format": fmt,
        "timestamped": has_timestamps,
        "screenplay": has_screenplay,
        "theatrical": has_acts,
        "complexity": "high" if has_screenplay else "medium",
    }


def clean_text(text, preserve_structure=True):
    """Clean raw text while preserving structure (old API)."""
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        # Strip trailing whitespace
        stripped = line.rstrip()
        if preserve_structure:
            cleaned.append(stripped)
        else:
            if stripped:
                cleaned.append(stripped)
    return "\n".join(cleaned)


def extract_stage_directions(text):
    """Extract stage directions from raw text (old API)."""
    directions = []
    # Match (stage directions) and [stage directions]
    directions.extend(_re.findall(r'\(([^)]+)\)', text))
    directions.extend(_re.findall(r'\[([^\]]+)\]', text))
    return directions


def segment_scenes(text, format_info=None):
    """Segment text into scenes (old API).
    Now uses marker-based detection as the primary approach."""
    if format_info is None:
        format_info = detect_format(text)

    # Use the new marker-based detection
    ground_truth = detect_scene_boundaries_from_markers(text)
    if ground_truth and ground_truth["count"] > 0:
        return ground_truth["scenes"]

    # Fallback: split by word count
    return _segment_by_word_count(text)


def detect_scene_boundaries_from_markers(text):
    """
    Phase A — V3 Spatial Formatting Scene Boundary Detection
    
    Replaces brittle regex completely with layout-aware spatial heuristics.
    Identifies bounds based on capitalization, line isolation, empty spaces, and
    classical structures combined rather than simple string matchers.
    
    Returns: { "count": N, "scenes": [...] }
    """
    import re
    lines = text.splitlines()
    if not lines:
        return {"count": 0, "scenes": []}

    # Pass 1: Group text into visual chunks separated by pure blank lines
    chunks = []
    current_chunk = []
    for i, line in enumerate(lines):
        if not line.strip():
            if current_chunk:
                chunks.append((current_chunk[0][0], current_chunk[-1][0], current_chunk))
                current_chunk = []
        else:
            current_chunk.append((i, line))
    if current_chunk:
        chunks.append((current_chunk[0][0], current_chunk[-1][0], current_chunk))

    boundaries = []
    L1_TRANSITIONS = {"CUT TO", "FADE", "DISSOLVE", "BLACKOUT", "SMASH CUT"}

    # Pass 2: Spatial Heuristic Evaluation
    for start_idx, end_idx, chunk_lines in chunks:
        # Check all lines in a chunk. Scene headings or Transitions often clump together (e.g. CUT TO \n EXT. BANK)
        for i_offset, (i, line) in enumerate(chunk_lines):
            stripped = line.strip().upper()
            
            # Classical Check
            has_marker = any(stripped.startswith(m) for m in ["INT.", "EXT.", "INT/EXT.", "SCENE", "ACT", "PROLOGUE", "EPILOGUE"])
            is_transition = any(t in stripped for t in L1_TRANSITIONS)
            
            # Spatial metric: Flushed extremely left? (Indentation < 5 spaces)
            leading_spaces = len(line) - len(line.lstrip())
            is_flush_left = leading_spaces < 5
            
            # Format metric: Is the string strictly UPPERCASE and has enough letters?
            letters = [c for c in stripped if c.isalpha()]
            is_all_caps = (stripped == line.strip()) and len(letters) > 3
            
            # V3 Rule: If it's a marker, OR if it's isolated (length 1), flush-left, and ALL CAPS.
            if has_marker or is_transition or (is_all_caps and is_flush_left and len(chunk_lines) == 1):
                marker_type = "L1_marker" if has_marker else ("transition" if is_transition else "spatial_header")
                boundaries.append((i, line.strip(), marker_type))
                
        # Handle visual break lines inside larger chunks if formatting failed to isolate them
        for i, line in chunk_lines:
            if re.match(r'^\s*[-_=*]{3,}\s*$', line):
                boundaries.append((i, line.strip(), "visual_break"))
                break

    # Guarantee at least one scene if parsing yields nothing but text exists
    if not boundaries:
        return {"count": 0, "scenes": []}

    # Pass 3: Bind chunks into Scenes
    scenes = []
    for i, (start_idx, marker_text, marker_type) in enumerate(boundaries):
        if i + 1 < len(boundaries):
            end_idx = boundaries[i + 1][0] - 1
        else:
            end_idx = len(lines) - 1

        scene_lines = lines[start_idx:end_idx + 1]
        content = "\n".join(scene_lines).strip()
        word_count = len(content.split())
        
        # Eliminate micro-artifacts smaller than 3 words (OCR phantom blocks)
        if word_count < 3 and i + 1 < len(boundaries):
            continue

        scenes.append({
            "scene_number": len(scenes) + 1,
            "scene_id": f"scene_{len(scenes) + 1:03d}",
            "start_line": start_idx + 1,
            "end_line": end_idx + 1,
            "content": content,
            "word_count": word_count,
            "marker": marker_text,
            "marker_type": marker_type,
        })
        
    # Catch prologue content appearing BEFORE the first boundary
    if boundaries[0][0] > 0:
        pre_content = "\n".join(lines[:boundaries[0][0]]).strip()
        if pre_content and len(pre_content.split()) > 5:
            prologue = {
                "scene_number": 0,
                "scene_id": "scene_000",
                "start_line": 1,
                "end_line": boundaries[0][0],
                "content": pre_content,
                "word_count": len(pre_content.split()),
                "marker": "PROLOGUE",
                "marker_type": "prologue",
            }
            scenes.insert(0, prologue)
            for j, s in enumerate(scenes):
                s["scene_number"] = j + 1
                s["scene_id"] = f"scene_{j + 1:03d}"

    return {
        "count": len(scenes),
        "scenes": scenes,
    }


def _segment_by_word_count(text):
    """Fallback: segment by word count budget."""
    words = text.split()
    scenes = []
    scene_num = 1
    idx = 0
    while idx < len(words):
        chunk = words[idx : idx + _MAX_WORDS]
        content = " ".join(chunk)
        scenes.append({
            "scene_number": scene_num,
            "content": content,
            "word_count": len(chunk),
        })
        scene_num += 1
        idx += _MAX_WORDS
    return scenes


def assign_timestamps_hybrid(scenes, emotion_map=None):
    """
    Extract explicit timestamps if present, then use the advanced hybrid estimator
    to intelligently predict durations for un-timestamped scenes based on 
    dialogue ratio, emotional pacing, and stage directions.
    """
    from .timestamp_estimator import interpolate_missing_timestamps
    ts_pattern = _re.compile(r'(\d{1,2}):(\d{2})(?::(\d{2}))?')
    timestamps = []

    for scene in scenes:
        content = scene.get("content", "") or scene.get("text", "")
        match = ts_pattern.search(content)
        start_sec = None
        
        if match:
            # Handle MM:SS vs HH:MM:SS
            parts = [m for m in match.groups() if m is not None]
            if len(parts) == 2:
                m, s = parts
                start_sec = int(m) * 60 + int(s)
            elif len(parts) == 3:
                h, m, s = parts
                start_sec = int(h) * 3600 + int(m) * 60 + int(s)

        # We don't eagerly estimate duration here anymore.
        # Just record the explicit anchor or mark as None for the interpolator.
        if start_sec is not None:
            timestamps.append({
                "start": float(start_sec),
                "end": None, 
                "duration": None,
                "source": "explicit"
            })
        else:
            timestamps.append({
                "start": None,
                "end": None,
                "duration": None,
                "source": "missing"
            })

    # Pass the partially-filled timeline to the interpolator engine
    interpolated_timestamps = interpolate_missing_timestamps(timestamps, scenes, emotion_map)
    return interpolated_timestamps


def build_scene_json(scene_id, scene_data, timestamp, emotion_analysis):
    """Build a single scene JSON object (old API)."""
    return {
        "scene_id": scene_id,
        "scene_number": scene_data.get("scene_number", 0),
        "text": scene_data.get("content", "") or scene_data.get("text", ""),
        "start": timestamp.get("start", 0),
        "end": timestamp.get("end", 0),
        "duration": timestamp.get("duration", 0),
        "emotion": emotion_analysis.get("primary_emotion", "neutral"),
        "emotion_confidence": emotion_analysis.get("confidence", 0.0),
        "secondary_emotions": emotion_analysis.get("secondary_emotions", []),
        "sentiment_score": emotion_analysis.get("sentiment_score", 0.0),
        "theatrical_context": emotion_analysis.get("theatrical_context", {}),
        "v3_metrics": emotion_analysis.get("v3_metrics", {}),
        "word_count": scene_data.get("word_count", len((scene_data.get("content", "") or scene_data.get("text", "")).split())),
    }


def build_complete_output(scene_data, metadata_info):
    """Build final output JSON with all scenes and metadata (old API)."""
    total_duration = sum(s.get("duration", 0) for s in scene_data)
    mins = int(total_duration // 60)
    secs = int(total_duration % 60)

    emotion_dist = {}
    for s in scene_data:
        e = s.get("emotion", "neutral")
        emotion_dist[e] = emotion_dist.get(e, 0) + 1

    dominant = max(emotion_dist.items(), key=lambda x: x[1])[0] if emotion_dist else "neutral"

    return {
        "metadata": {
            "total_scenes": len(scene_data),
            "total_duration_seconds": round(total_duration, 1),
            "total_duration_formatted": f"{mins}m {secs}s",
            "emotion_distribution": {
                "dominant_emotion": dominant,
                "distribution": emotion_dist,
            },
            **metadata_info,
        },
        "scenes": scene_data,
    }


def classify_document(text):
    """Classify whether a document is a script, event schedule, or unknown (old API)."""
    text_lower = text.lower()
    lines = text.strip().splitlines()

    # Check for script markers
    script_markers = sum(1 for m in _SCENE_MARKERS if m.lower() in text_lower)
    has_dialog = bool(_re.search(r'^[A-Z]{2,}:', text, _re.MULTILINE))
    has_screenplay = bool(_re.search(r'(?:INT\.|EXT\.)', text, _re.IGNORECASE))

    # Check for event schedule markers
    event_markers = ["schedule", "agenda", "program", "event", "ceremony"]
    event_score = sum(1 for m in event_markers if m in text_lower)
    has_time_slots = bool(_re.search(r'\d{1,2}:\d{2}\s*(?:am|pm|AM|PM)', text))

    if has_time_slots and event_score >= 2:
        return {
            "doc_type": "event_schedule",
            "confidence": 0.8,
            "reason": "Detected time-slots and event keywords",
        }
    elif script_markers >= 2 or has_dialog or has_screenplay:
        return {
            "doc_type": "script",
            "confidence": min(0.5 + script_markers * 0.1, 1.0),
            "reason": f"Detected {script_markers} script markers",
        }
    else:
        # Be permissive — if it has enough text, treat as script
        if len(lines) > 10:
            return {
                "doc_type": "script",
                "confidence": 0.4,
                "reason": "Assumed script based on text length",
            }
        return {
            "doc_type": "unknown_document",
            "confidence": 0.0,
            "reason": "No recognizable script or event structure",
        }


def process_script(input_path):
    """Backward-compat wrapper — calls the full Hitesh pipeline."""
    return run_phase_1(input_path)


# Update __all__ with compat functions
__all__ = [
    "run_phase_1",
    "detect_format",
    "clean_text",
    "extract_stage_directions",
    "segment_scenes",
    "detect_scene_boundaries_from_markers",
    "assign_timestamps_hybrid",
    "build_scene_json",
    "build_complete_output",
    "classify_document",
    "process_script",
]
