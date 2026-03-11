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
# OpenAI client used for LLM-based JSON generation
from utils.openai_client import openai_json

logger = logging.getLogger("phase_1.json_builder")

# Schema path
_SCHEMA_PATH = Path(__file__).parent.parent / "contracts" / "scene_schema.json"


def build_scene_json(
    scenes: List[Dict],
    immutable: ImmutableText,
) -> List[Dict]:
    """
    Build schema-conformant scene JSON objects.

    Args:
        scenes: Validated scenes with start_line, end_line, timestamps.
        immutable: Frozen ImmutableText for deterministic text slicing.

    Returns:
        List of scene dicts conforming to scene_schema.json.
    """
    logger.info(f"Phase 1E: Building JSON for {len(scenes)} scenes")

    # Detect script type (simple heuristic)
    script_type = _detect_script_type(immutable)

    output = []
    for scene in scenes:
        scene_json = _build_single_scene(scene, immutable, script_type)
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
        "dialogue_lines": _extract_dialogue(text),
    }

    return scene_json


# Cache for script type detection (avoids repeated Ollama calls)
_script_type_cache: Dict[str, str] = {}

VALID_SCRIPT_TYPES = {"raw_drama", "timestamped_drama", "event_schedule", "cue_sheet"}


def _detect_script_type(immutable: ImmutableText) -> str:
    """
    Script type detection.
    Tier 1: Ollama LLM classification
    Tier 2: Regex heuristic (original logic)
    Tier 3: 'raw_drama' default
    """
    # Check cache first
    cache_key = immutable.sha256_hash
    if cache_key in _script_type_cache:
        return _script_type_cache[cache_key]

    # Tier 1: Try Ollama
    if is_ollama_available():
        try:
            text_sample = immutable.raw_text[:2000]
            result = ollama_json(
                prompt=(
                    f"Classify this script/document into exactly one of these types: "
                    f"raw_drama, timestamped_drama, event_schedule, cue_sheet.\n\n"
                    f"- raw_drama: A play or screenplay without embedded timestamps\n"
                    f"- timestamped_drama: A play or screenplay with time markers like [00:05:30]\n"
                    f"- event_schedule: An event agenda with times like 9:00 AM, 10:30 AM\n"
                    f"- cue_sheet: A technical lighting cue document\n\n"
                    f"TEXT:\n{text_sample}\n\n"
                    f'Return JSON: {{"script_type": "..."}}'
                ),
                system_prompt="You are a document classifier. Output ONLY valid JSON.",
                expected_keys=["script_type"],
            )
            if result and result.get("script_type") in VALID_SCRIPT_TYPES:
                script_type = result["script_type"]
                _script_type_cache[cache_key] = script_type
                logger.info(f"Phase 1E: Ollama classified script as: {script_type}")
                return script_type
        except Exception as e:
            logger.warning(f"Phase 1E: Ollama script type detection failed: {e}")

    # Tier 2: Regex heuristic (original logic)
    text = immutable.raw_text[:2000]

    has_int_ext = bool(re.search(r"\bINT\.|EXT\.\b", text))
    has_timestamps = bool(re.search(r"\[.*\d+:\d+.*\]", text))
    has_cue_sheet = bool(re.search(r"\bcue\b.*\blight", text, re.IGNORECASE))
    has_schedule = bool(re.search(r"\b\d{1,2}:\d{2}\s*(am|pm|AM|PM)\b", text))

    if has_int_ext and has_timestamps:
        script_type = "timestamped_drama"
    elif has_int_ext:
        script_type = "raw_drama"
    elif has_schedule:
        script_type = "event_schedule"
    elif has_cue_sheet:
        script_type = "cue_sheet"
    elif has_timestamps:
        script_type = "timestamped_drama"
    else:
        # Tier 3: Safe default
        script_type = "raw_drama"

    _script_type_cache[cache_key] = script_type
    return script_type


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


def _extract_dialogue(text: str) -> List[Dict[str, str]]:
    """
    Extract structured dialogue from scene text.
    Handles both standard screenplay format and inline format.
    Splits dialogue into separate speaker lines based on character names.
    Returns a list of dicts with 'character' and 'line' keys.
    """
    if not text or not text.strip():
        return []

    dialogue_lines = []
    
    # regex pattern for standard screenplay format (character name on its own line)
    # Character name is typically all caps, may have (V.O.) or (CONT'D), followed by dialogue block
    # Matches:
    # CHARACTER
    # (parentheticals optional)
    # Dialogue line here
    standard_pattern = re.compile(
        r"^[ \t]*([A-Z][A-Z0-9\s\.\-']+(?:\s*\([^)]+\))?)[ \t]*\n"  # Character line
        r"((?:[ \t]*(?:\([^)]+\)[ \t]*\n)?(?:(?![ \t]*[A-Z]{2,}).+\n?)+))", # Dialogue block (allowing parentheticals)
        re.MULTILINE
    )
    
    matches = list(standard_pattern.finditer(text))
    
    if matches:
        # Standard screenplay format found
        for match in matches:
            character = match.group(1).strip()
            # Clean up character name (remove parentheticals like (V.O.) for cleaner UI if desired, but let's keep it for now)
            
            # Clean up dialogue block (remove parentheticals on their own lines, join lines)
            raw_dialogue = match.group(2)
            cleaned_lines = []
            for line in raw_dialogue.split('\n'):
                line = line.strip()
                if line and not (line.startswith('(') and line.endswith(')')):
                     cleaned_lines.append(line)
            
            if cleaned_lines:
                 dialogue_lines.append({
                     "character": character,
                     "line": " ".join(cleaned_lines)
                 })
    else:
        # Check for inline format: RAJU: Alright boys. PAPPU: Yes.
        # Or: RAJU Alright boys. (less common but possible)
        # We'll split by character names. We assume character names are ALL CAPS (at least 2 letters) followed by an optional colon.
        inline_pattern = re.compile(r"([A-Z]{2,}[A-Z0-9\s]*:?)\s*(.*?)(?=(?:[A-Z]{2,}[A-Z0-9\s]*:)|$)", re.IGNORECASE | re.DOTALL)
        
        # But wait, we only want ALL CAPS names.
        inline_pattern_strict = re.compile(r"([A-Z]{2,}[A-Z0-9\s]*:)\s*(.*?)(?=(?:[A-Z]{2,}[A-Z0-9\s]*:)|$)", re.DOTALL)
        
        inline_matches = list(inline_pattern_strict.finditer(text))
        if inline_matches:
             for match in inline_matches:
                 character = match.group(1).replace(":", "").strip()
                 line = match.group(2).strip()
                 # Remove parentheticals
                 line = re.sub(r"^\s*\([^)]+\)\s*", "", line)
                 if line:
                     dialogue_lines.append({
                         "character": character,
                         "line": line
                     })
        else:
            # Fallback for inline without colons: "RAJU Alright boys. PAPPU Yes."
            # This is risky as it might catch stage directions.
            fallback_pattern = re.compile(r"\b([A-Z]{3,})\b\s+((?:(?!\b[A-Z]{3,}\b).)+)", re.DOTALL)
            fallback_matches = list(fallback_pattern.finditer(text))
            
            # Only use fallback if it covers a significant portion of the text,
            # to avoid false positives on random acronyms in stage directions.
            if fallback_matches and len(fallback_matches) > 1:
                 # Check if the text actually looks like dialogue
                 # A weak heuristic: if we find multiple all-caps names followed by text.
                 for match in fallback_matches:
                     character = match.group(1).strip()
                     line = match.group(2).strip()
                     # Basic cleanup
                     line = re.sub(r"^\s*\([^)]+\)\s*", "", line)
                     
                     # Skip if line looks like a scene heading or technical instruction
                     if not re.match(r"(?:INT\.|EXT\.|FADE IN|FADE OUT|CUT TO|BLACKOUT)", character + " " + line, re.IGNORECASE):
                         if line:
                             dialogue_lines.append({
                                 "character": character,
                                 "line": line
                             })

    return dialogue_lines


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
