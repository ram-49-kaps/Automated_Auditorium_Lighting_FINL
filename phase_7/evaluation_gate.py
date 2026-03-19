"""
Phase 7 — Evaluation Gate
===========================
Main orchestrator that runs all 3 evaluation layers and produces
a per-scene EvaluationVerdict + overall EvaluationReport.

Execution proceeds ONLY if:
  - No critical FAIL
  - Coherence ≥ 0.6
  - Primary confidence ≥ 0.5
"""
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

from .schemas_v2 import (
    Verdict,
    TrendDirection,
    EvaluationVerdict,
    EvaluationReport,
)
from .evaluation.structural import (
    validate_schema,
    validate_emotion_hierarchy,
    validate_confidence,
)
from .evaluation.conflict import run_all_conflict_checks
from .evaluation.coherence import (
    compute_scene_coherence,
    validate_narrative_arc,
)
from .evaluation.transition import validate_sequence_transitions
from .evaluation.consistency import (
    compute_drift_with_threshold,
    compute_emotion_cue_variance,
)
from .evaluation.stability import (
    compute_cross_run_stability,
    compute_human_alignment_trend,
)


class EvaluationGate:
    """
    Orchestrates the full 3-layer evaluation pipeline.

    Usage:
        gate = EvaluationGate()
        report = gate.evaluate_pipeline(scenes, instructions, emotion_dists)
        if report.can_proceed:
            print("Pipeline output approved!")
        else:
            print("Pipeline output REJECTED. See report for details.")
    """

    def __init__(
        self,
        output_dir: Optional[str] = None,
        feedback_entries: Optional[List[dict]] = None,
    ):
        """
        Initialize the evaluation gate.

        Args:
            output_dir: Optional path to save evaluation reports.
            feedback_entries: Optional list of human feedback dicts
                             for alignment trend computation.
        """
        self._output_dir = Path(output_dir) if output_dir else None
        self._feedback_entries = feedback_entries or []

    def evaluate_scene(
        self,
        instruction: Dict[str, Any],
        emotion_dist: Dict[str, Any],
    ) -> EvaluationVerdict:
        """
        Run all evaluation layers on a single scene.

        Args:
            instruction: LightingInstruction dict.
            emotion_dist: Multi-emotion distribution dict.

        Returns:
            EvaluationVerdict for this scene.
        """
        scene_id = instruction.get("scene_id", "unknown")
        verdict = EvaluationVerdict(scene_id=scene_id)
        details: Dict[str, Any] = {}

        # ── Layer 1: Structural Validation ──────────────────────
        schema_v, schema_issues = validate_schema(instruction)
        verdict.schema_check = Verdict(schema_v)
        details["schema_issues"] = schema_issues

        hierarchy_v, hierarchy_issues = validate_emotion_hierarchy(emotion_dist)
        details["hierarchy_issues"] = hierarchy_issues

        conf_v, conf_issues = validate_confidence(emotion_dist)
        verdict.confidence_check = Verdict(conf_v)
        details["confidence_issues"] = conf_issues

        # If hierarchy fails, roll it into schema_check
        if hierarchy_v == "FAIL":
            verdict.schema_check = Verdict.FAIL
            details["schema_issues"].extend(hierarchy_issues)
        elif hierarchy_v == "WARN" and verdict.schema_check != Verdict.FAIL:
            verdict.schema_check = Verdict.WARN

        # ── Layer 3: Conflict & Coherence ───────────────────────
        conflict_result = run_all_conflict_checks(emotion_dist, instruction)
        conflict_overall = conflict_result["overall"]
        verdict.conflict_check = Verdict(conflict_overall)
        details["conflict_details"] = conflict_result

        coherence_score, coherence_v = compute_scene_coherence(
            emotion_dist, instruction, conflict_result
        )
        verdict.coherence_score = coherence_score
        details["coherence_verdict"] = coherence_v

        # ── Human alignment trend ──────────────────────────────
        if self._feedback_entries:
            trend_result = compute_human_alignment_trend(self._feedback_entries)
            trend_str = trend_result.get("trend", "stable")
            verdict.human_alignment_trend = TrendDirection(trend_str)
            details["human_alignment"] = trend_result
        else:
            verdict.human_alignment_trend = TrendDirection.STABLE

        verdict.details = details

        # Compute final verdict
        verdict.compute_final_verdict()

        return verdict

    def evaluate_pipeline(
        self,
        instructions: List[Dict[str, Any]],
        emotion_dists: List[Dict[str, Any]],
        runs: Optional[List[List[dict]]] = None,
    ) -> EvaluationReport:
        """
        Run full evaluation on an entire pipeline output.

        Args:
            instructions: List of LightingInstruction dicts.
            emotion_dists: List of multi-emotion distribution dicts
                          (must be same length as instructions).
            runs: Optional list of multiple runs for stability check.

        Returns:
            EvaluationReport with all verdicts and overall result.
        """
        report = EvaluationReport()

        # Evaluate each scene individually
        for i, instruction in enumerate(instructions):
            if i < len(emotion_dists):
                emotion_dist = emotion_dists[i]
            else:
                emotion_dist = {
                    "primary_emotion": "neutral",
                    "primary_weight": 1.0,
                    "primary_score": 1.0,
                }

            verdict = self.evaluate_scene(instruction, emotion_dist)
            report.verdicts.append(verdict)

        # ── Layer 2: Sequence-level metrics ─────────────────────

        # Drift check across sequence
        if len(instructions) >= 2:
            drift_v, drift_score, drift_issues = compute_drift_with_threshold(
                instructions
            )
            for v in report.verdicts:
                v.drift_status = Verdict(drift_v)
                v.details["drift_score"] = drift_score
                v.details["drift_issues"] = drift_issues

        # Emotion-cue consistency
        if len(instructions) >= 2:
            consistency_v, consistency_details = compute_emotion_cue_variance(
                instructions
            )
            for v in report.verdicts:
                v.consistency_check = Verdict(consistency_v)
                v.details["consistency_details"] = consistency_details

        # Narrative arc validation
        if len(instructions) >= 2:
            narrative_v, narrative_issues = validate_narrative_arc(instructions)
            for v in report.verdicts:
                v.narrative_validation = Verdict(narrative_v)
                v.details["narrative_issues"] = narrative_issues

        # Transition smoothness (sequence-level)
        if len(instructions) >= 2:
            trans_v, trans_issues = validate_sequence_transitions(instructions)
            if trans_v == "FAIL":
                for v in report.verdicts:
                    if v.conflict_check != Verdict.FAIL:
                        v.conflict_check = Verdict(trans_v)
                    v.details["transition_issues"] = trans_issues
            elif trans_issues:
                for v in report.verdicts:
                    v.details["transition_issues"] = trans_issues

        # Stability check (cross-run)
        if runs and len(runs) >= 2:
            stability_result = compute_cross_run_stability(runs)
            stability_score = stability_result.get("stability_score", 1.0)
            if stability_score < 0.9:
                for v in report.verdicts:
                    v.stability_check = Verdict.FAIL
                    v.details["stability_result"] = stability_result
            else:
                for v in report.verdicts:
                    v.stability_check = Verdict.PASS
                    v.details["stability_result"] = stability_result

        # Recompute final verdicts after sequence-level updates
        for v in report.verdicts:
            v.compute_final_verdict()

        # Compute summary
        report.compute_summary()

        # Save report if output_dir is set
        if self._output_dir:
            self._save_report(report)

        return report

    def should_proceed(self, report: EvaluationReport) -> bool:
        """
        Determine if pipeline execution should proceed.

        Rules:
          - No critical FAIL
          - Coherence ≥ 0.6
          - Primary confidence ≥ 0.5 (already checked per-scene)

        Args:
            report: EvaluationReport from evaluate_pipeline().

        Returns:
            True if pipeline can proceed.
        """
        return report.can_proceed

    def _save_report(self, report: EvaluationReport) -> Path:
        """Save evaluation report to JSON file."""
        if self._output_dir:
            self._output_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = self._output_dir / f"evaluation_report_{timestamp}.json"

            report_dict = report.model_dump()
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(report_dict, f, indent=2, default=str)

            return filepath
        return Path()

    def get_verdict_summary(self, report: EvaluationReport) -> str:
        """
        Get a human-readable summary of the evaluation report.

        Args:
            report: EvaluationReport instance.

        Returns:
            Formatted summary string.
        """
        lines = [
            "=" * 60,
            "EVALUATION GATE — SUMMARY",
            "=" * 60,
            f"Total scenes:  {report.total_scenes}",
            f"PASS:          {report.pass_count}",
            f"WARN:          {report.warn_count}",
            f"FAIL:          {report.fail_count}",
            f"Overall:       {report.overall_verdict.value}",
            f"Can proceed:   {'YES' if report.can_proceed else 'NO'}",
            "=" * 60,
        ]

        if report.fail_count > 0:
            lines.append("\n⚠ FAILED SCENES:")
            for v in report.verdicts:
                if v.final_verdict == Verdict.FAIL:
                    lines.append(f"  [{v.scene_id}]")
                    details = v.details
                    for key in ("schema_issues", "confidence_issues",
                                "conflict_details", "transition_issues"):
                        val = details.get(key)
                        if val:
                            if isinstance(val, list) and val:
                                for issue in val:
                                    lines.append(f"    - {issue}")
                            elif isinstance(val, dict):
                                issues = val.get("all_issues", [])
                                for issue in issues:
                                    lines.append(f"    - {issue}")

        return "\n".join(lines)
