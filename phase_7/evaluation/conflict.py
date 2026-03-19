"""
Layer 3 — Conflict Detection
==============================
Detects contradictions between emotion distribution and lighting cues.

Checks:
  1. Color conflict: >2 dominant color drivers OR warm+cold mix with high secondary
  2. Intensity conflict: primary low + secondary extreme high
  3. Movement conflict: secondary influencing movement (transition)
  4. Preset compliance: compare against EMOTION_PRESETS_v1
"""
from typing import Dict, Any, Tuple, List, Optional, Set

from ..presets_versioned import (
    EMOTION_PRESETS_v1,
    WARM_COLORS,
    COLD_COLORS,
    LOW_INTENSITY_EMOTIONS,
    LOW_INTENSITY_MAX,
    HIGH_INTENSITY_EMOTIONS,
    HIGH_INTENSITY_MIN,
    TRANSITION_CONFLICTS,
    MAX_SECONDARY_WEIGHT_FOR_TEMPERATURE_MIX,
    get_color_temperature,
)


def detect_color_conflict(
    emotion_dist: Dict[str, Any],
    instruction: Dict[str, Any],
) -> Tuple[str, List[str]]:
    """
    Detect color conflicts in a multi-emotion lighting instruction.

    Rules:
      - More than 2 dominant color drivers → FAIL
      - Warm vs cold blend allowed ONLY if secondary weight ≤ 0.3

    Args:
        emotion_dist: Multi-emotion distribution dict.
        instruction: LightingInstruction dict.

    Returns:
        Tuple of (verdict_str, list_of_issues).
    """
    issues: List[str] = []

    # Gather all unique colors from the instruction groups
    colors_used: Set[str] = set()
    for group in instruction.get("groups", []):
        color = group.get("parameters", {}).get("color")
        if color:
            colors_used.add(color)

    # Check how many distinct color temperature categories
    temps = {get_color_temperature(c) for c in colors_used}
    dominant_temps = temps - {"neutral"}  # Neutral doesn't drive conflict

    if len(dominant_temps) > 1:
        # Warm + Cold mix detected
        secondary_weight = emotion_dist.get("secondary_weight", 0.0)
        secondary_emotion = emotion_dist.get("secondary_emotion")

        if secondary_emotion is not None and secondary_weight > MAX_SECONDARY_WEIGHT_FOR_TEMPERATURE_MIX:
            issues.append(
                f"Color temperature conflict: warm+cold mix with "
                f"secondary_weight={secondary_weight} "
                f"(max {MAX_SECONDARY_WEIGHT_FOR_TEMPERATURE_MIX} for mixing)"
            )
            return "FAIL", issues
        elif secondary_emotion is not None:
            issues.append(
                f"Color temperature blend (warm+cold) with "
                f"secondary_weight={secondary_weight} — allowed but notable"
            )

    # Check color driver count (num unique non-neutral colors)
    non_neutral_colors = colors_used - {"white"}
    if len(non_neutral_colors) > 2:
        issues.append(
            f"Too many dominant color drivers: {len(non_neutral_colors)} "
            f"({non_neutral_colors}) — max 2 recommended"
        )
        return "FAIL", issues

    if issues:
        return "WARN", issues

    return "PASS", []


def detect_intensity_conflict(
    emotion_dist: Dict[str, Any],
    instruction: Dict[str, Any],
) -> Tuple[str, List[str]]:
    """
    Detect intensity conflicts between emotion and lighting.

    Rules:
      - Primary in low-intensity emotions + any group intensity > 0.8 → WARN
      - Primary in high-intensity emotions + primary group intensity < 0.4 → WARN

    Args:
        emotion_dist: Multi-emotion distribution dict.
        instruction: LightingInstruction dict.

    Returns:
        Tuple of (verdict_str, list_of_issues).
    """
    issues: List[str] = []

    primary_emotion = emotion_dist.get("primary_emotion", "neutral")

    # Get all intensities from groups
    intensities = [
        g.get("parameters", {}).get("intensity", 0.5)
        for g in instruction.get("groups", [])
    ]
    if not intensities:
        return "PASS", []

    max_intensity = max(intensities)
    primary_intensity = intensities[0] if intensities else 0.5  # First group = key light

    # Low-intensity emotion but high-intensity cue
    if primary_emotion in LOW_INTENSITY_EMOTIONS and max_intensity > 0.8:
        issues.append(
            f"Intensity conflict: '{primary_emotion}' is a low-intensity "
            f"emotion but max group intensity = {max_intensity:.2f} (> 0.8)"
        )

    # High-intensity emotion but low-intensity cue
    if primary_emotion in HIGH_INTENSITY_EMOTIONS and primary_intensity < 0.4:
        issues.append(
            f"Intensity conflict: '{primary_emotion}' is a high-intensity "
            f"emotion but primary group intensity = {primary_intensity:.2f} (< 0.4)"
        )

    if issues:
        return "WARN", issues

    return "PASS", []


def detect_movement_conflict(
    emotion_dist: Dict[str, Any],
    instruction: Dict[str, Any],
) -> Tuple[str, List[str]]:
    """
    Detect movement (transition) conflicts.

    Rules:
      - Movement (transition type) MUST be controlled ONLY by primary emotion.
      - If the transition type matches secondary emotion's preset but NOT
        primary emotion's preset → FAIL.
      - Transition type conflicts with primary emotion → WARN.

    Args:
        emotion_dist: Multi-emotion distribution dict.
        instruction: LightingInstruction dict.

    Returns:
        Tuple of (verdict_str, list_of_issues).
    """
    issues: List[str] = []

    primary_emotion = emotion_dist.get("primary_emotion", "neutral")
    secondary_emotion = emotion_dist.get("secondary_emotion")

    # Get transition types used in the instruction
    transitions_used: Set[str] = set()
    for group in instruction.get("groups", []):
        trans = group.get("transition")
        if trans and isinstance(trans, dict):
            t_type = trans.get("type")
            if t_type:
                transitions_used.add(t_type)

    if not transitions_used:
        return "PASS", []

    # Check if transition conflicts with primary emotion
    primary_conflicts = TRANSITION_CONFLICTS.get(primary_emotion, set())
    conflicting_transitions = transitions_used & primary_conflicts
    if conflicting_transitions:
        issues.append(
            f"Transition conflict: '{primary_emotion}' should not use "
            f"{conflicting_transitions} transitions"
        )

    # Check if secondary is influencing movement
    if secondary_emotion is not None:
        secondary_preset = EMOTION_PRESETS_v1.get(secondary_emotion, {})
        primary_preset = EMOTION_PRESETS_v1.get(primary_emotion, {})

        secondary_trans = secondary_preset.get("transition")
        primary_trans = primary_preset.get("transition")

        for t in transitions_used:
            if (
                t == secondary_trans
                and t != primary_trans
                and primary_trans is not None
            ):
                issues.append(
                    f"Movement conflict: transition '{t}' matches secondary "
                    f"emotion '{secondary_emotion}' but not primary "
                    f"'{primary_emotion}' (expected '{primary_trans}')"
                )
                return "FAIL", issues

    if issues:
        return "WARN", issues

    return "PASS", []


def check_preset_compliance(
    emotion: str,
    instruction: Dict[str, Any],
    presets: Optional[Dict] = None,
) -> Tuple[str, List[str]]:
    """
    Check if lighting cue matches the emotion preset.

    Verifies the primary group (FRONT_WASH / first group) against the
    expected preset for the detected emotion.

    Args:
        emotion: Detected primary emotion label.
        instruction: LightingInstruction dict.
        presets: Preset dict to check against (defaults to EMOTION_PRESETS_v1).

    Returns:
        Tuple of (verdict_str, list_of_issues).
    """
    if presets is None:
        presets = EMOTION_PRESETS_v1

    issues: List[str] = []

    preset = presets.get(emotion)
    if preset is None:
        issues.append(f"No preset defined for emotion '{emotion}'")
        return "WARN", issues

    groups = instruction.get("groups", [])
    if not groups:
        return "WARN", ["No groups in instruction to check"]

    # Use first group (typically FRONT_WASH / key light) for compliance check
    primary_group = groups[0]
    params = primary_group.get("parameters", {})
    trans = primary_group.get("transition", {})
    if isinstance(trans, dict):
        actual_transition = trans.get("type")
    else:
        actual_transition = None

    expected_intensity = preset.get("intensity")
    expected_color = preset.get("color")
    expected_transition = preset.get("transition")

    # Intensity check (allow ±0.1 tolerance due to strategy overrides)
    actual_intensity = params.get("intensity")
    if actual_intensity is not None and expected_intensity is not None:
        if abs(actual_intensity - expected_intensity) > 0.1:
            issues.append(
                f"Intensity mismatch for '{emotion}': "
                f"expected ~{expected_intensity}, got {actual_intensity}"
            )

    # Color check
    actual_color = params.get("color")
    if actual_color is not None and expected_color is not None:
        if actual_color != expected_color:
            issues.append(
                f"Color mismatch for '{emotion}': "
                f"expected '{expected_color}', got '{actual_color}'"
            )

    # Transition type check
    if actual_transition is not None and expected_transition is not None:
        if actual_transition != expected_transition:
            issues.append(
                f"Transition mismatch for '{emotion}': "
                f"expected '{expected_transition}', got '{actual_transition}'"
            )

    if issues:
        return "WARN", issues

    return "PASS", []


def run_all_conflict_checks(
    emotion_dist: Dict[str, Any],
    instruction: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Run all conflict detection checks and return a combined result.

    Args:
        emotion_dist: Multi-emotion distribution dict.
        instruction: LightingInstruction dict.

    Returns:
        Dict with individual verdicts, all issues, and overall verdict.
    """
    color_verdict, color_issues = detect_color_conflict(emotion_dist, instruction)
    intensity_verdict, intensity_issues = detect_intensity_conflict(emotion_dist, instruction)
    movement_verdict, movement_issues = detect_movement_conflict(emotion_dist, instruction)

    primary_emotion = emotion_dist.get("primary_emotion", "neutral")
    preset_verdict, preset_issues = check_preset_compliance(primary_emotion, instruction)

    all_issues = color_issues + intensity_issues + movement_issues + preset_issues
    verdicts = [color_verdict, intensity_verdict, movement_verdict, preset_verdict]

    if "FAIL" in verdicts:
        overall = "FAIL"
    elif "WARN" in verdicts:
        overall = "WARN"
    else:
        overall = "PASS"

    return {
        "overall": overall,
        "color_conflict": {"verdict": color_verdict, "issues": color_issues},
        "intensity_conflict": {"verdict": intensity_verdict, "issues": intensity_issues},
        "movement_conflict": {"verdict": movement_verdict, "issues": movement_issues},
        "preset_compliance": {"verdict": preset_verdict, "issues": preset_issues},
        "all_issues": all_issues,
        "total_conflicts": len(all_issues),
    }
