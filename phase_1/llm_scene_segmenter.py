"""
Phase 1C — LLM Scene Segmentation (Call 1)

Uses Qwen2.5-7B-Instruct via HuggingFace Inference API (free, no local download).
Fallback chain: HF API → Ollama phi3:mini → regex cascade → single scene.

Key properties:
  - Temperature = 0 → deterministic
  - JSON-only output
  - Chunked processing with deterministic merge
  - Retry once on failure → Ollama fallback → rule-based fallback
"""

import json
import os
import re
import logging
from typing import List, Dict, Optional

from config import (
    PHASE1_LLM_MODEL,
    PHASE1_LLM_TEMPERATURE,
    PHASE1_LLM_MAX_RETRIES,
    PHASE1_LLM_MAX_NEW_TOKENS,
)
from phase_1.chunk_preprocessor import ChunkInfo, merge_segmentation_results
from phase_1.immutable_structurer import ImmutableText
from utils.openai_client import openai_json_array

logger = logging.getLogger("phase_1.segmenter")

# ---------------------------------------------------------------------------
# HuggingFace Inference API client (lazy singleton)
# ---------------------------------------------------------------------------
_client = None


def _get_client():
    """Get or create HuggingFace InferenceClient (lazy, lightweight)."""
    global _client
    if _client is not None:
        return _client

    from dotenv import load_dotenv
    load_dotenv()

    api_token = os.environ.get("HF_API_TOKEN")
    if not api_token:
        raise RuntimeError(
            "HF_API_TOKEN not found in environment. "
            "Add it to .env file: HF_API_TOKEN=hf_..."
        )

    from huggingface_hub import InferenceClient

    _client = InferenceClient(
        model=PHASE1_LLM_MODEL,
        token=api_token,
    )

    logger.info(f"HF Inference API client ready: {PHASE1_LLM_MODEL}")
    return _client


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
SEGMENTATION_SYSTEM_PROMPT = """You are a script segmentation engine. Your ONLY job is to identify scene boundaries in a script.

RULES:
1. You receive a line-numbered script.
2. You must output ONLY a JSON array of scene objects.
3. Each scene object has exactly three fields: "scene_id", "start_line", "end_line".
4. scene_id format: "scene_001", "scene_002", etc.
5. start_line and end_line are integers matching the line numbers in the input.
6. Scenes must not overlap.
7. Scenes must cover the entire script (no gaps, except for small blank-line gaps).
8. Do NOT include any text, explanation, or markdown formatting — ONLY the JSON array.

MANDATORY SCENE BOUNDARIES (you MUST split here — NEVER merge these):
- Every line starting with INT. or EXT. starts a NEW scene. No exceptions.
- Every line starting with INTERIOR or EXTERIOR starts a NEW scene.
- If there are 5 INT./EXT. markers, you must produce AT LEAST 5 scenes.

ADDITIONAL SCENE BOUNDARIES (split here if dramatic context supports it):
- Major dramatic shift with no location change
- Time jump indicated by timestamps or markers
- ACT or SCENE markers

DO NOT split on:
- FADE IN, FADE OUT, CUT TO (these are transitions WITHIN or BETWEEN scenes, not scenes themselves)
- Individual dialogue lines
- Short stage directions within the same location

OUTPUT FORMAT (nothing else):
[
  {"scene_id": "scene_001", "start_line": 1, "end_line": 20},
  {"scene_id": "scene_002", "start_line": 21, "end_line": 35}
]"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def segment_scenes_llm(
    chunks: List[ChunkInfo],
    immutable: ImmutableText,
) -> List[Dict]:
    """
    Run LLM scene segmentation on script chunks.

    Args:
        chunks: Preprocessed script chunks.
        immutable: The frozen ImmutableText from Phase 1B.

    Returns:
        List of scene dicts with scene_id, start_line, end_line.

    If LLM fails after retry, falls back to rule-based segmentation.
    """
    logger.info(f"Phase 1C: Starting LLM scene segmentation ({len(chunks)} chunks)")

    # Check if LLM is disabled (saves API credits)
    try:
        from config import PHASE1_USE_LLM
        if not PHASE1_USE_LLM:
            logger.info("Phase 1C: LLM disabled (PHASE1_USE_LLM=False)")
            # Tier 1 fallback: try Ollama before regex
            ollama_result = _segment_scenes_ollama(immutable)
            if ollama_result:
                logger.info(f"Phase 1C: Ollama segmentation successful — {len(ollama_result)} scenes")
                return ollama_result
            logger.info("Phase 1C: Ollama unavailable — using rule-based segmentation")
            return segment_scenes_rulebased(immutable)
    except ImportError:
        pass  # Config flag not set — proceed with LLM

    # Process each chunk
    chunk_results: List[List[Dict]] = []
    all_succeeded = True

    for chunk in chunks:
        result = _segment_chunk(chunk, attempt=1)

        if result is None:
            # Retry once
            logger.warning(
                f"Phase 1C: Chunk {chunk.chunk_id} failed — retrying (attempt 2)"
            )
            result = _segment_chunk(chunk, attempt=2)

        if result is None:
            # Try Ollama for this chunk before regex fallback
            logger.info(f"Phase 1C: Chunk {chunk.chunk_id} — trying Ollama fallback")
            result = _segment_chunk_ollama(chunk, immutable)

        if result is None:
            logger.error(
                f"Phase 1C: Chunk {chunk.chunk_id} failed after all LLMs — "
                f"falling back to rule-based for this chunk"
            )
            result = _segment_chunk_rulebased(chunk, immutable)
            all_succeeded = False

        chunk_results.append(result)

    # Merge results from all chunks
    merged = merge_segmentation_results(chunk_results, chunks)

    if not merged:
        # Total failure — try Ollama, then rule-based
        logger.error("Phase 1C: No scenes from HF API")
        merged = _segment_scenes_ollama(immutable)
        if not merged:
            logger.error("Phase 1C: Ollama also failed — full rule-based fallback")
            merged = segment_scenes_rulebased(immutable)

    # Assign sequential scene_ids
    for i, scene in enumerate(merged):
        scene["scene_id"] = f"scene_{i + 1:03d}"

    logger.info(f"Phase 1C: Segmentation complete — {len(merged)} scenes")
    return merged


def segment_scenes_rulebased(immutable: ImmutableText) -> List[Dict]:
    """
    Universal Scene Detector — Multi-Strategy Rule-Based Segmentation.

    Cascading strategies (stops when enough boundaries found):
      Strategy 1: Screenplay markers (INT./EXT./CUT TO:/FADE)
      Strategy 2: Theatre markers (ACT/SCENE keywords)
      Strategy 3: Structural analysis (ALL-CAPS blocks, blank gaps, page breaks)
      Strategy 4: Page-based estimation (for PDFs with no markers)
      Strategy 5: Density-based fallback (split by text density changes)
    """
    logger.info("Phase 1C: Running universal scene detector (rule-based)")

    total_lines = immutable.total_lines

    # ---- Strategy 1: Screenplay markers ----
    screenplay_patterns = [
        re.compile(r"^\s*INT\.", re.IGNORECASE),
        re.compile(r"^\s*EXT\.", re.IGNORECASE),
        re.compile(r".+\s*[-–—]\s*(DAY|NIGHT|DAWN|DUSK|CONTINUOUS)\s*$", re.IGNORECASE),
    ]
    # Also check mid-line (for PDF-extracted text)
    midline_patterns = [
        re.compile(r"INT\.\s+\w+", re.IGNORECASE),
        re.compile(r"EXT\.\s+\w+", re.IGNORECASE),
    ]

    boundaries = _detect_with_patterns(immutable, screenplay_patterns, midline_patterns)
    if len(boundaries) >= 2:
        logger.info(f"Phase 1C: Strategy 1 (screenplay) found {len(boundaries)} boundaries")
        return _build_scenes_from_boundaries(boundaries, total_lines)

    # ---- Strategy 2: Theatre / Stage markers ----
    theatre_patterns = [
        re.compile(r"^\s*ACT\s+[IVXLCDM\d]+", re.IGNORECASE),
        re.compile(r"^\s*SCENE\s+[IVXLCDM\d]+", re.IGNORECASE),
        re.compile(r"^\s*ACT\s+(ONE|TWO|THREE|FOUR|FIVE)", re.IGNORECASE),
        re.compile(r"^\s*SCENE\s+(ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN)", re.IGNORECASE),
        re.compile(r"^\s*PROLOGUE\s*$", re.IGNORECASE),
        re.compile(r"^\s*EPILOGUE\s*$", re.IGNORECASE),
        re.compile(r"^\s*FADE\s+IN\s*[:\.]", re.IGNORECASE),
        re.compile(r"^\s*CUT\s+TO\s*:", re.IGNORECASE),
    ]
    theatre_midline = [
        re.compile(r"\bACT\s+[IVXLCDM\d]+", re.IGNORECASE),
        re.compile(r"\bSCENE\s+[IVXLCDM\d]+", re.IGNORECASE),
        re.compile(r"\bCUT\s+TO\s*:", re.IGNORECASE),
    ]

    boundaries = _detect_with_patterns(immutable, theatre_patterns, theatre_midline)
    if len(boundaries) >= 2:
        logger.info(f"Phase 1C: Strategy 2 (theatre) found {len(boundaries)} boundaries")
        return _build_scenes_from_boundaries(boundaries, total_lines)

    # ---- Strategy 3: Structural analysis ----
    # Look for: ALL-CAPS lines (character cues), large blank gaps, page breaks
    boundaries = _detect_structural_breaks(immutable)
    if len(boundaries) >= 2:
        logger.info(f"Phase 1C: Strategy 3 (structural) found {len(boundaries)} boundaries")
        return _build_scenes_from_boundaries(boundaries, total_lines)

    # ---- Strategy 4: Page-based estimation ----
    # For PDFs: estimate ~1 scene per 2-3 pages (typical theatre scripts)
    boundaries = _detect_page_breaks(immutable)
    if len(boundaries) >= 2:
        logger.info(f"Phase 1C: Strategy 4 (page-based) found {len(boundaries)} boundaries")
        return _build_scenes_from_boundaries(boundaries, total_lines)

    # ---- Strategy 5: Density-based fallback ----
    # Split text into equal chunks based on estimated scene count
    boundaries = _detect_density_breaks(immutable)
    if len(boundaries) >= 2:
        logger.info(f"Phase 1C: Strategy 5 (density) found {len(boundaries)} boundaries")
        return _build_scenes_from_boundaries(boundaries, total_lines)

    # Absolute fallback: single scene
    logger.warning("Phase 1C: All strategies failed — single scene")
    return [{
        "scene_id": "scene_001",
        "start_line": 1,
        "end_line": total_lines,
    }]


def _detect_with_patterns(
    immutable: ImmutableText,
    start_patterns: List[re.Pattern],
    midline_patterns: List[re.Pattern] = None,
) -> List[int]:
    """Detect boundaries using start-of-line patterns, with mid-line fallback."""
    boundaries = []
    for line_num, content in immutable.lines.items():
        stripped = content.strip()
        if not stripped:
            continue
        for pattern in start_patterns:
            if pattern.match(stripped):
                boundaries.append(line_num)
                break

    # Mid-line fallback if too few found
    if len(boundaries) < 2 and midline_patterns:
        for line_num, content in immutable.lines.items():
            if line_num in boundaries:
                continue
            stripped = content.strip()
            if not stripped:
                continue
            for pattern in midline_patterns:
                if pattern.search(stripped):
                    boundaries.append(line_num)
                    break
        boundaries.sort()

    return boundaries


def _detect_structural_breaks(immutable: ImmutableText) -> List[int]:
    """
    Detect scene boundaries from structural cues:
    - ALL-CAPS lines that look like scene/location headings (not character names)
    - Clusters of blank lines (≥3 consecutive blanks)
    - Lines that look like page header/footer patterns
    """
    boundaries = []
    lines_list = sorted(immutable.lines.items())

    # Find ALL-CAPS lines that look like headings (≥8 chars, not just names)
    all_caps_lines = []
    for line_num, content in lines_list:
        stripped = content.strip()
        if (stripped.isupper() and len(stripped) >= 8
                and not stripped.isdigit()
                and ' ' in stripped):  # Must have spaces (multi-word = heading)
            all_caps_lines.append(line_num)

    if len(all_caps_lines) >= 3:
        return all_caps_lines

    # Find large blank-line clusters (≥3 consecutive blanks)
    blank_streak = 0
    blank_start = 0
    for line_num, content in lines_list:
        if not content.strip():
            if blank_streak == 0:
                blank_start = line_num
            blank_streak += 1
        else:
            if blank_streak >= 3:
                # The line AFTER the blank cluster is a scene start
                boundaries.append(line_num)
            blank_streak = 0

    return boundaries


def _detect_page_breaks(immutable: ImmutableText) -> List[int]:
    """
    Detect page boundaries by looking for page number patterns.
    Common patterns: standalone numbers, 'Page X', or lines like '---'.
    Then group pages into scenes (~2-3 pages per scene for theatre).
    """
    page_break_lines = []
    prev_was_dense = False

    for line_num, content in sorted(immutable.lines.items()):
        stripped = content.strip()

        # Standalone page numbers
        if re.match(r'^\d{1,3}$', stripped):
            page_break_lines.append(line_num)
            continue

        # Form feed or separator lines
        if stripped in ('', '---', '***', '___') or re.match(r'^[-=_]{3,}$', stripped):
            if prev_was_dense:
                page_break_lines.append(line_num)

        prev_was_dense = len(stripped) > 10

    if not page_break_lines:
        return []

    # Group pages: every 2nd page break = scene boundary (rough heuristic)
    boundaries = []
    for i, line in enumerate(page_break_lines):
        if i % 2 == 0:  # Every other page break
            # Use the line AFTER the page number as scene start
            next_content_line = line + 1
            if next_content_line <= immutable.total_lines:
                boundaries.append(next_content_line)

    return boundaries


def _detect_density_breaks(immutable: ImmutableText) -> List[int]:
    """
    Estimate scenes by splitting text into roughly equal segments.
    Uses density heuristics calibrated for both screenplay and theatre formats.
    """
    total = immutable.total_lines
    if total < 20:
        return []

    # Count non-blank lines to estimate script density
    non_blank = sum(1 for _, c in immutable.lines.items() if c.strip())

    if non_blank == 0:
        return []

    # Heuristic: theatre scripts average ~50-70 non-blank lines per scene
    # Shorter scripts (< 200 non-blank) use ~40 lines/scene
    # Longer scripts (> 500 non-blank) use ~60 lines/scene
    if non_blank < 200:
        lines_per_scene = 40
    elif non_blank < 500:
        lines_per_scene = 50
    else:
        lines_per_scene = 60

    estimated_scenes = max(2, non_blank // lines_per_scene)

    # Cap at reasonable maximum (no script has > 50 scenes typically)
    estimated_scenes = min(estimated_scenes, 50)

    logger.info(
        f"Phase 1C density: {non_blank} non-blank lines / "
        f"{lines_per_scene} per scene = {estimated_scenes} estimated scenes"
    )

    # Create evenly-spaced boundaries
    step = total // estimated_scenes
    boundaries = [1 + i * step for i in range(estimated_scenes)]

    return boundaries

def _build_scenes_from_boundaries(boundaries: List[int], total_lines: int) -> List[Dict]:
    """Build scene dicts from a sorted list of boundary line numbers."""
    scenes = []
    for i, start in enumerate(boundaries):
        if i + 1 < len(boundaries):
            end = boundaries[i + 1] - 1
        else:
            end = total_lines

        scenes.append({
            "scene_id": f"scene_{i + 1:03d}",
            "start_line": start,
            "end_line": end,
        })

    logger.info(f"Phase 1C: Built {len(scenes)} scenes from boundaries")
    return scenes


# ---------------------------------------------------------------------------
# Internal: HF Inference API call
# ---------------------------------------------------------------------------
def _segment_chunk(chunk: ChunkInfo, attempt: int) -> Optional[List[Dict]]:
    """Process a single chunk through the HuggingFace Inference API."""
    try:
        client = _get_client()

        user_prompt = (
            f"Segment this script into scenes. Output ONLY a JSON array.\n\n"
            f"LINE-NUMBERED SCRIPT:\n{chunk.line_numbered_text}"
        )

        messages = [
            {"role": "system", "content": SEGMENTATION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        # Call HF Inference API
        response = client.chat_completion(
            messages=messages,
            max_tokens=PHASE1_LLM_MAX_NEW_TOKENS,
            temperature=PHASE1_LLM_TEMPERATURE if PHASE1_LLM_TEMPERATURE > 0 else 0.01,
            top_p=0.95,
        )

        # Extract response text
        response_text = response.choices[0].message.content.strip()

        # Parse JSON from response
        scenes = _parse_json_response(response_text, chunk)

        if scenes is not None:
            logger.info(
                f"Phase 1C: Chunk {chunk.chunk_id} → {len(scenes)} scenes "
                f"(attempt {attempt})"
            )

        return scenes

    except Exception as e:
        logger.error(f"Phase 1C: HF API error on chunk {chunk.chunk_id}: {e}")
        return None


def _segment_chunk_rulebased(chunk: ChunkInfo, immutable: ImmutableText) -> List[Dict]:
    """Rule-based fallback for a single chunk."""
    markers = [
        re.compile(r"^\s*INT\.", re.IGNORECASE),
        re.compile(r"^\s*EXT\.", re.IGNORECASE),
        re.compile(r"^\s*ACT\s+[IVX\d]+", re.IGNORECASE),
        re.compile(r"^\s*SCENE\s+[IVX\d]+", re.IGNORECASE),
        re.compile(r"^[A-Z][A-Z\s]{9,}$"),
        re.compile(r".+\s*[-–—]\s*(DAY|NIGHT|DAWN|DUSK|CONTINUOUS)\s*$", re.IGNORECASE),
    ]

    boundaries = []
    for line_num in range(chunk.start_line, chunk.end_line + 1):
        content = immutable.lines.get(line_num, "").strip()
        if not content:
            continue
        for pattern in markers:
            if pattern.match(content):
                boundaries.append(line_num)
                break

    if not boundaries:
        return [{
            "scene_id": "scene_001",
            "start_line": chunk.start_line,
            "end_line": chunk.end_line,
        }]

    scenes = []
    for i, start in enumerate(boundaries):
        end = boundaries[i + 1] - 1 if i + 1 < len(boundaries) else chunk.end_line
        scenes.append({
            "scene_id": f"scene_{i + 1:03d}",
            "start_line": start,
            "end_line": end,
        })

    return scenes


# ---------------------------------------------------------------------------
# Ollama-based segmentation — MARKER-GUIDED approach
# ---------------------------------------------------------------------------

def _annotate_lines_with_markers(lines_dict: dict) -> str:
    """
    Pre-scan lines for SCENE_MARKERS from config.
    Annotate matching lines with >>> [MARKER: ...] tags.
    Returns annotated, line-numbered text ready for the LLM.
    """
    try:
        from config import SCENE_MARKERS
    except ImportError:
        SCENE_MARKERS = [
            "INT.", "EXT.", "FADE IN", "FADE OUT", "CUT TO",
            "SCENE", "ACT", "INTERIOR", "EXTERIOR", "INT", "EXT"
        ]

    annotated_lines = []
    for line_num in sorted(lines_dict.keys()):
        content = lines_dict[line_num].strip()
        if not content:
            continue

        # Check if this line contains any marker
        found_markers = []
        content_upper = content.upper()
        for marker in SCENE_MARKERS:
            if marker.upper() in content_upper:
                found_markers.append(marker)

        if found_markers:
            marker_tags = ", ".join(found_markers)
            annotated_lines.append(f"{line_num}: >>> [MARKER: {marker_tags}] {content}")
        else:
            annotated_lines.append(f"{line_num}: {content}")

    return "\n".join(annotated_lines)


OLLAMA_SEGMENTATION_PROMPT = """You are a professional script scene segmentation engine.

The script below has been pre-scanned. Lines with potential scene markers are tagged with >>> [MARKER: ...].

YOUR JOB: Decide which marked lines are REAL scene boundaries and which to IGNORE.

MARKER GUIDE — what each means:
- INT. / INT / INTERIOR → Interior location change → USUALLY a scene start
- EXT. / EXT / EXTERIOR → Exterior location change → USUALLY a scene start
- FADE IN → Script beginning → scene start ONLY if it's the first line
- FADE OUT / FADE TO BLACK → Script ending → NOT a scene start
- CUT TO → Transition marker → ONLY a scene boundary if the NEXT line has a location (INT./EXT.)
- SCENE / ACT → Explicit scene or act break → ALWAYS a scene start
- Lines WITHOUT markers can also be scene starts if there is a dramatic shift or time jump

RULES:
1. Each scene has start_line and end_line (use the line numbers from the text).
2. Scenes MUST NOT overlap and must cover the entire script.
3. Prefer fewer, meaningful scenes over many tiny fragments.
4. Ignore "CUT TO:" when it's just a transition within the same location.
5. Output ONLY a JSON array.

OUTPUT FORMAT:
[{"scene_id": "scene_001", "start_line": 1, "end_line": 25}, ...]
"""


def _segment_scenes_ollama(immutable: ImmutableText) -> Optional[List[Dict]]:
    """
    Segment scenes using Ollama phi3:mini with marker-guided approach.
    Tier 1 fallback when HuggingFace API is unavailable.
    Returns None if Ollama is unavailable or fails.
    """
    if not is_ollama_available():
        return None

    # Build marker-annotated text
    annotated_text = _annotate_lines_with_markers(immutable.lines)

    # Truncate if too long (keep marker lines and surrounding context)
    if len(annotated_text) > 5000:
        annotated_text = annotated_text[:5000] + "\n... (truncated)"

    prompt = (
        f"Segment this script into scenes using the pre-annotated markers as hints.\n"
        f"Select only the RELEVANT markers as scene boundaries. Discard noise.\n"
        f"Output ONLY a JSON array.\n\n"
        f"ANNOTATED SCRIPT:\n{annotated_text}"
    )

    result = ollama_json_array(
        prompt=prompt,
        system_prompt=OLLAMA_SEGMENTATION_PROMPT,
        temperature=0.1,
    )

    if not result:
        logger.warning("Phase 1C: Ollama marker-guided segmentation returned no results")
        return None

    # Validate the scenes
    validated = []
    for scene in result:
        if not isinstance(scene, dict):
            continue
        try:
            sl = int(scene.get("start_line", 0))
            el = int(scene.get("end_line", 0))
            if sl > 0 and el >= sl:
                validated.append({
                    "scene_id": scene.get("scene_id", f"scene_{len(validated)+1:03d}"),
                    "start_line": sl,
                    "end_line": el,
                })
        except (ValueError, TypeError):
            continue

    if len(validated) < 1:
        logger.warning("Phase 1C: Ollama returned no valid scenes")
        return None

    # Re-number scene IDs
    for i, scene in enumerate(validated):
        scene["scene_id"] = f"scene_{i + 1:03d}"

    logger.info(f"Phase 1C: Ollama marker-guided segmentation → {len(validated)} scenes")
    return validated


def _segment_chunk_ollama(chunk: ChunkInfo, immutable: ImmutableText) -> Optional[List[Dict]]:
    """Ollama marker-guided fallback for a single chunk."""
    if not is_ollama_available():
        return None

    # Build annotated text for just this chunk's line range
    chunk_lines = {
        ln: immutable.lines[ln]
        for ln in sorted(immutable.lines.keys())
        if chunk.start_line <= ln <= chunk.end_line
    }
    annotated_text = _annotate_lines_with_markers(chunk_lines)

    prompt = (
        f"Segment this script chunk into scenes using the pre-annotated markers.\n"
        f"Output ONLY a JSON array.\n\n"
        f"ANNOTATED SCRIPT CHUNK:\n{annotated_text}"
    )

    result = ollama_json_array(
        prompt=prompt,
        system_prompt=OLLAMA_SEGMENTATION_PROMPT,
        temperature=0.1,
    )

    if not result:
        return None

    validated = []
    for scene in result:
        if not isinstance(scene, dict):
            continue
        try:
            sl = int(scene.get("start_line", 0))
            el = int(scene.get("end_line", 0))
            if sl >= chunk.start_line and el <= chunk.end_line and el >= sl:
                validated.append({
                    "scene_id": scene.get("scene_id", ""),
                    "start_line": sl,
                    "end_line": el,
                })
        except (ValueError, TypeError):
            continue

    return validated if validated else None


# ---------------------------------------------------------------------------
# JSON parsing
# ---------------------------------------------------------------------------
def _parse_json_response(response: str, chunk: ChunkInfo) -> Optional[List[Dict]]:
    """
    Extract and validate JSON array from LLM response.

    Handles:
      - Clean JSON
      - JSON wrapped in markdown code blocks
      - Partial JSON with trailing text
    """
    # Try direct parse
    try:
        data = json.loads(response)
        if isinstance(data, list):
            return _validate_scenes(data, chunk)
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code block
    code_block = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", response, re.DOTALL)
    if code_block:
        try:
            data = json.loads(code_block.group(1))
            if isinstance(data, list):
                return _validate_scenes(data, chunk)
        except json.JSONDecodeError:
            pass

    # Try finding array pattern
    array_match = re.search(r"\[.*\]", response, re.DOTALL)
    if array_match:
        try:
            data = json.loads(array_match.group(0))
            if isinstance(data, list):
                return _validate_scenes(data, chunk)
        except json.JSONDecodeError:
            pass

    logger.warning(f"Phase 1C: Could not parse JSON from LLM response for chunk {chunk.chunk_id}")
    return None


def _validate_scenes(scenes: List[Dict], chunk: ChunkInfo) -> Optional[List[Dict]]:
    """Validate scene list structure."""
    if not scenes:
        return None

    validated = []
    for scene in scenes:
        if not isinstance(scene, dict):
            continue
        # Must have start_line and end_line
        if "start_line" not in scene or "end_line" not in scene:
            continue
        try:
            sl = int(scene["start_line"])
            el = int(scene["end_line"])
        except (ValueError, TypeError):
            continue

        if sl > el:
            continue

        validated.append({
            "scene_id": scene.get("scene_id", ""),
            "start_line": sl,
            "end_line": el,
        })

    return validated if validated else None
