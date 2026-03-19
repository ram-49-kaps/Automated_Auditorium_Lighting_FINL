"""
Layer 1 — Structural Validation
=================================
Validates:
  1. Schema compliance (valid JSON structure, required fields, value ranges)
  2. Emotion hierarchy constraints (weights, emotion count)
  3. Confidence thresholds (flag low-confidence predictions)

Returns Verdict.PASS / Verdict.WARN / Verdict.FAIL for each check.
"""
from typing import Dict, Any, Tuple, List, Optional

# Valid enums from contracts
VALID_TRANSITION_TYPES = {"cut", "fade", "crossfade"}
VALID_GROUP_IDS = {
    "FRONT_WASH", "BACK_LIGHT", "SIDE_FILL",
    "SPOT_1", "SPOT_2", "SPOT_3",
}

# Confidence thresholds
PRIMARY_CONFIDENCE_MIN = 0.5
SECONDARY_CONFIDENCE_MIN = 0.4
ACCENT_CONFIDENCE_MIN = 0.3


def validate_schema(instruction: Dict[str, Any]) -> Tuple[str, List[str]]:
    """
    Validate a LightingInstruction dict against the schema contract.

    Checks:
      - Required top-level fields: scene_id, time_window, groups
      - time_window has start and end (numbers)
      - Each group has group_id and parameters
      - parameters.intensity is 0.0–1.0
      - transition.type is a valid enum value

    Args:
        instruction: LightingInstruction dict.

    Returns:
        Tuple of (verdict_str, list_of_issues).
        verdict_str is "PASS", "WARN", or "FAIL".
    """
    issues: List[str] = []

    # Required top-level fields
    for field in ("scene_id", "time_window", "groups"):
        if field not in instruction:
            issues.append(f"Missing required field: '{field}'")

    if issues:
        return "FAIL", issues

    # time_window validation
    tw = instruction.get("time_window", {})
    if not isinstance(tw, dict):
        issues.append("time_window must be an object")
    else:
        if "start" not in tw or "end" not in tw:
            issues.append("time_window missing 'start' or 'end'")
        else:
            if not isinstance(tw["start"], (int, float)):
                issues.append("time_window.start must be a number")
            if not isinstance(tw["end"], (int, float)):
                issues.append("time_window.end must be a number")
            elif isinstance(tw["start"], (int, float)) and isinstance(tw["end"], (int, float)):
                if tw["end"] < tw["start"]:
                    issues.append(
                        f"time_window.end ({tw['end']}) < start ({tw['start']})"
                    )

    # Groups validation
    groups = instruction.get("groups", [])
    if not isinstance(groups, list):
        issues.append("groups must be an array")
    elif len(groups) == 0:
        issues.append("Missing lighting groups — at least 1 group required")
    else:
        for i, group in enumerate(groups):
            prefix = f"groups[{i}]"

            if not isinstance(group, dict):
                issues.append(f"{prefix}: must be an object")
                continue

            if "group_id" not in group:
                issues.append(f"{prefix}: missing 'group_id'")

            if "parameters" not in group:
                issues.append(f"{prefix}: missing 'parameters'")
            else:
                params = group["parameters"]
                if not isinstance(params, dict):
                    issues.append(f"{prefix}.parameters: must be an object")
                else:
                    intensity = params.get("intensity")
                    if intensity is None:
                        issues.append(f"{prefix}.parameters: missing 'intensity'")
                    elif not isinstance(intensity, (int, float)):
                        issues.append(
                            f"{prefix}.parameters.intensity: must be a number"
                        )
                    elif not (0.0 <= intensity <= 1.0):
                        issues.append(
                            f"{prefix}.parameters.intensity: {intensity} "
                            f"out of range [0.0, 1.0]"
                        )

            # Transition validation (optional field)
            transition = group.get("transition")
            if transition is not None:
                if isinstance(transition, dict):
                    t_type = transition.get("type")
                    if t_type is not None and t_type not in VALID_TRANSITION_TYPES:
                        issues.append(
                            f"{prefix}.transition.type: '{t_type}' "
                            f"not in {VALID_TRANSITION_TYPES}"
                        )
                    t_dur = transition.get("duration")
                    if t_dur is not None and isinstance(t_dur, (int, float)):
                        if t_dur < 0:
                            issues.append(
                                f"{prefix}.transition.duration: {t_dur} < 0"
                            )

    if issues:
        # If any issue involves missing required fields → FAIL
        has_critical = any("Missing" in i or "missing" in i for i in issues)
        return ("FAIL" if has_critical else "WARN"), issues

    return "PASS", []


def validate_emotion_hierarchy(
    emotion_dist: Dict[str, Any]
) -> Tuple[str, List[str]]:
    """
    Validate multi-emotion hierarchy constraints.

    Checks:
      - 1–3 emotions only
      - Weight sum = 1.0 (±0.01 tolerance)
      - Primary weight ≥ 0.6
      - Accent weight ≤ 0.1

    Args:
        emotion_dist: Dict with primary/secondary/accent emotion fields.

    Returns:
        Tuple of (verdict_str, list_of_issues).
    """
    issues: List[str] = []

    primary_emotion = emotion_dist.get("primary_emotion")
    if not primary_emotion:
        return "FAIL", ["No primary_emotion found"]

    primary_weight = emotion_dist.get("primary_weight", 1.0)
    secondary_emotion = emotion_dist.get("secondary_emotion")
    secondary_weight = emotion_dist.get("secondary_weight", 0.0)
    accent_emotion = emotion_dist.get("accent_emotion")
    accent_weight = emotion_dist.get("accent_weight", 0.0)

    # Count active emotions
    num_emotions = 1
    if secondary_emotion is not None:
        num_emotions += 1
    if accent_emotion is not None:
        num_emotions += 1

    if num_emotions > 3:
        issues.append(f"Too many emotions: {num_emotions} (max 3)")

    # Weight sum
    total_weight = primary_weight
    if secondary_emotion is not None:
        total_weight += secondary_weight
    if accent_emotion is not None:
        total_weight += accent_weight

    if abs(total_weight - 1.0) > 0.01:
        issues.append(
            f"Weight sum = {total_weight:.4f} (must equal 1.0 ±0.01)"
        )

    # Primary weight constraint
    if primary_weight < 0.6:
        issues.append(
            f"Primary weight = {primary_weight} (must be ≥ 0.6)"
        )

    # Accent weight constraint
    if accent_emotion is not None and accent_weight > 0.1 + 0.001:
        issues.append(
            f"Accent weight = {accent_weight} (must be ≤ 0.1)"
        )

    if issues:
        has_critical = any(
            "Weight sum" in i or "Primary weight" in i
            for i in issues
        )
        return ("FAIL" if has_critical else "WARN"), issues

    return "PASS", []


def validate_confidence(
    emotion_dist: Dict[str, Any]
) -> Tuple[str, List[str]]:
    """
    Validate emotion detection confidence scores.

    Thresholds:
      - primary_score < 0.5 → FAIL
      - secondary_score < 0.4 → WARN (should drop secondary)
      - accent_score < 0.3 → WARN (should drop accent)

    Args:
        emotion_dist: Dict with emotion score fields.

    Returns:
        Tuple of (verdict_str, list_of_issues).
    """
    issues: List[str] = []

    primary_score = emotion_dist.get("primary_score", 1.0)
    if primary_score < PRIMARY_CONFIDENCE_MIN:
        issues.append(
            f"Primary confidence too low: {primary_score:.3f} "
            f"(minimum {PRIMARY_CONFIDENCE_MIN})"
        )
        return "FAIL", issues

    secondary_emotion = emotion_dist.get("secondary_emotion")
    if secondary_emotion is not None:
        secondary_score = emotion_dist.get("secondary_score", 0.0)
        if secondary_score < SECONDARY_CONFIDENCE_MIN:
            issues.append(
                f"Secondary confidence low: {secondary_score:.3f} "
                f"(minimum {SECONDARY_CONFIDENCE_MIN}) — consider dropping"
            )

    accent_emotion = emotion_dist.get("accent_emotion")
    if accent_emotion is not None:
        accent_score = emotion_dist.get("accent_score", 0.0)
        if accent_score < ACCENT_CONFIDENCE_MIN:
            issues.append(
                f"Accent confidence low: {accent_score:.3f} "
                f"(minimum {ACCENT_CONFIDENCE_MIN}) — consider dropping"
            )

    if issues:
        return "WARN", issues

    return "PASS", []
