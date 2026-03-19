"""
Layer 3 — Transition Smoothness Validation
============================================
Validates that scene-to-scene transitions are physically plausible.

Rules:
  - If transition type is "fade":
      intensity jump > 0.5 between adjacent scenes → FAIL
  - If transition type is "crossfade":
      intensity jump > 0.6 → WARN
  - Detects physically implausible transitions (negative durations, etc.)
"""
from typing import Dict, Any, List, Tuple


# Maximum intensity jump for each transition type
FADE_MAX_JUMP = 0.5
CROSSFADE_MAX_JUMP = 0.6
CUT_MAX_JUMP = 1.0  # Cuts can handle any jump


def validate_transition_smoothness(
    instruction_a: Dict[str, Any],
    instruction_b: Dict[str, Any],
) -> Tuple[str, List[str]]:
    """
    Validate that the transition between two consecutive instructions
    is physically plausible.

    Args:
        instruction_a: First LightingInstruction dict (outgoing scene).
        instruction_b: Second LightingInstruction dict (incoming scene).

    Returns:
        Tuple of (verdict_str, list_of_issues).
    """
    issues: List[str] = []

    groups_a = {g["group_id"]: g for g in instruction_a.get("groups", [])
                if "group_id" in g}
    groups_b = {g["group_id"]: g for g in instruction_b.get("groups", [])
                if "group_id" in g}

    # Check common groups
    common_ids = set(groups_a.keys()) & set(groups_b.keys())

    for gid in common_ids:
        ga = groups_a[gid]
        gb = groups_b[gid]

        # Get intensities
        int_a = ga.get("parameters", {}).get("intensity", 0.5)
        int_b = gb.get("parameters", {}).get("intensity", 0.5)
        jump = abs(int_b - int_a)

        # Get transition type of incoming scene
        trans_b = gb.get("transition", {})
        if isinstance(trans_b, dict):
            t_type = trans_b.get("type", "fade")
        else:
            t_type = "fade"

        # Apply transition-specific thresholds
        if t_type == "fade" and jump > FADE_MAX_JUMP:
            issues.append(
                f"{gid}: intensity jump {int_a:.2f} → {int_b:.2f} "
                f"(Δ={jump:.2f}) exceeds fade limit ({FADE_MAX_JUMP})"
            )
        elif t_type == "crossfade" and jump > CROSSFADE_MAX_JUMP:
            issues.append(
                f"{gid}: intensity jump {int_a:.2f} → {int_b:.2f} "
                f"(Δ={jump:.2f}) exceeds crossfade limit ({CROSSFADE_MAX_JUMP})"
            )
        # CUT transitions can handle any jump — no check needed

        # Check for negative or zero duration on non-cut transitions
        if isinstance(trans_b, dict):
            duration = trans_b.get("duration", 1.0)
            if isinstance(duration, (int, float)):
                if duration < 0:
                    issues.append(
                        f"{gid}: negative transition duration ({duration}s)"
                    )
                elif duration == 0 and t_type != "cut":
                    issues.append(
                        f"{gid}: zero duration on '{t_type}' transition "
                        f"(should be > 0 for non-cut)"
                    )

    if issues:
        # If any fade violation → FAIL
        has_fade_violation = any("exceeds fade limit" in i for i in issues)
        return ("FAIL" if has_fade_violation else "WARN"), issues

    return "PASS", []


def validate_sequence_transitions(
    instructions: List[Dict[str, Any]],
) -> Tuple[str, List[str]]:
    """
    Validate all consecutive transitions in a sequence.

    Args:
        instructions: List of LightingInstruction dicts.

    Returns:
        Tuple of (overall_verdict_str, all_issues).
    """
    if len(instructions) < 2:
        return "PASS", []

    all_issues: List[str] = []
    has_fail = False

    for i in range(1, len(instructions)):
        scene_a_id = instructions[i - 1].get("scene_id", f"scene_{i}")
        scene_b_id = instructions[i].get("scene_id", f"scene_{i + 1}")

        verdict, issues = validate_transition_smoothness(
            instructions[i - 1], instructions[i]
        )

        if issues:
            prefixed = [f"[{scene_a_id} → {scene_b_id}] {issue}" for issue in issues]
            all_issues.extend(prefixed)

        if verdict == "FAIL":
            has_fail = True

    if has_fail:
        return "FAIL", all_issues
    elif all_issues:
        return "WARN", all_issues
    else:
        return "PASS", []
