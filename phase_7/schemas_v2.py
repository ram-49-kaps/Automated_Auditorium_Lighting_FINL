"""
Phase 7 — Schema Extensions (v2)
==================================
Pydantic models for multi-emotion evaluation.
EXTENDS schemas.py — does NOT replace it.

Models:
  - EmotionLayer: single emotion with weight + score
  - MultiEmotionDistribution: primary/secondary/accent hierarchy
  - EvaluationVerdict: per-scene PASS/WARN/FAIL for each check
  - EvaluationReport: full pipeline report
  - HumanFeedbackEntry: human feedback log schema
"""
from pydantic import BaseModel, Field, model_validator
from typing import Optional, List, Dict, Any, Literal
from enum import Enum
from datetime import datetime


# ──────────────────────────────────────────────────────────────
# Verdict enum
# ──────────────────────────────────────────────────────────────
class Verdict(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class TrendDirection(str, Enum):
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"


# ──────────────────────────────────────────────────────────────
# Multi-Emotion Schemas
# ──────────────────────────────────────────────────────────────
class EmotionLayer(BaseModel):
    """Single emotion layer with weight and confidence score."""
    emotion: str
    weight: float = Field(ge=0.0, le=1.0)
    score: float = Field(ge=0.0, le=1.0)


class MultiEmotionDistribution(BaseModel):
    """
    Hierarchical emotion distribution for a scene.

    Hard constraints:
      - Max 3 emotions
      - Weight sum = 1.0 (within tolerance)
      - Primary weight ≥ 0.6
      - Accent weight ≤ 0.1
    """
    primary: EmotionLayer
    secondary: Optional[EmotionLayer] = None
    accent: Optional[EmotionLayer] = None
    num_emotions: int = Field(ge=1, le=3, default=1)
    method: str = "unknown"

    @model_validator(mode="after")
    def validate_constraints(self) -> "MultiEmotionDistribution":
        """Validate all hard constraints after model creation."""
        # Count actual emotions
        count = 1
        total_weight = self.primary.weight

        if self.secondary is not None:
            count += 1
            total_weight += self.secondary.weight

        if self.accent is not None:
            count += 1
            total_weight += self.accent.weight

        self.num_emotions = count

        # Weight sum check (allow ±0.01 floating point tolerance)
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(
                f"Weight sum must equal 1.0 (got {total_weight:.4f})"
            )

        # Primary weight constraint
        if self.primary.weight < 0.6:
            raise ValueError(
                f"Primary weight must be ≥ 0.6 (got {self.primary.weight})"
            )

        # Accent weight constraint
        if self.accent is not None and self.accent.weight > 0.1:
            raise ValueError(
                f"Accent weight must be ≤ 0.1 (got {self.accent.weight})"
            )

        return self

    @classmethod
    def from_analyzer_output(cls, output: Dict) -> "MultiEmotionDistribution":
        """
        Create from MultiEmotionAnalyzer output dict.

        Args:
            output: Result from analyze_multi_emotion()
        """
        primary = EmotionLayer(
            emotion=output["primary_emotion"],
            weight=output["primary_weight"],
            score=output["primary_score"],
        )

        secondary = None
        if output.get("secondary_emotion") is not None:
            secondary = EmotionLayer(
                emotion=output["secondary_emotion"],
                weight=output["secondary_weight"],
                score=output["secondary_score"],
            )

        accent = None
        if output.get("accent_emotion") is not None:
            accent = EmotionLayer(
                emotion=output["accent_emotion"],
                weight=output["accent_weight"],
                score=output["accent_score"],
            )

        return cls(
            primary=primary,
            secondary=secondary,
            accent=accent,
            method=output.get("method", "unknown"),
        )


# ──────────────────────────────────────────────────────────────
# Evaluation Verdict Schemas
# ──────────────────────────────────────────────────────────────
class EvaluationVerdict(BaseModel):
    """Per-scene evaluation result across all layers."""
    scene_id: str
    schema_check: Verdict = Verdict.PASS
    confidence_check: Verdict = Verdict.PASS
    consistency_check: Verdict = Verdict.PASS
    drift_status: Verdict = Verdict.PASS
    conflict_check: Verdict = Verdict.PASS
    coherence_score: float = Field(1.0, ge=0.0, le=1.0)
    stability_check: Verdict = Verdict.PASS
    narrative_validation: Verdict = Verdict.PASS
    human_alignment_trend: TrendDirection = TrendDirection.STABLE
    final_verdict: Verdict = Verdict.PASS

    # Detailed breakdown for debugging
    details: Dict[str, Any] = Field(default_factory=dict)

    def compute_final_verdict(self) -> Verdict:
        """
        Compute the final verdict based on all checks.

        Rules:
          - Any critical FAIL → FAIL
          - Coherence < 0.6 → FAIL
          - Any WARN → WARN
          - Otherwise → PASS
        """
        all_checks = [
            self.schema_check,
            self.confidence_check,
            self.conflict_check,
            self.stability_check,
        ]

        # Critical failures
        if any(c == Verdict.FAIL for c in all_checks):
            self.final_verdict = Verdict.FAIL
            return self.final_verdict

        if self.coherence_score < 0.6:
            self.final_verdict = Verdict.FAIL
            return self.final_verdict

        # Warnings
        all_with_warn = all_checks + [
            self.consistency_check,
            self.drift_status,
            self.narrative_validation,
        ]
        if any(c == Verdict.WARN for c in all_with_warn):
            self.final_verdict = Verdict.WARN
            return self.final_verdict

        if self.coherence_score < 0.8:
            self.final_verdict = Verdict.WARN
            return self.final_verdict

        self.final_verdict = Verdict.PASS
        return self.final_verdict


class EvaluationReport(BaseModel):
    """Full pipeline evaluation report."""
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    total_scenes: int = 0
    verdicts: List[EvaluationVerdict] = Field(default_factory=list)
    pass_count: int = 0
    warn_count: int = 0
    fail_count: int = 0
    overall_verdict: Verdict = Verdict.PASS
    can_proceed: bool = True

    def compute_summary(self) -> None:
        """Compute summary counts and overall verdict."""
        self.total_scenes = len(self.verdicts)
        self.pass_count = sum(1 for v in self.verdicts if v.final_verdict == Verdict.PASS)
        self.warn_count = sum(1 for v in self.verdicts if v.final_verdict == Verdict.WARN)
        self.fail_count = sum(1 for v in self.verdicts if v.final_verdict == Verdict.FAIL)

        if self.fail_count > 0:
            self.overall_verdict = Verdict.FAIL
            self.can_proceed = False
        elif self.warn_count > 0:
            self.overall_verdict = Verdict.WARN
            self.can_proceed = True  # Warnings allow proceeding
        else:
            self.overall_verdict = Verdict.PASS
            self.can_proceed = True


# ──────────────────────────────────────────────────────────────
# Human Feedback Schema
# ──────────────────────────────────────────────────────────────
class HumanFeedbackEntry(BaseModel):
    """Single human feedback entry for a scene."""
    scene_id: str
    emotion_distribution: Dict[str, Any]
    generated_cue: Dict[str, Any]
    human_modified_cue: Optional[Dict[str, Any]] = None
    human_rating: int = Field(ge=1, le=5)
    confidence_scores: Dict[str, float] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    notes: Optional[str] = None
