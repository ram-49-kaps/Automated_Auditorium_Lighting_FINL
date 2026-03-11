"""
Phase 1D — Deterministic Validation & Fallback

Validates LLM outputs before they reach Phase 1E.

Scene Validation Rules:
  - No overlapping line ranges
  - No gaps > tolerance
  - start_line < end_line for every scene
  - Non-blank line coverage ≥ 80%
  - Valid JSON structure

Timestamp Validation Rules:
  - Monotonic increasing start_time
  - All scenes have start_time
  - duration ≥ 0
  - No massive unrealistic jumps

Retry hierarchy:
  Validate → PASS → continue
           → FAIL → retry_callback once
                     → PASS → continue
                     → FAIL → fallback_callback
                               → PASS → continue
                               → FAIL → HARD FAIL
"""

import logging
from typing import List, Dict, Optional, Callable, Tuple
from dataclasses import dataclass, field

from config import (
    SCENE_GAP_TOLERANCE_LINES,
    SCENE_COVERAGE_THRESHOLD,
    TIMESTAMP_MAX_JUMP_SECONDS,
    PHASE1_LLM_MAX_RETRIES,
)
from phase_1.immutable_structurer import ImmutableText

logger = logging.getLogger("phase_1.validation")


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
class ValidationHardFail(Exception):
    """Raised when validation cannot produce valid output after all fallbacks."""
    pass


# ---------------------------------------------------------------------------
# Validation result
# ---------------------------------------------------------------------------
@dataclass
class ValidationResult:
    """Result of validation check."""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    manual_review_required: bool = False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def validate_and_enforce(
    scenes: List[Dict],
    immutable: ImmutableText,
    retry_callback: Optional[Callable] = None,
    fallback_callback: Optional[Callable] = None,
) -> Tuple[List[Dict], ValidationResult]:
    """
    Validate scenes with retry and fallback.

    Args:
        scenes: Scene list from LLM + timestamp engine.
        immutable: Frozen text for reference.
        retry_callback: Callable that re-runs LLM segmentation. Returns new scenes.
        fallback_callback: Callable for rule-based fallback. Returns new scenes.

    Returns:
        (validated_scenes, validation_result) tuple.

    Raises:
        ValidationHardFail: If all attempts fail.
    """
    # Attempt 1 — Validate current output
    result = _run_full_validation(scenes, immutable)

    if result.valid:
        logger.info("Phase 1D: Validation PASSED on first attempt")
        return scenes, result

    logger.warning(f"Phase 1D: Validation FAILED — {len(result.errors)} errors")
    for err in result.errors:
        logger.warning(f"  → {err}")

    # Attempt 2 — Retry LLM
    if retry_callback is not None:
        logger.info("Phase 1D: Retrying LLM (attempt 2)")
        try:
            retried_scenes = retry_callback()
            if retried_scenes:
                result2 = _run_full_validation(retried_scenes, immutable)
                if result2.valid:
                    logger.info("Phase 1D: Validation PASSED after retry")
                    # Flag OCR instability if applicable
                    if immutable.source_method == "ocr":
                        result2.manual_review_required = True
                        result2.warnings.append(
                            "OCR-based text required LLM retry — manual review recommended"
                        )
                    return retried_scenes, result2
                logger.warning("Phase 1D: Retry still failed validation")
        except Exception as e:
            logger.error(f"Phase 1D: Retry callback error: {e}")

    # Attempt 3 — Rule-based fallback
    if fallback_callback is not None:
        logger.info("Phase 1D: Falling back to rule-based segmentation")
        try:
            fallback_scenes = fallback_callback()
            if fallback_scenes:
                result3 = _run_full_validation(fallback_scenes, immutable)
                if result3.valid:
                    logger.info("Phase 1D: Validation PASSED with rule-based fallback")
                    result3.warnings.append("Used rule-based fallback segmentation")
                    if immutable.source_method == "ocr":
                        result3.manual_review_required = True
                    return fallback_scenes, result3

                # Fallback also failed — try lenient validation
                result3_lenient = _run_full_validation(
                    fallback_scenes, immutable, lenient=True
                )
                if result3_lenient.valid:
                    logger.warning(
                        "Phase 1D: Fallback passed LENIENT validation only"
                    )
                    result3_lenient.warnings.append(
                        "Used rule-based fallback with lenient validation"
                    )
                    result3_lenient.manual_review_required = True
                    return fallback_scenes, result3_lenient

        except Exception as e:
            logger.error(f"Phase 1D: Fallback callback error: {e}")

    # All attempts exhausted — HARD FAIL
    raise ValidationHardFail(
        f"Phase 1D: All validation attempts failed. "
        f"Errors: {result.errors}. "
        f"Cannot produce valid scene segmentation."
    )


# ---------------------------------------------------------------------------
# Full validation runner
# ---------------------------------------------------------------------------
def _run_full_validation(
    scenes: List[Dict],
    immutable: ImmutableText,
    lenient: bool = False,
) -> ValidationResult:
    """Run all validation checks."""
    errors = []
    warnings = []

    if not scenes:
        return ValidationResult(valid=False, errors=["No scenes produced"])

    # Scene structure validation
    scene_errors = _validate_scene_structure(scenes, immutable, lenient)
    errors.extend(scene_errors)

    # Timestamp validation
    ts_errors, ts_warnings = _validate_timestamps(scenes)
    errors.extend(ts_errors)
    warnings.extend(ts_warnings)

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Scene structure validation
# ---------------------------------------------------------------------------
def _validate_scene_structure(
    scenes: List[Dict],
    immutable: ImmutableText,
    lenient: bool = False,
) -> List[str]:
    """Validate scene line ranges."""
    errors = []

    # Check each scene individually
    for i, scene in enumerate(scenes):
        sid = scene.get("scene_id", f"scene_{i}")
        sl = scene.get("start_line")
        el = scene.get("end_line")

        if sl is None or el is None:
            errors.append(f"{sid}: Missing start_line or end_line")
            continue

        if sl > el:
            errors.append(f"{sid}: start_line ({sl}) > end_line ({el})")

        if sl < 1:
            errors.append(f"{sid}: start_line ({sl}) < 1")

        if el > immutable.total_lines:
            if not lenient:
                errors.append(
                    f"{sid}: end_line ({el}) > total lines ({immutable.total_lines})"
                )

    # Check for overlaps
    sorted_scenes = sorted(scenes, key=lambda s: s.get("start_line", 0))
    for i in range(1, len(sorted_scenes)):
        prev_end = sorted_scenes[i - 1].get("end_line", 0)
        curr_start = sorted_scenes[i].get("start_line", 0)

        if curr_start <= prev_end:
            errors.append(
                f"Overlap: scene {i-1} ends at line {prev_end}, "
                f"scene {i} starts at line {curr_start}"
            )

    # Check for gaps
    gap_tolerance = SCENE_GAP_TOLERANCE_LINES if not lenient else 20
    for i in range(1, len(sorted_scenes)):
        prev_end = sorted_scenes[i - 1].get("end_line", 0)
        curr_start = sorted_scenes[i].get("start_line", 0)
        gap = curr_start - prev_end - 1

        if gap > gap_tolerance:
            if lenient:
                pass  # Ignore gaps in lenient mode
            else:
                errors.append(
                    f"Gap of {gap} lines between scene {i-1} (end={prev_end}) "
                    f"and scene {i} (start={curr_start})"
                )

    # Check coverage (non-blank lines)
    if not lenient:
        covered_lines = set()
        for scene in scenes:
            sl = scene.get("start_line", 0)
            el = scene.get("end_line", 0)
            covered_lines.update(range(sl, el + 1))

        # Count non-blank lines covered
        non_blank = set()
        for line_num, content in immutable.lines.items():
            if content.strip():
                non_blank.add(line_num)

        if non_blank:
            covered_non_blank = covered_lines & non_blank
            coverage = len(covered_non_blank) / len(non_blank)

            if coverage < SCENE_COVERAGE_THRESHOLD:
                errors.append(
                    f"Non-blank line coverage {coverage:.1%} is below "
                    f"threshold {SCENE_COVERAGE_THRESHOLD:.0%} "
                    f"({len(covered_non_blank)}/{len(non_blank)} lines)"
                )

    return errors


# ---------------------------------------------------------------------------
# Timestamp validation
# ---------------------------------------------------------------------------
def _validate_timestamps(scenes: List[Dict]) -> Tuple[List[str], List[str]]:
    """Validate timestamp consistency."""
    errors = []
    warnings = []

    for i, scene in enumerate(scenes):
        sid = scene.get("scene_id", f"scene_{i}")
        st = scene.get("start_time")
        et = scene.get("end_time")

        if st is None:
            errors.append(f"{sid}: Missing start_time")
            continue

        if et is not None and et < st:
            errors.append(f"{sid}: end_time ({et}) < start_time ({st})")

        duration = scene.get("duration")
        if duration is not None and duration < 0:
            errors.append(f"{sid}: Negative duration ({duration})")

    # Check monotonic
    for i in range(1, len(scenes)):
        st_prev = scenes[i - 1].get("start_time", 0)
        st_curr = scenes[i].get("start_time", 0)

        if st_curr is not None and st_prev is not None and st_curr < st_prev:
            errors.append(
                f"Non-monotonic: scene {i} start_time ({st_curr}) < "
                f"scene {i-1} start_time ({st_prev})"
            )

    # Check jumps
    for i in range(1, len(scenes)):
        st_prev = scenes[i - 1].get("start_time", 0)
        st_curr = scenes[i].get("start_time", 0)

        if st_curr is not None and st_prev is not None:
            jump = st_curr - st_prev
            if jump > TIMESTAMP_MAX_JUMP_SECONDS:
                warnings.append(
                    f"Large timestamp jump ({jump:.0f}s) between "
                    f"scene {i-1} and scene {i}"
                )

    return errors, warnings
