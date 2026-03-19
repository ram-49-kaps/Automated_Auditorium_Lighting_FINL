"""
Event Type Detector — College Event Classification

Deterministic keyword + structural heuristic classifier.
No ML, no NLP libraries — pure regex and counting.

Returns:
    {
        "is_college_event": bool,
        "confidence": float,        # 0.0–1.0
        "matched_keywords": list,   # which phrases matched
        "keyword_score": float,     # 0.0–1.0
        "structural_score": float,  # 0.0–1.0
    }
"""

import logging
from typing import Dict, List

from event_processing.config import EVENT_KEYWORDS, STRUCTURAL_PATTERNS

# Import thresholds from project config
from config import (
    EVENT_DETECTION_KEYWORD_THRESHOLD,
    EVENT_DETECTION_STRUCTURAL_MIN,
    EVENT_DETECTION_CONFIDENCE_MIN,
)

logger = logging.getLogger("event_processing.detector")


def detect_college_event(text: str) -> Dict:
    """
    Classify whether the input text represents a college auditorium event.

    Algorithm:
      1. Scan for weighted keywords → compute keyword_score
      2. Count structural patterns (agenda formatting) → compute structural_score
      3. Combine: confidence = 0.6 * keyword_score + 0.4 * structural_score
      4. is_college_event = confidence >= EVENT_DETECTION_CONFIDENCE_MIN

    Args:
        text: Raw script text to classify.

    Returns:
        Detection result dict with is_college_event, confidence, and diagnostics.
    """
    if not text or not text.strip():
        return _empty_result()

    text_lower = text.lower()
    words = text_lower.split()
    word_count = len(words)

    if word_count < 10:
        return _empty_result()

    # ------------------------------------------------------------------
    # Step 1: Keyword matching (weighted)
    # ------------------------------------------------------------------
    matched_keywords: List[str] = []
    total_weight = 0.0

    for keyword, weight in EVENT_KEYWORDS.items():
        if keyword in text_lower:
            matched_keywords.append(keyword)
            # Count occurrences for density calculation
            occurrences = text_lower.count(keyword)
            total_weight += weight * min(occurrences, 3)  # Cap at 3 to prevent flooding

    # Normalize: keyword_score = weighted_hits / (word_count * threshold)
    # This produces 1.0 when keyword density exactly meets the threshold,
    # and >1.0 (capped) when it exceeds it.
    if word_count > 0 and EVENT_DETECTION_KEYWORD_THRESHOLD > 0:
        raw_density = total_weight / word_count
        keyword_score = min(1.0, raw_density / EVENT_DETECTION_KEYWORD_THRESHOLD)
    else:
        keyword_score = 0.0

    # ------------------------------------------------------------------
    # Step 2: Structural pattern matching
    # ------------------------------------------------------------------
    pattern_matches = 0

    for pattern in STRUCTURAL_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            pattern_matches += len(matches)

    # Normalize: structural_score = pattern_count / structural_min
    if EVENT_DETECTION_STRUCTURAL_MIN > 0:
        structural_score = min(1.0, pattern_matches / EVENT_DETECTION_STRUCTURAL_MIN)
    else:
        structural_score = 0.0

    # ------------------------------------------------------------------
    # Step 3: Combine scores
    # ------------------------------------------------------------------
    # Keyword evidence weighted more heavily (60%) since it's the primary signal.
    # Structural patterns are supporting evidence (40%).
    confidence = 0.6 * keyword_score + 0.4 * structural_score
    confidence = round(min(1.0, confidence), 3)

    is_college_event = confidence >= EVENT_DETECTION_CONFIDENCE_MIN

    result = {
        "is_college_event": is_college_event,
        "confidence": confidence,
        "matched_keywords": matched_keywords,
        "keyword_score": round(keyword_score, 3),
        "structural_score": round(structural_score, 3),
    }

    if is_college_event:
        logger.info(
            f"COLLEGE_EVENT detected: confidence={confidence:.3f}, "
            f"keywords={len(matched_keywords)}, "
            f"structural_patterns={pattern_matches}"
        )
    else:
        logger.debug(
            f"NON_EVENT: confidence={confidence:.3f} "
            f"(below threshold {EVENT_DETECTION_CONFIDENCE_MIN})"
        )

    return result


def _empty_result() -> Dict:
    """Return a safe empty detection result."""
    return {
        "is_college_event": False,
        "confidence": 0.0,
        "matched_keywords": [],
        "keyword_score": 0.0,
        "structural_score": 0.0,
    }
