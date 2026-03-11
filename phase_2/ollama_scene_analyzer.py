"""
Phase B — Full-Script LLM Scene Analysis

Single OpenAI call that processes the ENTIRE script with ground truth scene
boundaries, producing per-scene emotion analysis with full narrative context.

Key design:
  - Receives: full script text + scene boundaries (from Phase A)
  - Returns:  per-scene emotions/role analysis matching exactly N scenes
  - Fallback: per-scene OpenAI → per-scene DistilRoBERTa → neutral defaults

This solves the "context loss" problem: instead of analyzing each scene in
isolation, the LLM sees the complete story and understands the narrative arc.
"""

import json
import logging
from typing import List, Dict, Any, Optional

from utils.openai_client import openai_json, openai_json_array

logger = logging.getLogger("phase_2.scene_analyzer")


# ---------------------------------------------------------------------------
# System prompt for full-script analysis
# ---------------------------------------------------------------------------
FULL_SCRIPT_ANALYSIS_PROMPT = """You are a professional script emotion analyst and dramaturg.

You will receive:
1. A COMPLETE script (full text)
2. GROUND TRUTH scene boundaries (exact start_line / end_line for each scene)

YOUR JOB: Analyze the emotion of EACH scene considering the FULL narrative arc.

For each scene, provide:
- primary_emotion: The dominant emotion (e.g. joy, sadness, fear, anger, surprise, neutral, disgust, anticipation, tension, mystery, romantic, nostalgia, hope, triumph, despair, serenity, confusion, awe)
- primary_confidence: How confident you are (0.0 to 1.0)
- secondary_emotion: A secondary emotion present
- secondary_confidence: Confidence for secondary (0.0 to 1.0)
- accent_emotion: A subtle undertone emotion
- accent_confidence: Confidence for accent (0.0 to 1.0)
- narrative_role: One of: introduction, rising_action, climax, falling_action, resolution, transition, comic_relief
- mood_shift: Whether mood changes within the scene: none, gradual, sudden

CRITICAL RULES:
1. You MUST return EXACTLY the number of entries matching the scene count given.
2. Consider how each scene relates to the overall story arc.
3. A comedic scene after tension should reflect that tonal contrast.
4. Output ONLY a valid JSON array. No markdown, no explanation.

OUTPUT FORMAT:
[
  {
    "scene_id": "scene_001",
    "primary_emotion": "joy",
    "primary_confidence": 0.85,
    "secondary_emotion": "surprise",
    "secondary_confidence": 0.4,
    "accent_emotion": "anticipation",
    "accent_confidence": 0.2,
    "narrative_role": "introduction",
    "mood_shift": "none"
  },
  ...
]"""


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------
def analyze_all_scenes(
    full_script: str,
    scenes: List[Dict],
) -> List[Dict[str, Any]]:
    """
    Analyze all scenes at once using OpenAI with full narrative context.

    Args:
        full_script: The complete script text.
        scenes: Ground truth scenes from Phase A marker detection.
                Each scene must have: scene_id, start_line, end_line, content.

    Returns:
        List of emotion analysis dicts (one per scene), compatible with
        the backward-compat format in phase_2/__init__.py.

    Fallback chain:
        Tier 1: Single OpenAI call for all scenes (full context)
        Tier 2: Per-scene OpenAI calls (partial context)
        Tier 3: Per-scene existing analyze_emotion() (DistilRoBERTa etc.)
    """
    scene_count = len(scenes)
    if scene_count == 0:
        return []

    logger.info(f"Phase B: Analyzing {scene_count} scenes with full narrative context")

    # Tier 1: Full-script OpenAI analysis
    if scene_count > 10:
        logger.info(f"Phase B: Skipping full-script analysis (too many scenes: {scene_count}). Proceeding to per-scene.")
    else:
        result = _analyze_full_script_openai(full_script, scenes)
        if result and len(result) == scene_count:
            logger.info(f"Phase B: ✅ Full-script analysis complete — {len(result)} scenes")
            return [_format_emotion_result(r, scenes[i]) for i, r in enumerate(result)]
        elif result:
            logger.warning(
                f"Phase B: OpenAI returned {len(result)} entries but expected {scene_count}. "
                f"Trying per-scene fallback."
            )

    # Tier 2: Per-scene OpenAI calls (still has some context via prompt)
    per_scene_results = None
    logger.info("Phase B: Falling back to per-scene OpenAI analysis")
    per_scene_results = _analyze_per_scene_openai(full_script, scenes)
    if per_scene_results and all(r is not None for r in per_scene_results):
        return per_scene_results

    # Tier 3: Fall back to existing per-scene analyze_emotion (and merge partials)
    logger.info("Phase B: Falling back to existing per-scene emotion analysis")
    tier3_results = _analyze_with_existing_pipeline(scenes)

    if per_scene_results:
        logger.info("Phase B: Merging successful Tier 2 results with Tier 3 fallbacks")
        merged = []
        for r2, r3 in zip(per_scene_results, tier3_results):
            merged.append(r2 if r2 is not None else r3)
        return merged

    return tier3_results


# ---------------------------------------------------------------------------
# Tier 1: Full-script analysis (one OpenAI call)
# ---------------------------------------------------------------------------
def _analyze_full_script_openai(
    full_script: str,
    scenes: List[Dict],
) -> Optional[List[Dict]]:
    """Send full script + boundaries to OpenAI for holistic analysis."""
    try:
        # Build the scene boundaries summary
        boundaries_text = []
        for s in scenes:
            sid = s.get("scene_id", "")
            sl = s.get("start_line", "?")
            el = s.get("end_line", "?")
            marker = s.get("marker", "")
            boundaries_text.append(f"  {sid}: lines {sl}–{el} | {marker}")
        boundaries_summary = "\n".join(boundaries_text)

        # Build the prompt — include full script but truncate if too long
        script_text = full_script
        if len(script_text) > 6000:
            script_text = _build_condensed_script(full_script, scenes)

        prompt = (
            f"COMPLETE SCRIPT:\n"
            f"{'='*40}\n"
            f"{script_text}\n"
            f"{'='*40}\n\n"
            f"GROUND TRUTH SCENE BOUNDARIES ({len(scenes)} scenes):\n"
            f"{boundaries_summary}\n\n"
            f"Analyze EACH of the {len(scenes)} scenes above.\n"
            f"Consider the FULL narrative arc across ALL scenes.\n"
            f"Return EXACTLY {len(scenes)} entries in a JSON array.\n"
            f"Output ONLY the JSON array."
        )

        result = openai_json_array(
            prompt=prompt,
            system_prompt=FULL_SCRIPT_ANALYSIS_PROMPT,
            temperature=0.2,
        )

        return result

    except Exception as e:
        logger.warning(f"Phase B: Full-script OpenAI analysis failed: {e}")
        return None


def _build_condensed_script(full_script: str, scenes: List[Dict]) -> str:
    """
    For long scripts that exceed token limits, build a condensed version
    that keeps scene boundary lines + surrounding context (3 lines each side).
    """
    lines = full_script.splitlines()
    keep_lines = set()

    for s in scenes:
        sl = s.get("start_line", 1) - 1  # convert to 0-indexed
        el = s.get("end_line", len(lines)) - 1

        # Keep 5 lines from start + 3 lines from end of each scene
        for i in range(max(0, sl), min(len(lines), sl + 5)):
            keep_lines.add(i)
        for i in range(max(0, el - 2), min(len(lines), el + 1)):
            keep_lines.add(i)

    # Build condensed text
    result = []
    prev_i = -2
    for i in sorted(keep_lines):
        if i > prev_i + 1:
            result.append(f"  ... [{i - prev_i - 1} lines omitted] ...")
        result.append(f"{i+1}: {lines[i]}")
        prev_i = i

    return "\n".join(result)


def _analyze_per_scene_openai(
    full_script: str,
    scenes: List[Dict],
) -> Optional[List[Optional[Dict[str, Any]]]]:
    """Analyze each scene individually with OpenAI, including narrative context."""
    total = len(scenes)

    # Build a brief narrative summary for context
    scene_summary = ", ".join(
        f"Scene {s.get('scene_number', i+1)}: {s.get('marker', 'unknown')}"
        for i, s in enumerate(scenes)
    )

    results = []
    for i, scene in enumerate(scenes):
        scene_text = scene.get("content", "")
        if not scene_text:
            results.append(_neutral_default(scene))
            continue

        try:
            result = openai_json(
                prompt=(
                    f"NARRATIVE CONTEXT: This is scene {i+1} of {total}.\n"
                    f"All scenes in this script: {scene_summary}\n\n"
                    f"SCENE TEXT:\n{scene_text[:2000]}\n\n"
                    f"Analyze this scene's emotion considering its position in the narrative.\n"
                    f'Return JSON: {{"primary_emotion": "...", "primary_confidence": 0.0-1.0, '
                    f'"secondary_emotion": "...", "secondary_confidence": 0.0-1.0, '
                    f'"accent_emotion": "...", "accent_confidence": 0.0-1.0, '
                    f'"narrative_role": "introduction|rising_action|climax|falling_action|resolution", '
                    f'"mood_shift": "none|gradual|sudden"}}'
                ),
                system_prompt="You are a script emotion analyst. Output ONLY valid JSON.",
                expected_keys=["primary_emotion", "primary_confidence"],
            )

            if result:
                results.append(_format_emotion_result(result, scene))
            else:
                logger.warning(f"Phase B: Per-scene OpenAI returned nothing for scene {i+1}")
                results.append(None)

        except Exception as e:
            logger.warning(f"Phase B: Per-scene OpenAI failed for scene {i+1}: {e}")
            results.append(None)

    return results if any(r is not None for r in results) else None


# ---------------------------------------------------------------------------
# Tier 3: Existing pipeline fallback
# ---------------------------------------------------------------------------
def _analyze_with_existing_pipeline(scenes: List[Dict]) -> List[Dict[str, Any]]:
    """Fall back to the existing per-scene emotion analysis."""
    from phase_2 import analyze_emotion

    results = []
    for scene in scenes:
        text = scene.get("content", "")
        if text:
            emotion = analyze_emotion(text)
        else:
            emotion = {
                "primary_emotion": "neutral",
                "confidence": 0.5,
                "primary": "neutral",
                "primary_confidence": 0.5,
            }
        results.append(emotion)

    return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _format_emotion_result(llm_result: Dict, scene: Dict) -> Dict[str, Any]:
    """Convert LLM response to backward-compat emotion format."""
    primary = llm_result.get("primary_emotion", "neutral")
    primary_conf = float(llm_result.get("primary_confidence", 0.5))
    secondary = llm_result.get("secondary_emotion")
    secondary_conf = float(llm_result.get("secondary_confidence", 0.0))
    accent = llm_result.get("accent_emotion")
    accent_conf = float(llm_result.get("accent_confidence", 0.0))

    secondary_emotions = []
    if secondary:
        secondary_emotions.append({"emotion": secondary, "score": secondary_conf})
    if accent:
        secondary_emotions.append({"emotion": accent, "score": accent_conf})

    return {
        # Old format fields (backward-compat)
        "primary_emotion": primary,
        "confidence": primary_conf,
        "secondary_emotions": secondary_emotions,
        "sentiment_score": primary_conf,
        "theatrical_context": {
            "predicted_theme": primary,
            "confidence": primary_conf,
        },
        # New format fields
        "primary": primary,
        "primary_confidence": primary_conf,
        "secondary": secondary,
        "secondary_confidence": secondary_conf,
        "accent": accent,
        "accent_confidence": accent_conf,
        # Narrative fields (new)
        "narrative_role": llm_result.get("narrative_role", "unknown"),
        "mood_shift": llm_result.get("mood_shift", "none"),
        # Scene ref
        "scene_id": scene.get("scene_id"),
    }


def _neutral_default(scene: Dict) -> Dict[str, Any]:
    """Return neutral emotion default for a scene."""
    return {
        "primary_emotion": "neutral",
        "confidence": 0.5,
        "secondary_emotions": [],
        "sentiment_score": 0.0,
        "theatrical_context": {"predicted_theme": "neutral", "confidence": 0.5},
        "primary": "neutral",
        "primary_confidence": 0.5,
        "secondary": None,
        "secondary_confidence": 0.0,
        "accent": None,
        "accent_confidence": 0.0,
        "narrative_role": "unknown",
        "mood_shift": "none",
        "scene_id": scene.get("scene_id"),
    }
