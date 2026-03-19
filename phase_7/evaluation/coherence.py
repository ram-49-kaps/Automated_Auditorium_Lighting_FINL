"""
Layer 3 — Coherence & Narrative Arc Validation
================================================
Computes:
  1. Emotional Coherence Score:
       coherence = 1 - (conflicts_detected / total_possible_checks)
       < 0.8 → WARN, < 0.6 → FAIL

  2. Narrative Arc Validation:
       - Emotion progression must be plausible
       - Primary emotion cannot randomly flip without cause
       - Excessive accent usage → WARN
"""
from typing import Dict, Any, List, Tuple, Optional

from ..presets_versioned import EMOTION_PRESETS_v1, get_color_temperature


def compute_coherence_score(
    conflicts_detected: int,
    total_possible_checks: int,
) -> Tuple[float, str]:
    """
    Compute emotional coherence score.

    Formula: coherence = 1 - (conflicts / total_checks)
    Thresholds: < 0.6 → FAIL, < 0.8 → WARN, else → PASS

    Args:
        conflicts_detected: Number of conflicts found.
        total_possible_checks: Total checks performed.

    Returns:
        Tuple of (score, verdict_str).
    """
    if total_possible_checks <= 0:
        return 1.0, "PASS"

    score = 1.0 - (conflicts_detected / total_possible_checks)
    score = max(0.0, min(1.0, score))  # Clamp to [0, 1]

    if score < 0.6:
        return round(score, 4), "FAIL"
    elif score < 0.8:
        return round(score, 4), "WARN"
    else:
        return round(score, 4), "PASS"


def validate_narrative_arc(
    instructions: List[Dict[str, Any]],
    max_allowed_flips: int = 3,
    max_accent_ratio: float = 0.5,
) -> Tuple[str, List[str]]:
    """
    Validate narrative arc across a sequence of instructions.

    Checks:
      - Primary emotion cannot flip randomly (more than max_allowed_flips
        times without a reasonable transition)
      - Excessive accent usage (> max_accent_ratio of scenes have accents) → WARN
      - Emotion progression plausibility (no identical emotion for entire script
        unless very short)

    Args:
        instructions: List of LightingInstruction dicts (with metadata.emotion).
        max_allowed_flips: Max primary emotion changes before WARN.
        max_accent_ratio: Max fraction of scenes allowed to have accent emotions.

    Returns:
        Tuple of (verdict_str, list_of_issues).
    """
    issues: List[str] = []

    if len(instructions) < 2:
        return "PASS", []

    # Extract emotion sequence from metadata
    emotions: List[str] = []
    accent_count = 0

    for instr in instructions:
        metadata = instr.get("metadata", {})
        emotion = metadata.get("emotion", "neutral")
        emotions.append(emotion)

        # Check for accent emotion presence
        accent = metadata.get("accent_emotion")
        if accent is not None:
            accent_count += 1

    # Count primary emotion flips
    flips = 0
    for i in range(1, len(emotions)):
        if emotions[i] != emotions[i - 1]:
            flips += 1

    if flips > max_allowed_flips and len(emotions) > 5:
        issues.append(
            f"Primary emotion flips {flips} times across {len(emotions)} "
            f"scenes (max recommended: {max_allowed_flips}). "
            f"Sequence: {_summarize_sequence(emotions)}"
        )

    # Check for monotonic emotion (all same — less interesting but not wrong)
    unique_emotions = set(emotions)
    if len(unique_emotions) == 1 and len(emotions) > 5:
        issues.append(
            f"Flat emotional arc: all {len(emotions)} scenes have "
            f"'{emotions[0]}' — consider reviewing script segmentation"
        )

    # Excessive accent usage
    if len(instructions) > 0:
        accent_ratio = accent_count / len(instructions)
        if accent_ratio > max_accent_ratio:
            issues.append(
                f"Excessive accent usage: {accent_count}/{len(instructions)} "
                f"scenes ({accent_ratio:.0%}) have accent emotions "
                f"(max recommended: {max_accent_ratio:.0%})"
            )

    if issues:
        return "WARN", issues

    return "PASS", []


def _summarize_sequence(emotions: List[str], max_display: int = 8) -> str:
    """
    Create a compact summary of an emotion sequence.

    Args:
        emotions: List of emotion labels.
        max_display: Max items to show.

    Returns:
        Compact string like "neutral→joy→fear→..."
    """
    if len(emotions) <= max_display:
        return " → ".join(emotions)
    else:
        shown = emotions[:max_display]
        return " → ".join(shown) + f" → ... ({len(emotions) - max_display} more)"


def compute_scene_coherence(
    emotion_dist: Dict[str, Any],
    instruction: Dict[str, Any],
    conflict_result: Dict[str, Any],
) -> Tuple[float, str]:
    """
    Compute coherence score for a single scene given its conflict result.

    Uses the total_conflicts from run_all_conflict_checks().

    Args:
        emotion_dist: Multi-emotion distribution dict.
        instruction: LightingInstruction dict.
        conflict_result: Output from conflict.run_all_conflict_checks().

    Returns:
        Tuple of (coherence_score, verdict_str).
    """
    total_checks = 4  # color, intensity, movement, preset compliance
    conflicts_detected = conflict_result.get("total_conflicts", 0)

    return compute_coherence_score(conflicts_detected, total_checks)
