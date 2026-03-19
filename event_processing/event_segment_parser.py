"""
Event Segment Parser — Rule-Based Segment Extraction

Splits college event scripts into typed segments (SPEECH, PERFORMANCE,
AWARD, etc.) using structural delimiters and keyword classification.

No NLP libraries used — pure string operations and regex.
"""

import re
import logging
from typing import List, Dict

from event_processing.config import SEGMENT_CLASSIFIER_RULES, SegmentTypes

logger = logging.getLogger("event_processing.parser")

# ---------------------------------------------------------------------------
# Structural delimiters for splitting event text into blocks
# ---------------------------------------------------------------------------

# Numbered items: "1." or "1)" at line start
_NUMBERED_ITEM = re.compile(r"^\s*\d{1,2}[.)]\s+", re.MULTILINE)

# Time block headers: "10:00 AM" or "10.00 am"
_TIME_HEADER = re.compile(
    r"^\s*\d{1,2}[.:]\d{2}\s*(?:am|pm|AM|PM)?\s*[-–—:to]*",
    re.MULTILINE,
)

# Double-newline separator (blank line between sections)
_BLANK_LINE_SEP = re.compile(r"\n\s*\n")


def parse_event_segments(text: str) -> List[Dict]:
    """
    Parse a college event script into typed segments.

    Strategy:
      1. Try splitting by numbered items (most structured format)
      2. If that yields < 3 segments, try time-block splitting
      3. If still < 3, fall back to blank-line splitting
      4. Classify each block by keyword matching against SEGMENT_CLASSIFIER_RULES

    Args:
        text: Raw event script text.

    Returns:
        List of segment dicts with segment_id, segment_type, text,
        start_line, end_line.
    """
    if not text or not text.strip():
        return []

    lines = text.split("\n")

    # Try numbered splitting first (preferred — most deterministic)
    blocks = _split_by_numbered_items(lines)

    if len(blocks) < 3:
        # Try time-block splitting
        blocks = _split_by_time_headers(lines)

    if len(blocks) < 3:
        # Fall back to blank-line separation
        blocks = _split_by_blank_lines(lines)

    if not blocks:
        # Absolute fallback: treat entire text as one segment
        blocks = [{"text": text, "start_line": 1, "end_line": len(lines)}]

    # Classify each block
    segments = []
    for i, block in enumerate(blocks):
        segment_type = _classify_block(block["text"])
        segments.append({
            "segment_id": f"seg_{i + 1:03d}",
            "segment_type": segment_type,
            "text": block["text"],
            "start_line": block["start_line"],
            "end_line": block["end_line"],
        })

    logger.info(
        f"Parsed {len(segments)} segments: "
        + ", ".join(f"{s['segment_type']}" for s in segments)
    )

    return segments


# ---------------------------------------------------------------------------
# Splitting strategies
# ---------------------------------------------------------------------------

def _split_by_numbered_items(lines: List[str]) -> List[Dict]:
    """Split on lines starting with '1.', '2.', etc."""
    boundaries = []
    for i, line in enumerate(lines):
        if _NUMBERED_ITEM.match(line):
            boundaries.append(i)

    return _boundaries_to_blocks(lines, boundaries)


def _split_by_time_headers(lines: List[str]) -> List[Dict]:
    """Split on lines containing time markers like '10:00 AM'."""
    boundaries = []
    for i, line in enumerate(lines):
        if _TIME_HEADER.match(line):
            boundaries.append(i)

    return _boundaries_to_blocks(lines, boundaries)


def _split_by_blank_lines(lines: List[str]) -> List[Dict]:
    """Split on blank-line gaps (2+ consecutive empty lines)."""
    blocks = []
    current_block_start = 0
    current_lines = []
    blank_count = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            blank_count += 1
        else:
            if blank_count >= 2 and current_lines:
                # End current block, start new one
                block_text = "\n".join(current_lines).strip()
                if block_text:
                    blocks.append({
                        "text": block_text,
                        "start_line": current_block_start + 1,  # 1-indexed
                        "end_line": i,  # approximate
                    })
                current_lines = []
                current_block_start = i
            blank_count = 0
            current_lines.append(line)

    # Last block
    if current_lines:
        block_text = "\n".join(current_lines).strip()
        if block_text:
            blocks.append({
                "text": block_text,
                "start_line": current_block_start + 1,
                "end_line": len(lines),
            })

    return blocks


def _boundaries_to_blocks(lines: List[str], boundaries: List[int]) -> List[Dict]:
    """Convert boundary line indices to text blocks."""
    if not boundaries:
        return []

    blocks = []

    # Content before first boundary (preamble)
    if boundaries[0] > 0:
        preamble_lines = lines[0 : boundaries[0]]
        preamble_text = "\n".join(preamble_lines).strip()
        if preamble_text and len(preamble_text.split()) >= 5:
            blocks.append({
                "text": preamble_text,
                "start_line": 1,
                "end_line": boundaries[0],
            })

    # Each boundary → next boundary
    for i, start_idx in enumerate(boundaries):
        if i + 1 < len(boundaries):
            end_idx = boundaries[i + 1]
        else:
            end_idx = len(lines)

        block_lines = lines[start_idx:end_idx]
        block_text = "\n".join(block_lines).strip()

        if block_text:
            blocks.append({
                "text": block_text,
                "start_line": start_idx + 1,  # 1-indexed
                "end_line": end_idx,
            })

    return blocks


# ---------------------------------------------------------------------------
# Segment classification
# ---------------------------------------------------------------------------

def _classify_block(text: str) -> str:
    """
    Classify a text block into a segment type using keyword matching.

    Iterates SEGMENT_CLASSIFIER_RULES in priority order — first match wins.
    Falls back to INTRODUCTION if nothing matches.
    """
    text_lower = text.lower()

    for keywords, segment_type in SEGMENT_CLASSIFIER_RULES:
        for keyword in keywords:
            if keyword in text_lower:
                return segment_type

    return SegmentTypes.INTRODUCTION
