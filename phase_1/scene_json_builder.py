"""
Phase 1E — Scene JSON Construction

Builds final output conforming to contracts/scene_schema.json.

Key behaviors:
  - text sliced deterministically from ImmutableText.lines
  - emotion is always null (Phase 2's job)
  - explicit_lighting: verbatim regex matches, zero interpretation
  - script_type: simple heuristic from structural cues
  - Validated against scene_schema.json before returning
"""

import re
import json
import logging
from typing import List, Dict, Optional
from pathlib import Path

from phase_1.immutable_structurer import ImmutableText

logger = logging.getLogger("phase_1.json_builder")

# Schema path
_SCHEMA_PATH = Path(__file__).parent.parent / "contracts" / "scene_schema.json"


def build_scene_json(
    scenes: List[Dict],
    immutable: ImmutableText,
    chunk_summaries: Optional[List[str]] = None,
) -> List[Dict]:
    """
    Build schema-conformant scene JSON objects.

    Args:
        scenes: Validated scenes with start_line, end_line, timestamps.
        immutable: Frozen ImmutableText for deterministic text slicing.
        chunk_summaries: Optional list of chunk summaries from Phase 1C
                         Narrative Memory system.

    Returns:
        List of scene dicts conforming to scene_schema.json.
    """
    logger.info(f"Phase 1E: Building JSON for {len(scenes)} scenes")

    # Detect script type (simple heuristic)
    script_type = _detect_script_type(immutable)

    # Build a mapping from scene index to chunk summary
    # (simple: distribute summaries evenly across scenes)
    summary_map = _build_summary_map(scenes, chunk_summaries)

    output = []
    for i, scene in enumerate(scenes):
        scene_summary = summary_map.get(i)
        scene_json = _build_single_scene(scene, immutable, script_type, scene_summary)
        output.append(scene_json)

    # Validate against schema
    _validate_against_schema(output)

    logger.info(f"Phase 1E: Built and validated {len(output)} scene JSON objects")
    return output


def build_phase1_metadata(
    scenes: List[Dict],
    immutable: ImmutableText,
    validation_result=None,
) -> Dict:
    """
    Build Phase 1 metadata for pipeline consumption.

    Args:
        scenes: Final scene list.
        immutable: Frozen text.
        validation_result: Optional validation result.

    Returns:
        Metadata dict.
    """
    return {
        "scene_count": len(scenes),
        "total_lines": immutable.total_lines,
        "sha256_hash": immutable.sha256_hash,
        "source_method": immutable.source_method,
        "script_type": _detect_script_type(immutable),
        "manual_review_required": (
            validation_result.manual_review_required
            if validation_result else False
        ),
        "validation_warnings": (
            validation_result.warnings
            if validation_result else []
        ),
    }


# ---------------------------------------------------------------------------
# Internal builders
# ---------------------------------------------------------------------------

def _build_single_scene(
    scene: Dict,
    immutable: ImmutableText,
    script_type: str,
    chunk_summary: Optional[str] = None,
) -> Dict:
    """Build a single scene JSON conforming to schema."""
    sl = scene["start_line"]
    el = scene["end_line"]

    # -- Deterministic text slicing from frozen lines --
    text_lines = []
    for i in range(sl, el + 1):
        line = immutable.lines.get(i, "")
        text_lines.append(line)
    text = "\n".join(text_lines)

    # -- Time window --
    start_time = scene.get("start_time", 0.0)
    end_time = scene.get("end_time", 0.0)
    duration = scene.get("duration", end_time - start_time)

    # -- Location extraction (from scene headers if present) --
    location = _extract_location(text)

    # -- Build the scene dict (schema-conformant) --
    scene_json = {
        "scene_id": scene["scene_id"],
        "script_type": script_type,
        "time_window": {
            "start": round(start_time, 2),
            "end": round(end_time, 2),
        },
        "duration": round(duration, 2),
        "text": text,
        "location": location,
        "emotion": None,  # Phase 2's job — NEVER set here
        "explicit_lighting": _extract_explicit_lighting(text),
        "chunk_summary": chunk_summary,  # Narrative Memory: dramatic context
    }

    return scene_json


def _build_summary_map(
    scenes: List[Dict],
    chunk_summaries: Optional[List[str]],
) -> Dict[int, Optional[str]]:
    """
    Map scene indices to their corresponding chunk summary.

    Strategy: distribute chunk summaries evenly across scenes.
    If there are 3 chunks and 9 scenes, scenes 0-2 get summary 0,
    scenes 3-5 get summary 1, scenes 6-8 get summary 2.
    """
    if not chunk_summaries:
        return {}

    n_scenes = len(scenes)
    n_summaries = len(chunk_summaries)

    if n_summaries == 0 or n_scenes == 0:
        return {}

    mapping = {}
    scenes_per_chunk = max(1, n_scenes // n_summaries)

    for i in range(n_scenes):
        chunk_idx = min(i // scenes_per_chunk, n_summaries - 1)
        mapping[i] = chunk_summaries[chunk_idx]

    return mapping


def _detect_script_type(immutable: ImmutableText) -> str:
    """
    Simple heuristic for script type detection.
    No separate LLM call — just structural cues.
    """
    text = immutable.raw_text[:2000]  # Check first 2000 chars

    has_int_ext = bool(re.search(r"\bINT\.|EXT\.\b", text))
    has_timestamps = bool(re.search(r"\[.*\d+:\d+.*\]", text))
    has_cue_sheet = bool(re.search(r"\bcue\b.*\blight", text, re.IGNORECASE))
    has_schedule = bool(re.search(r"\b\d{1,2}:\d{2}\s*(am|pm|AM|PM)\b", text))

    if has_int_ext and has_timestamps:
        return "timestamped_drama"
    elif has_int_ext:
        return "raw_drama"
    elif has_schedule:
        return "event_schedule"
    elif has_cue_sheet:
        return "cue_sheet"
    elif has_timestamps:
        return "timestamped_drama"
    else:
        return "raw_drama"


def _extract_location(text: str) -> Optional[str]:
    """Extract location from INT./EXT. header lines."""
    # Match INT. or EXT. headers
    match = re.search(
        r"(?:INT\.|EXT\.|INTERIOR|EXTERIOR)\s*[.\-]?\s*(.+?)(?:\s*[-–—]\s*(?:DAY|NIGHT|DAWN|DUSK|CONTINUOUS))?$",
        text,
        re.IGNORECASE | re.MULTILINE,
    )
    if match:
        location = match.group(1).strip().rstrip("-–— ")
        return location if location else None
    return None


def _extract_explicit_lighting(text: str) -> List[str]:
    """
    Extract verbatim lighting cues from scene text.

    Matches common script lighting directions. Returns the matched strings
    exactly as written — zero interpretation (Phase 4 interprets them).
    """
    if not text or not text.strip():
        return []

    patterns = [
        # "BLACKOUT" / "BLACK OUT" / "LIGHTS OUT"
        re.compile(
            r"\b(?:black\s*out|lights?\s+out)\b",
            re.IGNORECASE,
        ),
        # "LIGHTS UP/DOWN/DIM/FLICKER/FADE/FLASH/RISE"
        re.compile(
            r"\b(?:the\s+)?lights?\s+(?:up|down|dim(?:s|med)?|flicker(?:s|ing)?|fade(?:s|d)?|flash(?:es|ing)?|rise(?:s)?|brighten(?:s)?)\b[^.\n]{0,40}",
            re.IGNORECASE,
        ),
        # "SPOTLIGHT ON ..." / "SPOT ON ..."
        re.compile(
            r"\bspot(?:light)?\s+on\b[^.\n]{0,60}",
            re.IGNORECASE,
        ),
        # "STROBE" / "STROBE EFFECT" / "STROBE LIGHTS"
        re.compile(
            r"\bstrobe(?:\s+(?:effect|lights?))?\b",
            re.IGNORECASE,
        ),
        # "DIM TO N%" / "LIGHTS TO N%" / "LIGHTS AT N%"
        re.compile(
            r"\b(?:dim|lights?)\s+(?:to|at)\s+\d{1,3}\s*%",
            re.IGNORECASE,
        ),
        # Parenthetical lighting notes: "(Lighting: dim blue wash)"
        re.compile(
            r"\(\s*(?:lighting|lights?)\s*[:;]\s*[^)]+\)",
            re.IGNORECASE,
        ),
        # "WASH OF <color>" / "<color> WASH"
        re.compile(
            r"\b(?:wash\s+of\s+\w+|\w+\s+wash)\b",
            re.IGNORECASE,
        ),
        # "LIGHTS COME UP" / "LIGHTS GO DOWN"
        re.compile(
            r"\blights?\s+(?:come|go)\s+(?:up|down)\b[^.\n]{0,40}",
            re.IGNORECASE,
        ),
    ]

    cues: List[str] = []
    seen: set = set()

    for pattern in patterns:
        for match in pattern.finditer(text):
            cue = match.group(0).strip()
            if cue and cue.lower() not in seen:
                seen.add(cue.lower())
                cues.append(cue)

    return cues


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------
def _validate_against_schema(scenes: List[Dict]) -> None:
    """
    Validate all scenes against scene_schema.json.
    Raises ValidationError if any scene fails.
    """
    try:
        import jsonschema
    except ImportError:
        logger.warning("jsonschema not installed — skipping schema validation")
        return

    if not _SCHEMA_PATH.exists():
        logger.warning(f"Schema file not found at {_SCHEMA_PATH} — skipping validation")
        return

    with open(_SCHEMA_PATH) as f:
        schema = json.load(f)

    for i, scene in enumerate(scenes):
        try:
            jsonschema.validate(instance=scene, schema=schema)
        except jsonschema.ValidationError as e:
            logger.error(
                f"Phase 1E: Scene {scene.get('scene_id', i)} failed schema validation: "
                f"{e.message}"
            )
            raise
