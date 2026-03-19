"""
Emotion Vector Model — Deterministic Post-Processing

Smooths emotion sequences to prevent abrupt jumps.
Recalculates dominant emotion excluding neutral.
Computes emotional drift score for validation.

NO LLM calls. Purely deterministic.
"""

from .config_full_context import (
    EMOTIONAL_DELTA_CAP,
    CONFIDENCE_PENALTY_ON_FLIP,
    ENABLE_SMOOTHING,
)


def smooth_emotion_sequence(scenes: list) -> list:
    """
    Smooth energy values across adjacent scenes and penalise abrupt flips.

    Rules:
      - If |energy[i] - energy[i-1]| > EMOTIONAL_DELTA_CAP → clamp the delta.
      - If emotion label changes between adjacent scenes → reduce confidence
        by CONFIDENCE_PENALTY_ON_FLIP.

    Args:
        scenes: List of scene dicts, each containing an "emotion" sub-dict
                with keys: label, energy, valence, confidence.

    Returns:
        The same list with smoothed energy values and adjusted confidences.
    """
    if not ENABLE_SMOOTHING or len(scenes) < 2:
        return scenes

    for i in range(1, len(scenes)):
        prev_emotion = scenes[i - 1]["emotion"]
        curr_emotion = scenes[i]["emotion"]

        # --- Energy clamping ---
        delta = curr_emotion["energy"] - prev_emotion["energy"]
        if abs(delta) > EMOTIONAL_DELTA_CAP:
            sign = 1 if delta > 0 else -1
            curr_emotion["energy"] = round(
                prev_emotion["energy"] + sign * EMOTIONAL_DELTA_CAP, 4
            )

        # --- Confidence penalty on label flip ---
        if curr_emotion["label"] != prev_emotion["label"]:
            curr_emotion["confidence"] = round(
                max(0.0, curr_emotion["confidence"] - CONFIDENCE_PENALTY_ON_FLIP), 4
            )

    return scenes


def recalculate_dominant_emotion(scenes: list, exclude_neutral: bool = True) -> str:
    """
    Compute the dominant emotion across all scenes using confidence-weighted
    tallying.

    Args:
        scenes:          List of scene dicts (post-smoothing).
        exclude_neutral: If True, ignore scenes where label == "neutral".

    Returns:
        The dominant emotion label string.
    """
    weights: dict = {}

    for scene in scenes:
        label = scene["emotion"]["label"]
        if exclude_neutral and label == "neutral":
            continue
        confidence = scene["emotion"].get("confidence", 0.5)
        weights[label] = weights.get(label, 0.0) + confidence

    if not weights:
        # All scenes were neutral — fall back
        return "neutral"

    return max(weights, key=weights.get)


def calculate_emotional_drift_score(scenes: list) -> dict:
    """
    Measure emotional instability in the sequence.

    Counts:
      1. Emotion label flips between adjacent scenes.
      2. Energy deltas that exceed EMOTIONAL_DELTA_CAP (pre-smoothing value).

    Returns:
        Dict with:
          - flip_count:        int
          - large_delta_count: int
          - total_transitions: int
          - drift_percentage:  float (0-100)
    """
    if len(scenes) < 2:
        return {
            "flip_count": 0,
            "large_delta_count": 0,
            "total_transitions": 0,
            "drift_percentage": 0.0,
        }

    flip_count = 0
    large_delta_count = 0
    total = len(scenes) - 1

    for i in range(1, len(scenes)):
        prev = scenes[i - 1]["emotion"]
        curr = scenes[i]["emotion"]

        if curr["label"] != prev["label"]:
            flip_count += 1

        if abs(curr["energy"] - prev["energy"]) > EMOTIONAL_DELTA_CAP:
            large_delta_count += 1

    drift_pct = round((flip_count / total) * 100, 2) if total > 0 else 0.0

    return {
        "flip_count": flip_count,
        "large_delta_count": large_delta_count,
        "total_transitions": total,
        "drift_percentage": drift_pct,
    }
