"""
Chunk Preprocessor — Hierarchical Sliding Window

Splits the immutable text into structural chunks before sending to the LLM.

Algorithm:
  1. Identify structural anchors (blank-line clusters, uppercase headers, separators)
  2. Split at anchors into structural chunks
  3. Enforce max chunk size (subdivide at next best boundary if exceeded)
  4. Add overlap between adjacent chunks for boundary context

Chunk merge rules (deterministic, applied AFTER LLM returns):
  1. EARLIER CHUNK WINS — if overlap zone has duplicate scene, keep earlier chunk's
  2. DEDUPLICATE BY START_LINE — identical start_line = same scene, keep earlier
  3. GLOBAL MONOTONIC ORDERING — start_line[i] < start_line[i+1]
  4. OVERLAP ZONE SCENES — scene starting in overlap zone assigned to current chunk
"""

import logging
from dataclasses import dataclass
from typing import List, Dict

from config import CHUNK_MAX_LINES, CHUNK_OVERLAP_LINES
from phase_1.immutable_structurer import ImmutableText, StructuralMetadata

logger = logging.getLogger("phase_1.chunker")


@dataclass
class ChunkInfo:
    """A single chunk of the script, ready for LLM processing."""
    chunk_id: int
    start_line: int            # 1-based, inclusive
    end_line: int              # 1-based, inclusive
    line_numbered_text: str    # "1: FADE IN:\n2: \n3: INT. ..."
    overlap_start: int         # First line that overlaps with previous chunk
    total_lines: int


def create_chunks(immutable: ImmutableText) -> List[ChunkInfo]:
    """
    Split immutable text into overlapping structural chunks.

    Args:
        immutable: The frozen ImmutableText from Phase 1B.

    Returns:
        List of ChunkInfo objects, ordered by start_line.
    """
    metadata = immutable.structural_metadata
    total = immutable.total_lines

    if total == 0:
        return []

    # If the script is small enough, return as a single chunk
    if total <= CHUNK_MAX_LINES:
        logger.info(f"Chunker: Script fits in single chunk ({total} lines)")
        return [_build_chunk(immutable.lines, 1, total, chunk_id=0, overlap_start=1)]

    # Find all candidate split points (structural anchors)
    split_points = _find_split_points(metadata, total)

    # Build chunks by grouping lines between split points
    chunks = _build_chunks_from_splits(
        immutable.lines, split_points, total, CHUNK_MAX_LINES, CHUNK_OVERLAP_LINES
    )

    logger.info(
        f"Chunker: Split {total} lines into {len(chunks)} chunks "
        f"(max={CHUNK_MAX_LINES}, overlap={CHUNK_OVERLAP_LINES})"
    )

    return chunks


def merge_segmentation_results(
    chunk_results: List[List[Dict]],
    chunks: List[ChunkInfo],
) -> List[Dict]:
    """
    Merge scene segmentation results from multiple chunks.

    Applies the 4 deterministic merge rules:
      1. Earlier chunk wins for scenes in overlap zones
      2. Deduplicate by start_line
      3. Enforce global monotonic ordering
      4. Overlap zone scenes assigned to current (earlier) chunk

    Args:
        chunk_results: Per-chunk scene lists from LLM.
        chunks: The ChunkInfo objects used for processing.

    Returns:
        Globally merged and validated list of scene dicts.
    """
    if not chunk_results:
        return []

    # Flatten all scenes with chunk provenance
    all_scenes = []
    for chunk_idx, scenes in enumerate(chunk_results):
        for scene in scenes:
            all_scenes.append({
                **scene,
                "_chunk_idx": chunk_idx,
                "_chunk_start": chunks[chunk_idx].start_line,
                "_chunk_end": chunks[chunk_idx].end_line,
            })

    # Sort by start_line, then by chunk_idx (earlier chunk first)
    all_scenes.sort(key=lambda s: (s.get("start_line", 0), s["_chunk_idx"]))

    # Rule 2 — Deduplicate by start_line (keep earlier chunk's version)
    seen_starts = set()
    deduped = []
    for scene in all_scenes:
        sl = scene.get("start_line")
        if sl not in seen_starts:
            seen_starts.add(sl)
            deduped.append(scene)
        else:
            logger.debug(
                f"Chunker merge: Dropping duplicate scene at start_line={sl} "
                f"from chunk {scene['_chunk_idx']}"
            )

    # Rule 3 — Enforce global monotonic ordering
    monotonic = []
    last_start = -1
    for scene in deduped:
        sl = scene.get("start_line", 0)
        if sl > last_start:
            monotonic.append(scene)
            last_start = sl
        else:
            logger.debug(
                f"Chunker merge: Removing non-monotonic scene at start_line={sl}"
            )

    # Rule 4 — Resolve overlaps by clipping start_line
    for i in range(1, len(monotonic)):
        prev_end = monotonic[i - 1].get("end_line", 0)
        curr_start = monotonic[i].get("start_line", 0)
        if curr_start <= prev_end:
            logger.info(
                f"Chunker merge: Fixing overlap — scene {i} start_line "
                f"{curr_start} → {prev_end + 1} (was overlapping with "
                f"previous end_line {prev_end})"
            )
            monotonic[i]["start_line"] = prev_end + 1

    # Clean up internal metadata
    for scene in monotonic:
        scene.pop("_chunk_idx", None)
        scene.pop("_chunk_start", None)
        scene.pop("_chunk_end", None)

    logger.info(
        f"Chunker merge: {len(all_scenes)} raw → {len(monotonic)} final scenes"
    )

    return monotonic


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _find_split_points(metadata: StructuralMetadata, total_lines: int) -> List[int]:
    """
    Find candidate split points from structural metadata.

    Priority order:
      1. Separator lines (INT., EXT., ACT, SCENE, ---)
      2. Uppercase headers
      3. Blank-line clusters (≥2 consecutive blanks)
    """
    candidates = set()

    # Separators are the strongest signal
    candidates.update(metadata.separator_line_indices)

    # Uppercase headers
    candidates.update(metadata.uppercase_line_indices)

    # Blank-line clusters (find positions where ≥2 consecutive blanks occur)
    blank_set = set(metadata.blank_line_indices)
    for idx in metadata.blank_line_indices:
        if (idx + 1) in blank_set:
            # Start of a blank cluster — split after it
            # Find end of cluster
            end = idx
            while (end + 1) in blank_set:
                end += 1
            # Split point is the line AFTER the blank cluster
            if end + 1 <= total_lines:
                candidates.add(end + 1)

    # Sort and return
    points = sorted(candidates)
    return points


def _build_chunks_from_splits(
    lines: Dict[int, str],
    split_points: List[int],
    total_lines: int,
    max_lines: int,
    overlap: int,
) -> List[ChunkInfo]:
    """Build chunks using split points, enforcing max size and overlap."""
    # Add boundaries
    boundaries = [1] + [sp for sp in split_points if 1 < sp <= total_lines]
    # Remove duplicates and sort
    boundaries = sorted(set(boundaries))

    # Group boundaries into chunks that don't exceed max_lines
    chunks = []
    chunk_id = 0
    i = 0

    while i < len(boundaries):
        chunk_start = boundaries[i]

        # Find end: accumulate segments until max_lines would be exceeded
        j = i + 1
        while j < len(boundaries):
            proposed_end = boundaries[j] - 1
            if proposed_end - chunk_start + 1 > max_lines:
                break
            j += 1

        # Chunk end
        if j < len(boundaries):
            chunk_end = boundaries[j] - 1
        else:
            chunk_end = total_lines

        # If chunk still exceeds max_lines (no split points within),
        # force-split at max_lines boundary
        if chunk_end - chunk_start + 1 > max_lines:
            chunk_end = chunk_start + max_lines - 1

        # Determine overlap start
        if chunk_id == 0:
            overlap_start = chunk_start
        else:
            overlap_start = max(chunk_start - overlap, 1)
            chunk_start = overlap_start  # Extend chunk back for overlap

        chunk = _build_chunk(lines, chunk_start, min(chunk_end, total_lines), chunk_id, overlap_start)
        chunks.append(chunk)
        chunk_id += 1

        # Move to next segment after this chunk (excluding overlap)
        # Find the next boundary after chunk_end
        i = j
        if i >= len(boundaries) and chunk_end < total_lines:
            # No more boundaries but lines remain
            remaining_start = chunk_end + 1
            overlap_start = max(remaining_start - overlap, 1)
            chunk = _build_chunk(
                lines, overlap_start, total_lines, chunk_id, overlap_start
            )
            chunks.append(chunk)
            break

    # If we never created any chunks (shouldn't happen), create one big chunk
    if not chunks:
        chunks.append(_build_chunk(lines, 1, total_lines, 0, 1))

    return chunks


def _build_chunk(
    lines: Dict[int, str],
    start: int,
    end: int,
    chunk_id: int,
    overlap_start: int,
) -> ChunkInfo:
    """Build a single ChunkInfo from line range."""
    numbered_lines = []
    for i in range(start, end + 1):
        content = lines.get(i, "")
        numbered_lines.append(f"{i}: {content}")

    return ChunkInfo(
        chunk_id=chunk_id,
        start_line=start,
        end_line=end,
        line_numbered_text="\n".join(numbered_lines),
        overlap_start=overlap_start,
        total_lines=end - start + 1,
    )
