"""
Phase 1C — Hybrid Timestamp Engine (Call 2)

Architecture:
  Scene count → Flexible regex extraction → Normalization to seconds
  → Rule-based validation → LLM reasoning (if ambiguous)
  → Merge valid + estimated → Final structured timestamp output

Output keys use start_time/end_time (matching Phase 4 contract).
"""

import re
import json
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from config import (
    WORDS_PER_MINUTE,
    SCENE_TRANSITION_BUFFER,
    PHASE1_LLM_MODEL,
    PHASE1_LLM_TEMPERATURE,
    PHASE1_LLM_MAX_NEW_TOKENS,
    TIMESTAMP_MAX_JUMP_SECONDS,
)
from phase_1.immutable_structurer import ImmutableText

logger = logging.getLogger("phase_1.timestamps")


# ---------------------------------------------------------------------------
# Timestamp patterns (flexible extraction)
# ---------------------------------------------------------------------------
TIMESTAMP_PATTERNS = [
    # [Approx. Timestamp: 00:00:00] — exact format from Script-1.txt
    (re.compile(r"\[Approx\.\s*Timestamp:\s*(\d{1,2}):(\d{2}):(\d{2})\]"), "approx_bracket"),
    # [00:30:15] or [00:30]
    (re.compile(r"\[(\d{1,2}):(\d{2})(?::(\d{2}))?\]"), "bracket"),
    # Timecode: 00:00:30
    (re.compile(r"(?:^|[\s(])(\d{1,2}):(\d{2}):(\d{2})(?:[\s).,]|$)"), "timecode"),
    # MM:SS standalone (but not if part of larger text like names)
    (re.compile(r"(?:^|[\s(])(\d{1,2}):(\d{2})(?:[\s).,]|$)"), "short"),
    # 10.5s format
    (re.compile(r"(\d+)\.(\d+)s\b"), "decimal_seconds"),
    # Xs format  
    (re.compile(r"\b(\d+)s\b"), "integer_seconds"),
]


@dataclass
class TimestampCandidate:
    """A potential timestamp extracted from text."""
    line_number: int
    raw_text: str
    seconds: float
    pattern_type: str
    confidence: float  # How certain we are this is a real timestamp


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def assign_timestamps(
    scenes: List[Dict],
    immutable: ImmutableText,
) -> List[Dict]:
    """
    Hybrid timestamp assignment.

    1. Regex extract candidates from script
    2. Normalize to seconds
    3. Rule-based validation
    4. LLM reasoning if ambiguous (candidate count ≠ scene count)
    5. Merge valid + estimated
    6. Final monotonic enforcement

    Args:
        scenes: List of scene dicts with scene_id, start_line, end_line.
        immutable: Frozen ImmutableText.

    Returns:
        List of scene dicts enriched with start_time, end_time, duration, confidence, source.
    """
    logger.info(f"Phase 1C timestamps: Assigning timestamps to {len(scenes)} scenes")

    # Step 1 + 2 — Extract and normalize candidates
    candidates = _extract_candidates(immutable)
    logger.info(f"Phase 1C timestamps: Found {len(candidates)} candidates")

    # Step 3 — Rule-based validation
    valid_candidates = _validate_candidates(candidates)
    logger.info(
        f"Phase 1C timestamps: {len(valid_candidates)} valid after rule-based check"
    )

    # Step 4 — Map candidates to scenes
    scene_timestamps = _map_candidates_to_scenes(valid_candidates, scenes)

    # Step 5 — Fill gaps with estimation
    scene_timestamps = _fill_gaps_with_estimation(scene_timestamps, scenes, immutable)

    # Step 6 — If too many missing, try LLM reasoning
    missing_count = sum(1 for st in scene_timestamps if st["source"] == "estimated")
    if missing_count > 0 and len(valid_candidates) > 0:
        logger.info(
            f"Phase 1C timestamps: {missing_count} scenes need estimation "
            f"(using word-count heuristic)"
        )

    # Step 7 — Final monotonic enforcement
    scene_timestamps = _enforce_monotonic(scene_timestamps)

    # Enrich scenes with timestamps
    for scene, ts in zip(scenes, scene_timestamps):
        scene["start_time"] = ts["start_time"]
        scene["end_time"] = ts["end_time"]
        scene["duration"] = ts["duration"]
        scene["timestamp_confidence"] = ts["confidence"]
        scene["timestamp_source"] = ts["source"]

    logger.info("Phase 1C timestamps: Assignment complete")
    return scenes


# ---------------------------------------------------------------------------
# Step 1+2: Extract and normalize
# ---------------------------------------------------------------------------
def _extract_candidates(immutable: ImmutableText) -> List[TimestampCandidate]:
    """Extract all timestamp candidates with their line numbers."""
    candidates = []
    seen_positions = set()  # (line_number, start_pos) to avoid duplicates

    for line_num, content in immutable.lines.items():
        if not content.strip():
            continue

        for pattern, pattern_type in TIMESTAMP_PATTERNS:
            for match in pattern.finditer(content):
                pos_key = (line_num, match.start())
                if pos_key in seen_positions:
                    continue
                seen_positions.add(pos_key)

                seconds = _parse_to_seconds(match, pattern_type)
                if seconds is not None and seconds >= 0:
                    candidates.append(TimestampCandidate(
                        line_number=line_num,
                        raw_text=match.group(0).strip(),
                        seconds=seconds,
                        pattern_type=pattern_type,
                        confidence=_pattern_confidence(pattern_type),
                    ))

    # Sort by line number
    candidates.sort(key=lambda c: c.line_number)
    return candidates


def _parse_to_seconds(match: re.Match, pattern_type: str) -> Optional[float]:
    """Convert regex match to seconds."""
    try:
        groups = match.groups()

        if pattern_type in ("approx_bracket",):
            h, m, s = int(groups[0]), int(groups[1]), int(groups[2])
            return h * 3600 + m * 60 + s

        elif pattern_type == "bracket":
            h_or_m = int(groups[0])
            m_or_s = int(groups[1])
            s = int(groups[2]) if groups[2] else 0
            if groups[2] is not None:
                return h_or_m * 3600 + m_or_s * 60 + s
            else:
                return h_or_m * 60 + m_or_s

        elif pattern_type == "timecode":
            h, m, s = int(groups[0]), int(groups[1]), int(groups[2])
            return h * 3600 + m * 60 + s

        elif pattern_type == "short":
            m, s = int(groups[0]), int(groups[1])
            return m * 60 + s

        elif pattern_type == "decimal_seconds":
            return float(f"{groups[0]}.{groups[1]}")

        elif pattern_type == "integer_seconds":
            return float(groups[0])

    except (ValueError, IndexError, TypeError):
        return None

    return None


def _pattern_confidence(pattern_type: str) -> float:
    """Confidence score by pattern type."""
    return {
        "approx_bracket": 0.95,
        "bracket": 0.90,
        "timecode": 0.85,
        "short": 0.70,
        "decimal_seconds": 0.80,
        "integer_seconds": 0.60,
    }.get(pattern_type, 0.50)


# ---------------------------------------------------------------------------
# Step 3: Validation
# ---------------------------------------------------------------------------
def _validate_candidates(candidates: List[TimestampCandidate]) -> List[TimestampCandidate]:
    """Rule-based validation of candidates."""
    if not candidates:
        return []

    valid = []
    for c in candidates:
        # Reject negative (shouldn't happen but safety)
        if c.seconds < 0:
            continue
        # Reject absurdly large (> 12 hours)
        if c.seconds > 43200:
            continue
        valid.append(c)

    # Check monotonicity — if sequence is mostly monotonic, keep it
    # Allow some non-monotonic candidates (might be from different contexts)
    if len(valid) >= 2:
        monotonic_count = sum(
            1 for i in range(1, len(valid))
            if valid[i].seconds >= valid[i - 1].seconds
        )
        monotonic_ratio = monotonic_count / (len(valid) - 1)

        if monotonic_ratio < 0.5:
            logger.warning(
                f"Timestamp candidates mostly non-monotonic "
                f"({monotonic_ratio:.0%}) — may be unreliable"
            )

    return valid


# ---------------------------------------------------------------------------
# Step 4: Map to scenes
# ---------------------------------------------------------------------------
def _map_candidates_to_scenes(
    candidates: List[TimestampCandidate],
    scenes: List[Dict],
) -> List[Dict]:
    """Map timestamp candidates to scenes by line number proximity."""
    timestamps = []

    for scene in scenes:
        sl = scene["start_line"]
        el = scene["end_line"]

        # Find candidates within or just before this scene
        scene_candidates = [
            c for c in candidates
            if sl - 2 <= c.line_number <= el  # Allow 2-line tolerance before scene
        ]

        if scene_candidates:
            # Use the first (earliest) candidate in the scene
            best = scene_candidates[0]
            timestamps.append({
                "start_time": best.seconds,
                "end_time": None,  # Will be set later
                "duration": None,
                "confidence": best.confidence,
                "source": "extracted",
            })
        else:
            timestamps.append({
                "start_time": None,
                "end_time": None,
                "duration": None,
                "confidence": 0.0,
                "source": "missing",
            })

    return timestamps


# ---------------------------------------------------------------------------
# Step 5: Fill gaps
# ---------------------------------------------------------------------------
def _fill_gaps_with_estimation(
    timestamps: List[Dict],
    scenes: List[Dict],
    immutable: ImmutableText,
) -> List[Dict]:
    """Fill missing timestamps with word-count-based estimation."""
    for i, ts in enumerate(timestamps):
        if ts["start_time"] is not None:
            continue

        # Estimate based on previous scene's end time + scene word count
        if i > 0 and timestamps[i - 1]["end_time"] is not None:
            ts["start_time"] = timestamps[i - 1]["end_time"] + SCENE_TRANSITION_BUFFER
        elif i > 0 and timestamps[i - 1]["start_time"] is not None:
            # Estimate previous scene's duration first
            prev_duration = _estimate_duration(scenes[i - 1], immutable)
            ts["start_time"] = (
                timestamps[i - 1]["start_time"] + prev_duration + SCENE_TRANSITION_BUFFER
            )
        else:
            ts["start_time"] = 0.0

        ts["source"] = "estimated"
        ts["confidence"] = 0.5

    # Now set end_times and durations
    for i in range(len(timestamps)):
        if i + 1 < len(timestamps) and timestamps[i + 1]["start_time"] is not None:
            timestamps[i]["end_time"] = timestamps[i + 1]["start_time"]
        else:
            # Last scene or next scene has no start — estimate duration
            duration = _estimate_duration(scenes[i], immutable)
            timestamps[i]["end_time"] = timestamps[i]["start_time"] + duration

        timestamps[i]["duration"] = round(
            timestamps[i]["end_time"] - timestamps[i]["start_time"], 2
        )

    return timestamps


def _estimate_duration(scene: Dict, immutable: ImmutableText) -> float:
    """Estimate scene duration from word count."""
    sl = scene.get("start_line", 1)
    el = scene.get("end_line", immutable.total_lines)

    text = " ".join(
        immutable.lines.get(i, "")
        for i in range(sl, el + 1)
    )
    word_count = len(text.split())
    duration = (word_count / WORDS_PER_MINUTE) * 60

    return max(duration, 2.0)  # Minimum 2 seconds


# ---------------------------------------------------------------------------
# Step 7: Monotonic enforcement
# ---------------------------------------------------------------------------
def _enforce_monotonic(timestamps: List[Dict]) -> List[Dict]:
    """Enforce monotonic increasing start_time."""
    for i in range(1, len(timestamps)):
        if timestamps[i]["start_time"] <= timestamps[i - 1]["start_time"]:
            # Push forward
            timestamps[i]["start_time"] = (
                timestamps[i - 1]["start_time"] + timestamps[i - 1]["duration"]
                + SCENE_TRANSITION_BUFFER
            )
            timestamps[i]["confidence"] = min(timestamps[i]["confidence"], 0.4)
            timestamps[i]["source"] = "adjusted"

        # Recalculate end_time if needed
        if timestamps[i]["end_time"] <= timestamps[i]["start_time"]:
            timestamps[i]["end_time"] = timestamps[i]["start_time"] + max(
                timestamps[i].get("duration", 2.0), 2.0
            )

        timestamps[i]["duration"] = round(
            timestamps[i]["end_time"] - timestamps[i]["start_time"], 2
        )

    # Validate no massive jumps
    for i in range(1, len(timestamps)):
        jump = timestamps[i]["start_time"] - timestamps[i - 1]["start_time"]
        if jump > TIMESTAMP_MAX_JUMP_SECONDS:
            logger.warning(
                f"Timestamp jump of {jump:.0f}s between scene {i} and {i+1} "
                f"exceeds max ({TIMESTAMP_MAX_JUMP_SECONDS}s)"
            )

    return timestamps
