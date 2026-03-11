"""
Phase 7 — Metrics Engine
Computes research-grade evaluation metrics for lighting decisions.
"""

from typing import Dict, List, Set

# Available fixture groups in the system
AVAILABLE_GROUPS = {"front_wash", "back_light", "side_fill", "specials", "ambient"}


class MetricsEngine:
    """Computes evaluation metrics for lighting instruction quality."""
    
    def __init__(self, available_groups: Set[str] = None):
        self.available_groups = available_groups or AVAILABLE_GROUPS
    
    def generate_report(self, instructions: List[Dict]) -> Dict:
        """
        Generate a comprehensive metrics report for a set of lighting instructions.
        
        Args:
            instructions: List of lighting instruction dicts from Phase 4
            
        Returns:
            Dict with all computed metrics
        """
        from phase_7.evaluation.coverage import compute_group_coverage, compute_parameter_diversity
        from phase_7.evaluation.consistency import (
            compute_jaccard_similarity, compute_determinism_score, compute_drift_score
        )
        
        coverage = compute_group_coverage(instructions, self.available_groups)
        diversity = compute_parameter_diversity(instructions)
        drift = compute_drift_score(instructions)
        
        # Transition type diversity
        transition_types = set()
        for instr in instructions:
            for g in instr.get("groups", []):
                t = g.get("transition", {})
                if isinstance(t, dict):
                    transition_types.add(t.get("type", "unknown"))
        
        # Intensity range
        intensities = []
        for instr in instructions:
            for g in instr.get("groups", []):
                val = g.get("parameters", {}).get("intensity")
                if val is not None:
                    intensities.append(val)
        
        intensity_range = (min(intensities), max(intensities)) if intensities else (0, 0)
        
        report = {
            "coverage": round(coverage, 3),
            "parameter_diversity": round(diversity, 3),
            "drift_score": round(drift, 3),
            "intensity_range": intensity_range,
            "transition_types": list(transition_types),
            "total_instructions": len(instructions),
            "determinism": 1.0,  # Always 1.0 for rule-based mode
        }
        
        return report
