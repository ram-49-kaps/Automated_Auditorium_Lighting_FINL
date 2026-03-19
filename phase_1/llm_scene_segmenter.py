"""
Phase 1C — LLM Scene Segmentation (Call 1)

Uses Qwen2.5-7B-Instruct via HuggingFace Inference API (free, no local download).

Key properties:
  - Temperature = 0 → deterministic
  - JSON-only output
  - Chunked processing with deterministic merge
  - Retry once on failure → fallback to rule-based
  - Generates chunk_summary per chunk for Narrative Memory system
"""

import json
import os
import re
import logging
from typing import List, Dict, Optional, Tuple

from config import (
    PHASE1_LLM_MODEL,
    PHASE1_LLM_TEMPERATURE,
    PHASE1_LLM_MAX_RETRIES,
    PHASE1_LLM_MAX_NEW_TOKENS,
)
from phase_1.chunk_preprocessor import ChunkInfo, merge_segmentation_results
from phase_1.immutable_structurer import ImmutableText

logger = logging.getLogger("phase_1.segmenter")

from utils.openai_client import llm_chat
# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
SEGMENTATION_SYSTEM_PROMPT = """You are a script segmentation engine. Your job is to identify scene boundaries in a script AND provide a brief dramatic summary of the chunk.

RULES:
1. You receive a line-numbered script.
2. You must output ONLY valid JSON — a single object with two fields: "scenes" and "chunk_summary".
3. "scenes" is an array of scene objects. Each scene object has exactly three fields: "scene_id", "start_line", "end_line".
4. scene_id format: "scene_001", "scene_002", etc.
5. start_line and end_line are integers matching the line numbers in the input.
6. Scenes must not overlap.
7. Scenes must cover the entire script (no gaps, except for small blank-line gaps).
8. "chunk_summary" is a 2-4 sentence dramatic synopsis of THIS chunk's content. Focus on: emotional texture, character dynamics, dramatic tension, and mood shifts. This summary will be used to guide lighting design.
9. Do NOT include any text, explanation, or markdown formatting — ONLY the JSON object.

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
{
  "scenes": [
    {"scene_id": "scene_001", "start_line": 1, "end_line": 20},
    {"scene_id": "scene_002", "start_line": 21, "end_line": 35}
  ],
  "chunk_summary": "A tense confrontation unfolds as the protagonist discovers betrayal. The mood shifts from cautious optimism to simmering anger, with dialogue carrying an undercurrent of fear."
}"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def segment_scenes_llm(
    chunks: List[ChunkInfo],
    immutable: ImmutableText,
) -> Tuple[List[Dict], List[str]]:
    """
    Run LLM scene segmentation on script chunks.

    Args:
        chunks: Preprocessed script chunks.
        immutable: The frozen ImmutableText from Phase 1B.

    Returns:
        Tuple of:
          - List of scene dicts with scene_id, start_line, end_line.
          - List of chunk_summary strings (one per chunk, for Narrative Memory).

    If LLM fails after retry, falls back to rule-based segmentation.
    """
    logger.info(f"Phase 1C: Starting LLM scene segmentation ({len(chunks)} chunks)")

    # Process each chunk
    chunk_results: List[List[Dict]] = []
    chunk_summaries: List[str] = []
    all_succeeded = True

    for chunk in chunks:
        scenes, summary = _segment_chunk(chunk, attempt=1)

        if scenes is None:
            # Retry once
            logger.warning(
                f"Phase 1C: Chunk {chunk.chunk_id} failed — retrying (attempt 2)"
            )
            scenes, summary = _segment_chunk(chunk, attempt=2)

        if scenes is None:
            logger.error(
                f"Phase 1C: Chunk {chunk.chunk_id} failed after retry — "
                f"falling back to rule-based for this chunk"
            )
            scenes = _segment_chunk_rulebased(chunk, immutable)
            summary = ""  # No summary available from rule-based fallback
            all_succeeded = False

        chunk_results.append(scenes)
        chunk_summaries.append(summary)

    # Merge results from all chunks
    merged = merge_segmentation_results(chunk_results, chunks)

    if not merged:
        # Total failure — fall back to full rule-based
        logger.error("Phase 1C: No scenes from LLM — full rule-based fallback")
        merged = segment_scenes_rulebased(immutable)

    # Assign sequential scene_ids
    for i, scene in enumerate(merged):
        scene["scene_id"] = f"scene_{i + 1:03d}"

    # Filter out empty summaries
    chunk_summaries = [s for s in chunk_summaries if s]

    logger.info(
        f"Phase 1C: Segmentation complete — {len(merged)} scenes, "
        f"{len(chunk_summaries)} chunk summaries collected"
    )
    return merged, chunk_summaries


def segment_scenes_rulebased(immutable: ImmutableText) -> List[Dict]:
    """
    Enhanced rule-based segmentation — no LLM needed.

    Detection layers (in priority order):
      1. INT. / EXT. / INTERIOR / EXTERIOR markers
      2. ACT / SCENE markers
      3. Full-uppercase lines ≥ 10 chars (likely sluglines or headers)
      4. Lines ending in DAY/NIGHT/DAWN/DUSK/CONTINUOUS
      5. Stage direction blocks (entrances/exits/blackouts)
      6. Significant whitespace gaps (≥ 3 consecutive blank lines)
      7. Dramatic structure cues (BLACKOUT, CURTAIN, END OF, INTERVAL)

    Post-processing:
      - Merge scenes shorter than MIN_SCENE_LINES into neighbors
      - Assign sequential scene_ids
    """
    logger.info("Phase 1C: Running enhanced rule-based segmentation")

    MIN_SCENE_LINES = 15  # Don't create scenes shorter than this

    # Layer 1-4: Standard structural markers
    structural_markers = [
        re.compile(r"^\s*INT\.", re.IGNORECASE),
        re.compile(r"^\s*EXT\.", re.IGNORECASE),
        re.compile(r"^\s*INTERIOR", re.IGNORECASE),
        re.compile(r"^\s*EXTERIOR", re.IGNORECASE),
        re.compile(r"^\s*ACT\s+[IVX\d]+", re.IGNORECASE),
        re.compile(r"^\s*SCENE\s+[IVX\d]+", re.IGNORECASE),
        re.compile(r"^[A-Z][A-Z\s]{9,}$"),  # Full uppercase ≥ 10 chars
        re.compile(r".+\s*[-–—]\s*(DAY|NIGHT|DAWN|DUSK|CONTINUOUS)\s*$", re.IGNORECASE),
    ]

    # Layer 5: Stage direction / dramatic break markers
    dramatic_markers = [
        re.compile(r"^\s*\(.*(?:enter|exit|enters|exits|leaves|arrives|appears|disappears).*\)\s*$", re.IGNORECASE),
        re.compile(r"^\s*(?:BLACKOUT|BLACK\s*OUT|LIGHTS?\s*(?:UP|DOWN|OUT|FADE)|CURTAIN|END\s+OF\s+(?:ACT|SCENE)|INTERVAL|INTERMISSION)", re.IGNORECASE),
        re.compile(r"^\s*\[.*(?:enter|exit|enters|exits|leaves|arrives|appears|disappears).*\]\s*$", re.IGNORECASE),
        re.compile(r"^\s*(?:TIME|LATER|MOMENTS?\s+LATER|HOURS?\s+LATER|THE\s+NEXT\s+(?:DAY|MORNING|EVENING))", re.IGNORECASE),
    ]

    boundaries: List[int] = []
    boundary_types: Dict[int, str] = {}  # For debugging

    sorted_lines = sorted(immutable.lines.keys())
    total_lines = len(sorted_lines)

    # Pass 1: Find structural markers
    for line_num in sorted_lines:
        content = immutable.lines.get(line_num, "").strip()
        if not content:
            continue
        for pattern in structural_markers:
            if pattern.match(content):
                boundaries.append(line_num)
                boundary_types[line_num] = "structural"
                break

    # Pass 2: Find dramatic break markers (only if not already a boundary)
    for line_num in sorted_lines:
        if line_num in boundary_types:
            continue
        content = immutable.lines.get(line_num, "").strip()
        if not content:
            continue
        for pattern in dramatic_markers:
            if pattern.match(content):
                boundaries.append(line_num)
                boundary_types[line_num] = "dramatic"
                break

    # Pass 3: Detect significant whitespace gaps (3+ consecutive blank lines)
    blank_run_start = None
    blank_count = 0
    for line_num in sorted_lines:
        content = immutable.lines.get(line_num, "").strip()
        if not content:
            if blank_run_start is None:
                blank_run_start = line_num
            blank_count += 1
        else:
            if blank_count >= 3 and line_num not in boundary_types:
                # The first non-blank line after a big gap is a scene start
                boundaries.append(line_num)
                boundary_types[line_num] = "whitespace_gap"
            blank_run_start = None
            blank_count = 0

    # Deduplicate and sort boundaries
    boundaries = sorted(set(boundaries))

    # If no boundaries found, try splitting by line count
    if not boundaries:
        logger.warning("Phase 1C fallback: No markers found — splitting by line count")
        # Split every ~60 lines for a reasonable scene size
        chunk_size = max(60, total_lines // 8)
        for i in range(0, total_lines, chunk_size):
            if i < total_lines:
                boundaries.append(sorted_lines[i])
        if not boundaries:
            return [{
                "scene_id": "scene_001",
                "start_line": 1,
                "end_line": immutable.total_lines,
            }]

    # Build scenes from boundaries
    scenes = []
    for i, start in enumerate(boundaries):
        if i + 1 < len(boundaries):
            end = boundaries[i + 1] - 1
        else:
            end = immutable.total_lines

        scenes.append({
            "scene_id": f"scene_{i + 1:03d}",
            "start_line": start,
            "end_line": end,
        })

    # Post-process: sub-split very long scenes at natural break points
    MAX_SCENE_LINES = 80  # Target max lines per scene
    TARGET_SCENE_LINES = 60  # Ideal scene size for lighting
    
    sub_split_scenes = []
    for scene in scenes:
        scene_length = scene["end_line"] - scene["start_line"] + 1
        if scene_length <= MAX_SCENE_LINES:
            sub_split_scenes.append(scene)
            continue
        
        # Find natural break points within this scene: blank lines, stage directions
        break_candidates = []
        stage_dir_pattern = re.compile(r"^\s*\(.*\)\s*$")
        
        for ln in range(scene["start_line"] + MIN_SCENE_LINES, scene["end_line"] - MIN_SCENE_LINES + 1):
            content = immutable.lines.get(ln, "").strip()
            # Empty lines and stage directions are good split points
            if not content:
                break_candidates.append(ln + 1)  # Split AFTER the blank line
            elif stage_dir_pattern.match(content):
                break_candidates.append(ln)
        
        if not break_candidates:
            # No natural breaks — just split by line count
            current = scene["start_line"]
            while current < scene["end_line"]:
                chunk_end = min(current + TARGET_SCENE_LINES - 1, scene["end_line"])
                sub_split_scenes.append({
                    "scene_id": "",
                    "start_line": current,
                    "end_line": chunk_end,
                })
                current = chunk_end + 1
        else:
            # Greedy split at natural breaks, targeting TARGET_SCENE_LINES
            current_start = scene["start_line"]
            for bp in break_candidates:
                segment_length = bp - current_start
                if segment_length >= TARGET_SCENE_LINES:
                    sub_split_scenes.append({
                        "scene_id": "",
                        "start_line": current_start,
                        "end_line": bp - 1,
                    })
                    current_start = bp
            # Remaining tail — keep splitting while too long
            while current_start <= scene["end_line"]:
                remaining = scene["end_line"] - current_start + 1
                if remaining <= MAX_SCENE_LINES:
                    # Small enough — emit final segment
                    sub_split_scenes.append({
                        "scene_id": "",
                        "start_line": current_start,
                        "end_line": scene["end_line"],
                    })
                    break
                
                # Still too long — find next break point at ~TARGET distance
                tail_breaks = [b for b in break_candidates 
                               if b > current_start + MIN_SCENE_LINES 
                               and b <= scene["end_line"]]
                split_done = False
                for bp in tail_breaks:
                    seg_len = bp - current_start
                    if seg_len >= TARGET_SCENE_LINES:
                        sub_split_scenes.append({
                            "scene_id": "",
                            "start_line": current_start,
                            "end_line": bp - 1,
                        })
                        current_start = bp
                        split_done = True
                        break
                
                if not split_done:
                    # No natural break found — force split by line count
                    chunk_end = min(current_start + TARGET_SCENE_LINES - 1, scene["end_line"])
                    sub_split_scenes.append({
                        "scene_id": "",
                        "start_line": current_start,
                        "end_line": chunk_end,
                    })
                    current_start = chunk_end + 1
    
    scenes = sub_split_scenes

    # Post-process: merge tiny scenes (< MIN_SCENE_LINES) into neighbors
    merged_scenes = []
    for scene in scenes:
        scene_length = scene["end_line"] - scene["start_line"] + 1
        if merged_scenes and scene_length < MIN_SCENE_LINES:
            # Merge into previous scene
            merged_scenes[-1]["end_line"] = scene["end_line"]
        else:
            merged_scenes.append(scene)

    # Re-index
    for i, scene in enumerate(merged_scenes):
        scene["scene_id"] = f"scene_{i + 1:03d}"

    logger.info(
        f"Phase 1C enhanced rule-based: {len(merged_scenes)} scenes "
        f"(from {len(boundaries)} raw boundaries, "
        f"{sum(1 for t in boundary_types.values() if t == 'structural')} structural, "
        f"{sum(1 for t in boundary_types.values() if t == 'dramatic')} dramatic, "
        f"{sum(1 for t in boundary_types.values() if t == 'whitespace_gap')} whitespace gaps)"
    )
    return merged_scenes


# ---------------------------------------------------------------------------
# Internal: HF Inference API call
# ---------------------------------------------------------------------------
def _segment_chunk(chunk: ChunkInfo, attempt: int) -> Tuple[Optional[List[Dict]], str]:
    """Process a single chunk through the unified LLM client.
    
    Returns:
        Tuple of (scenes_list_or_None, chunk_summary_string).
    """
    try:
        user_prompt = (
            f"Segment this script into scenes and provide a chunk_summary. "
            f"Output ONLY a JSON object with \"scenes\" and \"chunk_summary\".\n\n"
            f"LINE-NUMBERED SCRIPT:\n{chunk.line_numbered_text}"
        )

        # Call unified LLM API (uses pipeline-active model)
        response_text = llm_chat(
            prompt=user_prompt,
            system_prompt=SEGMENTATION_SYSTEM_PROMPT,
            max_tokens=PHASE1_LLM_MAX_NEW_TOKENS,
            temperature=PHASE1_LLM_TEMPERATURE if PHASE1_LLM_TEMPERATURE > 0 else 0.01,
        )
        
        if not response_text:
            logger.warning(f"Phase 1C: No response from LLM for chunk {chunk.chunk_id}")
            return None, ""

        # Parse JSON from response
        scenes, summary = _parse_json_response(response_text, chunk)

        if scenes is not None:
            logger.info(
                f"Phase 1C: Chunk {chunk.chunk_id} → {len(scenes)} scenes "
                f"(attempt {attempt})"
            )
            if summary:
                logger.info(
                    f"Phase 1C: Chunk {chunk.chunk_id} summary: "
                    f"{summary[:80]}..."
                )

        return scenes, summary

    except Exception as e:
        logger.error(f"Phase 1C: HF API error on chunk {chunk.chunk_id}: {e}")
        return None, ""


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
# JSON parsing
# ---------------------------------------------------------------------------
def _parse_json_response(response: str, chunk: ChunkInfo) -> Tuple[Optional[List[Dict]], str]:
    """
    Extract and validate JSON from LLM response.

    Handles:
      - New format: {"scenes": [...], "chunk_summary": "..."}
      - Legacy format: bare JSON array [...]
      - JSON wrapped in markdown code blocks
      - Partial JSON with trailing text
    
    Returns:
        Tuple of (validated_scenes_or_None, chunk_summary_string).
    """
    chunk_summary = ""

    def _try_extract(data):
        """Try to extract scenes and summary from parsed JSON data."""
        nonlocal chunk_summary
        if isinstance(data, dict):
            # New format: {"scenes": [...], "chunk_summary": "..."}
            scenes_data = data.get("scenes", [])
            chunk_summary = data.get("chunk_summary", "")
            if isinstance(scenes_data, list):
                return _validate_scenes(scenes_data, chunk)
        elif isinstance(data, list):
            # Legacy format: bare array
            return _validate_scenes(data, chunk)
        return None

    # Try direct parse
    try:
        data = json.loads(response)
        result = _try_extract(data)
        if result is not None:
            return result, chunk_summary
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code block
    code_block = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", response, re.DOTALL)
    if code_block:
        try:
            data = json.loads(code_block.group(1))
            result = _try_extract(data)
            if result is not None:
                return result, chunk_summary
        except json.JSONDecodeError:
            pass

    # Try finding object pattern first (new format)
    obj_match = re.search(r"\{.*\}", response, re.DOTALL)
    if obj_match:
        try:
            data = json.loads(obj_match.group(0))
            result = _try_extract(data)
            if result is not None:
                return result, chunk_summary
        except json.JSONDecodeError:
            pass

    # Try finding array pattern (legacy fallback)
    array_match = re.search(r"\[.*\]", response, re.DOTALL)
    if array_match:
        try:
            data = json.loads(array_match.group(0))
            if isinstance(data, list):
                result = _validate_scenes(data, chunk)
                if result is not None:
                    return result, chunk_summary
        except json.JSONDecodeError:
            pass

    logger.warning(f"Phase 1C: Could not parse JSON from LLM response for chunk {chunk.chunk_id}")
    return None, ""


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
